"""
Queue manager for human agent escalation
Handles priority queuing, wait time estimation, and context packaging
"""

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from core.logging_config import LogCategory, get_logger
from core.tracing import add_event, create_span, score_trace

logger = get_logger(LogCategory.ESCALATION)


@dataclass
class EscalationContext:
    """Complete context for escalation to human agent"""

    session_id: str
    user_id: str
    user_profile: Dict[str, Any]
    dialogue_history: List[Dict[str, Any]]
    collected_slots: Dict[str, Any]
    attempted_solutions: List[str]
    escalation_reason: str
    sentiment_score: float
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_profile": self.user_profile,
            "dialogue_history": self.dialogue_history,
            "collected_slots": self.collected_slots,
            "attempted_solutions": self.attempted_solutions,
            "escalation_reason": self.escalation_reason,
            "sentiment_score": self.sentiment_score,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationContext":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            user_profile=data.get("user_profile", {}),
            dialogue_history=data.get("dialogue_history", []),
            collected_slots=data.get("collected_slots", {}),
            attempted_solutions=data.get("attempted_solutions", []),
            escalation_reason=data.get("escalation_reason", "unknown"),
            sentiment_score=data.get("sentiment_score", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]),
            priority=data.get("priority", 0),
        )


@dataclass
class QueueEntry:
    """Entry in the escalation queue"""

    queue_id: str
    session_id: str
    context: EscalationContext
    position: int
    estimated_wait_time: int
    created_at: datetime = field(default_factory=datetime.now)
    assigned_agent: Optional[str] = None
    status: str = "waiting"

    def __lt__(self, other: "QueueEntry") -> bool:
        if self.context.priority != other.context.priority:
            return self.context.priority > other.context.priority
        return self.created_at < other.created_at


