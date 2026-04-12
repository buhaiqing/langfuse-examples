"""
Bidirectional synchronization and collaboration mode for human-agent interaction
Implements co-pilot mode, session takeover, and real-time state sync
"""

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.logging_config import LogCategory, get_logger
from core.tracing import create_span, score_trace

logger = get_logger(LogCategory.ESCALATION)


class CollaborationMode(str, Enum):
    """Collaboration modes between agent and human"""

    AUTO = "auto"  # Agent handles automatically
    COPILOT = "copilot"  # Agent suggests, human approves
    SUPERVISION = "supervision"  # Human monitors, can intervene
    TAKEOVER = "takeover"  # Human takes full control


class MessageType(str, Enum):
    """Message types for bidirectional communication"""

    # Agent → Human
    STATUS_UPDATE = "status_update"
    SUGGESTION = "suggestion"
    CONFIRMATION_REQUEST = "confirmation_request"
    CONTEXT_SYNC = "context_sync"

    # Human → Agent
    APPROVAL = "approval"
    REJECTION = "rejection"
    MODIFICATION = "modification"
    COMMAND = "command"
    TAKEOVER_REQUEST = "takeover_request"
    RELEASE_CONTROL = "release_control"

    # System
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class AgentStatus:
    """Agent current status"""

    session_id: str
    mode: CollaborationMode
    current_intent: Optional[str] = None
    confidence: float = 0.0
    active_tools: List[str] = field(default_factory=list)
    pending_actions: List[Dict[str, Any]] = field(default_factory=list)
    last_action_time: Optional[str] = None
    processing_time_ms: Optional[float] = None


