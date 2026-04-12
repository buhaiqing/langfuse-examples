"""
Tests for collaboration manager (bidirectional sync, co-pilot mode, takeover)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from modules.escalation.collaboration import (
    CollaborationManager,
    CollaborationMode,
    MessageType,
    AgentStatus,
    SuggestedAction,
    HumanCommand,
    SyncMessage,
)


class TestCollaborationManager:
    """Test suite for CollaborationManager"""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket client"""
        mock = AsyncMock()
        mock.send_message = AsyncMock()
        return mock

    @pytest.fixture
    def mock_escalation_manager(self):
        """Create mock escalation manager"""
        mock = AsyncMock()
        mock.set_session_mode = AsyncMock()
        return mock

    @pytest.fixture
    def collaboration_manager(self, mock_websocket, mock_escalation_manager):
        """Create collaboration manager instance"""
        manager = CollaborationManager(
            websocket_client=mock_websocket,
            escalation_manager=mock_escalation_manager,
        )
        return manager

    @pytest.mark.asyncio
    async def test_initialize_session(self, collaboration_manager):
        """Test session initialization"""
        session_id = "test_session_001"

        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.AUTO
        )

        assert session_id in collaboration_manager.collaboration_states
        assert (
            collaboration_manager.collaboration_states[session_id]
            == CollaborationMode.AUTO
        )
        assert session_id in collaboration_manager.pending_suggestions

    @pytest.mark.asyncio
    async def test_push_status_update(self, collaboration_manager, mock_websocket):
        """Test pushing status update to human"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        await collaboration_manager.push_status_update(
            session_id=session_id,
            intent="api_error",
            confidence=0.85,
            active_tools=["ticket_lookup"],
            processing_time_ms=1200.5,
        )

        # Verify message was sent
        assert mock_websocket.send_message.called
        call_args = mock_websocket.send_message.call_args
        assert call_args[0][0] == session_id

        message = call_args[0][1]
        assert message["message_type"] == MessageType.STATUS_UPDATE.value
        assert message["data"]["current_intent"] == "api_error"
        assert message["data"]["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_suggest_action_copilot_mode(
        self, collaboration_manager, mock_websocket
    ):
        """Test suggesting action in co-pilot mode"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.COPILOT
        )

        action_id = await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="send_response",
            payload={"response": "Suggested answer"},
            confidence=0.78,
            reasoning="Based on similar cases",
        )

        assert action_id.startswith("action_")

        # Verify suggestion stored
        pending = collaboration_manager.pending_suggestions[session_id]
        assert len(pending) == 1
        assert pending[0].action_id == action_id
        assert pending[0].confidence == 0.78

        # Verify message sent
        assert mock_websocket.send_message.called
        call_args = mock_websocket.send_message.call_args
        message = call_args[0][1]
        assert message["message_type"] == MessageType.SUGGESTION.value

    @pytest.mark.asyncio
    async def test_request_confirmation(self, collaboration_manager, mock_websocket):
        """Test requesting human confirmation"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        request_id = await collaboration_manager.request_confirmation(
            session_id=session_id,
            action_description="Escalate to senior support?",
            options=[
                {"value": "yes", "label": "Yes, escalate"},
                {"value": "no", "label": "No, continue with agent"},
            ],
        )

        assert request_id.startswith("confirm_")

        # Verify message sent
        assert mock_websocket.send_message.called
        call_args = mock_websocket.send_message.call_args
        message = call_args[0][1]
        assert message["message_type"] == MessageType.CONFIRMATION_REQUEST.value
        assert len(message["data"]["options"]) == 2

    @pytest.mark.asyncio
    async def test_sync_context(self, collaboration_manager, mock_websocket):
        """Test syncing conversation context"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        conversation_history = [
            {"role": "user", "content": "My API is not working"},
            {"role": "assistant", "content": "Let me help you troubleshoot"},
        ]

        await collaboration_manager.sync_context(
            session_id=session_id,
            conversation_history=conversation_history,
            user_profile={"tier": "enterprise"},
        )

        # Verify message sent
        assert mock_websocket.send_message.called
        call_args = mock_websocket.send_message.call_args
        message = call_args[0][1]
        assert message["message_type"] == MessageType.CONTEXT_SYNC.value
        assert len(message["data"]["conversation_history"]) == 2

    @pytest.mark.asyncio
    async def test_handle_approve_command(
        self, collaboration_manager, mock_websocket
    ):
        """Test handling approval command from human"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.COPILOT
        )

        # Create a pending suggestion
        action_id = await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="send_response",
            payload={"response": "Test"},
            confidence=0.8,
            reasoning="Test reasoning",
        )

        # Handle approval
        command_data = {
            "command_type": "approve",
            "target_action_id": action_id,
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "success"
        assert result["result"]["status"] == "approved"

        # Verify suggestion removed from pending
        pending = collaboration_manager.pending_suggestions[session_id]
        assert len(pending) == 0

        # Verify acknowledgment sent
        assert mock_websocket.send_message.call_count >= 2

    @pytest.mark.asyncio
    async def test_handle_reject_command(
        self, collaboration_manager, mock_websocket
    ):
        """Test handling rejection command from human"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.COPILOT
        )

        # Create a pending suggestion
        action_id = await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="send_response",
            payload={"response": "Test"},
            confidence=0.8,
            reasoning="Test reasoning",
        )

        # Handle rejection
        command_data = {
            "command_type": "reject",
            "target_action_id": action_id,
            "reason": "Not accurate enough",
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "success"
        assert result["result"]["status"] == "rejected"

        # Verify suggestion removed
        pending = collaboration_manager.pending_suggestions[session_id]
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_handle_modify_command(
        self, collaboration_manager, mock_websocket
    ):
        """Test handling modification command from human"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.COPILOT
        )

        # Create a pending suggestion
        action_id = await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="send_response",
            payload={"response": "Original response"},
            confidence=0.8,
            reasoning="Test",
        )

        # Handle modification
        command_data = {
            "command_type": "modify",
            "target_action_id": action_id,
            "payload": {"response": "Modified response"},
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "success"
        assert result["result"]["status"] == "modified"

        # Verify suggestion updated
        pending = collaboration_manager.pending_suggestions[session_id]
        assert len(pending) == 1
        assert pending[0].payload["response"] == "Modified response"

    @pytest.mark.asyncio
    async def test_handle_takeover_command(
        self, collaboration_manager, mock_websocket, mock_escalation_manager
    ):
        """Test handling session takeover command"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        command_data = {
            "command_type": "takeover",
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "success"
        assert result["result"]["status"] == "takeover_confirmed"

        # Verify mode changed
        assert (
            collaboration_manager.collaboration_states[session_id]
            == CollaborationMode.TAKEOVER
        )

        # Verify escalation manager notified
        mock_escalation_manager.set_session_mode.assert_called_with(
            session_id, "human_control"
        )

    @pytest.mark.asyncio
    async def test_handle_release_command(
        self, collaboration_manager, mock_websocket, mock_escalation_manager
    ):
        """Test handling release control command"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.TAKEOVER
        )

        command_data = {
            "command_type": "release",
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "success"
        assert result["result"]["status"] == "control_released"

        # Verify mode changed back to AUTO
        assert (
            collaboration_manager.collaboration_states[session_id]
            == CollaborationMode.AUTO
        )

        # Verify escalation manager notified
        mock_escalation_manager.set_session_mode.assert_called_with(
            session_id, "agent_control"
        )

    @pytest.mark.asyncio
    async def test_handle_override_command(
        self, collaboration_manager, mock_websocket
    ):
        """Test handling override command"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        command_data = {
            "command_type": "override",
            "payload": {
                "action": "send_custom_response",
                "response": "Human's custom response",
            },
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "success"
        assert result["result"]["status"] == "overridden"

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, collaboration_manager):
        """Test handling unknown command type"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        command_data = {
            "command_type": "unknown_command",
        }

        result = await collaboration_manager.handle_human_command(
            session_id, command_data
        )

        assert result["status"] == "error"
        assert "Unknown command type" in result["error"]

    @pytest.mark.asyncio
    async def test_set_collaboration_mode(
        self, collaboration_manager, mock_websocket
    ):
        """Test changing collaboration mode"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        await collaboration_manager.set_collaboration_mode(
            session_id, CollaborationMode.COPILOT
        )

        assert (
            collaboration_manager.collaboration_states[session_id]
            == CollaborationMode.COPILOT
        )

        # Verify notification sent
        assert mock_websocket.send_message.called

    @pytest.mark.asyncio
    async def test_get_pending_suggestions(self, collaboration_manager):
        """Test retrieving pending suggestions"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.COPILOT
        )

        # Add some suggestions
        await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="action1",
            payload={},
            confidence=0.8,
            reasoning="Test",
        )

        await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="action2",
            payload={},
            confidence=0.7,
            reasoning="Test",
        )

        pending = await collaboration_manager.get_pending_suggestions(session_id)
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_get_collaboration_state(self, collaboration_manager):
        """Test getting collaboration state"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(
            session_id, CollaborationMode.COPILOT
        )

        state = collaboration_manager.get_collaboration_state(session_id)

        assert state["session_id"] == session_id
        assert state["mode"] == CollaborationMode.COPILOT.value
        assert "pending_suggestions_count" in state

    @pytest.mark.asyncio
    async def test_cleanup_session(self, collaboration_manager):
        """Test cleaning up session state"""
        session_id = "test_session_001"
        await collaboration_manager.initialize_session(session_id)

        # Add some state
        await collaboration_manager.suggest_action(
            session_id=session_id,
            action_type="test",
            payload={},
            confidence=0.8,
            reasoning="Test",
        )

        # Cleanup
        await collaboration_manager.cleanup_session(session_id)

        assert session_id not in collaboration_manager.collaboration_states
        assert session_id not in collaboration_manager.pending_suggestions


