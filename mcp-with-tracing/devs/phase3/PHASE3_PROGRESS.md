# Phase 3: 集成测试 Markers 添加 - 进度报告

> **阶段**: Phase 3 补充任务  
> **开始日期**: 2026-04-13  
> **状态**: 🔄 进行中 (1/5 完成)

---

## 📋 任务概述

为所有集成测试文件添加 pytest markers，以便更好地组织和管理测试。

### 目标
- ✅ 转换脚本格式的测试为 pytest 格式
- ✅ 添加 `@pytest.mark.integration` marker
- ✅ 可选添加 `@pytest.mark.slow` marker（对于执行时间 > 5秒的测试）
- ✅ 确保所有测试通过

---

## 📊 完成进度

| 文件 | 状态 | 测试数 | Marker | 备注 |
|------|------|--------|--------|------|
| test_alerting.py | ✅ 完成 | 4 | integration | 已转换为 pytest 格式 |
| test_langfuse_connection.py | ⏳ 待处理 | - | - | 需要转换 |
| test_prompt_versioning.py | ⏳ 待处理 | - | - | 需要转换 |
| test_session_tracing.py | ⏳ 待处理 | - | - | 需要转换（含异步） |
| test_success_failure_tracking.py | ⏳ 待处理 | - | - | 需要转换 |

**进度**: 1/5 (20%)

---

## ✅ 已完成工作

### 1. test_alerting.py 转换

**转换前**: 脚本格式
```python
#!/usr/bin/env python3
def test_alert_rule_creation():
    print("Test 1: Alert Rule Creation")
    ...
    return True
```

**转换后**: pytest 格式
```python
"""Integration tests for alerting system."""
import pytest

@pytest.mark.integration
class TestAlertingIntegration:
    """Integration tests for the alerting system."""
    
    def test_alert_rule_creation(self):
        """Test creating alert rules with various configurations."""
        rule = AlertRule(...)
        assert rule.name == "success-rate-low"
```

**测试结果**:
```bash
$ pytest tests/integration/test_alerting.py -v -m integration
============================ 4 passed in 12.90s ============================
```

✅ 所有 4 个测试通过  
✅ Marker 正确识别  
✅ 并发执行正常 (2 workers)

---

## 📝 待完成任务

### 2. test_langfuse_connection.py

**当前状态**: 脚本格式，需要转换

**任务**:
- [ ] 移除 `#!/usr/bin/env python3`
- [ ] 添加 docstring
- [ ] 导入 pytest
- [ ] 移除 `sys.path.insert`
- [ ] 转换为 pytest 类格式
- [ ] 添加 `@pytest.mark.integration` marker
- [ ] 移除 `if __name__ == "__main__"` 块
- [ ] 使用 assert 替代 return

**预计工作量**: 15 分钟

---

### 3. test_prompt_versioning.py

**当前状态**: 脚本格式，需要转换

**任务**:
- [ ] 转换为 pytest 格式
- [ ] 添加 `@pytest.mark.integration` marker
- [ ] 清理 print 语句

**预计工作量**: 15 分钟

---

### 4. test_session_tracing.py

**当前状态**: 脚本格式，包含异步测试，需要转换

**特殊考虑**:
- ⚠️ 包含异步测试 (`async def`)
- ⚠️ 需要 `@pytest.mark.asyncio` marker
- ⚠️ 可能需要 `@pytest.mark.slow` marker（并发测试较慢）

**任务**:
- [ ] 转换为 pytest 格式
- [ ] 添加 `@pytest.mark.integration` marker
- [ ] 为异步测试添加 `@pytest.mark.asyncio`
- [ ] 为慢速测试添加 `@pytest.mark.slow`
- [ ] 保持异步功能正常

**预计工作量**: 30 分钟

---

### 5. test_success_failure_tracking.py

**当前状态**: 脚本格式，需要转换

**任务**:
- [ ] 转换为 pytest 格式
- [ ] 添加 `@pytest.mark.integration` marker
- [ ] 清理代码

**预计工作量**: 15 分钟

---

## 🔧 技术细节

### Marker 使用规范

#### 基础用法
```python
@pytest.mark.integration
def test_example():
    """Integration test."""
    assert True
```

#### 多个 Markers
```python
@pytest.mark.integration
@pytest.mark.slow  # 执行时间 > 5秒
@pytest.mark.asyncio  # 异步测试
async def test_slow_async_integration():
    """Slow async integration test."""
    await asyncio.sleep(1)
    assert True
```

#### 类级别 Marker
```python
@pytest.mark.integration
class TestExampleIntegration:
    """All tests in this class are integration tests."""
    
    def test_1(self):
        pass
    
    def test_2(self):
        pass
```

---

## 🚀 运行命令

### 运行所有集成测试
```bash
pytest -m integration -v
```

### 跳过慢速测试
```bash
pytest -m "integration and not slow" -v
```

### 只运行慢速测试
```bash
pytest -m slow -v
```

### 运行特定文件的集成测试
```bash
pytest tests/integration/test_alerting.py -m integration -v
```

### 无并发运行（调试用）
```bash
pytest tests/integration/ -m integration -v -n 0
```

---

## 📚 参考文档

- [集成测试 Markers 指南](INTEGRATION_TEST_MARKERS_GUIDE.md)
- [测试组织指南](../docs/testing-organization.md)
- [并发测试配置](../docs/concurrent-testing-guide.md)
- [pytest markers 官方文档](https://docs.pytest.org/en/stable/how-to/mark.html)

---

## 🛠️ 工具和脚本

### 自动化脚本
- `scripts/add_test_markers.py` - 批量添加 markers（仅适用于已是 pytest 格式的文件）

**使用方法**:
```bash
python scripts/add_test_markers.py
```

**限制**: 不能转换脚本格式的文件，只能为已有 `import pytest` 的文件添加 markers。

---

## 🎯 下一步计划

### 短期（今天）
1. ✅ 完成 test_alerting.py 转换
2. ⏳ 转换 test_langfuse_connection.py
3. ⏳ 转换 test_prompt_versioning.py

### 中期（本周）
4. ⏳ 转换 test_session_tracing.py（含异步）
5. ⏳ 转换 test_success_failure_tracking.py
6. ⏳ 验证所有集成测试通过
7. ⏳ 更新文档

### 长期
- [ ] 为所有集成测试添加适当的 markers
- [ ] 建立 CI/CD 中的测试分组策略
- [ ] 添加测试执行时间监控

---

## 📊 质量标准

### 完成标准
- [x] test_alerting.py 转换完成
- [ ] 所有 5 个文件转换完成
- [ ] 所有测试通过 (`pytest -m integration -v`)
- [ ] Markers 正确工作
- [ ] 文档更新完成

### 代码质量
- [ ] 遵循 pytest 最佳实践
- [ ] 清晰的测试命名
- [ ] 完整的 docstrings
- [ ] 无 print 语句（或注释掉）
- [ ] 使用 assert 而非 return

---

## 🐛 已知问题

### 无

---

## 📝 更新历史

| 日期 | 版本 | 变更说明 | 负责人 |
|------|------|----------|--------|
| 2026-04-13 | 0.2.0 | 完成 test_alerting.py 转换 | AI |
| 2026-04-13 | 0.1.0 | 创建进度报告 | AI |

---

**当前状态**: 🔄 20% 完成 (1/5 文件)

**下一步**: 继续转换剩余的 4 个集成测试文件。
