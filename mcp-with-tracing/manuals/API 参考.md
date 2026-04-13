# API 参考文档

> 版本：1.0.0

## MCP Tools 列表

本系统提供以下 MCP 工具供客户端调用，所有工具均集成了 Langfuse 可观测性追踪。

### 反馈收集工具 (Feedback Tools)

#### 1. submit_feedback_accept
**功能**: 提交正面反馈（接受）

**用途**: 当用户对 AI 助手的回答满意时调用，记录接受行为。

**参数**:
- `trace_id` (str, 必需): 被评价响应的 Trace ID
- `comment` (str, 可选): 可选的评论，说明接受的原因

**返回值**:
```python
{
    "status": "success",
    "message": "Feedback recorded",
    "feedback_type": "accept"
}
```

**使用示例**:
```python
result = submit_feedback_accept(
    trace_id="trace_abc123",
    comment="回答准确且有帮助"
)
```

**Langfuse 追踪**: 自动记录为 `submit_feedback_accept` span，包含会话上下文。

---

#### 2. submit_feedback_reject
**功能**: 提交负面反馈（拒绝）

**用途**: 当用户对 AI 助手的回答不满意时调用，记录拒绝行为及原因。

**参数**:
- `trace_id` (str, 必需): 被评价响应的 Trace ID
- `reason` (str, 可选): 拒绝的原因分类（如："incorrect", "incomplete", "irrelevant"）
- `comment` (str, 可选): 详细的评论说明

**返回值**:
```python
{
    "status": "success",
    "message": "Feedback recorded",
    "feedback_type": "reject"
}
```

**使用示例**:
```python
result = submit_feedback_reject(
    trace_id="trace_abc123",
    reason="incorrect",
    comment="提供的信息已过时"
)
```

**Langfuse 追踪**: 自动记录为 `submit_feedback_reject` span，可用于分析失败模式。

---

#### 3. submit_feedback_rating
**功能**: 提交评分反馈（1-5 分）

**用途**: 允许用户对 AI 助手的回答进行量化评分。

**参数**:
- `trace_id` (str, 必需): 被评价响应的 Trace ID
- `rating` (int, 必需): 评分值（1-5），1 为最差，5 为最好
- `comment` (str, 可选): 可选的评论说明

**返回值**:
```python
# 成功
{
    "status": "success",
    "message": "Rating 4/5 recorded",
    "feedback_type": "rating"
}

# 失败（评分超出范围）
{
    "status": "error",
    "message": "Rating must be between 1 and 5"
}
```

**使用示例**:
```python
result = submit_feedback_rating(
    trace_id="trace_abc123",
    rating=4,
    comment="回答很有帮助，但可以更详细"
)
```

**Langfuse 追踪**: 自动记录为 `submit_feedback_rating` span，评分会作为 numeric score 附加到 trace。

**注意事项**:
- 评分必须在 1-5 范围内，否则会返回错误
- 建议在用户完成对话后调用

---

#### 4. submit_feedback_comment
**功能**: 提交文本评论

**用途**: 允许用户提供详细的文本反馈，不局限于接受/拒绝或评分。

**参数**:
- `trace_id` (str, 必需): 被评论响应的 Trace ID
- `comment` (str, 必需): 评论文本内容

**返回值**:
```python
{
    "status": "success",
    "message": "Comment recorded",
    "feedback_type": "comment"
}
```

**使用示例**:
```python
result = submit_feedback_comment(
    trace_id="trace_abc123",
    comment="希望能提供更多代码示例和最佳实践建议"
)
```

**Langfuse 追踪**: 自动记录为 `submit_feedback_comment` span，评论内容会关联到对应的 trace。

---

## 会话管理 API

> **注意**: 以下 API 为内部 Python API，不直接暴露为 MCP Tool。

### set_session
```python
set_session(session_id: str, user_id: str = None, metadata: dict = None)
```
**用途**: 设置当前会话上下文，用于关联多个 trace。

### get_session_id
```python
get_session_id() -> str | None
```
**用途**: 获取当前会话 ID。

### clear_session
```python
clear_session()
```
**用途**: 清除当前会话上下文。

## 反馈收集 API (内部 Python API)

> **注意**: 以下 API 为内部 Python API，MCP Tool 层已封装为 `submit_feedback_*` 系列工具。

### record_acceptance
```python
record_acceptance(trace_id: str, user_id: str = None, comment: str = None)
```
**用途**: 记录接受反馈（内部函数）。

