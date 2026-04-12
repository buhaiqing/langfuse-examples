# Langfuse Sessions 使用指南

> **文档版本**: 1.0.0  
> **最后更新**: 2026-04-13  
> **适用项目**: MCP with Tracing

---

## 📋 目录

1. [Sessions 概述](#sessions-概述)
2. [核心概念](#核心概念)
3. [Session 管理 API](#session-管理-api)
4. [在 MCP Server 中使用 Sessions](#在-mcp-server-中使用-sessions)
5. [Langfuse Console 中的 Session 视图](#langfuse-console-中的-session-视图)
6. [自定义 Dashboard 查询](#自定义-dashboard-查询)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)

---

## Sessions 概述

Langfuse Sessions 允许你将多个相关的 traces 组合成一个逻辑会话，便于：

- 🔍 **端到端追踪**: 查看用户从开始到结束的完整交互流程
- 📊 **会话分析**: 分析会话级别的成功率、延迟等指标
- 🎯 **问题定位**: 快速识别失败会话并回放整个交互过程
- 📈 **趋势监控**: 跟踪会话级别的性能趋势

---

## 核心概念

### Session ID

- **格式**: `session-{uuid}` (例如: `session-a1b2c3d4e5f6...`)
- **约束**: 
  - 最大长度: 200 字符
  - 仅 ASCII 字符
  - 唯一性保证
  
### Session 生命周期

```
Session Start
    ↓
Trace 1 (工具调用 A)
    ↓
Trace 2 (工具调用 B)
    ↓
Trace 3 (工具调用 C)
    ↓
Session End
```

### Context Propagation

使用 `contextvars` 自动传播 session_id 和 user_id 到所有子 observations。

---

## Session 管理 API

### 1. 创建 Session

```python
from src.observability.session import SessionManager

# 自动生成 session_id
ctx = SessionManager.start_session(user_id="user-123")

# 指定 session_id
ctx = SessionManager.start_session(
    session_id="my-custom-session",
    user_id="user-123",
    metadata={"channel": "web_chat", "priority": "high"}
)
```

### 2. 设置 Session Context

```python
from src.observability.session import set_session, get_session_id

# 设置当前 session
set_session(
    session_id="session-abc123",
    user_id="user-456",
    metadata={"product": "api_support"}
)

# 获取当前 session_id
current_session = get_session_id()
```

### 3. 清除 Session

```python
from src.observability.session import clear_session

clear_session()
```

### 4. 传播 Session 属性

```python
from src.observability.session import SessionManager

with SessionManager.propagate_session_ctx():
    # 所有在此上下文中的 observation 自动继承 session_id
    result = tool_call()
```

---

## 在 MCP Server 中使用 Sessions

### 自动 Session 管理

MCP Server 已集成自动 session 管理，无需手动操作：

```python
from src.observability.langfuse_client import get_observer

observer = get_observer()

# trace_tool_call 会自动处理 session context
with observer.trace_tool_call(
    tool_name="get_order_status",
    input_args={"order_id": "ORD-123"},
    session_id="session-abc",  # 可选，不提供则自动生成
    user_id="user-456",
):
    # 执行工具逻辑
    result = process_order("ORD-123")
```

### 多工具调用的 Session 连续性

```python
from src.observability.session import set_session
from src.observability.langfuse_client import get_observer

# 设置 session context
set_session(session_id="session-xyz", user_id="user-789")

observer = get_observer()

# 第一个工具调用
with observer.trace_tool_call(
    tool_name="authenticate_user",
    input_args={"username": "john"},
):
    authenticate()

# 第二个工具调用（自动继承 session_id）
with observer.trace_tool_call(
    tool_name="fetch_profile",
    input_args={"user_id": "john"},
):
    fetch_profile()

# 第三个工具调用（仍然在同一 session 中）
with observer.trace_tool_call(
    tool_name="update_preferences",
    input_args={"theme": "dark"},
):
    update_prefs()
```

所有三个工具调用都会关联到同一个 session (`session-xyz`)。

---

## Langfuse Console 中的 Session 视图

### 访问 Sessions

1. 登录 [Langfuse Cloud](https://cloud.langfuse.com)
2. 导航到左侧菜单的 **Sessions**
3. 查看所有活跃和历史 sessions

### Session Replay

点击任意 session 查看详细信息：

- **Traces 列表**: 该 session 中的所有 traces
- **时间线**: 可视化的 trace 执行顺序
- **元数据**: session_id, user_id, 自定义 metadata
- **错误追踪**: 失败的 traces 高亮显示

### Session 过滤

支持按以下条件过滤 sessions：

- `session_id`: 精确匹配
- `user_id`: 用户维度分析
- `metadata.*`: 自定义元数据字段
- `time range`: 时间范围
- `tags`: 标签过滤

---

## 自定义 Dashboard 查询

### SQL 查询示例

#### 1. 会话成功率

```sql
SELECT
  DATE_TRUNC('hour', t.timestamp) AS time_bucket,
  COUNT(DISTINCT t.session_id) AS total_sessions,
  COUNT(DISTINCT CASE WHEN t.level != 'ERROR' THEN t.session_id END) AS successful_sessions,
  ROUND(
    COUNT(DISTINCT CASE WHEN t.level != 'ERROR' THEN t.session_id END) * 100.0 / 
    COUNT(DISTINCT t.session_id), 
    2
  ) AS success_rate_pct
FROM traces t
WHERE t.session_id IS NOT NULL
GROUP BY time_bucket
ORDER BY time_bucket DESC
LIMIT 24;
```

#### 2. 平均会话时长

```sql
SELECT
  t.session_id,
  MAX(t.timestamp) - MIN(t.timestamp) AS session_duration,
  COUNT(*) AS trace_count
FROM traces t
WHERE t.session_id IS NOT NULL
GROUP BY t.session_id
HAVING COUNT(*) > 1
ORDER BY session_duration DESC
LIMIT 100;
```

#### 3. 按用户分组的会话统计

```sql
SELECT
  t.user_id,
  COUNT(DISTINCT t.session_id) AS session_count,
  AVG(EXTRACT(EPOCH FROM (MAX(t.timestamp) - MIN(t.timestamp)))) AS avg_session_duration_sec,
  ROUND(
    COUNT(CASE WHEN t.level = 'ERROR' THEN 1 END) * 100.0 / COUNT(*),
    2
  ) AS error_rate_pct
FROM traces t
WHERE t.user_id IS NOT NULL
GROUP BY t.user_id
ORDER BY session_count DESC
LIMIT 50;
```

#### 4. 高失败率会话检测

```sql
SELECT
  t.session_id,
  t.user_id,
  COUNT(*) AS total_traces,
  COUNT(CASE WHEN t.level = 'ERROR' THEN 1 END) AS failed_traces,
  ROUND(
    COUNT(CASE WHEN t.level = 'ERROR' THEN 1 END) * 100.0 / COUNT(*),
    2
  ) AS failure_rate_pct
FROM traces t
WHERE t.session_id IS NOT NULL
GROUP BY t.session_id, t.user_id
HAVING COUNT(CASE WHEN t.level = 'ERROR' THEN 1 END) >= 2
ORDER BY failure_rate_pct DESC
LIMIT 20;
```

### Python SDK 查询

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com"
)

# 获取特定 session 的所有 traces
traces = langfuse.fetch_traces(session_id="session-abc123")

for trace in traces.data:
    print(f"Trace: {trace.name}, Status: {trace.level}")
```

---

## 最佳实践

### ✅ 推荐做法

1. **始终设置 user_id**
   ```python
   set_session(session_id="session-123", user_id="user-456")
   ```

2. **添加有意义的 metadata**
   ```python
   set_session(
       session_id="session-123",
       user_id="user-456",
       metadata={
           "channel": "web_chat",
           "customer_tier": "enterprise",
           "product_version": "v2.3"
       }
   )
   ```

3. **及时清理 session context**
   ```python
   try:
       set_session(session_id="session-123", user_id="user-456")
       # 执行操作
   finally:
       clear_session()
   ```

4. **使用 propagate_attributes 确保传播**
   ```python
   with SessionManager.propagate_session_ctx():
       # 所有子 observation 自动继承 session_id
       result = tool_call()
   ```

### ❌ 避免的做法

1. **不要硬编码 session IDs**
   ```python
   # ❌ 错误
   session_id = "fixed-session-id"
   
   # ✅ 正确
   session_id = SessionManager.generate_session_id()
   ```

2. **不要在多线程间共享 session context**
   ```python
   # ❌ 错误 - contextvars 不跨线程传播
   Thread(target=process, args=(session_id,)).start()
   
   # ✅ 正确 - 在每个线程中设置 context
   def process_in_thread(sid):
       set_session(session_id=sid)
       # 处理逻辑
   
   Thread(target=process_in_thread, args=(session_id,)).start()
   ```

3. **不要忘记设置 user_id**
   ```python
   # ❌ 不完整
   set_session(session_id="session-123")
   
   # ✅ 完整
   set_session(session_id="session-123", user_id="user-456")
   ```

---

## 常见问题

### Q1: Session ID 的最大长度是多少？

**A**: 200 字符。超过此长度会导致 Langfuse API 拒绝请求。

### Q2: 如何在异步环境中使用 Sessions？

**A**: `contextvars` 天然支持 async/await，无需额外配置：

```python
import asyncio
from src.observability.session import set_session

async def handle_request():
    set_session(session_id="session-123", user_id="user-456")
    await process_data()
```

### Q3: Session 会自动过期吗？

**A**: 不会。Sessions 是永久存储的，但你可以通过查询时指定时间范围来限制结果。

### Q4: 如何删除旧的 Sessions？

**A**: 目前 Langfuse 不支持直接删除 sessions。建议：
- 定期归档旧数据
- 使用 retention policies（企业版功能）
- 查询时限定时间范围

### Q5: 一个 Session 可以有多少个 Traces？

**A**: 没有硬性限制，但建议保持在合理范围内（<1000 traces/session）以保证查询性能。

### Q6: 如何调试 Session 未正确关联的问题？

**A**: 检查以下几点：
1. 确认 `set_session()` 在 trace 之前调用
2. 验证 `propagate_session_ctx()` 正确使用
3. 检查 Langfuse Console 中 session_id 是否一致
4. 查看应用日志中的 session context 信息

---

## 相关资源

- [Langfuse Sessions 官方文档](https://langfuse.com/docs/observability/features/sessions)
- [Langfuse SDK Instrumentation](https://langfuse.com/docs/observability/sdk/instrumentation)
- [ContextVars 文档](https://docs.python.org/3/library/contextvars.html)
- [Phase 2 开发计划](../devs/phase2/phase2_plan.md)
- [Phase 2 进度跟踪](../devs/phase2/phase2_progress.md)

---

## 附录: Session ID 生成算法

```python
import uuid

def generate_session_id() -> str:
    """
    生成符合 Langfuse 规范的 session ID。
    
    格式: session-{32-char-hex}
    示例: session-a1b2c3d4e5f6789012345678abcdef90
    """
    return f"session-{uuid.uuid4().hex}"
```

---

**文档维护**: 如有问题或改进建议，请联系开发团队。
