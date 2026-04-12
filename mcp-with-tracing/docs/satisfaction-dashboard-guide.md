# 用户满意度仪表板配置指南

本文档说明如何在 Langfuse 中配置用户满意度分析和反馈追踪仪表板。

## 概述

Phase 4 实现了完整的用户反馈收集功能，支持：

- **接受/拒绝信号**: 简单的二元反馈
- **评分系统**: 1-5 星评分
- **评论收集**: 文本反馈
- **满意度分析**: 接受率、平均评分等指标

## 使用方式

### 1. 收集反馈

```python
from src.observability.feedback import (
    record_acceptance,
    record_rejection,
    record_rating,
    record_comment,
)

# 记录用户接受
record_acceptance(
    trace_id="trace-123",
    user_id="user-456",
    comment="Great response!"
)

# 记录用户拒绝
record_rejection(
    trace_id="trace-124",
    user_id="user-456",
    reason="inaccurate",
    comment="Information was incorrect"
)

# 记录评分 (1-5)
record_rating(
    trace_id="trace-125",
    rating=4,
    user_id="user-456",
    comment="Very helpful"
)

# 记录文本评论
record_comment(
    trace_id="trace-126",
    comment="The response was detailed and accurate",
    user_id="user-456"
)
```

### 2. 与 MCP 工具集成

```python
from src.observability import observe_tool
from src.observability.feedback import record_acceptance

@mcp.tool()
@observe_tool(name="response_tool")
def generate_response(query: str, user_feedback: bool = False) -> str:
    """Generate response with optional feedback."""
    response = llm_generate(query)
    
    if user_feedback:
        # 用户标记为有帮助
        record_acceptance(trace_id=get_current_trace_id())
    
    return response
```

### 3. 获取反馈统计

```python
from src.observability.feedback import (
    get_acceptance_rate,
    get_feedback_statistics,
)

# 获取接受率
rate = get_acceptance_rate()
print(f"Acceptance Rate: {rate:.1f}%")

# 获取详细统计
stats = get_feedback_statistics()
print(f"Total Feedback: {stats['total_feedback']}")
print(f"Average Rating: {stats.get('average_rating', 'N/A')}")
```

## Langfuse 仪表板配置

### 创建满意度仪表板

1. **访问 Langfuse Dashboard**: https://cloud.langfuse.com
2. **导航到 Custom Dashboards**
3. **创建新仪表板**: "User Satisfaction Analytics"

### 关键指标配置

#### 1. 接受率趋势 (Acceptance Rate Trend)

```
Metric: Acceptance Rate
Group By: Time (Hourly/Daily)
Filter: score name = "user-feedback"
Time Range: Last 7 days
Visualization: Line Chart
```

**查询配置**:
- X 轴：时间
- Y 轴：接受率 (%)
- 目标线: 85%
- 告警线：70%

#### 2. 评分分布 (Rating Distribution)

```
Metric: Average Score
Group By: Score value
Filter: score name = "rating"
Time Range: Last 7 days
Visualization: Bar Chart
```

**查询配置**:
- X 轴：评分 (1-5)
- Y 轴：数量
- 排序：升序

#### 3. 拒绝原因分析 (Rejection Reasons)

```
Metric: Rejection Count
Group By: metadata.rejection_reason
Filter: score = 0
Time Range: Last 7 days
Visualization: Pie Chart
```

**查询配置**:
- 切片：拒绝原因
- 显示：百分比

#### 4. 用户满意度热图 (Satisfaction Heatmap)

```
Metric: Acceptance Rate
Group By: Hour of Day, Day of Week
Filter: score name = "user-feedback"
Time Range: Last 30 days
Visualization: Heatmap
```

**查询配置**:
- X 轴：星期
- Y 轴：小时
- 颜色：接受率

### 仪表板布局建议

```
┌─────────────────────────────────────────────────────┐
│        User Satisfaction Dashboard                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Acceptance Rate Trend]    [Rating Distribution]  │
│  (Line - Last 7 Days)       (Bar - 1-5 Stars)     │
│                                                     │
│  [Satisfaction Score]       [Rejection Reasons]    │
│  (Gauge - Current)          (Pie - Categories)    │
│                                                     │
│  [Hourly Heatmap]           [Recent Feedback]     │
│  (Heatmap - Pattern)        (Table - Details)     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Langfuse Scores 配置

### Score 类型

Langfuse 支持以下类型的 Scores：

| 类型 | 值范围 | 用途 |
|------|--------|------|
| NUMERIC | 0-1 | 接受/拒绝 |
| NUMERIC | 1-5 | 星级评分 |
| BOOLEAN | true/false | 是否满意 |

### 通过 API 记录 Score

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-...",
    secret_key="sk-...",
)

# 记录接受 (value=1)
langfuse.score(
    trace_id="trace-123",
    name="user-feedback",
    value=1,
    comment="User accepted the response"
)

# 记录拒绝 (value=0)
langfuse.score(
    trace_id="trace-123",
    name="user-feedback",
    value=0,
    comment="User rejected the response",
    metadata={"reason": "inaccurate"}
)

# 记录评分
langfuse.score(
    trace_id="trace-123",
    name="rating",
    value=4,
    comment="4 out of 5 stars"
)
```