### record_rejection
```python
record_rejection(trace_id: str, user_id: str = None, reason: str = None, comment: str = None)
```
**用途**: 记录拒绝反馈（内部函数）。

### record_rating
```python
record_rating(trace_id: str, rating: int, user_id: str = None, comment: str = None)
```
**用途**: 记录评分反馈（内部函数）。

### get_acceptance_rate
```python
get_acceptance_rate() -> float
```
**用途**: 获取接受率统计。

## 告警管理 API

> **注意**: 以下 API 为内部 Python API，用于配置和管理告警规则。

### AlertRule
```python
AlertRule(
    name: str,
    metric: str,
    threshold: float,
    operator: str,
    severity: AlertSeverity,
    window_minutes: int = 60
)
```
**用途**: 定义告警规则，用于监控关键指标并触发通知。

## 版本管理 API

> **注意**: 以下 API 为内部 Python API，用于管理提示词版本。

### register_prompt_version
```python
register_prompt_version(
    prompt_id: str,
    version: str,
    description: str = None,
    metadata: dict = None
)
```
**用途**: 注册新的提示词版本，用于 A/B 测试和版本追踪。

### get_active_prompt_version
```python
get_active_prompt_version(prompt_id: str) -> str | None
```
**用途**: 获取指定提示词的当前活跃版本。

## 装饰器

> **用途**: 用于增强 MCP Tool 的可观测性，自动集成 Langfuse 追踪。

### observe_tool
```python
@observe_tool(name: str = None)
def my_tool(...):
    pass
```
**用途**: 装饰 MCP Tool 函数，自动添加 Langfuse span 追踪和会话上下文传播。

**参数**:
- `name` (str, 可选): Span 名称，默认为函数名

**示例**:
```python
@mcp.tool()
@observe_tool(name="custom_tool_name")
def my_custom_tool(param: str) -> dict:
    return {"result": param}
```

## 通知渠道

> **注意**: 以下 API 为内部 Python API，用于配置告警通知。

### WeComNotifier
```python
WeComNotifier(webhook_url: str)
```
**用途**: 企业微信通知器，用于发送告警消息到企业微信群。

**参数**:
- `webhook_url` (str): 企业微信机器人 webhook URL

**示例**:
```python
from src.observability.notification import WeComNotifier

notifier = WeComNotifier(
    webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
)
notifier.send_alert(message="检测到异常", severity="high")
```

详见：docs/wecom-alert-setup.md

---

## 快速开始

### 1. 启动 MCP 服务器
```bash
python -m src.server
```

### 2. 在客户端调用 MCP Tool
```python
from fastmcp import Client

async with Client("http://localhost:8000/sse") as client:
    # 提交正面反馈
    result = await client.call_tool(
        "submit_feedback_accept",
        {"trace_id": "trace_abc123", "comment": "很好"}
    )
    
    # 提交评分
    result = await client.call_tool(
        "submit_feedback_rating",
        {"trace_id": "trace_abc123", "rating": 5, "comment": "非常满意"}
    )
```

### 3. 查看 Langfuse 追踪
所有工具调用都会自动在 Langfuse Dashboard 中生成 trace，您可以：
- 查看用户满意度趋势
- 分析失败模式
- 监控响应质量
- 进行 A/B 测试

访问：https://cloud.langfuse.com（或您的自部署实例）

---

## 最佳实践

1. **始终提供 trace_id**: 确保每个反馈都能关联到正确的对话 trace
2. **使用有意义的 comment**: 详细的评论有助于后续分析和改进
3. **合理使用评分**: 1-5 分评分系统适合量化用户满意度
4. **结合多种反馈类型**: accept/reject + rating + comment 组合使用效果最佳
5. **监控关键指标**: 定期检查 acceptance_rate、average_rating 等指标

---

## 常见问题

**Q: 如何获取 trace_id？**  
A: trace_id 由 Langfuse SDK 在创建 trace 时自动生成，可以通过 `langfuse.get_trace_id()` 获取。

**Q: 反馈数据保存在哪里？**  
A: 所有反馈数据都发送到 Langfuse 平台，作为 score 附加到对应的 trace 上。

**Q: 可以批量提交反馈吗？**  
A: 当前版本需要逐个调用，未来可能支持批量操作。

**Q: 如何处理匿名用户的反馈？**  
A: 可以不传 user_id，系统会自动使用 session_id 作为标识。
