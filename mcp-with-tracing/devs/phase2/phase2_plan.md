# Phase 2: 会话追踪 (Session Tracing) - 任务分解

> **阶段目标**: 将多个工具调用链接为端到端用户会话  
> **预计工作量**: 5 个子任务  
> **开始日期**: 2026-04-08  
> **状态**: 待开始

---

## 任务分解

### 任务 2.1: 实现会话上下文管理
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- `src/observability/session.py`

**具体内容**:
1. 创建 SessionManager 类
2. 实现自动生成 session_id (UUID 或时间戳+随机)
3. 实现 session 生命周期管理 (创建、更新、结束)
4. 从 contextvars 读取当前 session

**QA验证**:
- [ ] 运行测试: `python -m pytest tests/test_session.py -v`
- [ ] Session ID 格式符合规范 (<=200字符, ASCII)
- [ ] 多次调用返回不同 session ID

---

### 任务 2.2: 通过 MCP 请求传播 session_id
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- 更新 `src/observability/langfuse_client.py`

**具体内容**:
1. 使用 `propagate_attributes` 将 session_id 传播到所有子 observation
2. 在 LangfuseObserver.trace_tool_call() 中自动附加 session context
3. 实现 session 跨工具调用的连续性

**QA验证**:
- [ ] 单个 session 内的多个工具调用共享同一 session_id
- [ ] 不同 session 的调用相互隔离

---

### 任务 2.3: 使用 `propagate_attributes` 附加会话/用户元数据
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- 更新 `src/observability/decorators.py`

**具体内容**:
1. 更新 @observe_tool 装饰器自动读取 session context
2. 使用 langfuse 4.x 的 `propagate_attributes` API
3. 附加 user_id, session_id 到根 observation

**QA验证**:
- [ ] 装饰器自动使用 contextvars 中的 session_id
- [ ] Langfuse 控制台显示正确的 session 关联

---

### 任务 2.4: 在 Langfuse 中创建会话视图
**分类**: unspecified-high | **技能**: [] | **优先级**: Medium

**输出文件**:
- `docs/session-dashboard.md` (可选)

**具体内容**:
1. 文档说明 Langfuse Sessions 功能
2. 配置建议用于查看 session replay
3. 创建自定义 dashboard 的查询示例

**QA验证**:
- [ ] 文档完整可用

---

### 任务 2.5: 测试多会话场景
**分类**: quick | **技能**: [] | **优先级**: Medium

**输出文件**:
- `scripts/test_session_tracing.py`

**具体内容**:
1. 创建多会话并发测试
2. 测试 session 隔离
3. 测试 session replay 功能

**QA验证**:
- [ ] 运行测试: `python scripts/test_session_tracing.py`
- [ ] 多个 session 的 traces 正确分离

---

## 并行执行机会

| 波次 | 任务 | 依赖 |
|------|------|------|
| 1 | 2.1 (Session 上下文管理) | 无 |
| 2 | 2.2 (传播 session_id) | 2.1 |
| 2 | 2.3 (附加元数据装饰器) | 2.1 |
| 3 | 2.4 (会话视图文档) | 无 |
| 3 | 2.5 (多会话测试) | 2.2, 2.3 |

---

## Langfuse 4.x API 参考

```python
# 使用 propagate_attributes 传播 session
from langfuse.decorators import propagate_attributes

with propagate_attributes(session_id="session-123", user_id="user-456"):
    # 所有子 observation 自动继承 session_id
    result = tool_call()
```

**参考文档**:
- https://langfuse.com/docs/observability/features/sessions
- https://langfuse.com/docs/observability/sdk/instrumentation

---

## 交付物清单

- [ ] `src/observability/session.py` - Session 管理器
- [ ] 更新的 `langfuse_client.py` - 支持 session 传播
- [ ] 更新的 `decorators.py` - 自动附加 session 元数据
- [ ] `docs/session-dashboard.md` - Session 可视化文档
- [ ] `scripts/test_session_tracing.py` - Session 追踪测试

---

## 成功标准

- [ ] 所有测试通过
- [ ] Session ID 在多个工具调用间正确传播
- [ ] Langfuse 控制台可查看 session replay
- [ ] 多个并发 session 正确隔离
