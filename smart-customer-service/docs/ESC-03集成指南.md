# ESC-03 集成指南

**日期**: 2026-04-13  
**模块**: CollaborationManager 集成到 EscalationManager

---

## 📋 集成概述

ESC-03 协作管理器已成功集成到现有的 EscalationManager 系统中，提供了完整的人机协作功能。

### 集成架构

```
Application Layer
    ↓
EscalationManager (增强版)
    ├── CollaborationManager (新增)
    │   ├── WebSocketClient
    │   ├── Command Handlers
    │   └── State Management
    ├── Escalation Logic (原有)
    └── Fallback Responses (原有)
```

---

## 🔧 使用方法

### 1. 初始化（应用启动时）

```python
from modules.escalation import get_escalation_manager
from modules.escalation.websocket_client import WebSocketClient

# 创建 WebSocket 客户端
websocket_client = WebSocketClient(
    url="wss://human-agent-workstation.example.com/ws",
    api_key="your_api_key",
)

# 连接 WebSocket
await websocket_client.connect()

# 获取 EscalationManager（自动初始化 CollaborationManager）
escalation_manager = get_escalation_manager(
    websocket_client=websocket_client,
    enable_collaboration=True,  # 启用协作功能
)
```

### 2. 会话升级时初始化协作

```python
from modules.escalation.collaboration import CollaborationMode

# 当需要转接人工客服时
async def handle_escalation(session_id: str):
    # 初始化协作模式（默认 AUTO）
    await escalation_manager.initialize_collaboration(
        session_id=session_id,
        mode=CollaborationMode.COPILOT,  # 推荐：Co-pilot 模式
    )
    
    # 或者使用其他模式
    # CollaborationMode.AUTO         - 全自动
    # CollaborationMode.SUPERVISION  - 监督模式
    # CollaborationMode.TAKEOVER     - 人工接管
```

### 3. Agent 推送状态更新

```python
# 在对话处理过程中推送状态
await escalation_manager.collaboration_manager.push_status_update(
    session_id=session_id,
    intent="api_error",
    confidence=0.85,
    active_tools=["ticket_lookup", "kb_search"],
    processing_time_ms=1200.5,
)
```

### 4. Agent 提出建议（Co-pilot 模式）

```python
# 当 Agent 需要人工审批时
action_id = await escalation_manager.collaboration_manager.suggest_action(
    session_id=session_id,
    action_type="send_response",
    payload={
        "response": "Based on your API error logs, I recommend...",
    },
    confidence=0.78,
    reasoning="Found 3 similar cases in knowledge base",
)

# action_id 用于后续追踪
print(f"Suggested action: {action_id}")
```

### 5. 接收人工命令

```python
# WebSocket 接收到人工命令时
async def on_human_command_received(session_id: str, command_data: dict):
    result = await escalation_manager.handle_human_command(
        session_id=session_id,
        command_data=command_data,
    )
    
    if result["status"] == "success":
        print(f"Command executed: {result['result']}")
    else:
        print(f"Command failed: {result['error']}")
```

### 6. 会话结束时清理

```python
# 会话结束时
async def cleanup_session(session_id: str):
    await escalation_manager.cleanup_collaboration(session_id)
    logger.info(f"Session {session_id} cleaned up")
```

---

## 💡 典型工作流

### Co-pilot 模式完整示例

```python
from modules.escalation import get_escalation_manager
from modules.escalation.collaboration import CollaborationMode
from modules.escalation.websocket_client import WebSocketClient

async def copilot_workflow():
    # 1. 初始化
    ws_client = WebSocketClient(url="wss://...")
    await ws_client.connect()
    
    manager = get_escalation_manager(
        websocket_client=ws_client,
        enable_collaboration=True,
    )
    
    session_id = "session_001"
    
    # 2. 初始化协作
    await manager.initialize_collaboration(
        session_id,
        mode=CollaborationMode.COPILOT,
    )
    
    # 3. Agent 处理用户请求
    # ... intent recognition, RAG, tool calling ...
    
    # 4. Agent 推送状态
    await manager.collaboration_manager.push_status_update(
        session_id=session_id,
        intent="billing_issue",
        confidence=0.92,
    )
    
    # 5. Agent 提出建议
    action_id = await manager.collaboration_manager.suggest_action(
        session_id=session_id,
        action_type="send_response",
        payload={"response": "Your billing issue is..."},
        confidence=0.85,
        reasoning="Matched billing policy section 3.2",
    )
    
    # 6. 等待人工审批（通过 WebSocket）
    # Human sends: {"command_type": "approve", "target_action_id": "..."}
    
    # 7. 处理人工命令
    result = await manager.handle_human_command(
        session_id=session_id,
        command_data={
            "command_type": "approve",
            "target_action_id": action_id,
        },
    )
    
    # 8. 执行批准的操作
    if result["result"]["status"] == "approved":
        # Send the approved response to user
        await send_response_to_user(payload["response"])
    
    # 9. 清理
    await manager.cleanup_collaboration(session_id)
    await ws_client.close()
```

