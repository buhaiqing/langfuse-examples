# Langfuse 会话视图配置指南

本文档说明如何在 Langfuse 中查看和分析会话追踪数据。

## 会话追踪概述

Phase 2 实现了完整的会话追踪功能，支持：

- **Session ID 自动传播**: 使用 Langfuse 4.x 的 `propagate_attributes` API
- **跨工具调用关联**: 同一 session 内的所有工具调用自动关联
- **Session Replay**: 在 Langfuse 控制台查看完整会话历史

## 使用方式

### 1. 设置 Session

```python
from src.observability import set_session, SessionManager

# 方式 1：手动设置 session
set_session(
    session_id="user-session-123",
    user_id="user-456",
    metadata={"app": "mcp-server"}
)

# 方式 2：自动生成 session ID
ctx = SessionManager.start_session(
    user_id="user-456",
    metadata={"source": "web"}
)
print(f"Session ID: {ctx['session_id']}")
```

### 2. 工具自动继承 Session

```python
from src.observability import observe_tool

@mcp.tool()
@observe_tool(name="echo")
def echo(message: str) -> str:
    # 自动继承当前 session 的 session_id 和 user_id
    return f"Echo: {message}"

@mcp.tool()
@observe_tool(name="calculate")
def calculate(op: str, a: float, b: float) -> float:
    # 同一 session 内的多次调用自动关联
    pass
```

### 3. 使用 context manager

```python
from src.observability.session import SessionManager

with SessionManager.propagate_session_ctx():
    # 所有嵌套的 Langfuse observations 自动继承 session_id
    result1 = tool_call_1()
    result2 = tool_call_2()
```

## Langfuse 控制台查看会话

### Session Replay

1. 访问 Langfuse Dashboard: https://cloud.langfuse.com
2. 导航到 **Sessions** 页面
3. 点击任意 session ID 查看详细追踪
4. 查看跨多个工具调用的完整会话历史

### Session 视图功能

- **时间线视图**: 按时间顺序显示所有追踪
- **Trace 关联**: 显示同一 session 内的所有 traces
- **输入/输出**: 查看每个工具调用的完整上下文
- **错误追踪**: 标识失败的调用

### 查询示例

在 Langfuse 控制台使用以下过滤器：

```
# 按 session ID 过滤
session_id = "session-abc123"

# 按 user ID 过滤
user_id = "user-456"

# 组合过滤
session_id = "session-abc123" AND level = "ERROR"
```

## 多会话隔离

每个会话完全隔离，确保：

- 不同用户的 session_id 不会相互干扰
- 会话元数据正确传播到所有子 observations
- Langfuse 中会话视图清晰分离

## 最佳实践

### Session ID 生成

```python
# 推荐：使用内置生成器（UUID 格式）
from src.observability.session import SessionManager
session_id = SessionManager.generate_session_id()
# 输出：session-<uuid>

# 或自定义格式（需符合 Langfuse 限制）
# - 最大 200 字符
# - 仅 ASCII 字符
import uuid
session_id = f"user-{user_id}-{uuid.uuid4().hex[:8]}"
```

### Session 生命周期

```python
# 开始新会话
set_session(session_id="new-session", user_id="user-123")

# 执行多个工具调用
result1 = tool_call_1()
result2 = tool_call_2()

# 会话结束（可选）
clear_session()
```

### 错误处理

```python
from src.observability.langfuse_client import get_observer

observer = get_observer()

try:
    with observer.trace_tool_call(
        tool_name="my_tool",
        input_args={"key": "value"},
        session_id="session-123",
        user_id="user-456",
    ) as obs:
        result = execute_tool()
        obs.update(output=result)
except Exception as e:
    # 错误自动记录到 Langfuse
    pass
```

## 会话分析仪表板

Langfuse 提供以下内置分析：

- **Sessions by time**: 会话数量随时间变化
- **Observations per session**: 每会话的平均调用数
- **Error rate by session**: 会话错误率
- **User engagement**: 基于 user_id 的活跃度分析

## 参考文档

- [Langfuse Sessions 文档](https://langfuse.com/docs/observability/features/sessions)
- [propagate_attributes API](https://langfuse.com/docs/observability/sdk/instrumentation)
