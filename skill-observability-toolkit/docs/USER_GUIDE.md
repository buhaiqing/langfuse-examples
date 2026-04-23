# skill-observability-toolkit 用户手册

> **Agent Skill + CLI 可观测性增强方案** - 完整操作指南

---

## 目录

1. [系统概述](#1-系统概述)
2. [安装与配置](#2-安装与配置)
3. [CLI 命令详解](#3-cli-命令详解)
4. [Skill 开发指南](#4-skill-开发指南)
5. [追踪与分析](#5-追踪与分析)
6. [CI/CD 集成](#6-cicd-集成)
7. [Langfuse 可视化](#7-langfuse-可视化)
8. [故障排查](#8-故障排查)
9. [最佳实践](#9-最佳实践)

---

## 1. 系统概述

### 1.1 什么是 skill-observability-toolkit？

**核心定位**: Agent Skill 的透明化可观测性平台

**技术架构**: CLI 命令行工具 + Python SDK + Langfuse 集成

**解决问题**:
- ✅ Skill 执行黑盒 → 透明化追踪
- ✅ 问题定位困难 → Trace ID 精准定位
- ✅ 可靠性无量化 → Trust Score 科学评分
- ✅ 手动配置繁琐 → CLI 自动化流程

### 1.2 技术能力矩阵

| 能力层 | 功能模块 | 技术手段 | 用户价值 |
|---|---|---|---|
| **声明层** | Manifest 解析 | skill.yaml YAML Schema | Skill 能力透明声明 |
| **追踪层** | STOP Tracer | NDJSON + ContextVar | 执行过程完整记录 |
| **验证层** | Assertion Engine | 预置/后置断言 | 输入输出自动验证 |
| **集成层** | Langfuse SDK | 装饰器 + 客户端 | 可观测性平台统一 |
| **关联层** | Trace Propagation | Trace ID 传播 | 跨层 Trace 关联 |
| **命令层** | CLI Tools | 7 个命令 | 开发运维自动化 |

---

## 2. 安装与配置

### 2.1 系统要求

```bash
# Python 版本
Python 3.10+ (推荐 3.11 或 3.12)

# 操作系统
Linux / macOS / Windows (WSL)

# 包管理器
pip 或 uv (推荐 uv)
```

### 2.2 安装方式

#### 方式一：从源码安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/langfuse/langfuse-examples.git
cd langfuse-examples/skill-observability-toolkit

# 安装依赖
pip install -e .
# 或使用 uv（更快）
uv pip install -e .
```

#### 方式二：从 PyPI 安装

```bash
pip install skill-observability-toolkit
```

### 2.3 环境配置

```bash
# 创建配置文件
cp .env.example .env

# 编辑配置（必需）
vim .env
```

**必需配置项**:

```bash
# Langfuse 配置（云端）
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com

# 或 Langfuse 配置（私有化）
LANGFUSE_HOST=http://your-langfuse-server:3000

# OpenAI 配置（可选）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# 可选配置
ENVIRONMENT=development
LOG_LEVEL=INFO
ENABLE_TRACING=true
```

### 2.4 验证安装

```bash
# 检查 CLI 命令
stop --version
stop --help

# 验证配置
stop validate-config

# 测试连接
stop test-connection
```

---

## 3. CLI 命令详解

### 3.1 命令概览

```bash
stop <command> [options]

命令列表:
  init          创建新 Skill 项目
  validate      验证 skill.yaml Manifest
  run           执行 Skill 并追踪
  report        生成追踪报告
  compare       对比多个版本 Skill
  trust-score   计算 Trust Score
```

### 3.2 `stop init` - 项目初始化

**功能**: 创建完整的 Skill 项目骨架

**用法**:
```bash
stop init <skill-name> [options]

# 示例
stop init my-code-reviewer
stop init api-analyzer --template advanced
stop init data-processor --author "张三"
```

**生成文件**:
```
my-code-reviewer/
├── skill.yaml              # Skill Manifest
├── src/
│   ├── main.py            # 入口函数
│   ├── skill.py           # Skill 实现
│   └── tools.py           # 工具定义
├── tests/
│   ├── test_skill.py      # 单元测试
│   └── fixtures/          # 测试数据
├── .sop/
│   └── logs/              # 追踪日志目录
├── README.md              # Skill 说明
└── requirements.txt       # 依赖清单
```

**skill.yaml 结构**:
```yaml
sop: "1.0.0"
name: my-code-reviewer
version: "1.0.0"
description: "代码审查 Skill"

inputs:
  - name: code_path
    type: file_path
    required: true
    description: "待审查的代码路径"

outputs:
  - name: review_result
    type: json
    description: "审查结果报告"

assertions:
  pre:
    - check: file_exists
      path: inputs.code_path
      message: "代码文件必须存在"
  post:
    - check: output_exists
      path: outputs.review_result
      message: "必须生成审查结果"

trust_score:
  enabled: true
  history_window: 30
  min_pass_rate: 0.8

tools_used:
  - name: llm-analyzer
    version: "1.0.0"
    description: "LLM 代码分析工具"
```

### 3.3 `stop validate` - Manifest 验证

**功能**: 9 层校验 skill.yaml 结构完整性

**验证规则**:

| 层级 | 校验项 | 错误类型 | 严重性 |
|---|---|---|---|
| L1 | 必需字段 | `sop/name/version/description` 缺失 | **ERROR** |
| L2 | 字段格式 | name 非 kebab-case, version 非 semver | **ERROR** |
| L3 | Inputs 结构 | `name/type/required` 缺失 | **ERROR** |
| L4 | Outputs 结构 | `name/type` 缺失 | **ERROR** |
| L5 | Assertions 结构 | `check/message/type` 缺失或错误 | **ERROR** |
| L6 | Tools 引用 | `name/version` 缺失 | **ERROR** |
| L7 | Trust Score | 配置项缺失或格式错误 | **WARNING** |
| L8 | Tags 标签 | 格式不规范 | **WARNING** |
| L9 | Metadata | 非标准字段检查 | **INFO** |

**用法**:
```bash
stop validate [manifest-path]

# 默认路径
stop validate                   # 验证当前目录 skill.yaml

# 指定路径
stop validate path/to/skill.yaml

# 详细模式
stop validate --verbose

# 严格模式（Warning 也视为 Error）
stop validate --strict
```

**输出示例**:
```
ℹ️  Validating: skill.yaml

✅ Required fields: OK
✅ Field formats: OK
✅ Inputs structure: OK (3 inputs defined)
✅ Outputs structure: OK (2 outputs defined)
⚠️  Assertions: WARNING (no pre-checks defined)
✅ Tools reference: OK (1 tool referenced)
✅ Trust Score: OK
ℹ️  Tags: INFO (missing recommended tags: 'team', 'priority')
ℹ️  Metadata: INFO (unknown field: 'custom_config')

❌ Manifest has 1 error(s), 2 warning(s):

  1. ERROR: Missing pre-assertions. Pre-checks required for input validation.
```

### 3.4 `stop run` - Skill 执行追踪

**功能**: 执行 Skill 并生成 NDJSON 追踪日志

**用法**:
```bash
stop run [options]

# 基础执行
stop run

# 带参数执行
stop run --input '{"code_path": "/path/to/code.py"}'

# 指定 Skill 版本
stop run --version "1.2.0"

# 仅追踪模式（不执行 Skill）
stop run --trace-only

# 同步到 Langfuse
stop run --sync-langfuse

# 输出到文件
stop run --output trace.ndjson
```

**追踪日志格式** (NDJSON):
```json
{"timestamp": "2026-04-24T10:30:00Z", "trace_id": "skill_trace_abc123", "type": "trace_start", "name": "my-code-reviewer", "version": "1.0.0"}
{"timestamp": "2026-04-24T10:30:01Z", "trace_id": "skill_trace_abc123", "span_id": "span_001", "type": "span_start", "name": "skill.execute", "input": {"code_path": "/path/to/code.py"}}
{"timestamp": "2026-04-24T10:30:05Z", "trace_id": "skill_trace_abc123", "span_id": "span_002", "type": "span_start", "name": "tool.llm-analyzer", "parent_span_id": "span_001"}
{"timestamp": "2026-04-24T10:30:10Z", "trace_id": "skill_trace_abc123", "span_id": "span_002", "type": "span_end", "output": {"analysis": "..."}}
{"timestamp": "2026-04-24T10:30:15Z", "trace_id": "skill_trace_abc123", "span_id": "span_001", "type": "span_end", "output": {"review_result": {...}}, "status": "success"}
{"timestamp": "2026-04-24T10:30:16Z", "trace_id": "skill_trace_abc123", "type": "trace_end", "duration_ms": 16000, "trust_score": 1.0}
```

### 3.5 `stop report` - 追踪报告分析

**功能**: 解析追踪日志生成可视化报告

**用法**:
```bash
stop report [options]

# 最近 10 次追踪
stop report --last 10

# 指定时间范围
stop report --from "2026-04-20" --to "2026-04-24"

# 指定 Skill
stop report --skill "my-code-reviewer"

# 指定 Trace ID
stop report --trace-id "skill_trace_abc123"

# 导出格式
stop report --format json      # JSON 格式
stop report --format markdown  # Markdown 格式
stop report --format html      # HTML 格式
```

**报告内容**:
```
📊 Skill Execution Report - my-code-reviewer v1.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Trace ID: skill_trace_abc123
Duration: 16,000 ms (16 seconds)
Status: ✅ SUCCESS
Trust Score: 1.00 (100% assertions passed)

Execution Flow:
├── skill.execute (15,000ms)
│   ├── tool.llm-analyzer (5,000ms)
│   │   └─ Output: {analysis: "..."}
│   └─ Output: {review_result: {...}}

Assertions:
├── Pre-check: file_exists ✅ PASS
├── Post-check: output_exists ✅ PASS
└─ Trust Score: 2/2 passed = 1.00

Performance Metrics:
├── Total Duration: 16s
├── Tool Calls: 1
├── Success Rate: 100%
└─ Average Trust Score (last 30 days): 0.92
```

### 3.6 `stop compare` - 多版本对比

**功能**: A/B 测试 Skill 版本性能对比

**用法**:
```bash
stop compare <skill-name> --versions <v1,v2>

# 对比两个版本
stop compare my-code-reviewer --versions "1.0.0,1.1.0"

# 指定对比维度
stop compare my-code-reviewer --versions "1.0.0,1.1.0" --metrics "duration,trust_score"

# 输出对比报告
stop compare my-code-reviewer --versions "1.0.0,1.1.0" --output comparison.md
```

### 3.7 `stop trust-score` - 可靠性评分

**功能**: 计算 Skill 历史执行的 Trust Score

**Trust Score 公式**:
```
Trust Score = Σ(passed_assertions) / Σ(total_assertions)
```

**用法**:
```bash
stop trust-score <skill-name> [options]

# 计算当前 Trust Score
stop trust-score my-code-reviewer

# 历史范围
stop trust-score my-code-reviewer --days 30

# 详细断言分析
stop trust-score my-code-reviewer --verbose
```

**输出示例**:
```
🎯 Trust Score Report - my-code-reviewer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Trust Score: 0.92 (Excellent)

Last 30 Days Statistics:
├── Total Executions: 150
├── Successful: 138 (92%)
├── Failed: 12 (8%)

Assertion Analysis:
├── file_exists (pre): 150/150 passed (100%)
├── output_exists (post): 138/150 passed (92%)
└─ Overall: 288/300 = 0.96

Recommendations:
✅ Skill is production-ready (Trust Score > 0.90)
⚠️  Monitor 'output_exists' assertion (92% pass rate)
```

---

## 4. Skill 开发指南

### 4.1 基础 Skill 结构

**最小 Skill 示例**:

```python
# src/main.py
from skill_observability_toolkit import trace_skill_execution

@trace_skill_execution(skill_name="simple-skill", version="1.0.0")
def execute(input_data: dict) -> dict:
    """Skill 入口函数"""
    
    # 1. 输入处理
    processed_input = process_input(input_data)
    
    # 2. 核心逻辑
    result = core_logic(processed_input)
    
    # 3. 输出封装
    return format_output(result)
```

### 4.2 装饰器详解

#### @trace_skill_execution

**功能**: 自动追踪 Skill 执行全过程

**参数**:
```python
@trace_skill_execution(
    skill_name: str,       # Skill 名称
    version: str,          # Skill 版本
    trace_id: str = None,  # 指定 Trace ID
    session_id: str = None,# Session ID
    user_id: str = None,   # User ID
    metadata: dict = None  # 自定义元数据
)
```

**示例**:
```python
@trace_skill_execution(
    skill_name="code-reviewer",
    version="2.0.0",
    session_id="session_abc",
    user_id="user_123",
    metadata={"environment": "production", "team": "backend"}
)
def review_code(code_path: str) -> dict:
    return analyze_code(code_path)
```

#### @trace_tool_call

**功能**: 追踪 Skill 内部工具调用

**参数**:
```python
@trace_tool_call(
    tool_name: str,        # 工具名称
    tool_input: dict = None,# 工具输入
    trace_id: str = None   # 指定 Trace ID
)
```

**示例**:
```python
@trace_tool_call(tool_name="llm-analyzer")
def analyze_with_llm(code: str) -> dict:
    return llm_api_call(code)

@trace_tool_call(tool_name="file-reader")
def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()
```

### 4.3 断言定义

**skill.yaml 断言配置**:

```yaml
assertions:
  pre:
    # 输入验证断言
    - check: file_exists
      path: inputs.code_path
      message: "代码文件必须存在"
      
    - check: string_not_empty
      path: inputs.query
      message: "查询字符串不能为空"
      
    - check: type_is
      path: inputs.config
      expected_type: dict
      message: "配置必须是字典类型"
  
  post:
    # 输出验证断言
    - check: output_exists
      path: outputs.review_result
      message: "必须生成审查结果"
      
    - check: key_exists
      path: outputs.review_result.issues
      message: "结果必须包含 issues 字段"
      
    - check: list_not_empty
      path: outputs.review_result.issues
      message: "必须发现至少一个问题"
```

**内置断言类型**:

| 断言类型 | 校验内容 | 适用阶段 |
|---|---|---|
| `file_exists` | 文件存在检查 | Pre |
| `file_not_empty` | 文件非空检查 | Pre |
| `string_not_empty` | 字符串非空检查 | Pre/Post |
| `string_empty` | 字符串为空检查 | Pre/Post |
| `list_not_empty` | 列表非空检查 | Post |
| `list_empty` | 列表为空检查 | Post |
| `value_equal` | 值相等检查 | Post |
| `value_not_equal` | 值不等检查 | Post |
| `value_greater_than` | 值大于检查 | Post |
| `value_less_than` | 值小于检查 | Post |
| `value_in_range` | 值在范围内检查 | Post |
| `type_is` | 类型检查 | Pre/Post |
| `type_is_not` | 类型非检查 | Pre/Post |
| `key_exists` | 键存在检查 | Post |
| `key_not_exists` | 键不存在检查 | Post |

### 4.4 Trust Score 配置

```yaml
trust_score:
  enabled: true              # 启用 Trust Score
  history_window: 30         # 统计窗口（天）
  min_pass_rate: 0.8         # 最低通过率阈值
```

**Trust Score 决策规则**:

| Trust Score | 决策建议 |
|---|---|
| **≥ 0.90** | ✅ 生产就绪，推荐使用 |
| **0.80-0.90** | ⚠️ 需要监控，谨慎使用 |
| **0.60-0.80** | ❌ 不建议生产，仅测试 |
| **< 0.60** | ❌ 需要修复，不建议使用 |

---

## 5. 追踪与分析

### 5.1 追踪数据存储

**本地存储**:
```
.sop/logs/
├── 2026-04-24/
│   ├── skill_trace_abc123.ndjson
│   ├── skill_trace_def456.ndjson
│   └─ index.json          # 追踪索引
```

**云端同步**:
- Langfuse Cloud: 自动同步
- Langfuse 私有化: 配置 LANGFUSE_HOST

### 5.2 Trace ID 传播机制

**跨层传播链**:
```
CI Layer → Skill Layer → MCP Layer

ci_build_abc123 
    ↓ (自动继承)
skill_ci_build_abc123
    ↓ (自动继承)
mcp_skill_ci_build
```

**手动传播示例**:

```python
from skill_observability_toolkit.correlation.propagation import (
    propagate_ci_to_skill,
    propagate_skill_to_mcp,
    create_trace_chain
)

# CI → Skill
skill_trace_id = propagate_ci_to_skill("ci_build_abc123")

# Skill → MCP
mcp_trace_id = propagate_skill_to_mcp(skill_trace_id)

# 完整链
chain = create_trace_chain(
    ci_trace_id="ci_build_abc123",
    skill_trace_id="skill_ci_build_abc123",
    mcp_trace_id="mcp_skill_ci_build"
)
```

### 5.3 统一标签体系

**标签自动注入**:

```python
from skill_observability_toolkit.correlation.labels import (
    LabelManager,
    LabelType
)

manager = LabelManager()

# 注册标准标签
manager.add_label("service", "code-reviewer")
manager.add_label("version", "2.0.0")
manager.add_label("environment", "production")
manager.add_label("team", "backend")
manager.add_label("priority", "high")
manager.add_label("region", "cn-east")
```

---

## 6. CI/CD 集成

### 6.1 GitHub Actions 集成

**Workflow 配置**:

```yaml
# .github/workflows/skill-validation.yml
name: Skill Validation

on:
  push:
    paths:
      - 'skills/**'
  pull_request:
    paths:
      - 'skills/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Toolkit
        run: pip install skill-observability-toolkit
      
      - name: Validate Skills
        run: |
          for skill in skills/*/skill.yaml; do
            stop validate "$skill" --strict
          done
      
      - name: Run Skills
        run: |
          stop run --skill "skills/my-skill" --sync-langfuse
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
```

### 6.2 GitLab CI 集成

**Pipeline 配置**:

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - test
  - deploy

skill-validate:
  stage: validate
  script:
    - pip install skill-observability-toolkit
    - stop validate skills/*/skill.yaml --strict
    
skill-test:
  stage: test
  script:
    - stop run --skill "skills/my-skill" --sync-langfuse
  variables:
    LANGFUSE_PUBLIC_KEY: $LANGFUSE_PUBLIC_KEY
    LANGFUSE_SECRET_KEY: $LANGFUSE_SECRET_KEY
```

### 6.3 Build Profiler 集成

**构建分析示例**:

```python
from skill_observability_toolkit.ci.profiler import BuildProfiler

profiler = BuildProfiler()

# 分析构建步骤
with profiler.profile_step("compile"):
    compile_code()

with profiler.profile_step("test"):
    run_tests()

# 生成报告
report = profiler.generate_report()
```

---

## 7. Langfuse 可视化

### 7.1 Dashboard 集成

**Langfuse Dashboard 特性**:

| 特性 | 说明 |
|---|---|
| **Trace Timeline** | Skill 执行时间线可视化 |
| **Span Tree** | Span 调用树形结构 |
| **Assertion Scores** | 断言通过率统计 |
| **Trust Score Trend** | Trust Score 趋势图 |
| **Cost Tracking** | Token 消耗成本追踪 |

### 7.2 查询技巧

**Langfuse Trace 查询**:

```sql
-- 查询特定 Skill
WHERE name = 'my-code-reviewer'

-- 查询失败 Trace
WHERE status = 'error'

-- 查询低 Trust Score
WHERE metadata.trust_score < 0.80

-- 跨层关联查询
WHERE metadata.parent_trace_id = 'ci_build_abc123'
```

### 7.3 Grafana 集成

**Prometheus Metrics**:

```python
from skill_observability_toolkit.integrations.prometheus_exporter import (
    PrometheusExporter
)

exporter = PrometheusExporter()

# 导出 Metrics
exporter.export_skill_metrics(skill_name="my-skill")
```

**Grafana Dashboard 模板**:

```json
{
  "title": "Skill Observability Dashboard",
  "panels": [
    {
      "title": "Trust Score Trend",
      "type": "graph",
      "targets": [
        {
          "expr": "skill_trust_score{skill=\"my-skill\"}"
        }
      ]
    },
    {
      "title": "Execution Duration",
      "type": "heatmap",
      "targets": [
        {
          "expr": "skill_duration_ms{skill=\"my-skill\"}"
        }
      ]
    }
  ]
}
```

---

## 8. 故障排查

### 8.1 常见问题

#### 问题 1: Trace 未出现在 Langfuse

**症状**: `stop run` 执行成功，但 Langfuse Dashboard 无 Trace

**排查步骤**:
```bash
# 1. 检查配置
cat .env | grep LANGFUSE

# 2. 测试连接
curl -I https://cloud.langfuse.com/api/health

# 3. 强制同步
stop run --sync-langfuse --force

# 4. 检查日志
tail -f .sop/logs/errors.log
```

**解决方案**:
- ✅ 验证 LANGFUSE_PUBLIC_KEY/SECRET_KEY 正确
- ✅ 检查 LANGFUSE_HOST 是否可达
- ✅ 调用 `langfuse.flush()` 强制发送

#### 问题 2: 断言验证失败

**症状**: Pre-check 或 Post-check 报错

**排查步骤**:
```bash
# 1. 查看断言配置
stop validate --verbose

# 2. 检查断言详情
stop report --trace-id "skill_trace_xxx" --verbose

# 3. 手动测试断言
python -c "
from skill_observability_toolkit.stop.assertions import AssertionEngine
engine = AssertionEngine()
result = engine.execute('file_exists', {'path': '/tmp/test.txt'})
print(result)
"
```

#### 问题 3: Trust Score 异常

**症状**: Trust Score 计算不准确

**排查步骤**:
```bash
# 1. 查看历史数据
stop trust-score my-skill --verbose --days 30

# 2. 检查断言历史
grep "assertion" .sop/logs/*.ndjson | wc -l

# 3. 重算 Trust Score
stop trust-score my-skill --recalculate
```

### 8.2 日志查看

**日志位置**:
```
.sop/logs/
├── app.log               # 应用日志
├── trace.log             # 追踪日志
├── error.log             # 错误日志
└── debug.log             # 调试日志（LOG_LEVEL=DEBUG）
```

**日志级别配置**:
```bash
# .env
LOG_LEVEL=DEBUG    # 详细日志
LOG_LEVEL=INFO     # 正常日志
LOG_LEVEL=WARNING  # 仅警告
LOG_LEVEL=ERROR    # 仅错误
```

---

## 9. 最佳实践

### 9.1 Skill 设计原则

#### 原则 1: 单一职责

**每个 Skill 只做一件事**:

```yaml
# Good: 单一职责
name: code-quality-checker
description: "检查代码质量指标"

# Bad: 多职责混杂
name: code-review-and-deploy
description: "代码审查并自动部署"
```

#### 原则 2: 明确输入输出

**完整的输入输出定义**:

```yaml
inputs:
  - name: code_path
    type: file_path
    required: true
    description: "待检查代码路径"
    constraints:
      max_size_mb: 10
      
outputs:
  - name: quality_report
    type: json
    description: "质量报告"
    properties:
      score: number
      issues: array
      recommendations: array
```

#### 原则 3: 断言全覆盖

**完整的断言体系**:

```yaml
assertions:
  pre:
    - check: file_exists        # 文件存在
      path: inputs.code_path
    - check: file_not_empty     # 文件非空
      path: inputs.code_path
    - check: type_is            # 类型正确
      path: inputs.config
      expected_type: dict
      
  post:
    - check: output_exists      # 输出存在
      path: outputs.quality_report
    - check: key_exists         # 关键字段存在
      path: outputs.quality_report.score
    - check: value_in_range     # 值在合理范围
      path: outputs.quality_report.score
      min: 0.0
      max: 100.0
```

### 9.2 CLI 工作流最佳实践

**推荐工作流**:

```bash
# 1. 创建 Skill
stop init my-skill --template advanced

# 2. 编写实现
vim src/skill.py

# 3. 本地验证
stop validate --strict

# 4. 本地测试
stop run --input '{"test": "data"}' --verbose

# 5. 查看报告
stop report --last 1 --verbose

# 6. CI 集成
git add skills/my-skill/
git commit -m "Add my-skill"
git push

# 7. 生产部署
stop trust-score my-skill --days 7
# 若 Trust Score >= 0.90，则部署
```

### 9.3 Trust Score 目标设定

**不同场景的 Trust Score 目标**:

| Skill 类型 | 最低 Trust Score | 推荐目标 |
|---|---|---|
| **生产关键 Skill** | 0.95 | 0.99 |
| **生产辅助 Skill** | 0.90 | 0.95 |
| **测试验证 Skill** | 0.80 | 0.90 |
| **实验性 Skill** | 0.70 | 0.80 |

### 9.4 成本优化策略

**Token 消耗优化**:

```python
# 1. 合理设置 Timeout
@trace_skill_execution(
    skill_name="fast-analyzer",
    version="1.0.0",
    timeout_seconds=30  # 避免长时间运行
)

# 2. 输入预处理（减少无效调用）
def preprocess_input(input_data):
    if not validate_input(input_data):
        return {"error": "invalid input"}  # 早返回
    
    # 仅有效输入才调用 LLM
    return analyze_with_llm(input_data)

# 3. 缓存机制
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_analysis(code_hash: str):
    return analyze_code(code_hash)
```

---

## 附录

### A. 命令参考卡

```
┌─────────────────────────────────────────────────────────┐
│           stop CLI 命令速查表                              │
├─────────────────────────────────────────────────────────┤
│ stop init <name>              创建 Skill 项目             │
│ stop validate [path]          验证 Manifest               │
│ stop run [options]            执行 Skill 并追踪            │
│ stop report [options]         生成追踪报告                 │
│ stop compare <skill>          版本对比                    │
│ stop trust-score <skill>      计算可靠性评分               │
│ stop --help                   显示帮助                    │
│ stop --version                显示版本                    │
└─────────────────────────────────────────────────────────┘
```

### B. 配置模板

```bash
# .env.example - 完整配置模板

# Langfuse 配置（必需）
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com

# OpenAI 配置（可选）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# 运行环境
ENVIRONMENT=development
LOG_LEVEL=INFO
ENABLE_TRACING=true

# Trust Score 配置
TRUST_SCORE_HISTORY_WINDOW=30
TRUST_SCORE_MIN_PASS_RATE=0.8

# 存储配置
TRACE_LOG_DIR=.sop/logs
TRACE_SYNC_INTERVAL=60  # seconds

# 性能配置
MAX_TRACE_SIZE_MB=10
MAX_SPAN_DEPTH=10
```

### C. 常用代码片段

**快速追踪模板**:
```python
from skill_observability_toolkit import (
    trace_skill_execution,
    trace_tool_call
)

@trace_skill_execution(skill_name="my-skill", version="1.0.0")
def execute(input_data: dict) -> dict:
    # 工具调用
    data = read_data(input_data["path"])
    result = analyze_data(data)
    return {"result": result}

@trace_tool_call(tool_name="data-reader")
def read_data(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()

@trace_tool_call(tool_name="data-analyzer")
def analyze_data(data: str) -> dict:
    return {"analysis": "..."}
```

---

**文档版本**: v1.0  
**更新日期**: 2026-04-24  
**维护者**: 平台团队  
**反馈渠道**: GitHub Issues