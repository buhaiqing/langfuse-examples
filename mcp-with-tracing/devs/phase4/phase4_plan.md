# Phase 4: 反馈收集 (Feedback Collection) - 任务分解

> **阶段目标**: 捕获和分析用户满意度信号  
> **预计工作量**: 5 个子任务  
> **开始日期**: 2026-04-08  
> **状态**: 待开始

---

## 任务分解

### 任务 4.1: 实现反馈收集 API
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- `src/observability/feedback.py`

**具体内容**:
1. 创建 FeedbackCollector 类
2. 实现 record_acceptance() 和 record_rejection() 方法
3. 支持可选的评论和评分

**QA验证**:
- [ ] 运行测试: `python -m pytest tests/test_feedback.py -v`
- [ ] 接受/拒绝信号正确记录

---

### 任务 4.2: 创建反馈观察模式
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- 更新 `src/observability/langfuse_client.py`

**具体内容**:
1. 集成 feedback 到追踪流程
2. 使用 Langfuse 的 score 功能记录反馈
3. 关联 feedback 到具体 trace

**QA验证**:
- [ ] 反馈数据正确附加到 trace
- [ ] Langfuse 控制台可见反馈

---

### 任务 4.3: 构建反馈聚合查询
**分类**: unspecified-high | **技能**: [] | **优先级**: Medium

**输出文件**:
- `scripts/query_feedback.py`

**具体内容**:
1. 创建反馈聚合统计脚本
2. 计算用户接受率
3. 按时间段和版本分析反馈

**QA验证**:
- [ ] 脚本正确聚合反馈数据
- [ ] 接受率计算正确

---

### 任务 4.4: 创建用户满意度仪表板
**分类**: unspecified-high | **技能**: [] | **优先级**: Medium

**输出文件**:
- `docs/satisfaction-dashboard.md`

**具体内容**:
1. 文档说明 Langfuse Scores 功能
2. 创建满意度 dashboard 配置
3. 关键指标展示建议

**QA验证**:
- [ ] 文档完整可用

---

### 任务 4.5: 与客户端反馈机制集成
**分类**: deep | **技能**: [] | **优先级**: Medium

**输出文件**:
- 更新 `src/server.py` 或新文件 `src/tools/feedback_tool.py`

**具体内容**:
1. 创建 MCP 反馈工具
2. 提供 API 端点接收用户反馈
3. 集成到现有工具链

**QA验证**:
- [ ] 反馈工具可用
- [ ] 端到端反馈流程正常

---

## 并行执行机会

| 波次 | 任务 | 依赖 |
|------|------|------|
| 1 | 4.1 (反馈 API) | 无 |
| 2 | 4.2 (反馈观察) | 4.1 |
| 3 | 4.3 (聚合查询) | 4.2 |
| 3 | 4.4 (仪表板) | 无 |
| 3 | 4.5 (客户端集成) | 4.2 |

---

## Langfuse 4.x Feedback API

```python
# 使用 score 记录反馈
from langfuse import Langfuse

client = Langfuse(...)
client.score_current_trace(
    name="user-feedback",
    value=1,  # 1=accept, 0=reject
    comment="Great response!"
)
```

**参考文档**: Langfuse Scores 功能

---

## 交付物清单

- [ ] `src/observability/feedback.py` - 反馈收集器
- [ ] 更新的 `langfuse_client.py` - 支持反馈追踪
- [ ] `scripts/query_feedback.py` - 反馈聚合脚本
- [ ] `docs/satisfaction-dashboard.md` - 满意度仪表板文档
- [ ] `src/tools/feedback_tool.py` - 反馈工具 (可选)

---

## 成功标准

- [ ] 所有测试通过
- [ ] 反馈正确记录到 Langfuse
- [ ] 可按版本和时间聚合反馈
- [ ] 用户满意度指标可计算
