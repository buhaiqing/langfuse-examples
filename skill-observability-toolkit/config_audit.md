# 配置审计报告

**项目**: skill-observability-toolkit  
**日期**: 2026-04-24  
**审计范围**: 所有 Python 源文件

---

## 执行摘要

- **总 Python 文件数**: 39 个
- **代码总行数**: 9,485 行
- **直接使用 `os.getenv` 的文件**: 3 个
- **直接使用 `os.getenv` 的调用次数**: 20+ 次
- **配置覆盖现状**: ~85% (config.py 已统一管理，但 CI 模块仍直接读取环境变量)

---

## 直接使用 os.getenv 的位置

### 1. CI/CD 模块 (3 个文件)

#### 文件 1: `ci/gitlab_ci.py`
```python
# 行号 ~3
return os.getenv("GITLAB_CI") == "true"
```

#### 文件 2: `ci/github_actions.py`
```python
# 行号 ~3
return os.getenv("GITHUB_ACTIONS") == "true"
```

#### 文件 3: `ci/context.py`
```python
# 行号 ~20-50
if os.getenv("GITHUB_ACTIONS") == "true":
    run_id = os.getenv("GITHUB_RUN_ID")
    workflow = os.getenv("GITHUB_WORKFLOW")
    job = os.getenv("GITHUB_JOB")
elif os.getenv("GITLAB_CI") == "true":
    pipeline_id = os.getenv("CI_PIPELINE_ID")
    stage = os.getenv("CI_JOB_STAGE")
    job = os.getenv("CI_JOB_NAME")
```

#### 文件 4: `ci/decorators.py`
```python
# 行号 ~30-70
if os.getenv("GITHUB_ACTIONS") == "true":
    "ci_trace_id": os.getenv("GITHUB_RUN_ID"),
    "ci_workflow": os.getenv("GITHUB_WORKFLOW"),
    "ci_job": os.getenv("GITHUB_JOB"),
    "ci_step": os.getenv("GITHUB_STEP"),
    "ci_run_number": os.getenv("GITHUB_RUN_NUMBER"),
    "ci_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
    "ci_actor": os.getenv("GITHUB_ACTOR"),
    "ci_repository": os.getenv("GITHUB_REPOSITORY"),
    "ci_ref": os.getenv("GITHUB_REF"),
```

---

## 配置对比分析

### 当前 config.py 已定义字段

```python
class ObservabilityConfig(BaseSettings):
    # Langfuse 配置
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str
    
    # Tracing 配置
    enable_tracing: bool
    trace_output_path: str | None
    
    # CI 环境配置 (已定义但未使用)
    ci_platform: str = "unknown"  # ← 已定义
    ci_trace_id: str | None       # ← 已定义，但未在 CI 模块使用
    
    # Logging 配置
    log_level: str
```

### 问题识别

**现状**: CI 模块使用了**两种配置方式并存**:
1. `config.py` 定义了 `ci_platform`, `ci_trace_id` 字段
2. 但实际代码中 CI 模块 (`ci/`) 仍直接调用 `os.getenv()`

**原因**: `config.py` 的 CI 字段通过`detect_ci_environment()` 自动检测，但 CI 模块未使用 `get_config()` 统一访问。

---

## 迁移计划

### 阶段 1: CI 环境变量统一 (优先级：高)

#### 需要修改的文件
| 文件 | 修改行数 | 环境变量 | 改为 config.xxx |
|------|----------|---------|-----------------|
| `ci/gitlab_ci.py` | 1 行 | GITLAB_CI | `get_config().ci_platform == "gitlab_ci"` |
| `ci/github_actions.py` | 1 行 | GITHUB_ACTIONS | `get_config().ci_platform == "github_actions"` |
| `ci/context.py` | 10 行 | GITHUB_*, CI_* | `get_config()` 集中获取 |
| `ci/decorators.py` | 15 行 | GITHUB_*, CI_* | `get_config()` 集中获取 |

#### config.py 需要新增的字段
```python
# 在 ObservabilityConfig 类中添加
ci_github_workflow: str | None = None
ci_github_job: str | None = None
ci_github_step: str | None = None
ci_github_run_number: str | None = None
ci_gitlab_pipeline: str | None = None
ci_gitlab_stage: str | None = None
```

#### 预计改动
- **总行数**: ~30 行修改
- **影响模块**: CI/CD tracing
- **风险**: 低 (向后兼容)

### 阶段 2: 其他模块审计 (优先级：中)

检查以下模块是否也需要统一:
- [ ] `integrations/` 模块
- [ ] `cli/` 模块
- [ ] 测试 fixtures

---

## 建议

### 1. config.py 增强
建议在 `config.py` 的`detect_ci_environment()` 方法中**自动填充**所有 CI 相关字段:

```python
def detect_ci_environment(self) -> dict[str, str | None]:
    if os.getenv("GITHUB_ACTIONS") == "true":
        # 填充所有 GitHub Actions 相关字段
        self.ci_platform = "github_actions"
        self.ci_trace_id = os.getenv("GITHUB_RUN_ID")
        self.ci_github_workflow = os.getenv("GITHUB_WORKFLOW")
        self.ci_github_job = os.getenv("GITHUB_JOB")
        # ... 其他字段
```

### 2. CI 模块重构
建议将 `ci/context.py` 的 CI 环境检测逻辑**合并到**`config.py`:

**当前**: CI 模块独立检测 + config.py 独立检测 (重复)  
**建议**: config.py 统一检测 → CI 模块使用 `get_config()`

### 3. 配置验证
建议在 `validate_config()` 中添加 CI 环境验证:

```python
def validate_config() -> list[str]:
    errors = []
    config = get_config()
    
    # 如果启用了 CI tracing 但未检测到 CI 环境
    if config.enable_tracing and config.ci_platform == "unknown":
        errors.append(
            "CI tracing enabled but not running in CI environment. "
            "Set CI environment variables or disable CI tracing."
        )
    
    return errors
```

---

## 统计结果

```bash
# 当前直接使用 os.getenv 的调用统计
$ grep -r "os.getenv" src/ --include="*.py" | grep -v config.py | wc -l
20+

# 主要集中在这 4 个文件
ci/github_actions.py:     1 次
ci/gitlab_ci.py:          1 次
ci/context.py:           8 次
ci/decorators.py:        10+ 次
```

---

## 下一步行动

### 立即执行 (Phase 1.3)
- [ ] 修改 `config.py` 添加 CI 详细字段
- [ ] 修改 `ci/github_actions.py` 使用 `get_config()`
- [ ] 修改 `ci/gitlab_ci.py` 使用 `get_config()`
- [ ] 修改 `ci/context.py` 重构为配置辅助函数
- [ ] 修改 `ci/decorators.py` 使用 `get_config()`

### 验证方法
```bash
# 修改后统计应显著减少
grep -r "os.getenv" src/ --include="*.py" | grep -v config.py
# 预期结果：仅保留 config.py 中的集中访问
```

---

**审计报告生成完成**  
**建议优先级**: High (CI 模块配置统一)  
**预计工作量**: 1-2 小时  
**影响范围**: CI/CD 追踪功能