class TestCollaborationModes:
    """Test collaboration mode enums and transitions"""

    def test_collaboration_mode_values(self):
        """Test all collaboration modes exist"""
        assert CollaborationMode.AUTO.value == "auto"
        assert CollaborationMode.COPILOT.value == "copilot"
        assert CollaborationMode.SUPERVISION.value == "supervision"
        assert CollaborationMode.TAKEOVER.value == "takeover"

    def test_message_type_values(self):
        """Test all message types exist"""
        # Agent → Human
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.SUGGESTION.value == "suggestion"
        assert MessageType.CONFIRMATION_REQUEST.value == "confirmation_request"
        assert MessageType.CONTEXT_SYNC.value == "context_sync"

        # Human → Agent
        assert MessageType.APPROVAL.value == "approval"
        assert MessageType.REJECTION.value == "rejection"
        assert MessageType.MODIFICATION.value == "modification"
        assert MessageType.COMMAND.value == "command"
        assert MessageType.TAKEOVER_REQUEST.value == "takeover_request"
        assert MessageType.RELEASE_CONTROL.value == "release_control"


class TestDataClasses:
    """Test data class structures"""

    def test_agent_status_creation(self):
        """Test AgentStatus dataclass"""
        status = AgentStatus(
            session_id="test_001",
            mode=CollaborationMode.COPILOT,
            current_intent="api_error",
            confidence=0.85,
            active_tools=["tool1", "tool2"],
        )

        assert status.session_id == "test_001"
        assert status.mode == CollaborationMode.COPILOT
        assert status.confidence == 0.85
        assert len(status.active_tools) == 2

    def test_suggested_action_creation(self):
        """Test SuggestedAction dataclass"""
        action = SuggestedAction(
            action_id="action_001",
            action_type="send_response",
            payload={"response": "Test"},
            confidence=0.78,
            reasoning="Based on analysis",
        )

        assert action.action_id == "action_001"
        assert action.confidence == 0.78
        assert isinstance(action.timestamp, str)

    def test_human_command_creation(self):
        """Test HumanCommand dataclass"""
        command = HumanCommand(
            command_type="approve",
            target_action_id="action_001",
            reason="Looks good",
        )

        assert command.command_type == "approve"
        assert command.target_action_id == "action_001"

    def test_sync_message_creation(self):
        """Test SyncMessage dataclass"""
        message = SyncMessage(
            message_id="msg_001",
            message_type=MessageType.STATUS_UPDATE,
            sender="agent",
            session_id="session_001",
            data={"key": "value"},
        )

        assert message.message_id == "msg_001"
        assert message.sender == "agent"
        assert isinstance(message.timestamp, str)