### 在 Observations 中记录 Score

```python
with langfuse.trace(name="tool-execution") as trace:
    with trace.span(name="llm-call") as span:
        result = call_llm(prompt)
        
        # 在 observation 上记录 score
        span.score(
            name="quality-check",
            value=1,
            comment="High quality output"
        )
```

## 分析查询示例

### 按时间分组的接受率

```
Daily Acceptance Rate (Last 30 Days)

SELECT 
    DATE(timestamp) as date,
    COUNT(*) FILTER (WHERE value = 1) * 100.0 / COUNT(*) as acceptance_rate
FROM scores
WHERE name = 'user-feedback'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date
```

### 平均评分趋势

```
Average Rating Trend

SELECT 
    DATE(timestamp) as date,
    AVG(value) as avg_rating
FROM scores
WHERE name = 'rating'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date
```

### 拒绝原因分布

```
Rejection Reasons Distribution

SELECT 
    metadata->>'rejection_reason' as reason,
    COUNT(*) as count
FROM scores
WHERE name = 'user-feedback'
  AND value = 0
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY metadata->>'rejection_reason'
ORDER BY count DESC
```

### 用户活跃度分析

```
Feedback by User

SELECT 
    user_id,
    COUNT(*) as feedback_count,
    COUNT(*) FILTER (WHERE value = 1) * 100.0 / COUNT(*) as acceptance_rate
FROM scores
WHERE name = 'user-feedback'
GROUP BY user_id
HAVING COUNT(*) >= 5
ORDER BY feedback_count DESC
```

## 最佳实践

### 反馈收集时机

| 场景 | 反馈类型 | 时机 |
|------|----------|------|
| 工具调用完成 | 接受/拒绝 | 用户查看结果后 |
| 对话结束 | 评分 | 会话结束时 |
| 帮助投票 | 点赞/踩 | 用户点击后 |
| 调查 | 评论 | 用户主动提交 |

### Score 命名规范

```
格式：[category]-[type]

示例:
- user-feedback      - 用户接受/拒绝
- rating             - 星级评分
- quality-check      - 质量检查
- satisfaction       - 满意度调查
```

### 元数据标准

```python
metadata = {
    "trace_id": "trace-123",
    "user_id": "user-456",
    "session_id": "session-789",
    "tool_name": "response-generator",
    "prompt_version": "v2.0",
    "feedback_source": "thumbs-up-button",
    "timestamp": "2026-04-08T10:30:00Z",
}
```

### 告警配置

建议为以下指标设置告警：

```
1. 接受率低于 70%
   - Severity: Warning
   - Window: 1 hour
   - Channel: Slack

2. 平均评分低于 3.5
   - Severity: Warning
   - Window: 4 hours
   - Channel: Email

3. 拒绝率突然上升 (>50%)
   - Severity: Critical
   - Window: 30 minutes
   - Channel: PagerDuty
```

## 与 Prompt 版本关联

将反馈与 Phase 3 的提示词版本关联：

```python
from src.observability.feedback import record_acceptance
from src.observability import get_active_prompt_version

prompt_id = "customer-support"
version = get_active_prompt_version(prompt_id)

feedback = record_acceptance(
    trace_id="trace-123",
    metadata={
        "prompt_id": prompt_id,
        "prompt_version": version,
    }
)
```

在 Langfuse 中按版本分析反馈：

```
Acceptance Rate by Prompt Version

SELECT 
    metadata->>'prompt_version' as version,
    COUNT(*) FILTER (WHERE value = 1) * 100.0 / COUNT(*) as acceptance_rate
FROM scores
WHERE name = 'user-feedback'
  AND metadata->>'prompt_id' = 'customer-support'
GROUP BY metadata->>'prompt_version'
```

## 常见问题

### Q: 如何处理匿名反馈？

```python
# 不提供 user_id
record_acceptance(
    trace_id="trace-123",
    # user_id 可选
)
```

### Q: 如何收集多个反馈？

```python
# 同一 trace 可以记录多个 scores
langfuse.score(trace_id, name="initial-reaction", value=1)
langfuse.score(trace_id, name="final-satisfaction", value=4)
```

### Q: 如何删除错误反馈？

```python
# Langfuse 不支持删除，建议记录修正
langfuse.score(
    trace_id="trace-123",
    name="correction",
    value=1,  # 正确值
    comment="Correcting previous incorrect feedback"
)
```

## 参考文档

- [Langfuse Scores Overview](https://langfuse.com/docs/scores/overview)
- [Langfuse Custom Dashboards](https://langfuse.com/docs/metrics/features/custom-dashboards)
- [Langfuse API Reference](https://langfuse.com/api-reference)