### 会话接管示例

```python
async def takeover_workflow():
    session_id = "session_002"
    
    # 1. 初始化协作
    await escalation_manager.initialize_collaboration(
        session_id,
        mode=CollaborationMode.AUTO,  # 开始是自动模式
    )
    
    # 2. Agent 自动处理...
    
    # 3. 人工决定接管
    # Human sends: {"command_type": "takeover"}
    
    result = await escalation_manager.handle_human_command(
        session_id=session_id,
        command_data={"command_type": "takeover"},
    )
    
    # 4. 模式已切换为 TAKEOVER
    # Agent 停止自动响应，人工完全控制
    
    # 5. 人工处理完成后释放
    # Human sends: {"command_type": "release"}
    
    result = await escalation_manager.handle_human_command(
        session_id=session_id,
        command_data={"command_type": "release"},
    )
    
    # 6. 模式切换回 AUTO，Agent 恢复控制
```

---

## 🎯 与现有代码集成点

### 1. API Routes (FastAPI)

```python
# backend/api/routes.py

from fastapi import APIRouter, WebSocket
from modules.escalation import get_escalation_manager

router = APIRouter()

@router.post("/sessions/{session_id}/escalate")
async def escalate_session(session_id: str):
    """Escalate session to human agent with collaboration"""
    manager = get_escalation_manager()
    
    # Initialize collaboration
    await manager.initialize_collaboration(
        session_id,
        mode=CollaborationMode.COPILOT,
    )
    
    return {"status": "escalated", "collaboration_mode": "copilot"}


@router.websocket("/sessions/{session_id}/collaboration")
async def collaboration_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for human-agent collaboration"""
    await websocket.accept()
    
    manager = get_escalation_manager()
    
    try:
        while True:
            # Receive command from human
            data = await websocket.receive_json()
            
            # Handle command
            result = await manager.handle_human_command(
                session_id=session_id,
                command_data=data,
            )
            
            # Send result back
            await websocket.send_json(result)
    
    except WebSocketDisconnect:
        await manager.cleanup_collaboration(session_id)
```

### 2. Dialogue Manager 集成

```python
# backend/modules/dialogue_manager.py

from modules.escalation import get_escalation_manager

class DialogueManager:
    async def process_message(self, session_id: str, user_message: str):
        # ... existing logic ...
        
        # Get escalation manager
        escalation_mgr = get_escalation_manager()
        
        # Check if session is in takeover mode
        if escalation_mgr.collaboration_manager:
            state = escalation_mgr.collaboration_manager.get_collaboration_state(
                session_id
            )
            
            if state["mode"] == "takeover":
                # Human is controlling, skip agent processing
                return {"status": "waiting_for_human"}
        
        # ... continue with normal processing ...
```

### 3. Main Application

```python
# backend/main.py

from modules.escalation.websocket_client import WebSocketClient
from modules.escalation import get_escalation_manager

async def startup_event():
    """Application startup"""
    # Initialize WebSocket client
    ws_client = WebSocketClient(
        url=os.getenv("HUMAN_AGENT_WS_URL"),
        api_key=os.getenv("HUMAN_AGENT_API_KEY"),
    )
    
    try:
        await ws_client.connect()
        logger.info("WebSocket connected to human agent workstation")
    except Exception as e:
        logger.error(f"Failed to connect WebSocket: {e}")
        ws_client = None
    
    # Initialize escalation manager with collaboration
    get_escalation_manager(
        websocket_client=ws_client,
        enable_collaboration=True,
    )
    
    logger.info("EscalationManager initialized with collaboration support")


async def shutdown_event():
    """Application shutdown"""
    manager = get_escalation_manager()
    
    if manager.collaboration_manager:
        # Cleanup all active sessions
        for session_id in list(manager.collaboration_manager.collaboration_states.keys()):
            await manager.cleanup_collaboration(session_id)
    
    logger.info("Application shutdown complete")
```

