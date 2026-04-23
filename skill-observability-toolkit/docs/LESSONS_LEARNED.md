# 开发经验教训总结

> 本文档记录开发过程中遇到的关键问题、根因分析和预防措施，避免后续重复犯错。

---

## 一、API契约不匹配问题

### 问题现象
- **test_validate.py**: 测试调用`ManifestParser.load()`，但实现只有`parse()`方法
- **test_validate.py**: 验证逻辑期望`input_field.constraints`字段，但`SkillInput`类未定义
- **test_tracer.py**: 测试期望`TracerContextNotInitialized`异常，但实现抛出`TracingError`

### 根因分析
```
测试期望 ≠ 实现现实
      ↓
原因：测试先行编写，实现后补，两者未同步
      ↓
深层：缺乏API设计文档，测试与实现各自理解需求
```

### 预防措施

**MUST DO（强制执行）**:
1. **API先行定义**：开发前先定义接口契约（函数签名、类属性、异常类型）
2. **测试驱动验证**：实现前先写测试，确保API契约明确
3. **属性完整性检查**：dataclass新增字段后，立即更新`to_dict()`和相关验证逻辑

**开发流程改进**:
```python
# Step 1: 定义API契约（写在docstring或接口文件）
class ManifestParser:
    def load(self, path: str) -> SkillManifest:  # 明确声明
        """Load from file path"""
        
    def parse(self, content: str) -> SkillManifest:
        """Parse from YAML content"""

# Step 2: 测试先行验证契约
def test_load_method_exists():
    parser = ManifestParser()
    assert hasattr(parser, 'load')  # 契约验证

# Step 3: 实现同步契约
def load(self, path: str) -> SkillManifest:
    return self.parse(self._read_file(path))
```

---

## 二、异常处理错误模式

### 问题现象
```python
# 错误写法（导致TypeError）
try:
    data = yaml.safe_load(content)
except yaml.YAMLError as e:
    raise ManifestParseError from e(f"Failed to parse YAML: {e}")
    # 错误：from e(...) - e是异常对象，不可调用
```

### 根因分析
```
Python异常链语法混淆：
- raise X from Y  ← Y必须是异常对象
- raise X("msg") from Y ← 正确写法
```

### 预防措施

**正确异常处理模式**:
```python
# 模式1：保留原始异常链
try:
    data = yaml.safe_load(content)
except yaml.YAMLError as e:
    raise ManifestParseError(f"Failed to parse YAML: {e}") from e

# 模式2：不保留链（独立异常）
try:
    validate(data)
except ValidationError as e:
    raise ManifestValidationError(str(e))  # 无from

# 模式3：异常转换
try:
    risky_operation()
except OriginalError:
    raise NewError("context message") from None
```

---

## 三、ContextVar类型注解陷阱

### 问题现象
```python
# 问题写法
ctx_span_stack: ContextVar[list | None] = ContextVar("span_stack", default=None)

# 测试期望
assert ctx.ctx_span_stack.get() == []  # None != []
```

### 根因分析
```
ContextVar设计缺陷：
- default=None → 初始值None
- 测试期望空列表[] → 类型注解与默认值不一致
- end_trace()后应重置为[]，而非None
```

### 预防措施

**ContextVar最佳实践**:
```python
# 正确模式：类型注解与默认值一致
ctx_span_stack: ContextVar[list[dict]] = ContextVar("span_stack", default=[])

# 重置逻辑
def end_trace(self):
    self.ctx_trace_id.set(None)
    self.ctx_span_stack.set([])  # 保持类型一致

# 初始化检查
def get_current_span(self) -> dict | None:
    stack = self.ctx_span_stack.get()
    return stack[-1] if stack else None  # 空列表自然处理
```

---

## 四、测试数据管理问题

### 问题现象
- 26个测试文件被删除未恢复
- fixture数据与测试期望不匹配
- `conftest.py`缺失导致fixture依赖失败

### 根因分析
```
Git操作失误：
- git restore未及时执行
- 测试数据在worktree中被修改，主仓库未同步
- fixture定义分散，未集中管理
```

### 预防措施

**测试数据管理规范**:
1. **集中fixture定义**：所有测试fixture统一在`tests/conftest.py`
2. **Git恢复自动化**：开发前先执行`git status`检查删除文件
3. **fixture文档化**：每个fixture添加docstring说明用途

```python
# conftest.py最佳实践
@pytest.fixture
def valid_skill_content() -> str:
    """标准有效skill YAML内容（用于parse测试）"""
    return """
    sop: "1.0.0"
    name: api-expert-skill
    version: "1.0.0"
    ...
    """

@pytest.fixture
def valid_manifest(valid_skill_content) -> SkillManifest:
    """已解析的SkillManifest对象"""
    parser = ManifestParser()
    return parser.parse(content=valid_skill_content)
```

