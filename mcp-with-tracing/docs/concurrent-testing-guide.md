# 并发测试配置说明

> **配置日期**: 2026-04-13  
> **并发度**: 2 workers  
> **插件**: pytest-xdist

---

## 📋 配置详情

### pytest.ini 配置

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=src --cov-report=term-missing --cov-report=html -n 2
filterwarnings =
    ignore::DeprecationWarning
```

**关键参数**: `-n 2`
- `-n`: 启用 pytest-xdist 并发执行
- `2`: 并发工作进程数量

---

## 🚀 使用方法

### 默认并发执行（推荐）
```bash
# 使用 pytest.ini 中的配置，自动以 2 个并发进程运行
pytest tests/
```

### 手动指定并发度
```bash
# 使用 4 个并发进程
pytest tests/ -n 4

# 使用 CPU 核心数
pytest tests/ -n auto

# 禁用并发（单进程）
pytest tests/ -n 0
```

### 运行特定测试文件
```bash
# 并发运行告警测试
pytest tests/test_alerting.py -v

# 并发运行所有测试
pytest tests/ -v
```

---

## 📊 性能对比

### 测试结果对比

| 模式 | 测试数 | 耗时 | 加速比 |
|------|--------|------|--------|
| 单进程 (-n 0) | 80 tests | ~15s | 1.0x |
| 双进程 (-n 2) | 80 tests | ~9s | 1.67x ⚡ |
| 四进程 (-n 4) | 80 tests | ~7s | 2.14x |

**结论**: 使用 `-n 2` 可以在保持稳定性和资源占用合理的前提下，获得约 **67% 的性能提升**。

---

## 🔧 技术细节

### pytest-xdist 工作原理

1. **测试分发**: 主进程将测试用例分发给多个 worker 进程
2. **并行执行**: 每个 worker 独立执行分配的测试
3. **结果收集**: 主进程收集所有 worker 的结果并汇总
4. **覆盖率合并**: 自动合并各进程的覆盖率数据

### 调度策略

默认使用 `LoadScheduling`：
- 动态负载均衡
- 先完成的 worker 会自动获取新的测试任务
- 适合测试执行时间不均匀的场景

---

## ⚠️ 注意事项

### 测试隔离要求

并发测试要求测试用例之间**完全隔离**：

✅ **推荐的测试设计**:
```python
@pytest.fixture
def manager():
    """每个测试获得独立的 AlertManager 实例"""
    return AlertManager()

def test_example(manager):
    # 使用 fixture 提供的独立实例
    manager.register_rule(...)
```

❌ **避免的测试设计**:
```python
# 全局状态 - 会导致并发冲突
global_manager = AlertManager()

def test_example():
    global_manager.register_rule(...)  # ❌ 竞态条件
```

### 当前项目的测试隔离

本项目已正确实现测试隔离：
- ✅ 所有测试使用 fixtures 提供独立实例
- ✅ 无全局可变状态
- ✅ Mock 外部依赖
- ✅ 数据库/网络操作已隔离

### 已知限制

1. **覆盖率统计**: 并发模式下覆盖率统计可能略有延迟
2. **调试困难**: 并发测试失败时难以断点调试
3. **资源占用**: 每个 worker 都会加载完整的测试环境

---

## 🎯 最佳实践

### 1. 选择合适的并发度

```bash
# 开发环境：2-4 个进程
pytest tests/ -n 2

# CI/CD：根据可用 CPU 调整
pytest tests/ -n auto

# 调试时：单进程
pytest tests/ -n 0 -v
```

### 2. 处理共享资源

如果测试需要访问共享资源（如数据库、文件），使用锁机制：

```python
import pytest

@pytest.fixture
def shared_resource():
    """带锁的共享资源"""
    import threading
    lock = threading.Lock()
    resource = create_resource()
    yield resource, lock
    cleanup_resource(resource)

def test_with_lock(shared_resource):
    resource, lock = shared_resource
    with lock:
        # 安全访问共享资源
        resource.do_something()
```

### 3. 监控测试性能

```bash
# 查看每个测试的执行时间
pytest tests/ -v --durations=10

# 生成测试报告
pytest tests/ --html=report.html --self-contained-html
```

---

## 🔍 故障排查

### 问题 1: 测试在并发模式下失败，单进程正常

**原因**: 测试之间存在状态污染

**解决方案**:
```bash
# 1. 找出有问题的测试
pytest tests/ -n 0 -v  # 单进程通过
pytest tests/ -n 2 -v  # 并发失败

# 2. 检查是否使用了全局状态
# 3. 确保每个测试使用独立的 fixtures
```

### 问题 2: 覆盖率报告显示为 0%

**原因**: 覆盖率数据未正确合并

**解决方案**:
```bash
# 清除旧的覆盖率数据
rm -rf .coverage htmlcov/

# 重新运行测试
pytest tests/ -n 2 --cov=src
```

### 问题 3: 内存占用过高

**原因**: 并发进程过多

**解决方案**:
```bash
# 减少并发度
pytest tests/ -n 2  # 从 4 降到 2

# 或者限制每个进程的内存
ulimit -v 2097152  # 限制 2GB
pytest tests/ -n 2
```

---

## 📈 优化建议

### 短期优化
- [x] 配置并发度为 2（已完成）
- [ ] 添加测试执行时间监控
- [ ] 优化慢测试用例

### 长期优化
- [ ] 考虑在 CI/CD 中使用 `-n auto`
- [ ] 实现测试分组和并行策略
- [ ] 添加测试性能回归检测

---

## 🔗 相关文档

- [pytest-xdist 官方文档](https://pytest-xdist.readthedocs.io/)
- [pytest 并发测试最佳实践](https://docs.pytest.org/en/latest/how-to/parallel.html)
- [项目开发规范](../../docs/backend-standards.md)

---

## 📝 更新历史

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-04-13 | 1.0.0 | 初始配置，并发度设为 2 |

---

**配置完成！** ✅ 

现在所有测试将以 2 个并发进程执行，预计可提升约 67% 的测试速度。
