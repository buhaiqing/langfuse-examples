# 提示词有效性仪表板配置指南

本文档说明如何在 Langfuse 中配置和分析提示词版本的有效性。

## 概述

Phase 3 实现了完整的提示词版本管理功能，支持：

- **版本注册和追踪**: 注册和管理多个提示词版本
- **A/B 测试**: 同时运行多个版本并比较效果
- **版本元数据注入**: 自动将版本信息附加到追踪
- **有效性分析**: 比较不同版本的性能指标

## 使用方式

### 1. 注册提示词版本

```python
from src.observability.prompt_versioning import (
    register_prompt_version,
    set_active_prompt_version,
)

# 注册初始版本
register_prompt_version(
    prompt_id="customer-support-prompt",
    version="v1.0",
    description="Initial customer support response prompt",
    metadata={
        "author": "team-a",
        "model": "gpt-4",
        "temperature": 0.7,
    }
)

# 注册 A/B 测试版本
register_prompt_version(
    prompt_id="customer-support-prompt",
    version="v2.0",
    description="Improved with empathy training",
    metadata={
        "author": "team-b",
        "model": "gpt-4",
        "temperature": 0.5,
    }
)

# 设置活跃版本
set_active_prompt_version("customer-support-prompt", "v2.0")
```

### 2. 在追踪中注入版本信息

#### 方法 1: 使用 propagate_attributes

```python
from src.observability import get_active_prompt_version
from langfuse import propagate_attributes

prompt_id = "customer-support-prompt"
active_version = get_active_prompt_version(prompt_id)

with propagate_attributes(
    metadata={
        "prompt_id": prompt_id,
        "prompt_version": active_version,
    }
):
    # 所有嵌套的 observations 自动继承版本信息
    response = call_llm(prompt)
```

#### 方法 2: 使用 track_prompt_version 装饰器

```python
from src.observability import track_prompt_version

# 指定版本
@mcp.tool()
@track_prompt_version(
    prompt_id="customer-support-prompt",
    version="v2.0"
)
def respond_to_customer(query: str) -> str:
    # 自动附加 prompt_id 和 version 到追踪
    return generate_response(query)

# 使用活跃版本（推荐）
@mcp.tool()
@track_prompt_version(prompt_id="customer-support-prompt")
def respond_to_customer_v2(query: str) -> str:
    # 自动获取并使用当前活跃版本
    return generate_response(query)
```

#### 方法 3: 使用 LangfuseObserver

```python
from src.observability.langfuse_client import get_observer

observer = get_observer()

with observer.trace_tool_call(
    tool_name="llm_tool",
    input_args={"query": "test"},
    prompt_version="v2.0",
    prompt_id="customer-support-prompt",
) as obs:
    result = call_llm(prompt)
    if obs:
        obs.update(output=result)
```

### 3. 使用装饰器自动附加版本

**注意**: `track_prompt_version` 装饰器已更新，现在支持自动获取活跃版本。

```python
from src.observability import track_prompt_version

@mcp.tool()
@track_prompt_version(
    prompt_id="customer-support-prompt",
    version="v2.0"  # 可选，不指定则使用活跃版本
)
def respond_to_customer(query: str) -> str:
    # 自动附加 prompt_id 和 version 到追踪
    return generate_response(query)
```

### 4. 查询和比较版本

使用命令行工具查询版本信息：

```bash
# 列出所有提示词及其版本
python scripts/query_prompt_versions.py

# 列出特定提示词的版本
python scripts/query_prompt_versions.py list customer-support-prompt

# 比较两个版本（A/B 测试）
python scripts/query_prompt_versions.py compare customer-support-prompt v1.0 v2.0

# 查看版本性能指标
python scripts/query_prompt_versions.py performance customer-support-prompt v1.0
```

## Langfuse 仪表板配置

### 创建提示词有效性仪表板

1. **访问 Langfuse Dashboard**: https://cloud.langfuse.com
2. **导航到 Custom Dashboards**
3. **创建新仪表板**: "Prompt Effectiveness Analysis"

### 关键指标配置

#### 1. 成功率对比 (Success Rate by Version)

```
Metric: Success Rate
Group By: metadata.prompt_version
Filter: metadata.prompt_id = "customer-support-prompt"
Time Range: Last 7 days
Visualization: Line Chart
```

**查询配置**:
- X 轴：时间
- Y 轴：成功率 (%)
- 分组：prompt_version
- 阈值线：90%

#### 2. P95 延迟对比 (Latency Comparison)

```
Metric: P95 Latency
Group By: metadata.prompt_version
Filter: metadata.prompt_id = "customer-support-prompt"
Time Range: Last 7 days
Visualization: Bar Chart
```

**查询配置**:
- X 轴：版本
- Y 轴：延迟 (ms)
- 目标：<500ms