---

## 五、委托机制失败问题

### 问题现象
- explore/librarian agents因"certificate error"失败
- task启动失败"Model not found: opencode/claude-haiku-4-5"

### 根因分析
```
外部依赖问题：
- 网络证书验证失败
- 模型配置与实际可用模型不匹配
- 后台任务超时未处理
```

### 预防措施

**委托容错策略**:
1. **失败降级**：agent失败后立即切换到直接工具执行
2. **超时设置**：后台任务设置合理timeout（60s-120s）
3. **结果验证**：委托返回后检查`status: error`，立即fallback

```python
# 委托容错模式
try:
    result = task(subagent_type="explore", ...)
    if result.status == "error":
        # 降级到直接grep
        result = grep(pattern, output_mode="content")
except Exception:
    # 网络问题fallback
    result = read(file_path)
```

---

## 六、TODO清理延迟问题

### 问题现象
- 代码中遗留6个TODO标记未实现
- TODO标记无优先级标注
- 长期TODO累积影响代码质量

### 根因分析
```
开发习惯问题：
- TODO视为"可接受"的临时状态
- 未建立TODO清理机制
- 缺乏TODO追踪流程
```

### 预防措施

**TODO管理规范**:
1. **即时实现**：TODO仅在开发过程中短暂存在，commit前必须清理
2. **分类标注**：TODO必须标注优先级（CRITICAL/MEDIUM/LOW）
3. **定期扫描**：每周执行`grep TODO`检查累积情况

```python
# TODO标注规范
# TODO: [MEDIUM] Implement storage (file, database, etc.) - @bohaiqing - 2026-04-24
# TODO: [CRITICAL] Fix validation logic before release - Must complete today
# TODO: [LOW] Add caching optimization - Can defer to next sprint
```

---

## 七、覆盖率提升策略

### 问题现象
- 当前覆盖率48%，大量模块0%
- 测试集中在少数模块，边界情况未覆盖
- CLI模块、集成模块缺乏测试

### 根因分析
```
测试策略失衡：
- 只测试"容易测"的部分
- 边界条件、异常路径被忽略
- 集成测试依赖外部服务，难以执行
```

### 预防措施

**覆盖率提升计划**:
1. **按模块优先级补充测试**：
   - 高：stop/*, core/* (核心业务)
   - 中：cli/*, ci/* (用户交互)
   - 低：integrations/* (外部依赖)

2. **测试类型完整性**：
   - 正常路径：基础功能验证
   - 边界路径：空值、极限值、错误格式
   - 异常路径：网络错误、权限错误、资源耗尽

3. **覆盖率目标设定**：
   - 核心模块：>90%
   - CLI模块：>70%
   - 集成模块：>50%（允许mock）

---

## 八、预防措施总结表

| 问题类型 | 核心教训 | 预防措施 | 检查频率 |
|---------|---------|---------|---------|
| API契约不匹配 | 测试先行定义契约 | 实现前写测试验证API | 每次开发 |
| 异常处理错误 | from语法正确使用 | 异常链严格按规范 | 代码提交 |
| ContextVar陷阱 | 类型注解=默认值 | 初始化类型一致检查 | 类定义 |
| 测试数据管理 | fixture集中+Git检查 | 开发前检查git status | 每次开发 |
| 委托机制失败 | agent失败降级 | 网络问题fallback策略 | 任务委托 |
| TODO清理延迟 | commit前必须清理 | TODO标注优先级+扫描 | 每次提交 |
| 覆盖率不足 | 按优先级补充测试 | 边界+异常路径覆盖 | 每周 |

---

## 九、开发流程改进建议

### 开发前检查清单
```bash
# 1. Git状态检查
git status --porcelain | grep "^D"  # 检查删除文件
git restore --source=HEAD tests/unit/test_*.py  # 恢复测试

# 2. API契约检查
grep -r "def load\|def parse" src/ | head -20  # 确认方法存在
grep -r "class.*Parser\|class.*Context" tests/  # 测试期望确认

# 3. TODO扫描
grep -r "TODO:" src/ | wc -l  # 应为0或标注清晰

# 4. Coverage基线
pytest --cov=src --cov-report=term-missing | grep "TOTAL"
```

### 开发中验证流程
1. **增量测试**：每实现一个功能，立即运行相关测试
2. **类型检查**：修改dataclass后，运行`mypy`验证
3. **契约验证**：新增方法后，检查测试是否能调用

### 开发后交付检查
```bash
# 提交前完整验证
pytest tests/ -v --tb=short
pytest --cov=src --cov-fail-under=80
grep -r "TODO:" src/  # 应无遗留
ruff check src/ tests/
black --check src/ tests/
```

---

**文档版本**: v1.0  
**更新日期**: 2026-04-24  
**维护者**: 开发团队  
**下次审查**: 2026-05-01