class TestIntegration:
    """Integration tests for complete collaboration workflow"""

    @pytest.mark.asyncio
    async def test_full_copilot_workflow(self):
        """Test complete co-pilot workflow: suggest → approve/reject"""
        from unittest.mock import AsyncMock

        mock_ws = AsyncMock()
        mock_escalation = AsyncMock()

        manager = CollaborationManager(mock_ws, mock_escalation)

        session_id = "integration_test_001"
        await manager.initialize_session(session_id, CollaborationMode.COPILOT)

        # Agent suggests action
        action_id = await manager.suggest_action(
            session_id=session_id,
            action_type="send_response",
            payload={"response": "Suggested answer"},
            confidence=0.8,
            reasoning="High confidence prediction",
        )

        # Verify suggestion pending
        pending = await manager.get_pending_suggestions(session_id)
        assert len(pending) == 1

        # Human approves
        result = await manager.handle_human_command(
            session_id,
            {"command_type": "approve", "target_action_id": action_id},
        )

        assert result["status"] == "success"

        # Verify suggestion cleared
        pending = await manager.get_pending_suggestions(session_id)
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_takeover_and_release_workflow(self):
        """Test takeover and release workflow"""
        from unittest.mock import AsyncMock

        mock_ws = AsyncMock()
        mock_escalation = AsyncMock()
        mock_escalation.set_session_mode = AsyncMock()

        manager = CollaborationManager(mock_ws, mock_escalation)

        session_id = "integration_test_002"
        await manager.initialize_session(session_id)

        # Human takes over
        await manager.handle_human_command(
            session_id, {"command_type": "takeover"}
        )

        state = manager.get_collaboration_state(session_id)
        assert state["mode"] == "takeover"

        # Human releases control
        await manager.handle_human_command(
            session_id, {"command_type": "release"}
        )

        state = manager.get_collaboration_state(session_id)
        assert state["mode"] == "auto"
