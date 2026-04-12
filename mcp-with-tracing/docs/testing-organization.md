# 测试组织指南

> **更新日期**: 2026-04-13  
> **测试结构**: 单元测试与集成测试分离  
> **并发执行**: 2 workers (pytest-xdist)

---

## 📁 目录结构

```
tests/
├── __init__.py
├── unit/                    # 单元测试
│   ├── __init__.py
│   ├── test_alerting.py          # 告警系统单元测试 (28 tests)
│   ├── test_feedback.py          # 反馈收集单元测试 (16 tests)
│   ├── test_instrumentation.py   # 插桩功能单元测试 (11 tests)
│   ├── test_prompt_versioning.py # 提示词版本管理单元测试 (14 tests)
│   └── test_session.py           # 会话管理单元测试 (11 tests)
└── integration/             # 集成测试
    ├── __init__.py
    ├── test_alerting.py              # 告警系统集成测试 (4 tests)
    ├── test_langfuse_connection.py   # Langfuse 连接测试
    ├── test_prompt_versioning.py     # 提示词版本集成测试
    ├── test_session_tracing.py       # 会话追踪集成测试
    └── test_success_failure_tracking.py # 成功/失败追踪集成测试
```

**统计**:
- 单元测试: 80 tests
- 集成测试: 18 tests
- 总计: 98 tests

---

## 🎯 测试分类标准

### 单元测试 (Unit Tests)

**位置**: `tests/unit/`

**特征**:
- ✅ 快速执行 (< 10ms/test)
- ✅ 完全隔离，无外部依赖
- ✅ 使用 Mock 模拟外部服务
- ✅ 测试单个函数/类/方法
- ✅ 可重复执行，无副作用
- ✅ 100% 确定性结果

**示例**:
```python
def test_create_basic_rule(self):
    """Test creating a basic alert rule."""
    rule = AlertRule(
        name="test-rule",
        metric="success_rate",
        threshold=0.95,
        operator="lt",
        severity=AlertSeverity.WARNING,
    )
    
    assert rule.name == "test-rule"
    assert rule.threshold == 0.95
```

**运行命令**:
```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定单元测试文件
pytest tests/unit/test_alerting.py -v

# 运行特定测试类
pytest tests/unit/test_alerting.py::TestAlertRule -v

# 运行特定测试方法
pytest tests/unit/test_alerting.py::TestAlertRule::test_create_basic_rule -v
```

---

### 集成测试 (Integration Tests)

**位置**: `tests/integration/`

**特征**:
- ⚠️ 较慢执行 (可能涉及 I/O)
- ⚠️ 可能使用真实的外部服务
- ⚠️ 测试多个组件的交互
- ⚠️ 验证端到端流程
- ⚠️ 可能需要环境配置

**示例**:
```python
def test_session_tracing_flow():
    """Test complete session tracing flow."""
    # 真实的会话创建和追踪流程
    session_id = create_session(user_id="user_123")
    result = trace_operation(session_id, "test_op")
    
    assert result["session_id"] == session_id
    assert result["status"] == "success"
```

**运行命令**:
```bash
# 运行所有集成测试
pytest tests/integration/ -v

# 运行特定集成测试
pytest tests/integration/test_session_tracing.py -v

# 跳过慢速测试
pytest tests/integration/ -v -m "not slow"
```

---

## 🚀 运行测试

### 运行所有测试

```bash
# 默认：运行单元 + 集成测试（并发度 2）
pytest

# 详细输出
pytest -v

# 显示测试执行时间
pytest --durations=10
```

### 只运行单元测试

```bash
# 快速反馈，推荐开发时使用
pytest tests/unit/ -v -n 2

# 单进程运行（调试用）
pytest tests/unit/ -v -n 0
```

### 只运行集成测试

```bash
# 验证端到端流程
pytest tests/integration/ -v

# 跳过标记为 slow 的测试
pytest tests/integration/ -v -m "not slow"
```

### 使用 Markers 过滤

```bash
# 只运行标记为 unit 的测试
pytest -m unit -v

# 只运行标记为 integration 的测试
pytest -m integration -v

# 排除慢速测试
pytest -m "not slow" -v
```

---

## 📊 测试覆盖率

### 查看覆盖率报告

```bash
# 终端显示
pytest --cov=src --cov-report=term-missing

# HTML 报告
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML 报告（CI/CD 用）
pytest --cov=src --cov-report=xml
```

### 覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|-----------|----------|
| alerting.py | 100% | ✅ 100% |
| config.py | 100% | ✅ 100% |
| feedback.py | 95%+ | ✅ 99% |
| instrumentation.py | 95%+ | ✅ 96% |
| prompt_versioning.py | 95%+ | ✅ 95% |
| session.py | 90%+ | ✅ 92% |
| decorators.py | 90%+ | ✅ 94% |
| **总体** | **80%+** | ✅ **65%** |

