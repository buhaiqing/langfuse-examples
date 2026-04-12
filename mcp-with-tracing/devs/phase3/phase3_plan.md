# Phase 3: 提示词版本管理 (Prompt Versioning) - 任务分解

> **阶段目标**: 追踪和比较不同提示词版本  
> **预计工作量**: 5 个子任务  
> **开始日期**: 2026-04-08  
> **状态**: 待开始

---

## 任务分解

### 任务 3.1: 实现提示词版本元数据注入
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- `src/observability/prompt_versioning.py`

**具体内容**:
1. 创建 PromptVersionManager 类
2. 实现版本注册和查询接口
3. 支持动态版本切换

**QA验证**:
- [ ] 运行测试: `python -m pytest tests/test_prompt_versioning.py -v`
- [ ] 版本注册和查询正常工作

---

### 任务 3.2: 将 `version` 属性附加到追踪
**分类**: deep | **技能**: [] | **优先级**: High

**输出文件**:
- 更新 `src/observability/langfuse_client.py`

**具体内容**:
1. 在 trace_tool_call 中自动附加 prompt_version
2. 使用 metadata 字段存储版本信息
3. 确保版本属性在所有子 observation 中可见

**QA验证**:
- [ ] Langfuse 控制台显示 prompt_version
- [ ] 版本信息在 trace 属性中可见

---

### 任务 3.3: 创建版本比较查询
**分类**: unspecified-high | **技能**: [] | **优先级**: Medium

**输出文件**:
- `scripts/query_prompt_versions.py`

**具体内容**:
1. 创建 Langfuse API 查询脚本
2. 按 version 分组统计成功率和延迟
3. 支持 A/B 测试结果对比

**QA验证**:
- [ ] 脚本可按版本查询追踪数据
- [ ] 输出版本比较统计

---

### 任务 3.4: 构建提示词有效性仪表板
**分类**: unspecified-high | **技能**: [] | **优先级**: Medium

**输出文件**:
- `docs/prompt-effectiveness-dashboard.md`

**具体内容**:
1. 文档说明如何在 Langfuse 创建 prompt 有效性 dashboard
2. 提供关键指标查询示例
3. 建议 dashboard 布局

**QA验证**:
- [ ] 文档完整可用
- [ ] 包含实际可用的查询

---

### 任务 3.5: 测试 A/B 切换场景
**分类**: quick | **技能**: [] | **优先级**: Medium

**输出文件**:
- `scripts/test_prompt_versioning.py`

**具体内容**:
1. 测试不同版本的追踪数据分离
2. 测试动态版本切换
3. 验证版本元数据正确传递

**QA验证**:
- [ ] 运行测试: `python scripts/test_prompt_versioning.py`
- [ ] 版本隔离正确

---

## 并行执行机会

| 波次 | 任务 | 依赖 |
|------|------|------|
| 1 | 3.1 (版本管理器) | 无 |
| 2 | 3.2 (附加版本属性) | 3.1 |
| 3 | 3.3 (版本查询) | 3.2 |
| 3 | 3.4 (仪表板文档) | 无 |
| 3 | 3.5 (A/B测试) | 3.2 |

---

## Langfuse 4.x 提示词版本 API

```python
# 在追踪时附加版本
with observer.trace_tool_call(
    tool_name="llm_tool",
    input_args=...,
    prompt_version="v1.0",
) as observation:
    # 版本自动附加到 metadata
    result = call_llm(prompt)
```

---

## 交付物清单

- [ ] `src/observability/prompt_versioning.py` - 版本管理器
- [ ] 更新的 `langfuse_client.py` - 支持版本传播
- [ ] `scripts/query_prompt_versions.py` - 版本查询脚本
- [ ] `docs/prompt-effectiveness-dashboard.md` - 仪表板文档
- [ ] `scripts/test_prompt_versioning.py` - 版本测试

---

## 成功标准

- [ ] 所有测试通过
- [ ] 版本元数据在 Langfuse 中正确显示
- [ ] 可按版本查询和比较追踪数据
- [ ] A/B 测试场景正常工作