#### 3. Token 使用效率 (Token Efficiency)

```
Metric: Average Tokens per Call
Group By: metadata.prompt_version
Filter: metadata.prompt_id = "customer-support-prompt"
Time Range: Last 7 days
Visualization: Table
```

**查询配置**:
- 列：版本、平均 Token 数、总调用数
- 排序：按 Token 效率

#### 4. 用户接受率 (User Acceptance Rate)

```
Metric: Acceptance Rate (Score >= 4)
Group By: metadata.prompt_version
Filter: metadata.prompt_id = "customer-support-prompt"
Time Range: Last 7 days
Visualization: Gauge
```

**查询配置**:
- 目标：>85%
- 告警：<70%

### 仪表板布局建议

```
┌─────────────────────────────────────────────────────┐
│          Prompt Effectiveness Dashboard             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Success Rate Trend]      [Acceptance Rate Gauge]  │
│  (Line Chart by Version)   (Current Version vs     │
│                             Target)                 │
│                                                     │
│  [P95 Latency Comparison]  [Token Usage Table]     │
│  (Bar Chart by Version)    (Efficiency Metrics)    │
│                                                     │
│  [Version Distribution]    [Recent Errors]         │
│  (Pie Chart - Call Split)  (Error Rate by Version) │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## A/B 测试配置

### 流量分配

```python
import random

def select_prompt_version(prompt_id: str) -> str:
    """Select version for A/B test with traffic split."""
    versions = get_prompt_version_manager().get_all_versions(prompt_id)
    
    if len(versions) < 2:
        return versions[0].version if versions else "v1.0"
    
    # 50/50 traffic split for A/B test
    if random.random() < 0.5:
        return "v1.0"  # Control
    else:
        return "v2.0"  # Treatment
```

### 统计显著性

在 Langfuse 中监控以下指标以确定统计显著性：

- **样本量**: 每组至少 100 次调用
- **置信水平**: 95%
- **最小检测效应**: 5% 改进

## 分析查询示例

### 按版本分组的成功率

```
Success Rate by Version (Last 7 Days)

SELECT 
    metadata->>'prompt_version' as version,
    COUNT(*) FILTER (WHERE level != 'ERROR') * 100.0 / COUNT(*) as success_rate
FROM observations
WHERE metadata->>'prompt_id' = 'customer-support-prompt'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY version
ORDER BY success_rate DESC
```

### 平均响应时间对比

```
Average Response Time by Version

SELECT 
    metadata->>'prompt_version' as version,
    AVG(end_time - start_time) as avg_response_time_ms
FROM observations
WHERE metadata->>'prompt_id' = 'customer-support-prompt'
GROUP BY version
```

### 版本效果趋势

```
Daily Success Rate Trend by Version

SELECT 
    DATE(timestamp) as date,
    metadata->>'prompt_version' as version,
    COUNT(*) FILTER (WHERE level != 'ERROR') * 100.0 / COUNT(*) as success_rate
FROM observations
WHERE metadata->>'prompt_id' = 'customer-support-prompt'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), version
ORDER BY date, version
```

## 最佳实践

### 版本命名规范

```
格式：v{major}.{minor}[.{patch}][-{suffix}]

示例:
- v1.0        - 初始版本
- v1.1        - 小幅改进
- v2.0        - 重大改进
- v2.0-beta   - 测试版本
```

### 元数据标准

```python
metadata = {
    "prompt_id": "unique-identifier",
    "version": "v1.0",
    "author": "team-or-person",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000,
    "created_date": "2026-04-08",
    "description": "Brief description of changes",
}
```

### A/B 测试指南

1. **单变量测试**: 每次只改变一个因素
2. **足够样本**: 确保统计显著性
3. **明确假设**: 记录测试假设
4. **时间窗口**: 至少运行 7 天
5. **监控副作用**: 关注延迟、成本等

## 常见问题

### Q: 如何回滚到旧版本？

```python
# 立即切换到旧版本
set_active_prompt_version("prompt-id", "v1.0")

# 新调用将使用 v1.0
```

### Q: 如何删除测试版本？

```python
# 不推荐删除，建议标记为已弃用
register_prompt_version(
    "prompt-id",
    "v3.0-deprecated",
    "Deprecated version - do not use"
)
```

### Q: 如何确定哪个版本更好？

在 Langfuse 仪表板中比较：
1. 成功率 (最高)
2. 用户接受率 (最高)
3. 响应时间 (最低)
4. Token 效率 (最高)

## 参考文档

- [Langfuse Custom Dashboards](https://langfuse.com/docs/metrics/features/custom-dashboards)
- [Langfuse Sessions](https://langfuse.com/docs/observability/features/sessions)
- [Langfuse Scores](https://langfuse.com/docs/scores/overview)
