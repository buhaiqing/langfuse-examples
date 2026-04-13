# 测试快速参考

## 🚀 常用命令

### 使用 Makefile（推荐）

```bash
# 查看所有命令
make help

# 单元测试（开发时最快）
make test-unit

# 集成测试
make test-integration

# 所有测试
make test

# 快速测试（无覆盖率）
make test-fast

# HTML 覆盖率报告
make test-html
```

### 直接使用 pytest

```bash
# 所有测试
pytest tests/ -v -n 2

# 只运行单元测试
pytest tests/unit/ -v -n 2

# 只运行集成测试
pytest tests/integration/ -v

# 特定测试文件
pytest tests/unit/test_alerting.py -v

# 特定测试类
pytest tests/unit/test_alerting.py::TestAlertRule -v

# 特定测试方法
pytest tests/unit/test_alerting.py::TestAlertRule::test_create_basic_rule -v

# 无并发（调试用）
pytest tests/unit/ -v -n 0
```

---

## 📁 测试位置

| 类型 | 路径 | 数量 | 用途 |
|------|------|------|------|
| 单元测试 | `tests/unit/` | 80 tests | 快速反馈，隔离测试 |
| 集成测试 | `tests/integration/` | 18 tests | 端到端流程验证 |
| **总计** | `tests/` | **98 tests** | **完整验证** |

---

## 🎯 测试标记

```bash
# 只运行标记为 unit 的测试
pytest -m unit -v

# 只运行标记为 integration 的测试
pytest -m integration -v

# 排除慢速测试
pytest -m "not slow" -v
```

---

## 📊 覆盖率

```bash
# 终端显示
pytest --cov=src --cov-report=term-missing

# HTML 报告
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML 报告（CI/CD）
pytest --cov=src --cov-report=xml
```

---

## 🐛 调试技巧

```bash
# 显示测试执行时间
pytest --durations=10

# 遇到第一个失败就停止
pytest -x

# 详细输出
pytest -vv

# 显示 print 输出
pytest -s

#  pdb 调试
pytest --pdb
```

---

## 📝 编写测试

### 单元测试模板

```python
def test_example(self):
    # Arrange (准备)
    manager = AlertManager()
    
    # Act (执行)
    result = manager.check_rule("test", 50)
    
    # Assert (断言)
    assert result is not None
```

### 使用 Fixtures

```python
@pytest.fixture
def manager():
    """Provide fresh instance for each test."""
    return AlertManager()

def test_with_fixture(manager):
    # 使用 fixture
    manager.register_rule(...)
```

### Mock 外部依赖

```python
from unittest.mock import Mock, patch

@patch("module.Class")
def test_with_mock(self, mock_class):
    mock_class.return_value.method.return_value = "result"
    # 测试逻辑
```

---

## 🔧 配置

### pytest.ini 关键配置

```ini
[pytest]
testpaths = tests/unit tests/integration
addopts = -v --cov=src -n 2
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
```

---

## 💡 最佳实践

1. **开发时**: `make test-unit` （最快反馈）
2. **提交前**: `make test` （完整验证）
3. **查覆盖率**: `make test-html` （可视化报告）
4. **调试时**: `pytest -n 0 --pdb` （单进程 + 调试器）

---

## 📚 文档

- [测试组织指南](docs/testing-organization.md)
- [并发测试配置](docs/concurrent-testing-guide.md)
- [测试分离总结](devs/TEST_SEPARATION_SUMMARY.md)
- [项目完成总结](devs/PROJECT_COMPLETION_SUMMARY.md)

---

**快速开始**: `make test-unit` 🚀
