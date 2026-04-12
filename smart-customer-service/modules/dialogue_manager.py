"""
Dialogue state management module with Langfuse tracing
Maintains conversation context across multiple turns
"""

import time
from dataclasses import dataclass, field
from typing import Any

from core.scoring import score_dialogue_coherence, score_slot_completion_rate
from core.tracing import create_span


@dataclass
class ConversationState:
    """Represents the state of a conversation session"""

    session_id: str
    current_intent: str | None = None
    collected_slots: dict[str, Any] = field(default_factory=dict)
    dialogue_history: list[dict[str, str]] = field(default_factory=list)
    context_variables: dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    last_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class DialogueStateManager:
    """Manages conversation state with Langfuse tracing"""

    def __init__(self):
        # In production, use Redis or database for persistence
        self.state_store: dict[str, ConversationState] = {}

    async def update_state(
        self,
        session_id: str,
        user_input: str,
        bot_response: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationState:
        """
        Update conversation state with full Langfuse tracing

        Args:
            session_id: Session identifier
            user_input: User's message
            bot_response: Bot's response
            metadata: Additional metadata (extracted slots, context updates, etc.)

        Returns:
            Updated conversation state
        """
        metadata = metadata or {}

        # Get or create session state
        if session_id not in self.state_store:
            self.state_store[session_id] = ConversationState(session_id=session_id)

        state = self.state_store[session_id]

        # Create main span for state update
        with create_span(
            name="dialogue_state_update",
            input_data={"session_id": session_id, "turn_number": state.turn_count + 1},
            metadata={"current_intent": state.current_intent, "turn_count": state.turn_count},
        ) as main_span:

            # Step 1: Update dialogue history
            history_span = create_span(
                name="history_update",
                input_data={"user_message": user_input, "bot_response": bot_response},
            )

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            state.dialogue_history.append(
                {"role": "user", "content": user_input, "timestamp": timestamp}
            )
            state.dialogue_history.append(
                {"role": "assistant", "content": bot_response, "timestamp": timestamp}
            )

            # Keep only last 20 messages to manage context size
            if len(state.dialogue_history) > 20:
                state.dialogue_history = state.dialogue_history[-20:]

            history_span.end(
                output_data={"history_length": len(state.dialogue_history)},
                metadata={"max_history_length": 20},
            )

            # Step 2: Update slots
            slot_span = create_span(
                name="slot_accumulation",
                input_data={
                    "existing_slots": state.collected_slots,
                    "new_slots": metadata.get("extracted_slots", {}),
                },
            )

            new_slots = metadata.get("extracted_slots", {})
            state.collected_slots.update(new_slots)

            completion_rate = self._calculate_slot_completion(state)

            slot_span.end(
                output_data={
                    "updated_slots": state.collected_slots,
                    "completion_rate": completion_rate,
                }
            )

            # Score slot completion
            score_slot_completion_rate(
                completion_rate, comment=f"Slot completion after turn {state.turn_count + 1}"
            )

            # Step 3: Update context variables
            context_span = create_span(
                name="context_update",
                input_data={"context_updates": metadata.get("context_updates", {})},
            )

            context_updates = metadata.get("context_updates", {})
            state.context_variables.update(context_updates)

            # Update intent if provided
            if metadata.get("intent"):
                old_intent = state.current_intent
                state.current_intent = metadata["intent"]
                context_updates["intent_changed"] = old_intent != state.current_intent

            context_span.end(output_data={"current_context": state.context_variables})

            # Update turn count
            state.turn_count += 1

            # Calculate dialogue coherence
            coherence = self._evaluate_coherence(state)
            score_dialogue_coherence(coherence, comment=f"Turn {state.turn_count} coherence score")

            # Save state
            self.state_store[session_id] = state

            # Update main span
            main_span.end(
                output_data={
                    "turn_count": state.turn_count,
                    "intent": state.current_intent,
                    "slots_count": len(state.collected_slots),
                    "coherence": coherence,
                }
            )

            return state

    def get_state(self, session_id: str) -> ConversationState | None:
        """Get conversation state for a session"""
        return self.state_store.get(session_id)

    def clear_state(self, session_id: str):
        """Clear conversation state for a session"""
        if session_id in self.state_store:
            del self.state_store[session_id]

    def _calculate_slot_completion(self, state: ConversationState) -> float:
        """Calculate slot filling completion rate"""
        # Define required slots based on intent
        required_slots_map = {
            "api_error_troubleshooting": ["error_code"],
            "ticket_status_query": ["ticket_id"],
            "account_login_issue": ["account_type"],
        }

        required_slots = required_slots_map.get(state.current_intent, [])

        if not required_slots:
            return 1.0

        filled_count = sum(1 for slot in required_slots if slot in state.collected_slots)

        return filled_count / len(required_slots)

    def _evaluate_coherence(self, state: ConversationState) -> float:
        """Evaluate dialogue coherence (0-1)"""
        if state.turn_count == 0:
            return 1.0

        # Simple coherence metrics
        # 1. Check if conversation is progressing (not too many turns)
        turn_penalty = max(0, (state.turn_count - 10) * 0.05)

        # 2. Check if intent is stable
        intent_stability = 1.0  # Could track intent changes over time

        # 3. Check if slots are being filled progressively
        slot_progress = min(len(state.collected_slots) / 3.0, 1.0)

        # Weighted coherence score
        coherence = 0.4 * (1.0 - turn_penalty) + 0.3 * intent_stability + 0.3 * slot_progress

        return round(max(0, min(1, coherence)), 2)


# Singleton instance
dialogue_manager = DialogueStateManager()


async def update_conversation_state(
    session_id: str, user_input: str, bot_response: str, metadata: dict[str, Any] | None = None
) -> ConversationState:
    """
    Convenience function to update conversation state

    Args:
        session_id: Session identifier
        user_input: User's message
        bot_response: Bot's response
        metadata: Additional metadata

    Returns:
        Updated conversation state
    """
    return await dialogue_manager.update_state(session_id, user_input, bot_response, metadata)


def get_conversation_state(session_id: str) -> ConversationState | None:
    """Get conversation state"""
    return dialogue_manager.get_state(session_id)


# Export
__all__ = [
    "ConversationState",
    "DialogueStateManager",
    "update_conversation_state",
    "get_conversation_state",
]