class QueueManager:
    """
    Manages escalation queue with priority scheduling and wait time estimation.
    Features:
    - Priority-based queue (VIP customers get priority)
    - Dynamic wait time estimation
    - Agent assignment
    - Full Langfuse tracing
    """

    def __init__(
        self,
        max_queue_size: int = 100,
        base_wait_time: int = 120,
        agent_count: int = 5,
    ):
        self.max_queue_size = max_queue_size
        self.base_wait_time = base_wait_time
        self.agent_count = agent_count

        self._queue: List[QueueEntry] = []
        self._queue_map: Dict[str, QueueEntry] = {}
        self._agent_status: Dict[str, str] = {}
        self._completed_count: int = 0
        self._lock = asyncio.Lock()

        for i in range(agent_count):
            self._agent_status[f"agent_{i}"] = "available"

        logger.info(f"QueueManager initialized with {agent_count} agents")

    async def enqueue(
        self,
        context: EscalationContext,
    ) -> str:
        """
        Add escalation request to queue.

        Args:
            context: Escalation context

        Returns:
            Queue ID
        """
        with create_span("queue_enqueue", input_data={"priority": context.priority}) as span:
            async with self._lock:
                if len(self._queue) >= self.max_queue_size:
                    raise ValueError("Queue is full")

                queue_id = str(uuid4())
                position = self._calculate_position(context.priority)
                wait_time = self._estimate_wait_time(position)

                entry = QueueEntry(
                    queue_id=queue_id,
                    session_id=context.session_id,
                    context=context,
                    position=position,
                    estimated_wait_time=wait_time,
                )

                heapq.heappush(self._queue, entry)
                self._queue_map[queue_id] = entry

                self._update_positions()

                span.add_event(
                    "entry_queued",
                    output_data={
                        "queue_id": queue_id,
                        "position": position,
                        "estimated_wait_time": wait_time,
                    },
                )

                score_trace("queue_position", position)
                score_trace("estimated_wait_time_seconds", wait_time)

                logger.info(
                    f"Queued escalation {queue_id} at position {position}, "
                    f"wait time: {wait_time}s"
                )

                return queue_id

    async def dequeue(self) -> Optional[QueueEntry]:
        """
        Remove and return highest priority entry from queue.

        Returns:
            QueueEntry or None if queue is empty
        """
        with create_span("queue_dequeue") as span:
            async with self._lock:
                if not self._queue:
                    return None

                entry = heapq.heappop(self._queue)
                del self._queue_map[entry.queue_id]

                self._update_positions()
                self._completed_count += 1

                span.add_event(
                    "entry_dequeued",
                    output_data={
                        "queue_id": entry.queue_id,
                        "session_id": entry.session_id,
                    },
                )

                logger.info(f"Dequeued {entry.queue_id} for assignment")

                return entry

    async def get_position(self, queue_id: str) -> int:
        """
        Get current position in queue.

        Args:
            queue_id: Queue entry ID

        Returns:
            Position (1-based), or -1 if not found
        """
        async with self._lock:
            entry = self._queue_map.get(queue_id)
            if not entry:
                return -1
            return entry.position

    async def estimate_wait_time(self, queue_id: str) -> int:
        """
        Estimate wait time for a queue entry.

        Args:
            queue_id: Queue entry ID

        Returns:
            Estimated wait time in seconds
        """
        with create_span("queue_estimate_wait_time") as span:
            async with self._lock:
                entry = self._queue_map.get(queue_id)
                if not entry:
                    return 0

                position = entry.position
                wait_time = self._estimate_wait_time(position)

                entry.estimated_wait_time = wait_time

                span.add_event(
                    "wait_time_estimated",
                    output_data={"position": position, "wait_time": wait_time},
                )

                return wait_time

    async def assign_agent(self, queue_id: str, agent_id: str) -> bool:
        """
        Assign an agent to a queue entry.

        Args:
            queue_id: Queue entry ID
            agent_id: Agent identifier

        Returns:
            True if assignment successful
        """
        with create_span("queue_assign_agent", input_data={"agent_id": agent_id}) as span:
            async with self._lock:
                entry = self._queue_map.get(queue_id)
                if not entry:
                    return False

                if self._agent_status.get(agent_id) != "available":
                    logger.warning(f"Agent {agent_id} is not available")
                    return False

                entry.assigned_agent = agent_id
                entry.status = "assigned"
                self._agent_status[agent_id] = "busy"

                span.add_event(
                    "agent_assigned",
                    output_data={"queue_id": queue_id, "agent_id": agent_id},
                )

                logger.info(f"Assigned agent {agent_id} to queue {queue_id}")

                return True

    async def release_agent(self, agent_id: str) -> None:
        """
        Release an agent back to available pool.

        Args:
            agent_id: Agent identifier
        """
        async with self._lock:
            self._agent_status[agent_id] = "available"
            logger.debug(f"Released agent {agent_id}")

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get current queue statistics.

        Returns:
            Dictionary with queue stats
        """
        async with self._lock:
            available_agents = sum(
                1 for status in self._agent_status.values() if status == "available"
            )

            return {
                "queue_length": len(self._queue),
                "max_queue_size": self.max_queue_size,
                "available_agents": available_agents,
                "total_agents": len(self._agent_status),
                "completed_count": self._completed_count,
                "average_wait_time": self._calculate_average_wait_time(),
            }

    def _calculate_position(self, priority: int) -> int:
        """Calculate position based on priority and arrival time"""
        higher_priority = sum(
            1 for entry in self._queue if entry.context.priority > priority
        )
        return higher_priority + 1

    def _estimate_wait_time(self, position: int) -> int:
        """
        Estimate wait time based on position and agent availability.

        Args:
            position: Queue position

        Returns:
            Estimated wait time in seconds
        """
        available_agents = sum(
            1 for status in self._agent_status.values() if status == "available"
        )

        if available_agents == 0:
            available_agents = 1

        base_time_per_customer = self.base_wait_time
        estimated_time = (position * base_time_per_customer) // available_agents

        return min(estimated_time, 3600)

    def _calculate_average_wait_time(self) -> float:
        """Calculate average wait time for completed escalations"""
        if self._completed_count == 0:
            return 0.0
        total_wait = sum(
            entry.estimated_wait_time
            for entry in self._queue_map.values()
            if entry.status == "assigned"
        )
        return total_wait / max(self._completed_count, 1)

    def _update_positions(self) -> None:
        """Update positions for all queue entries"""
        sorted_queue = sorted(self._queue, key=lambda x: (x.context.priority, x.created_at))
        for i, entry in enumerate(sorted_queue):
            entry.position = i + 1


class ContextPackager:
    """
    Packages conversation context for handoff to human agent.
    Ensures complete and well-organized context transfer.
    """

    def __init__(self, max_history_length: int = 20):
        self.max_history_length = max_history_length

    def package_context(
        self,
        session_id: str,
        user_id: str,
        conversation_state: Any,
        escalation_reason: str,
        sentiment_score: float,
        priority: int = 0,
    ) -> EscalationContext:
        """
        Package complete context for escalation.

        Args:
            session_id: Session identifier
            user_id: User identifier
            conversation_state: Current conversation state
            escalation_reason: Reason for escalation
            sentiment_score: User sentiment score
            priority: Priority level

        Returns:
            EscalationContext object
        """
        with create_span("context_packaging") as span:
            dialogue_history = self._extract_dialogue_history(conversation_state)
            collected_slots = self._extract_slots(conversation_state)
            attempted_solutions = self._extract_attempted_solutions(conversation_state)
            user_profile = self._build_user_profile(conversation_state, user_id)

            context = EscalationContext(
                session_id=session_id,
                user_id=user_id,
                user_profile=user_profile,
                dialogue_history=dialogue_history,
                collected_slots=collected_slots,
                attempted_solutions=attempted_solutions,
                escalation_reason=escalation_reason,
                sentiment_score=sentiment_score,
                priority=priority,
            )

            span.add_event(
                "context_packaged",
                output_data={
                    "history_length": len(dialogue_history),
                    "slot_count": len(collected_slots),
                    "solutions_attempted": len(attempted_solutions),
                },
            )

            logger.info(f"Packaged context for session {session_id}")

            return context

    def _extract_dialogue_history(self, conversation_state: Any) -> List[Dict[str, Any]]:
        """Extract and format dialogue history"""
        history = getattr(conversation_state, "history", [])

        formatted_history = []
        for turn in history[-self.max_history_length :]:
            formatted_history.append({
                "role": turn.get("role", "user"),
                "content": turn.get("content", ""),
                "timestamp": turn.get("timestamp", ""),
            })

        return formatted_history

    def _extract_slots(self, conversation_state: Any) -> Dict[str, Any]:
        """Extract collected slots from conversation state"""
        slots = getattr(conversation_state, "collected_slots", {})
        return dict(slots)

    def _extract_attempted_solutions(self, conversation_state: Any) -> List[str]:
        """Extract list of attempted solutions"""
        attempted = getattr(conversation_state, "attempted_solutions", [])
        return list(attempted)

    def _build_user_profile(
        self, conversation_state: Any, user_id: str
    ) -> Dict[str, Any]:
        """Build user profile from conversation state"""
        profile = {
            "user_id": user_id,
            "intent": getattr(conversation_state, "intent", "unknown"),
            "turn_count": getattr(conversation_state, "turn_count", 0),
        }

        entities = getattr(conversation_state, "entities", {})
        profile.update(entities)

        return profile


def create_queue_manager(
    max_queue_size: int = 100,
    base_wait_time: int = 120,
    agent_count: int = 5,
) -> QueueManager:
    """
    Factory function to create queue manager.

    Args:
        max_queue_size: Maximum queue size
        base_wait_time: Base wait time per customer (seconds)
        agent_count: Number of available agents

    Returns:
        QueueManager instance
    """
    return QueueManager(
        max_queue_size=max_queue_size,
        base_wait_time=base_wait_time,
        agent_count=agent_count,
    )


def create_context_packager(
    max_history_length: int = 20,
) -> ContextPackager:
    """
    Factory function to create context packager.

    Args:
        max_history_length: Maximum dialogue history length

    Returns:
        ContextPackager instance
    """
    return ContextPackager(max_history_length=max_history_length)
