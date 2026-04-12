# 集成测试 Markers 添加指南

> **更新日期**: 2026-04-13  
> **状态**: 🔄 进行中  
> **目标**: 为所有集成测试添加 pytest markers

---

## 📋 当前状态

### 已完成 ✅
- [x] `tests/integration/test_alerting.py` - 已转换为 pytest 格式并添加 `@pytest.mark.integration`

### 待处理 ⏳
- [ ] `tests/integration/test_langfuse_connection.py` - 需要转换
- [ ] `tests/integration/test_prompt_versioning.py` - 需要转换
- [ ] `tests/integration/test_session_tracing.py` - 需要转换
- [ ] `tests/integration/test_success_failure_tracking.py` - 需要转换

---

## 🎯 Markers 定义

在 `pytest.ini` 中已定义的 markers:

```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, may use external services)
    slow: Slow running tests (> 5 seconds)
```

---

## 📝 转换步骤

### 步骤 1: 添加 pytest import

```python
# 之前
#!/usr/bin/env python3
import sys
import os

# 之后
"""Integration tests for XXX."""
import pytest
```

### 步骤 2: 移除脚本代码

```python
# 删除这些行
sys.path.insert(0, ...)
if __name__ == "__main__":
    main()
```

### 步骤 3: 添加 Markers

#### 方式 1: 类级别 marker（推荐）

```python
@pytest.mark.integration
class TestXXXIntegration:
    """Integration tests for XXX."""
    
    def test_example(self):
        """Test description."""
        assert True
```

#### 方式 2: 函数级别 marker

```python
@pytest.mark.integration
def test_example():
    """Test description."""
    assert True
```

#### 方式 3: 多个 markers

```python
@pytest.mark.integration
@pytest.mark.slow  # 如果测试执行时间 > 5秒
def test_slow_integration():
    """Slow integration test."""
    assert True
```

### 步骤 4: 清理 print 语句

```python
# 之前
print("✓ Test passed")

# 之后（可选，保留用于调试）
# print("✓ Test passed")  # 注释掉或使用 logging
```

---

## 🔧 示例转换

### 转换前（脚本格式）

```python
#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability.alerting import AlertManager

def test_example():
    print("=" * 60)
    print("Test Example")
    print("=" * 60)
    
    manager = AlertManager()
    assert manager is not None
    print("✓ Test passed")
    return True

if __name__ == "__main__":
    success = test_example()
    sys.exit(0 if success else 1)
```

### 转换后（pytest 格式）

```python
"""Integration tests for alerting system."""
import pytest
from src.observability.alerting import AlertManager


@pytest.mark.integration
class TestAlertingIntegration:
    """Integration tests for the alerting system."""

    def test_example(self):
        """Test example description."""
        manager = AlertManager()
        assert manager is not None
```

---

## 🚀 批量添加工具

已创建脚本: `scripts/add_test_markers.py`

**使用方法**:
```bash
cd /Users/bohaiqing/opensource/git/langfuse-examples/mcp-with-tracing
python scripts/add_test_markers.py
```

**注意**: 此脚本只能为已经是 pytest 格式的文件添加 markers，不能转换脚本格式的文件。

---

## 📊 测试运行命令

### 运行所有集成测试

```bash
# 使用 marker 过滤
pytest -m integration -v

# 或直接指定目录
pytest tests/integration/ -v
```

### 跳过慢速测试

```bash
# 跳过标记为 slow 的测试
pytest -m "integration and not slow" -v
```

### 只运行慢速测试

```bash
pytest -m slow -v
```

### 并发执行

```bash
# 集成测试通常不需要并发（可能有外部依赖）
pytest tests/integration/ -v -n 0
```

---

## ✅ 验证清单

转换完成后，检查以下项：

- [ ] 文件顶部有 docstring 说明
- [ ] 导入了 `pytest`
- [ ] 移除了 `sys.path.insert` 等脚本代码
- [ ] 添加了 `@pytest.mark.integration` marker
- [ ] 测试函数以 `test_` 开头
- [ ] 移除了 `if __name__ == "__main__"` 块
- [ ] 使用 `assert` 而非 `return True/False`
- [ ] 运行 `pytest -m integration -v` 全部通过

---

## 🐛 常见问题

### Q1: 测试找不到？

**原因**: 文件命名不符合 pytest 规范

**解决**: 确保文件名以 `test_` 开头
```bash
# ✅ 正确
test_example.py

# ❌ 错误
example_test.py
```

### Q2: Marker 不生效？

**原因**: pytest.ini 中未定义 marker

**解决**: 在 `pytest.ini` 中添加 marker 定义
```ini
[pytest]
markers =
    integration: Integration tests
```

### Q3: 导入错误？

**原因**: 使用了相对路径导入

**解决**: 使用绝对导入
```python
# ✅ 正确
from src.observability.alerting import AlertManager

# ❌ 错误
sys.path.insert(0, ...)
from observability.alerting import AlertManager
```

---

## 📚 参考文档

- [pytest markers 文档](https://docs.pytest.org/en/stable/how-to/mark.html)
- [测试组织指南](../docs/testing-organization.md)
- [并发测试配置](../docs/concurrent-testing-guide.md)

---

## 📝 更新历史

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-04-13 | 1.0.0 | 初始版本，完成 test_alerting.py 转换 |

---

**下一步**: 手动转换剩余的集成测试文件，或编写自动化脚本完成转换。