@dataclass
class SuggestedAction:
    """Action suggested by agent for human approval"""

    action_id: str
    action_type: str  # e.g., "send_response", "call_tool", "escalate"
    payload: Dict[str, Any]
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HumanCommand:
    """Command from human to agent"""

    command_type: str  # e.g., "approve", "reject", "modify", "override"
    target_action_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SyncMessage:
    """Unified message structure for bidirectional sync"""

    message_id: str
    message_type: MessageType
    sender: str  # "agent" or "human"
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CollaborationManager:
    """
    Manages bidirectional synchronization and collaboration between agent and human.

    Features:
    - Real-time status updates (Agent → Human)
    - Command processing (Human → Agent)
    - Co-pilot mode with suggestion/approval workflow
    - Session takeover and release
    - Context synchronization
    - Full Langfuse tracing
    """

    def __init__(self, websocket_client: Any, escalation_manager: Any):
        """
        Initialize collaboration manager.

        Args:
            websocket_client: WebSocketClient instance for communication
            escalation_manager: EscalationManager instance for session control
        """
        self.websocket_client = websocket_client
        self.escalation_manager = escalation_manager

        # Session collaboration states
        self.collaboration_states: Dict[str, CollaborationMode] = {}
        self.pending_suggestions: Dict[str, List[SuggestedAction]] = {}
        self.command_handlers: Dict[str, Callable] = {}

        # Register default command handlers
        self._register_default_handlers()

        logger.info("CollaborationManager initialized")

    def _register_default_handlers(self):
        """Register default command handlers"""
        self.command_handlers = {
            "approve": self._handle_approve,
            "reject": self._handle_reject,
            "modify": self._handle_modify,
            "override": self._handle_override,
            "takeover": self._handle_takeover,
            "release": self._handle_release,
        }

    async def initialize_session(
        self, session_id: str, mode: CollaborationMode = CollaborationMode.AUTO
    ) -> None:
        """
        Initialize collaboration state for a session.

        Args:
            session_id: Session identifier
            mode: Initial collaboration mode
        """
        self.collaboration_states[session_id] = mode
        self.pending_suggestions[session_id] = []

        logger.info(f"Session {session_id} initialized in {mode.value} mode")

    async def push_status_update(
        self,
        session_id: str,
        intent: Optional[str] = None,
        confidence: float = 0.0,
        active_tools: Optional[List[str]] = None,
        processing_time_ms: Optional[float] = None,
    ) -> None:
        """
        Push agent status update to human operator.

        Args:
            session_id: Session identifier
            intent: Current recognized intent
            confidence: Confidence score
            active_tools: Currently active tools
            processing_time_ms: Processing time in milliseconds
        """
        with create_span("push_status_update", input_data={
            "session_id": session_id,
            "intent": intent,
        }) as span:
            mode = self.collaboration_states.get(session_id, CollaborationMode.AUTO)

            status = AgentStatus(
                session_id=session_id,
                mode=mode,
                current_intent=intent,
                confidence=confidence,
                active_tools=active_tools or [],
                processing_time_ms=processing_time_ms,
                last_action_time=datetime.now().isoformat(),
            )

            message = SyncMessage(
                message_id=f"status_{session_id}_{int(time.time())}",
                message_type=MessageType.STATUS_UPDATE,
                sender="agent",
                session_id=session_id,
                data=asdict(status),
            )

            await self._send_message(session_id, message)

            span.add_event(
                "status_sent",
                output_data={"mode": mode.value, "intent": intent},
            )

            logger.debug(
                f"Status update sent for session {session_id}: "
                f"intent={intent}, confidence={confidence:.2f}"
            )

    async def suggest_action(
        self,
        session_id: str,
        action_type: str,
        payload: Dict[str, Any],
        confidence: float,
        reasoning: str,
    ) -> str:
        """
        Suggest an action for human approval (Co-pilot mode).

        Args:
            session_id: Session identifier
            action_type: Type of action (e.g., "send_response")
            payload: Action payload/data
            confidence: Confidence score
            reasoning: Explanation for the suggestion

        Returns:
            Action ID for tracking
        """
        with create_span("suggest_action", input_data={
            "session_id": session_id,
            "action_type": action_type,
        }) as span:
            mode = self.collaboration_states.get(session_id, CollaborationMode.AUTO)

            if mode != CollaborationMode.COPILOT:
                logger.warning(
                    f"Suggestion sent but session not in co-pilot mode: {session_id}"
                )

            action_id = f"action_{session_id}_{int(time.time())}"

            suggestion = SuggestedAction(
                action_id=action_id,
                action_type=action_type,
                payload=payload,
                confidence=confidence,
                reasoning=reasoning,
            )

            # Store pending suggestion
            if session_id not in self.pending_suggestions:
                self.pending_suggestions[session_id] = []
            self.pending_suggestions[session_id].append(suggestion)

            message = SyncMessage(
                message_id=f"suggest_{action_id}",
                message_type=MessageType.SUGGESTION,
                sender="agent",
                session_id=session_id,
                data=asdict(suggestion),
            )

            await self._send_message(session_id, message)

            span.add_event(
                "suggestion_sent",
                output_data={
                    "action_id": action_id,
                    "confidence": confidence,
                },
            )

            logger.info(
                f"Action suggested for session {session_id}: {action_id} "
                f"(confidence={confidence:.2f})"
            )

            return action_id

    async def request_confirmation(
        self,
        session_id: str,
        action_description: str,
        options: List[Dict[str, Any]],
    ) -> str:
        """
        Request human confirmation for a critical action.

        Args:
            session_id: Session identifier
            action_description: Description of the action requiring confirmation
            options: Available options for the human to choose

        Returns:
            Confirmation request ID
        """
        with create_span("request_confirmation", input_data={
            "session_id": session_id,
            "options_count": len(options),
        }) as span:
            request_id = f"confirm_{session_id}_{int(time.time())}"

            message = SyncMessage(
                message_id=request_id,
                message_type=MessageType.CONFIRMATION_REQUEST,
                sender="agent",
                session_id=session_id,
                data={
                    "request_id": request_id,
                    "description": action_description,
                    "options": options,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            await self._send_message(session_id, message)

            span.add_event(
                "confirmation_requested",
                output_data={"request_id": request_id},
            )

            logger.info(f"Confirmation requested for session {session_id}: {request_id}")

            return request_id

    async def sync_context(
        self,
        session_id: str,
        conversation_history: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Sync full context to human operator.

        Args:
            session_id: Session identifier
            conversation_history: Recent conversation turns
            user_profile: User profile information
            metadata: Additional context metadata
        """
        with create_span("sync_context", input_data={
            "session_id": session_id,
            "history_length": len(conversation_history),
        }) as span:
            message = SyncMessage(
                message_id=f"context_{session_id}_{int(time.time())}",
                message_type=MessageType.CONTEXT_SYNC,
                sender="agent",
                session_id=session_id,
                data={
                    "conversation_history": conversation_history[-10:],  # Last 10 turns
                    "user_profile": user_profile,
                    "metadata": metadata,
                    "synced_at": datetime.now().isoformat(),
                },
            )

            await self._send_message(session_id, message)

            span.add_event(
                "context_synced",
                output_data={"history_turns": len(conversation_history)},
            )

            logger.debug(f"Context synced for session {session_id}")

    async def handle_human_command(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process command received from human operator.

        Args:
            session_id: Session identifier
            command_data: Command data from human

        Returns:
            Command execution result
        """
        with create_span("handle_human_command", input_data={
            "session_id": session_id,
            "command_type": command_data.get("command_type"),
        }) as span:
            try:
                command = HumanCommand(
                    command_type=command_data["command_type"],
                    target_action_id=command_data.get("target_action_id"),
                    payload=command_data.get("payload"),
                    reason=command_data.get("reason"),
                )

                handler = self.command_handlers.get(command.command_type)

                if not handler:
                    raise ValueError(f"Unknown command type: {command.command_type}")

                result = await handler(session_id, command)

                span.add_event(
                    "command_executed",
                    output_data={
                        "command_type": command.command_type,
                        "success": True,
                    },
                )

                score_trace("human_command_success_rate", 1.0)

                logger.info(
                    f"Command executed for session {session_id}: "
                    f"{command.command_type}"
                )

                return {"status": "success", "result": result}

            except Exception as e:
                logger.error(f"Failed to execute command: {e}")
                span.end(output_data={"error": str(e)})

                score_trace("human_command_success_rate", 0.0)

                return {"status": "error", "error": str(e)}

    async def _handle_approve(self, session_id: str, command: HumanCommand) -> Dict[str, Any]:
        """Handle approval command"""
        action_id = command.target_action_id

        # Remove from pending suggestions
        if session_id in self.pending_suggestions:
            self.pending_suggestions[session_id] = [
                s for s in self.pending_suggestions[session_id]
                if s.action_id != action_id
            ]

        # Send approval acknowledgment
        ack_message = SyncMessage(
            message_id=f"ack_{action_id}",
            message_type=MessageType.APPROVAL,
            sender="agent",
            session_id=session_id,
            data={"action_id": action_id, "status": "approved"},
        )
        await self._send_message(session_id, ack_message)

        return {"action_id": action_id, "status": "approved"}

    async def _handle_reject(self, session_id: str, command: HumanCommand) -> Dict[str, Any]:
        """Handle rejection command"""
        action_id = command.target_action_id

        # Remove from pending suggestions
        if session_id in self.pending_suggestions:
            self.pending_suggestions[session_id] = [
                s for s in self.pending_suggestions[session_id]
                if s.action_id != action_id
            ]

        # Send rejection acknowledgment
        ack_message = SyncMessage(
            message_id=f"ack_{action_id}",
            message_type=MessageType.REJECTION,
            sender="agent",
            session_id=session_id,
            data={
                "action_id": action_id,
                "status": "rejected",
                "reason": command.reason,
            },
        )
        await self._send_message(session_id, ack_message)

        return {"action_id": action_id, "status": "rejected"}

    async def _handle_modify(self, session_id: str, command: HumanCommand) -> Dict[str, Any]:
        """Handle modification command"""
        action_id = command.target_action_id
        modified_payload = command.payload

        # Update the suggestion with modifications
        if session_id in self.pending_suggestions:
            for suggestion in self.pending_suggestions[session_id]:
                if suggestion.action_id == action_id:
                    suggestion.payload.update(modified_payload or {})
                    break

        # Send modification acknowledgment
        ack_message = SyncMessage(
            message_id=f"ack_{action_id}",
            message_type=MessageType.MODIFICATION,
            sender="agent",
            session_id=session_id,
            data={
                "action_id": action_id,
                "status": "modified",
                "modifications": modified_payload,
            },
        )
        await self._send_message(session_id, ack_message)

        return {
            "action_id": action_id,
            "status": "modified",
            "modifications": modified_payload,
        }

    async def _handle_override(self, session_id: str, command: HumanCommand) -> Dict[str, Any]:
        """Handle override command (human provides alternative action)"""
        override_payload = command.payload

        # Execute the override action
        # This would integrate with the dialogue manager to execute human's action
        logger.info(
            f"Override executed for session {session_id}: {override_payload}"
        )

        return {"status": "overridden", "action": override_payload}

    async def _handle_takeover(self, session_id: str, command: HumanCommand) -> Dict[str, Any]:
        """Handle session takeover request"""
        # Change collaboration mode to TAKEOVER
        self.collaboration_states[session_id] = CollaborationMode.TAKEOVER

        # Notify escalation manager
        if hasattr(self.escalation_manager, 'set_session_mode'):
            await self.escalation_manager.set_session_mode(
                session_id, "human_control"
            )

        # Send takeover confirmation
        ack_message = SyncMessage(
            message_id=f"takeover_{session_id}_{int(time.time())}",
            message_type=MessageType.TAKEOVER_REQUEST,
            sender="agent",
            session_id=session_id,
            data={
                "status": "takeover_confirmed",
                "mode": CollaborationMode.TAKEOVER.value,
                "timestamp": datetime.now().isoformat(),
            },
        )
        await self._send_message(session_id, ack_message)

        logger.info(f"Session {session_id} taken over by human")

        return {"status": "takeover_confirmed", "mode": "human_control"}

    async def _handle_release(self, session_id: str, command: HumanCommand) -> Dict[str, Any]:
        """Handle release control command (return to agent)"""
        # Change collaboration mode back to AUTO or COPILOT
        self.collaboration_states[session_id] = CollaborationMode.AUTO

        # Notify escalation manager
        if hasattr(self.escalation_manager, 'set_session_mode'):
            await self.escalation_manager.set_session_mode(
                session_id, "agent_control"
            )

        # Send release confirmation
        ack_message = SyncMessage(
            message_id=f"release_{session_id}_{int(time.time())}",
            message_type=MessageType.RELEASE_CONTROL,
            sender="agent",
            session_id=session_id,
            data={
                "status": "control_released",
                "mode": CollaborationMode.AUTO.value,
                "timestamp": datetime.now().isoformat(),
            },
        )
        await self._send_message(session_id, ack_message)

        logger.info(f"Session {session_id} control released back to agent")

        return {"status": "control_released", "mode": "agent_control"}

    async def set_collaboration_mode(
        self, session_id: str, mode: CollaborationMode
    ) -> None:
        """
        Set collaboration mode for a session.

        Args:
            session_id: Session identifier
            mode: New collaboration mode
        """
        old_mode = self.collaboration_states.get(session_id, CollaborationMode.AUTO)
        self.collaboration_states[session_id] = mode

        logger.info(
            f"Collaboration mode changed for session {session_id}: "
            f"{old_mode.value} → {mode.value}"
        )

        # Notify human operator of mode change
        message = SyncMessage(
            message_id=f"mode_change_{session_id}_{int(time.time())}",
            message_type=MessageType.STATUS_UPDATE,
            sender="agent",
            session_id=session_id,
            data={
                "mode_changed": True,
                "old_mode": old_mode.value,
                "new_mode": mode.value,
            },
        )
        await self._send_message(session_id, message)

    async def get_pending_suggestions(self, session_id: str) -> List[SuggestedAction]:
        """
        Get pending suggestions for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of pending suggestions
        """
        return self.pending_suggestions.get(session_id, [])

    async def _send_message(self, session_id: str, message: SyncMessage) -> None:
        """
        Send message through WebSocket client.

        Args:
            session_id: Session identifier
            message: Message to send
        """
        try:
            message_dict = asdict(message)
            await self.websocket_client.send_message(session_id, message_dict)
        except Exception as e:
            logger.error(f"Failed to send message for session {session_id}: {e}")
            raise

    def get_collaboration_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get current collaboration state for a session.

        Args:
            session_id: Session identifier

        Returns:
            Collaboration state dict
        """
        mode = self.collaboration_states.get(session_id, CollaborationMode.AUTO)
        pending = self.pending_suggestions.get(session_id, [])

        return {
            "session_id": session_id,
            "mode": mode.value,
            "pending_suggestions_count": len(pending),
            "pending_suggestions": [asdict(s) for s in pending],
        }

    async def cleanup_session(self, session_id: str) -> None:
        """
        Cleanup collaboration state for a session.

        Args:
            session_id: Session identifier
        """
        self.collaboration_states.pop(session_id, None)
        self.pending_suggestions.pop(session_id, None)

        logger.debug(f"Collaboration state cleaned up for session {session_id}")
