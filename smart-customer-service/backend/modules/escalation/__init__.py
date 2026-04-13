"""
Escalation module for human agent handoff
"""

from modules.escalation.websocket_client import (
    WebSocketClient,
    WSMessage,
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
    "WSMessage",
    "QueueManager",
    "ContextPackager",
    "EscalationContext",
    "create_queue_manager",
    "create_context_packager",
]