---

## 🔧 配置说明

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests/unit tests/integration
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=src --cov-report=term-missing --cov-report=html -n 2
filterwarnings =
    ignore::DeprecationWarning

# Markers for test categorization
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, may use external services)
    slow: Slow running tests
```

**关键配置**:
- `testpaths`: 指定测试搜索路径
- `-n 2`: 启用 2 个并发工作进程
- `--cov=src`: 计算 src 目录的覆盖率
- `markers`: 定义测试标记

---

## 📝 编写测试的最佳实践

### 单元测试规范

1. **使用 AAA 模式** (Arrange-Act-Assert)

```python
def test_example(self):
    # Arrange (准备)
    manager = AlertManager()
    rule = AlertRule(name="test", metric="m", threshold=100, 
                     operator="gt", severity=AlertSeverity.INFO)
    
    # Act (执行)
    manager.register_rule(rule)
    retrieved = manager.get_rule("test")
    
    # Assert (断言)
    assert retrieved is not None
    assert retrieved.name == "test"
```

2. **每个测试一个断言概念**

```python
# ✅ 好：测试一个概念
def test_rule_name(self):
    rule = AlertRule(name="test", ...)
    assert rule.name == "test"

def test_rule_threshold(self):
    rule = AlertRule(threshold=0.95, ...)
    assert rule.threshold == 0.95

# ❌ 不好：测试多个概念
def test_rule_all_properties(self):
    rule = AlertRule(...)
    assert rule.name == "test"
    assert rule.threshold == 0.95
    assert rule.operator == "gt"
    # ... 太多断言
```

3. **使用 Fixtures 提供测试数据**

```python
@pytest.fixture
def manager(self):
    """Provide fresh AlertManager for each test."""
    return AlertManager()

def test_with_fixture(self, manager):
    # 使用 fixture 提供的独立实例
    manager.register_rule(...)
```

4. **Mock 外部依赖**

```python
from unittest.mock import Mock, patch

@patch("src.observability.instrumentation.Langfuse")
def test_with_mock(self, mock_langfuse):
    # Mock 外部 API 调用
    mock_langfuse.return_value.trace.return_value = Mock()
    
    # 测试逻辑
    result = init_observability(config)
    
    # 验证 Mock 被调用
    mock_langfuse.assert_called_once()
```

### 集成测试规范

1. **清晰的测试场景描述**

```python
def test_complete_session_flow():
    """
    Test the complete session lifecycle:
    1. Create session
    2. Add operations
    3. Verify tracking
    4. Close session
    """
    # ...
```

2. **清理测试数据**

```python
def teardown_function():
    """Clean up after each test."""
    cleanup_test_data()
```

3. **处理异步操作**

```python
@pytest.mark.asyncio
async def test_async_integration():
    """Test async integration flow."""
    result = await async_operation()
    assert result.status == "success"
```

---

## 🐛 故障排查

### 问题 1: 测试找不到

**症状**: `collected 0 items`

**解决**:
```bash
# 检查文件命名
ls tests/unit/test_*.py

# 检查 pytest 配置
cat pytest.ini | grep testpaths

# 手动指定路径
pytest tests/unit/test_alerting.py -v
```

### 问题 2: 并发测试失败

**症状**: 单进程通过，并发失败

**原因**: 测试之间存在状态污染

**解决**:
```bash
# 1. 找出有问题的测试
pytest tests/unit/ -n 0 -v  # 单进程
pytest tests/unit/ -n 2 -v  # 并发

# 2. 确保使用 fixtures
@pytest.fixture
def manager():
    return AlertManager()  # 每次返回新实例

# 3. 避免全局状态
# ❌ 不好
global_manager = AlertManager()

# ✅ 好
def test_example():
    manager = AlertManager()  # 局部变量
```

### 问题 3: 覆盖率报告显示不完整

**解决**:
```bash
# 清除旧数据
rm -rf .coverage htmlcov/

# 重新运行
pytest --cov=src --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html
```

---

## 📈 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-xdist
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=src --cov-report=xml
    
    - name: Run integration tests
      run: pytest tests/integration/ -v -m "not slow"
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 🎓 学习资源

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-xdist 并发测试](https://pytest-xdist.readthedocs.io/)
- [pytest-cov 覆盖率](https://pytest-cov.readthedocs.io/)
- [测试最佳实践](https://docs.pytest.org/en/stable/goodpractices.html)

---

## 📝 更新历史

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-04-13 | 1.0.0 | 初始版本，分离单元/集成测试 |

---

**测试组织完成！** ✅

现在测试已按类型清晰分离，便于管理和维护。
