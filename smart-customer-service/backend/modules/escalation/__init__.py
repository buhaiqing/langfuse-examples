"""
Escalation module for human agent handoff
"""

from modules.escalation.websocket_client import (
    WebSocketClient,
    EscalationWebSocketClient,
    WSMessage,
    create_escalation_websocket,
)
from modules.escalation.queue_manager import (
    QueueManager,
    ContextPackager,
    EscalationContext,
    create_queue_manager,
    create_context_packager,
)

__all__ = [
    "WebSocketClient",
    "EscalationWebSocketClient",
    "WSMessage",
    "QueueManager",
    "ContextPackager",
    "EscalationContext",
    "create_escalation_websocket",
    "create_queue_manager",
    "create_context_packager",
]
