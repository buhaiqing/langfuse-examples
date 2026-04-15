"""
服务层模块

提供:
- 意图识别服务
- RAG 知识库服务
- 升级管理服务
- 数据分析服务
- WebSocket 同步服务
- 客服状态服务
"""

from services.intent_recognition import (
    IntentRecognitionService,
    IntentRecognitionResult,
    Entity,
    INTENT_DEFINITIONS,
    intent_service,
)

from services.rag_service import (
    RAGService,
    RAGQueryResult,
    rag_service,
)

from services.escalation_service import (
    EscalationService,
    EscalationRequest,
    escalation_service,
)

from services.analytics import (
    AnalyticsService,
    analytics_service,
)

from services.websocket_sync import (
    WSMessageType,
    PubSubMessage,
    RedisPubSubManager,
    WebSocketSyncService,
    get_ws_sync_service,
    init_ws_sync_service,
)

from services.agent_status_service import (
    AgentStatus,
    AgentRole,
    AgentInfo,
    AgentStatusChange,
    AgentPerformance,
    AgentStatusService,
    get_agent_status_service,
    init_agent_status_service,
)

__all__ = [
    # 意图识别
    "IntentRecognitionService",
    "IntentRecognitionResult",
    "Entity",
    "INTENT_DEFINITIONS",
    "intent_service",
    # RAG 服务
    "RAGService",
    "RAGQueryResult",
    "rag_service",
    # 升级管理
    "EscalationService",
    "EscalationRequest",
    "escalation_service",
    # 数据分析
    "AnalyticsService",
    "analytics_service",
    # WebSocket 同步
    "WSMessageType",
    "PubSubMessage",
    "RedisPubSubManager",
    "WebSocketSyncService",
    "get_ws_sync_service",
    "init_ws_sync_service",
    # 客服状态
    "AgentStatus",
    "AgentRole",
    "AgentInfo",
    "AgentStatusChange",
    "AgentPerformance",
    "AgentStatusService",
    "get_agent_status_service",
    "init_agent_status_service",
]