---

## 📊 监控与可观测性

### Langfuse 追踪

所有协作操作都会自动记录到 Langfuse：

```python
# 自动追踪的 Spans:
- push_status_update
- suggest_action
- request_confirmation
- sync_context
- handle_human_command

# 自动上报的 Metrics:
- human_command_success_rate (0 or 1)
```

### 查询示例

```python
# 在 Langfuse Dashboard 中查询
# Filter by:
# - Trace name: "handle_human_command"
# - Score: "human_command_success_rate"
# - Metadata: {"session_id": "session_001"}
```

---

## ⚙️ 配置选项

### 环境变量

```env
# .env

# Collaboration Settings
ENABLE_COLLABORATION=true
COLLABORATION_DEFAULT_MODE=copilot  # auto, copilot, supervision, takeover

# WebSocket Settings
HUMAN_AGENT_WS_URL=wss://human-agent-workstation.example.com/ws
HUMAN_AGENT_API_KEY=your_api_key_here
```

### 代码配置

```python
# 禁用协作功能（仅使用基础升级功能）
manager = get_escalation_manager(
    websocket_client=None,
    enable_collaboration=False,  # 禁用
)

# 自定义协作模式
await manager.initialize_collaboration(
    session_id,
    mode=CollaborationMode.SUPERVISION,  # 监督模式
)
```

---

## 🧪 测试

### 单元测试

```bash
# 运行协作管理器测试
pytest backend/tests/test_collaboration.py -v

# 运行集成测试
pytest backend/tests/test_collaboration.py::TestIntegration -v
```

### 手动测试

```python
# 测试脚本
import asyncio
from modules.escalation import get_escalation_manager
from modules.escalation.collaboration import CollaborationMode

async def test_collaboration():
    manager = get_escalation_manager(enable_collaboration=False)  # No WebSocket for test
    
    session_id = "test_session"
    
    # Test initialization
    await manager.initialize_collaboration(session_id, CollaborationMode.COPILOT)
    
    # Test state query
    state = manager.collaboration_manager.get_collaboration_state(session_id)
    print(f"State: {state}")
    
    # Test cleanup
    await manager.cleanup_collaboration(session_id)
    print("Test passed!")

asyncio.run(test_collaboration())
```

---

## 🚀 部署注意事项

### 1. WebSocket 连接管理

```python
# 确保 WebSocket 重连机制
ws_client = WebSocketClient(
    url=WS_URL,
    reconnect=True,           # 启用自动重连
    max_reconnect_attempts=10,
    reconnect_delay=5,        # 5秒后重试
)
```

### 2. 资源清理

```python
# 应用关闭时清理所有会话
async def cleanup_all_sessions():
    manager = get_escalation_manager()
    
    if manager.collaboration_manager:
        active_sessions = list(
            manager.collaboration_manager.collaboration_states.keys()
        )
        
        for session_id in active_sessions:
            try:
                await manager.cleanup_collaboration(session_id)
            except Exception as e:
                logger.error(f"Failed to cleanup session {session_id}: {e}")
```

### 3. 性能优化

```python
# 批量处理命令（高负载场景）
async def batch_process_commands(commands: list):
    results = []
    for session_id, command_data in commands:
        result = await manager.handle_human_command(session_id, command_data)
        results.append(result)
    return results
```

---

## 📝 总结

ESC-03 协作管理器已成功集成到 EscalationManager，提供：

- ✅ **无缝集成**: 向后兼容，不影响现有功能
- ✅ **灵活配置**: 可选择启用/禁用协作功能
- ✅ **完整追踪**: 所有操作自动记录到 Langfuse
- ✅ **生产就绪**: 包含错误处理、资源清理、重连机制

**立即开始使用**:

```python
from modules.escalation import get_escalation_manager

# 一行代码获取带协作功能的 EscalationManager
manager = get_escalation_manager(
    websocket_client=ws_client,
    enable_collaboration=True,
)
```

🎉 **人机协作功能现已可用！**
