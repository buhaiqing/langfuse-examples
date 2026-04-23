# Skill Observability Toolkit 设计文档

> **项目**: skill-observability-toolkit  
> **版本**: 1.0.0  
> **最后更新**: 2026-04-23  
> **协议版本**: STOP 0.1  
> **位置**: langfuse-examples/skill-observability-toolkit

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [核心模块设计](#3-核心模块设计)
4. [数据流设计](#4-数据流设计)
5. [API 设计](#5-api-设计)
6. [目录结构设计](#6-目录结构设计)
7. [实施计划](#7-实施计划)
8. [测试策略](#8-测试策略)
9. [部署方案](#9-部署方案)

---

## 1. 项目概述

### 1.1 项目背景

Agent Skill 生态正在爆发,但 Skill 执行过程是黑盒。STOP (Skill Transparency & Observability Protocol) 是一个开放规范,让 Skill 的能力声明、执行追踪、结果验证变得标准化和可观测。

本项目将 STOP Protocol 与 Langfuse 深度集成,实现端到端的 Skill 可观测性平台。

### 1.2 核心价值

| 价值点 | 说明 |
|--------|------|
| **Skill 透明化** | 通过 STOP Protocol 声明能力,追踪执行过程 |
| **端到端关联** | 从 CI/CD 构建到 Skill 执行到生产环境,完整 Trace 链路 |
| **Trust Score** | 量化 Skill 可信度,基于历史断言通过率 |
| **复用现有能力** | 复用 mcp-with-tracing 的告警和反馈系统 |

### 1.3 技术栈

- **Python**: 3.10+
- **追踪后端**: Langfuse Cloud / 私有化部署
- **协议版本**: STOP 0.1
- **CI 平台**: GitHub Actions (优先), GitLab CI

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         端到端可观测性平台                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    统一可视化层 (Unified View)                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │    │
│  │  │  Langfuse   │  │  Grafana    │  │  Custom Dashboard       │ │    │
│  │  │  Dashboard  │  │  Dashboard  │  │  (Web/App)              │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    数据存储层 (Storage Layer)                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │    │
│  │  │  Langfuse   │  │  Prometheus │  │  Elasticsearch/Loki     │ │    │
│  │  │  Cloud      │  │  (Metrics)  │  │  (Logs)                 │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    数据采集层 (Collection Layer)                  │    │
│  │                                                                  │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │    │
│  │  │   Layer 1       │  │   Layer 2       │  │   Layer 3       │ │    │
│  │  │   Skill         │  │   CI/CD         │  │   MCP Server    │ │    │
│  │  │   Execution     │  │   Pipeline      │  │   Production    │ │    │
│  │  │                 │  │                 │  │                 │ │    │
│  │  │ • STOP Protocol │  │ • Build Trace   │  │ • Tool Trace    │ │    │
│  │  │ • Langfuse SDK  │  │ • Test Metrics  │  │ • Session Mgmt  │ │    │
│  │  │ • Assertions    │  │ • Deploy Trace  │  │ • Alerting      │ │    │
│  │  │ • Trust Score   │  │ • Cost Tracking │  │ • Feedback      │ │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │    │
│  │                                                                  │    │
│  │  Trace ID 传播: ci_build_abc → skill_exec_123 → mcp_tool_456    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    执行环境层 (Execution Layer)                   │    │
│  │                                                                  │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │    │
│  │  │  Agent CLI      │  │  CI/CD Platform │  │  Production     │ │    │
│  │  │  (Claude Code   │  │  (GitHub        │  │  Environment    │ │    │
│  │  │   /Cursor)      │  │  Actions/       │  │  (K8s/VM)       │ │    │
│  │  │                 │  │  GitLab CI)     │  │                 │ │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块关系图

```
skill-observability-toolkit/
│
├── src/
│   ├── stop/                    # STOP Protocol 实现
│   │   ├── manifest.py         # skill.yaml 解析
│   │   ├── tracer.py           # Trace 生成
│   │   ├── assertions.py       # 断言验证
│   │   └── trust_score.py      # Trust Score 计算
│   │
│   ├── langfuse_integration/    # Langfuse 集成
│   │   ├── client.py           # Langfuse 客户端封装
│   │   ├── decorators.py       # @trace_skill, @trace_tool
│   │   ├── context.py          # Trace ID 传播
│   │   └── metrics.py          # 指标收集
│   │
│   ├── ci/                      # CI/CD 追踪
│   │   ├── decorators.py       # @trace_ci_step
│   │   ├── profiler.py         # 构建性能分析
│   │   ├── github_actions.py   # GitHub Actions 适配
│   │   └── gitlab_ci.py        # GitLab CI 适配
│   │
│   └── cli/                     # CLI 工具
│       ├── init.py             # stop init
│       ├── validate.py         # stop validate
│       ├── run.py              # stop run
│       └── report.py           # stop report
│
├── examples/                    # 示例
│   ├── basic-skill/            # 基础 Skill 示例
│   ├── ci-integration/         # CI 集成示例
│   └── complete-workflow/      # 完整工作流示例
│
├── tests/                       # 测试
│   ├── unit/                   # 单元测试
│   └── integration/            # 集成测试
│
└── docs/                        # 文档
    ├── api-reference.md        # API 参考
    ├── ci-integration.md       # CI 集成指南
    └── troubleshooting.md      # 故障排查
```

---

## 3. 核心模块设计

### 3.1 STOP Protocol 模块

#### 3.1.1 Manifest 解析器

```python
# src/stop/manifest.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import yaml


@dataclass
class SkillInput:
    """Skill 输入定义"""
    name: str
    type: str  # file_path, string, integer, boolean, url, json
    required: bool = True
    description: str = ""
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class SkillOutput:
    """Skill 输出定义"""
    name: str
    type: str
    description: str = ""
    guaranteed: bool = True


@dataclass
class SideEffect:
    """副作用声明"""
    type: str  # filesystem, network, database, external_service
    access: str  # read, write, execute
    paths: Optional[List[str]] = None
    description: str = ""


@dataclass
class ObservabilityConfig:
    """可观测性配置"""
    level: str  # L0, L1, L2, L3
    langfuse_integration: Optional[Dict[str, Any]] = None
    metrics_enabled: bool = False


@dataclass
class SkillManifest:
    """Skill Manifest 完整定义"""
    sop: str
    name: str
    version: str
    description: str
    inputs: List[SkillInput]
    outputs: List[SkillOutput]
    tools_used: List[str]
    side_effects: List[SideEffect]
    requirements: Optional[Dict[str, Any]] = None
    observability: Optional[ObservabilityConfig] = None
    assertions: Optional[Dict[str, Any]] = None


class ManifestParser:
    """Manifest 解析器"""
    
    def load(self, path: str) -> SkillManifest:
        """从文件加载 Manifest"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return self._parse(data)
    
    def parse(self, yaml_content: str) -> SkillManifest:
        """从字符串解析 Manifest"""
        data = yaml.safe_load(yaml_content)
        return self._parse(data)
    
    def _parse(self, data: Dict[str, Any]) -> SkillManifest:
        """解析 Manifest 数据"""
        # 实现解析逻辑
        pass
    
    def validate(self, manifest: SkillManifest) -> List[str]:
        """验证 Manifest 有效性,返回错误列表"""
        errors = []
        # 验证必填字段
        # 验证名称格式 (kebab-case)
        # 验证类型合法性
        return errors
```

#### 3.1.2 Trace 生成器

```python
# src/stop/tracer.py
import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List


class SpanKind(Enum):
    """Span 类型"""
    SKILL_EXECUTE = "skill.execute"
    TOOL_CALL = "tool.call"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    HTTP_REQUEST = "http.request"
    LLM_CALL = "llm.call"
    CUSTOM = "custom"


@dataclass
class Span:
    """Span 数据结构"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    kind: SpanKind = SpanKind.CUSTOM
    name: str = ""
    status: str = "ok"  # ok, error, skipped
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class STOPTracer:
    """STOP Protocol Tracer"""
    
    def __init__(self, output_dir: str = ".sop/traces"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._current_trace_id: Optional[str] = None
        self._spans: List[Span] = []
    
    def start_trace(self, trace_id: Optional[str] = None) -> str:
        """启动新的 Trace"""
        self._current_trace_id = trace_id or f"t_{uuid.uuid4().hex[:12]}"
        self._spans = []
        return self._current_trace_id
    
    def start_span(
        self,
        name: str,
        kind: SpanKind,
        parent_span_id: Optional[str] = None
    ) -> Span:
        """启动新的 Span"""
        span = Span(
            span_id=f"s_{uuid.uuid4().hex[:8]}",
            trace_id=self._current_trace_id,
            parent_span_id=parent_span_id,
            start_time=datetime.utcnow().isoformat() + "Z",
            kind=kind,
            name=name,
        )
        self._spans.append(span)
        return span
    
    def end_span(
        self,
        span: Span,
        status: str = "ok",
        attributes: Optional[Dict[str, Any]] = None
    ):
        """结束 Span"""
        span.end_time = datetime.utcnow().isoformat() + "Z"
        span.duration_ms = self._calculate_duration(span)
        span.status = status
        if attributes:
            span.attributes.update(attributes)
    
    def flush(self):
        """将 Spans 写入 NDJSON 文件"""
        if not self._spans:
            return
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"trace_{self._current_trace_id}_{timestamp}.ndjson"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for span in self._spans:
                f.write(json.dumps(self._span_to_dict(span), ensure_ascii=False) + "\n")
        
        self._spans = []
    
    def _calculate_duration(self, span: Span) -> float:
        """计算 Span 持续时间"""
        if not span.start_time or not span.end_time:
            return 0.0
        start = datetime.fromisoformat(span.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(span.end_time.replace("Z", "+00:00"))
        return (end - start).total_seconds() * 1000
    
    def _span_to_dict(self, span: Span) -> Dict[str, Any]:
        """将 Span 转换为字典"""
        return {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": span.duration_ms,
            "kind": span.kind.value,
            "name": span.name,
            "status": span.status,
            "attributes": span.attributes,
        }
```

#### 3.1.3 断言引擎

```python
# src/stop/assertions.py
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AssertionResult:
    """断言结果"""
    check: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class AssertionChecker(ABC):
    """断言检查器基类"""
    
    @abstractmethod
    def check(self, config: Dict[str, Any], context: Dict[str, Any]) -> AssertionResult:
        pass


class EnvVarChecker(AssertionChecker):
    """环境变量检查器"""
    
    def check(self, config: Dict[str, Any], context: Dict[str, Any]) -> AssertionResult:
        name = config.get("name")
        message = config.get("message", f"Environment variable {name} is required")
        
        value = os.getenv(name)
        passed = value is not None
        
        return AssertionResult(
            check="env_var",
            passed=passed,
            message=message if not passed else f"Environment variable {name} is set",
            details={"name": name, "value": value[:10] + "..." if value and len(value) > 10 else value}
        )


class FileExistsChecker(AssertionChecker):
    """文件存在性检查器"""
    
    def check(self, config: Dict[str, Any], context: Dict[str, Any]) -> AssertionResult:
        path = config.get("path", "")
        # 支持变量插值
        path = self._interpolate(path, context)
        message = config.get("message", f"File {path} must exist")
        
        import os.path
        passed = os.path.exists(path)
        
        return AssertionResult(
            check="file_exists",
            passed=passed,
            message=message if not passed else f"File {path} exists",
            details={"path": path}
        )
    
    def _interpolate(self, template: str, context: Dict[str, Any]) -> str:
        """变量插值"""
        result = template
        for key, value in context.get("inputs", {}).items():
            result = result.replace(f"${{inputs.{key}}}", str(value))
        return result


class FileMatchesChecker(AssertionChecker):
    """文件内容匹配检查器"""
    
    def check(self, config: Dict[str, Any], context: Dict[str, Any]) -> AssertionResult:
        path = config.get("path", "")
        pattern = config.get("pattern", "")
        message = config.get("message", f"File {path} must match pattern {pattern}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            passed = bool(re.search(pattern, content))
        except Exception as e:
            return AssertionResult(
                check="file_matches",
                passed=False,
                message=f"Failed to read file: {e}",
                details={"path": path, "error": str(e)}
            )
        
        return AssertionResult(
            check="file_matches",
            passed=passed,
            message=message if not passed else f"File {path} matches pattern",
            details={"path": path, "pattern": pattern}
        )


class OutputChecker(AssertionChecker):
    """输出字段检查器"""
    
    def check(self, config: Dict[str, Any], context: Dict[str, Any]) -> AssertionResult:
        field = config.get("field", "")
        output = context.get("output", {})
        
        # 支持嵌套字段访问 (e.g., "output.article_url")
        field_name = field.replace("output.", "")
        value = output.get(field_name)
        
        passed = True
        message = f"Output field {field_name} is valid"
        
        if "not_empty" in config:
            if not value:
                passed = False
                message = f"Output field {field_name} is empty"
        
        if "matches" in config:
            pattern = config["matches"]
            if not re.match(pattern, str(value)):
                passed = False
                message = f"Output field {field_name} does not match pattern {pattern}"
        
        return AssertionResult(
            check="output",
            passed=passed,
            message=message,
            details={"field": field_name, "value": str(value)[:100]}
        )


class AssertionEngine:
    """断言引擎"""
    
    def __init__(self):
        self._checkers: Dict[str, AssertionChecker] = {
            "env_var": EnvVarChecker(),
            "file_exists": FileExistsChecker(),
            "file_matches": FileMatchesChecker(),
            "output": OutputChecker(),
        }
    
    def run_assertions(
        self,
        assertions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[AssertionResult]:
        """运行断言列表"""
        results = []
        for assertion in assertions:
            check_type = assertion.get("check")
            checker = self._checkers.get(check_type)
            if checker:
                result = checker.check(assertion, context)
                results.append(result)
            else:
                results.append(AssertionResult(
                    check=check_type,
                    passed=False,
                    message=f"Unknown check type: {check_type}"
                ))
        return results
    
    def calculate_trust_score(self, results: List[AssertionResult]) -> float:
        """计算 Trust Score"""
        if not results:
            return 1.0
        passed = sum(1 for r in results if r.passed)
        return passed / len(results)
```

### 3.2 Langfuse 集成模块

#### 3.2.1 客户端封装

```python
# src/langfuse_integration/client.py
import os
from typing import Optional

from langfuse import Langfuse


class LangfuseClient:
    """Langfuse 客户端封装"""
    
    _instance: Optional[Langfuse] = None
    
    @classmethod
    def get_instance(cls) -> Optional[Langfuse]:
        """获取单例实例"""
        if cls._instance is None:
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        """初始化 Langfuse 客户端"""
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if not public_key or not secret_key:
            print("⚠️  Langfuse credentials not configured. Tracing disabled.")
            cls._instance = None
            return
        
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        cls._instance = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        print(f"✅ Langfuse initialized (host={host})")
    
    @classmethod
    def is_enabled(cls) -> bool:
        """检查是否启用"""
        return cls.get_instance() is not None
```

#### 3.2.2 追踪装饰器

```python
# src/langfuse_integration/decorators.py
import functools
import time
from typing import Any, Callable, Dict, Optional

from langfuse_integration.client import LangfuseClient
from stop.tracer import STOPTracer, SpanKind


def trace_skill_execution(
    skill_name: str,
    version: str = "1.0.0",
    trace_id: Optional[str] = None
):
    """
    Skill 执行追踪装饰器
    
    Args:
        skill_name: Skill 名称
        version: Skill 版本
        trace_id: 可选的 Trace ID (用于跨层关联)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = LangfuseClient.get_instance()
            stop_tracer = STOPTracer()
            
            # 启动 Trace
            current_trace_id = stop_tracer.start_trace(trace_id)
            
            # 记录到 Langfuse
            if langfuse:
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name=f"skill:{skill_name}",
                    trace_id=current_trace_id,
                    metadata={
                        "skill_version": version,
                        "execution_mode": "skill_runtime",
                        "stop_protocol": "L2",
                    }
                ) as langfuse_span:
                    return _execute_with_tracing(
                        func, args, kwargs,
                        stop_tracer, langfuse_span,
                        skill_name, version
                    )
            else:
                return _execute_with_tracing(
                    func, args, kwargs,
                    stop_tracer, None,
                    skill_name, version
                )
        
        return wrapper
    return decorator


def _execute_with_tracing(
    func: Callable,
    args: tuple,
    kwargs: dict,
    stop_tracer: STOPTracer,
    langfuse_span: Any,
    skill_name: str,
    version: str
):
    """执行函数并记录追踪"""
    start_time = time.time()
    
    # 启动 STOP Span
    stop_span = stop_tracer.start_span(
        name=f"skill.execute:{skill_name}",
        kind=SpanKind.SKILL_EXECUTE
    )
    
    try:
        # 执行函数
        result = func(*args, **kwargs)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # 结束 STOP Span
        stop_tracer.end_span(
            stop_span,
            status="ok",
            attributes={
                "skill_name": skill_name,
                "version": version,
                "duration_ms": duration_ms,
                "status": "success",
            }
        )
        
        # 记录到 Langfuse
        if langfuse_span:
            langfuse_span.end(
                output_data={
                    "status": "success",
                    "duration_ms": duration_ms,
                    "result_summary": str(result)[:500],
                }
            )
            
            # 记录评分
            from langfuse_integration.client import LangfuseClient
            langfuse = LangfuseClient.get_instance()
            if langfuse:
                langfuse.score_current_trace(
                    name="execution_time_ms",
                    value=duration_ms,
                    comment=f"Skill {skill_name} v{version} execution time"
                )
                langfuse.score_current_trace(
                    name="success",
                    value=1,
                    data_type="BOOLEAN"
                )
        
        # 刷新 STOP Trace
        stop_tracer.flush()
        
        return result
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # 记录异常到 STOP
        stop_tracer.end_span(
            stop_span,
            status="error",
            attributes={
                "skill_name": skill_name,
                "version": version,
                "duration_ms": duration_ms,
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
        )
        stop_tracer.flush()
        
        # 记录异常到 Langfuse
        if langfuse_span:
            langfuse_span.end(
                output_data={
                    "status": "error",
                    "duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            
            from langfuse_integration.client import LangfuseClient
            langfuse = LangfuseClient.get_instance()
            if langfuse:
                langfuse.score_current_trace(
                    name="success",
                    value=0,
                    data_type="BOOLEAN"
                )
        
        raise


def trace_tool_call(tool_name: str, tool_input: Optional[Dict] = None):
    """
    工具调用追踪装饰器
    
    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = LangfuseClient.get_instance()
            
            if not langfuse:
                return func(*args, **kwargs)
            
            start_time = time.time()
            
            with langfuse.start_as_current_observation(
                as_type="span",
                name=f"tool:{tool_name}",
                input_data=tool_input or {},
                metadata={
                    "tool_category": "skill_internal",
                }
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    span.end(
                        output_data={
                            "status": "success",
                            "duration_ms": duration_ms,
                        }
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    span.end(
                        output_data={
                            "status": "error",
                            "duration_ms": duration_ms,
                            "error": str(e),
                        }
                    )
                    raise
        
        return wrapper
    return decorator
```

#### 3.2.3 Trace ID 上下文传播

```python
# src/langfuse_integration/context.py
import contextvars
from typing import Optional

# 上下文变量
_trace_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id",
    default=None
)

_parent_trace_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "parent_trace_id",
    default=None
)


def set_trace_id(trace_id: str) -> None:
    """设置当前 Trace ID"""
    _trace_id_context.set(trace_id)


def get_trace_id() -> Optional[str]:
    """获取当前 Trace ID"""
    return _trace_id_context.get()


def set_parent_trace_id(parent_trace_id: str) -> None:
    """设置父 Trace ID (用于跨层关联)"""
    _parent_trace_id_context.set(parent_trace_id)


def get_parent_trace_id() -> Optional[str]:
    """获取父 Trace ID"""
    return _parent_trace_id_context.get()


def clear_trace_context() -> None:
    """清除 Trace 上下文"""
    _trace_id_context.set(None)
    _parent_trace_id_context.set(None)


class TraceContextManager:
    """Trace 上下文管理器"""
    
    def __init__(self, trace_id: Optional[str] = None, parent_trace_id: Optional[str] = None):
        self.trace_id = trace_id
        self.parent_trace_id = parent_trace_id
        self._tokens = []
    
    def __enter__(self):
        if self.trace_id:
            self._tokens.append(_trace_id_context.set(self.trace_id))
        if self.parent_trace_id:
            self._tokens.append(_parent_trace_id_context.set(self.parent_trace_id))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in self._tokens:
            # 恢复上下文
            pass
        return False
```

### 3.3 CI/CD 追踪模块

#### 3.3.1 CI 步骤追踪装饰器

```python
# src/ci/decorators.py
import functools
import os
import time
from typing import Any, Callable, Dict, Optional

from langfuse_integration.client import LangfuseClient
from langfuse_integration.context import set_trace_id, get_trace_id


def trace_ci_step(
    step_name: str,
    auto_capture_env: bool = True,
    trace_id: Optional[str] = None
):
    """
    CI 步骤追踪装饰器
    
    Args:
        step_name: 步骤名称
        auto_capture_env: 是否自动捕获 CI 环境变量
        trace_id: 可选的 Trace ID
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = LangfuseClient.get_instance()
            
            # 生成或使用 Trace ID
            current_trace_id = trace_id or get_trace_id() or _generate_ci_trace_id()
            set_trace_id(current_trace_id)
            
            metadata = {}
            if auto_capture_env:
                metadata = _capture_ci_environment()
            
            if not langfuse:
                return func(*args, **kwargs)
            
            start_time = time.time()
            
            with langfuse.start_as_current_observation(
                as_type="span",
                name=f"ci:{step_name}",
                trace_id=current_trace_id,
                metadata=metadata
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    span.end(
                        output_data={
                            "status": "success",
                            "duration_ms": duration_ms,
                        }
                    )
                    
                    # 记录评分
                    langfuse.score_current_trace(
                        name=f"ci_{step_name}_duration_ms",
                        value=duration_ms
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    span.end(
                        output_data={
                            "status": "error",
                            "duration_ms": duration_ms,
                            "error": str(e),
                        }
                    )
                    
                    langfuse.score_current_trace(
                        name=f"ci_{step_name}_success",
                        value=0,
                        data_type="BOOLEAN"
                    )
                    
                    raise
        
        return wrapper
    return decorator


def _generate_ci_trace_id() -> str:
    """生成 CI Trace ID"""
    import uuid
    return f"ci_{uuid.uuid4().hex[:12]}_{int(time.time())}"


def _capture_ci_environment() -> Dict[str, Any]:
    """捕获 CI 环境变量"""
    env_vars = {}
    
    # GitHub Actions
    if os.getenv("GITHUB_ACTIONS"):
        env_vars.update({
            "ci_platform": "github-actions",
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
            "github_sha": os.getenv("GITHUB_SHA"),
            "github_ref": os.getenv("GITHUB_REF"),
            "github_repository": os.getenv("GITHUB_REPOSITORY"),
            "github_actor": os.getenv("GITHUB_ACTOR"),
        })
    
    # GitLab CI
    elif os.getenv("GITLAB_CI"):
        env_vars.update({
            "ci_platform": "gitlab-ci",
            "ci_pipeline_id": os.getenv("CI_PIPELINE_ID"),
            "ci_commit_sha": os.getenv("CI_COMMIT_SHA"),
            "ci_commit_ref_name": os.getenv("CI_COMMIT_REF_NAME"),
            "ci_project_path": os.getenv("CI_PROJECT_PATH"),
        })
    
    return env_vars
```

#### 3.3.2 构建性能分析器

```python
# src/ci/profiler.py
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class BuildMetrics:
    """构建指标"""
    step_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "running"  # running, success, failed
    
    def complete(self, status: str = "success"):
        """完成步骤"""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status


class BuildProfiler:
    """构建性能分析器"""
    
    def __init__(self):
        self._metrics: List[BuildMetrics] = []
        self._current_step: Optional[BuildMetrics] = None
    
    def start_step(self, step_name: str) -> BuildMetrics:
        """开始步骤"""
        metrics = BuildMetrics(
            step_name=step_name,
            start_time=datetime.utcnow()
        )
        self._metrics.append(metrics)
        self._current_step = metrics
        return metrics
    
    def end_step(self, status: str = "success"):
        """结束当前步骤"""
        if self._current_step:
            self._current_step.complete(status)
            self._current_step = None
    
    def get_summary(self) -> Dict:
        """获取构建摘要"""
        total_duration = sum(m.duration_ms for m in self._metrics)
        successful_steps = sum(1 for m in self._metrics if m.status == "success")
        
        return {
            "total_steps": len(self._metrics),
            "successful_steps": successful_steps,
            "failed_steps": len(self._metrics) - successful_steps,
            "total_duration_ms": total_duration,
            "steps": [
                {
                    "name": m.step_name,
                    "duration_ms": m.duration_ms,
                    "status": m.status,
                }
                for m in self._metrics
            ]
        }
    
    def get_bottlenecks(self, threshold_ms: float = 10000) -> List[Dict]:
        """获取性能瓶颈"""
        slow_steps = [
            {
                "name": m.step_name,
                "duration_ms": m.duration_ms,
            }
            for m in self._metrics
            if m.duration_ms > threshold_ms
        ]
        return sorted(slow_steps, key=lambda x: x["duration_ms"], reverse=True)
```

### 3.4 CLI 工具模块

#### 3.4.1 初始化命令

```python
# src/cli/init.py
import os
import re
from pathlib import Path

import click
import yaml


@click.command()
@click.option('--name', prompt='Skill name (kebab-case)', help='Skill name')
@click.option('--version', default='1.0.0', help='Skill version')
@click.option('--description', prompt='Description', help='Skill description')
@click.option('--level', type=click.Choice(['L0', 'L1', 'L2', 'L3']), default='L2', help='Observability level')
def init(name, version, description, level):
    """初始化 Skill 项目"""
    
    # 验证名称格式
    if not _validate_kebab_case(name):
        click.echo("❌ Skill name must be kebab-case (e.g., my-skill)")
        return
    
    # 创建目录
    skill_dir = Path(name)
    skill_dir.mkdir(exist_ok=True)
    
    # 生成 skill.yaml
    manifest = {
        "sop": "0.1",
        "name": name,
        "version": version,
        "description": description,
        "inputs": [
            {
                "name": "input_path",
                "type": "file_path",
                "required": True,
                "description": "Input file path"
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "string",
                "description": "Execution result",
                "guaranteed": True
            }
        ],
        "tools_used": ["exec", "read"],
        "side_effects": [],
        "observability": {
            "level": level,
            "langfuse_integration": {
                "enabled": True,
                "trace_name": "skill-execution",
                "auto_score": ["execution_time_ms", "success_rate"]
            }
        }
    }
    
    # 写入文件
    manifest_path = skill_dir / "skill.yaml"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)
    
    click.echo(f"✅ Created {manifest_path}")
    
    # 创建 src 目录和示例文件
    src_dir = skill_dir / "src"
    src_dir.mkdir(exist_ok=True)
    
    # 生成示例 main.py
    main_py = src_dir / "main.py"
    main_content = f'''"""
{name} Skill - Main entry point
"""

from skill_observability_toolkit import trace_skill_execution, trace_tool_call


@trace_skill_execution(skill_name="{name}", version="{version}")
def execute_skill(input_path: str) -> dict:
    """
    Execute the skill
    
    Args:
        input_path: Input file path
    
    Returns:
        Execution result
    """
    # Read input file
    content = read_input_file(input_path)
    
    # Process content
    result = process_content(content)
    
    return {{
        "result": result,
        "status": "success"
    }}


@trace_tool_call(tool_name="read_input_file")
def read_input_file(file_path: str) -> str:
    """Read input file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def process_content(content: str) -> str:
    """Process content"""
    # TODO: Implement processing logic
    return content.upper()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_path>")
        sys.exit(1)
    
    result = execute_skill(sys.argv[1])
    print(result)
'''
    
    with open(main_py, 'w', encoding='utf-8') as f:
        f.write(main_content)
    
    click.echo(f"✅ Created {main_py}")
    click.echo(f"\n🎉 Skill '{name}' initialized successfully!")
    click.echo(f"   Observability level: {level}")
    click.echo(f"\nNext steps:")
    click.echo(f"   1. Edit {manifest_path} to define inputs/outputs")
    click.echo(f"   2. Implement logic in {main_py}")
    click.echo(f"   3. Run: stop validate {manifest_path}")


def _validate_kebab_case(name: str) -> bool:
    """验证 kebab-case 格式"""
    return bool(re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name))
```

#### 3.4.2 验证命令

```python
# src/cli/validate.py
import sys
from pathlib import Path

import click
import yaml

from stop.manifest import ManifestParser


@click.command()
@click.argument('manifest_path', type=click.Path(exists=True))
def validate(manifest_path):
    """验证 skill.yaml 文件"""
    
    click.echo(f"🔍 Validating {manifest_path}...")
    
    parser = ManifestParser()
    
    try:
        manifest = parser.load(manifest_path)
    except Exception as e:
        click.echo(f"❌ Failed to parse YAML: {e}")
        sys.exit(1)
    
    # 验证
    errors = parser.validate(manifest)
    
    if errors:
        click.echo(f"\n❌ Validation failed ({len(errors)} error(s)):")
        for error in errors:
            click.echo(f"   - {error}")
        sys.exit(1)
    else:
        click.echo(f"\n✅ {manifest_path} is valid!")
        click.echo(f"\n   Name: {manifest.name}")
        click.echo(f"   Version: {manifest.version}")
        click.echo(f"   Observability Level: {manifest.observability.level if manifest.observability else 'L0'}")
        click.echo(f"   Inputs: {len(manifest.inputs)}")
        click.echo(f"   Outputs: {len(manifest.outputs)}")
```

---

## 4. 数据流设计

### 4.1 端到端 Trace 数据流

```
┌────────────────────────────────────────────────────────────────────────┐
│                         端到端 Trace 数据流                            │
└────────────────────────────────────────────────────────────────────────┘

1. CI Pipeline 触发
   │
   ├── GitHub Actions / GitLab CI
   │
   └── 生成根 Trace ID: ci_build_abc123
       │
       ▼
2. CI 步骤执行
   │
   ├── @trace_ci_step("dependency-installation")
   │   └── Span: ci:dependency-installation
   │       └── Langfuse Trace: ci_build_abc123
   │
   ├── @trace_ci_step("run-tests")
   │   └── Span: ci:run-tests
   │       └── Langfuse Trace: ci_build_abc123
   │
   └── @trace_ci_step("execute-skill")
       │
       └── 传递 Trace ID 到 Skill 层
           │
           ▼
3. Skill 执行层
   │
   ├── @trace_skill_execution(trace_id="ci_build_abc123")
   │   │
   │   ├── STOP Span: skill.execute:api-expert
   │   │   └── STOP Trace: skill_def456
   │   │       └── .sop/traces/trace_skill_def456.ndjson
   │   │
   │   ├── Langfuse Span: skill:api-expert
   │   │   └── Langfuse Trace: ci_build_abc123 (复用)
   │   │
   │   ├── @trace_tool_call("read_file")
   │   │   └── Span: tool:read_file
     │   │       └── Langfuse Trace: ci_build_abc123
   │   │
   │   ├── @trace_tool_call("exec_pylint")
   │   │   └── Span: tool:exec_pylint
   │   │       └── Langfuse Trace: ci_build_abc123
   │   │
   │   └── Assertions 验证
   │       └── Trust Score 计算
   │
   └── 返回结果到 CI
       │
       ▼
4. CI 继续执行
   │
   ├── @trace_ci_step("build-docker")
   │   └── Span: ci:build-docker
   │       └── Langfuse Trace: ci_build_abc123
   │
   └── @trace_ci_step("deploy-staging")
       │
       └── 传递 Trace ID 到 MCP Server
           │
           ▼
5. MCP Server 生产层 (复用 mcp-with-tracing)
   │
   ├── @observe_tool("health-check")
   │   └── Span: mcp:health-check
   │       └── Langfuse Trace: ci_build_abc123
   │
   ├── 用户反馈收集
   │   └── Score: user_satisfaction
   │       └── Langfuse Trace: ci_build_abc123
   │
   └── Smart Alerting (如有异常)
       └── 触发告警

6. 统一视图
   │
   └── Langfuse Dashboard
       └── Trace: ci_build_abc123
           ├── Span: ci:dependency-installation
           ├── Span: ci:run-tests
           ├── Span: skill:api-expert
           │   ├── Span: tool:read_file
           │   └── Span: tool:exec_pylint
           ├── Span: ci:build-docker
           ├── Span: ci:deploy-staging
           └── Span: mcp:health-check
```

### 4.2 数据格式

#### STOP Trace (NDJSON)

```ndjson
{"trace_id":"ci_build_abc123","span_id":"s_001","kind":"ci.step","name":"dependency-installation","status":"ok","duration_ms":15000,"start_time":"2026-04-23T10:00:00Z","end_time":"2026-04-23T10:00:15Z","attributes":{"ci_platform":"github-actions","github_run_id":"123456"}}
{"trace_id":"ci_build_abc123","span_id":"s_002","kind":"skill.execute","name":"api-expert","status":"ok","duration_ms":5000,"start_time":"2026-04-23T10:00:15Z","end_time":"2026-04-23T10:00:20Z","attributes":{"skill_version":"1.0.0","trust_score":0.95}}
{"trace_id":"ci_build_abc123","span_id":"s_003","parent_span_id":"s_002","kind":"tool.call","name":"read_file","status":"ok","duration_ms":12,"start_time":"2026-04-23T10:00:15Z","end_time":"2026-04-23T10:00:15.012Z","attributes":{"file_path":"src/main.py","size_bytes":1024}}
```

#### Langfuse Trace

```json
{
  "trace_id": "ci_build_abc123",
  "name": "ci-pipeline",
  "timestamp": "2026-04-23T10:00:00Z",
  "metadata": {
    "ci_platform": "github-actions",
    "github_sha": "abc123",
    "project": "my-project"
  },
  "scores": [
    {"name": "execution_time_ms", "value": 5000},
    {"name": "success", "value": 1, "data_type": "BOOLEAN"},
    {"name": "trust_score", "value": 0.95}
  ]
}
```

---

## 5. API 设计

### 5.1 Python SDK API

```python
# 核心装饰器
from skill_observability_toolkit import (
    trace_skill_execution,    # Skill 执行追踪
    trace_tool_call,          # 工具调用追踪
    trace_ci_step,            # CI 步骤追踪
)

# STOP Protocol
from skill_observability_toolkit.stop import (
    ManifestParser,           # Manifest 解析
    STOPTracer,               # Trace 生成
    AssertionEngine,          # 断言引擎
)

# Langfuse 集成
from skill_observability_toolkit.langfuse import (
    LangfuseClient,           # 客户端
    TraceContextManager,      # 上下文管理
)

# CI/CD
from skill_observability_toolkit.ci import (
    BuildProfiler,            # 构建性能分析
    GitHubActionsAdapter,     # GitHub Actions 适配
)
```

### 5.2 CLI API

```bash
# 初始化
stop init [--name NAME] [--version VERSION] [--description DESC] [--level LEVEL]

# 验证
stop validate <skill.yaml>

# 执行 (带追踪)
stop run [--trace] [--trace-id ID] <skill_path>

# 查看追踪
stop trace <trace_id>

# 生成报告
stop report [--last N] [--format json|html]

# 启动本地仪表板
stop dashboard [--port PORT] [--host HOST]

# 环境检查
stop doctor
```

---

## 6. 目录结构设计

### 6.1 完整目录结构

```
skill-observability-toolkit/
│
├── README.md                    # 项目说明
├── LICENSE                      # 许可证
├── pyproject.toml               # Python 项目配置
├── requirements.txt             # 依赖
├── requirements-dev.txt         # 开发依赖
│
├── src/
│   └── skill_observability_toolkit/    # 主包
│       │
│       ├── __init__.py                # 包入口
│       │
│       ├── stop/                      # STOP Protocol 实现
│       │   ├── __init__.py
│       │   ├── manifest.py           # Manifest 解析
│       │   ├── tracer.py             # Trace 生成
│       │   ├── assertions.py         # 断言引擎
│       │   ├── trust_score.py        # Trust Score 计算
│       │   └── types.py              # 类型定义
│       │
│       ├── langfuse_integration/      # Langfuse 集成
│       │   ├── __init__.py
│       │   ├── client.py             # 客户端封装
│       │   ├── decorators.py         # 追踪装饰器
│       │   ├── context.py            # Trace ID 上下文
│       │   ├── metrics.py            # 指标收集
│       │   └── scoring.py            # 评分系统
│       │
│       ├── ci/                        # CI/CD 追踪
│       │   ├── __init__.py
│       │   ├── decorators.py         # CI 装饰器
│       │   ├── profiler.py           # 性能分析
│       │   ├── github_actions.py      # GitHub Actions 适配
│       │   ├── gitlab_ci.py          # GitLab CI 适配
│       │   └── reporters.py          # 报告生成
│       │
│       └── cli/                       # CLI 工具
│           ├── __init__.py
│           ├── main.py               # CLI 入口
│           ├── init.py               # init 命令
│           ├── validate.py           # validate 命令
│           ├── run.py                # run 命令
│           ├── report.py             # report 命令
│           └── doctor.py             # doctor 命令
│
├── examples/                          # 示例
│   ├── basic-skill/                   # 基础 Skill 示例
│   │   ├── skill.yaml
│   │   ├── src/
│   │   │   └── main.py
│   │   └── README.md
│   │
│   ├── ci-integration/                # CI 集成示例
│   │   ├── .github/
│   │   │   └── workflows/
│   │   │       └── ci.yml
│   │   ├── skill.yaml
│   │   ├── src/
│   │   │   └── main.py
│   │   └── README.md
│   │
│   └── complete-workflow/             # 完整工作流示例
│       ├── skill.yaml
│       ├── src/
│       │   └── main.py
│       ├── .github/
│       │   └── workflows/
│       │       └── ci.yml
│       └── README.md
│
├── tests/                             # 测试
│   ├── __init__.py
│   ├── conftest.py                   # Pytest 配置
│   ├── unit/                         # 单元测试
│   │   ├── test_manifest.py
│   │   ├── test_tracer.py
│   │   ├── test_assertions.py
│   │   ├── test_decorators.py
│   │   └── test_context.py
│   │
│   ├── integration/                  # 集成测试
│   │   ├── test_langfuse_connection.py
│   │   ├── test_stop_protocol.py
│   │   └── test_ci_integration.py
│   │
│   └── fixtures/                     # 测试数据
│       ├── valid_skill.yaml
│       └── invalid_skill.yaml
│
├── docs/                             # 文档
│   ├── DESIGN.md                     # 设计文档 (本文件)
│   ├── api-reference.md              # API 参考
│   ├── quick-start.md                # 快速开始
│   ├── ci-integration.md             # CI 集成指南
│   ├── troubleshooting.md            # 故障排查
│   └── architecture.md               # 架构说明
│
└── scripts/                          # 脚本
    ├── setup.sh                      # 安装脚本
    ├── test.sh                       # 测试脚本
    └── release.sh                    # 发布脚本
```

---

## 7. 实施计划

### 7.1 Phase 1: Skill 层基础 (2-3 周)

**目标**: 实现 STOP Protocol L0-L2 + Langfuse 追踪 SDK

**Week 1: 核心模块**
- [ ] Task 1.1: 项目骨架搭建
  - 创建目录结构
  - 配置 pyproject.toml
  - 设置 pytest

- [ ] Task 1.2: STOP Manifest 解析器
  - 实现 ManifestParser 类
  - 支持 YAML 加载和验证
  - 单元测试

- [ ] Task 1.3: STOP Tracer
  - 实现 STOPTracer 类
  - NDJSON 输出格式
  - Span 树结构

- [ ] Task 1.4: 断言引擎
  - 实现 AssertionEngine
  - 支持预定义检查器
  - Trust Score 计算

**Week 2: Langfuse 集成**
- [ ] Task 1.5: Langfuse 客户端封装
  - 实现 LangfuseClient
  - 配置管理

- [ ] Task 1.6: 追踪装饰器
  - 实现 @trace_skill_execution
  - 实现 @trace_tool_call
  - 异常处理

- [ ] Task 1.7: Trace ID 上下文
  - 实现 TraceContextManager
  - 跨层传播机制

**Week 3: CLI 和示例**
- [ ] Task 1.8: CLI init 命令
  - 交互式生成 skill.yaml
  - 项目模板

- [ ] Task 1.9: CLI validate 命令
  - Manifest 验证
  - 错误报告

- [ ] Task 1.10: 基础示例
  - 创建 basic-skill 示例
  - 编写文档

**交付物**:
- STOP Protocol L0-L2 完整实现
- Langfuse SDK 集成
- CLI init + validate 命令
- 1 个完整示例
- 单元测试覆盖率 >90%

---

### 7.2 Phase 2: CI/CD 层 (2-3 周)

**目标**: 实现 CI/CD 追踪 + 性能分析

**Week 4: CI 追踪**
- [ ] Task 2.1: @trace_ci_step 装饰器
  - CI 环境变量捕获
  - Span 生成

- [ ] Task 2.2: GitHub Actions 适配
  - 环境变量映射
  - Workflow 集成示例

- [ ] Task 2.3: GitLab CI 适配
  - 环境变量映射
  - Pipeline 集成示例

**Week 5: 性能分析**
- [ ] Task 2.4: BuildProfiler
  - 步骤时长追踪
  - 瓶颈识别

- [ ] Task 2.5: 报告生成
  - HTML 报告
  - JSON 输出

- [ ] Task 2.6: CLI report 命令
  - 报告查看
  - 历史对比

**Week 6: 示例和测试**
- [ ] Task 2.7: CI 集成示例
  - GitHub Actions workflow
  - GitLab CI pipeline

- [ ] Task 2.8: 集成测试
  - CI 环境模拟
  - 端到端测试

**交付物**:
- @trace_ci_step 装饰器
- GitHub Actions + GitLab CI 支持
- BuildProfiler 性能分析
- CI 集成示例
- 集成测试

---

### 7.3 Phase 3: 端到端关联 (2-3 周)

**目标**: Trace ID 跨层传播 + 统一视图

**Week 7: Trace ID 传播**
- [ ] Task 3.1: CI → Skill 传播
  - 环境变量传递
  - 上下文继承

- [ ] Task 3.2: Skill → MCP 传播
  - 复用 mcp-with-tracing
  - Trace ID 关联

- [ ] Task 3.3: 统一标签体系
  - 标准化标签
  - 跨层一致性

**Week 8: 统一视图**
- [ ] Task 3.4: Langfuse Dashboard 优化
  - 自定义视图
  - 跨层关联展示

- [ ] Task 3.5: 报告增强
  - 端到端报告
  - 性能趋势

- [ ] Task 3.6: CLI dashboard 命令
  - 本地仪表板
  - 实时查看

**Week 9: 示例和文档**
- [ ] Task 3.7: 完整工作流示例
  - CI → Skill → MCP
  - 端到端演示

- [ ] Task 3.8: 文档完善
  - 架构说明
  - 最佳实践

**交付物**:
- Trace ID 跨层传播
- 统一标签体系
- 端到端报告
- 完整工作流示例
- 完整文档

---

### 7.4 Phase 4: 复用集成 (1-2 周)

**目标**: 复用 mcp-with-tracing 的告警和反馈系统

**Week 10: 告警集成**
- [ ] Task 4.1: 告警规则复用
  - 导入 alerting.py
  - Skill 执行失败告警

- [ ] Task 4.2: Smart Alerting 集成
  - 复用 smart_alerting.py
  - Trust Score 异常检测

**Week 11: 反馈集成**
- [ ] Task 4.3: 反馈收集复用
  - 导入 feedback.py
  - Skill 执行反馈

- [ ] Task 4.4: 评分系统
  - 复用 scoring.py
  - 统一评分体系

**交付物**:
- 告警系统集成
- 反馈系统集成
- 统一评分体系
- 完整示例

---

### 7.5 Phase 5: 发布和生态 (持续)

**目标**: 发布到 PyPI + 社区推广

- [ ] Task 5.1: PyPI 发布
  - 打包配置
  - 发布流程

- [ ] Task 5.2: 文档网站
  - MkDocs 站点
  - API 文档

- [ ] Task 5.3: 社区推广
  - 博客文章
  - 示例仓库

- [ ] Task 5.4: 贡献指南
  - CONTRIBUTING.md
  - Code of Conduct

**交付物**:
- PyPI 包
- 文档网站
- 社区推广
- 贡献指南

---

## 8. 测试策略

### 8.1 测试金字塔

```
                    ┌─────────┐
                    │  E2E   │  10%  (端到端测试)
                    │  Tests │
                   ┌┴─────────┴┐
                   │Integration│  20%  (集成测试)
                   │   Tests   │
                  ┌┴───────────┴┐
                  │    Unit      │  70%  (单元测试)
                  │    Tests     │
                  └──────────────┘
```

### 8.2 单元测试

**覆盖模块**:
- Manifest 解析器
- STOP Tracer
- 断言引擎
- 装饰器
- 上下文管理

**测试框架**: pytest + pytest-asyncio + pytest-cov

**示例**:

```python
# tests/unit/test_manifest.py
import pytest
from skill_observability_toolkit.stop.manifest import ManifestParser


class TestManifestParser:
    """Manifest 解析器测试"""
    
    def test_load_valid_manifest(self):
        """测试加载有效 Manifest"""
        parser = ManifestParser()
        manifest = parser.load("tests/fixtures/valid_skill.yaml")
        
        assert manifest.name == "test-skill"
        assert manifest.version == "1.0.0"
        assert len(manifest.inputs) == 1
    
    def test_validate_missing_required_field(self):
        """测试验证缺失必填字段"""
        parser = ManifestParser()
        errors = parser.validate(invalid_manifest)
        
        assert len(errors) > 0
        assert any("name" in e for e in errors)
    
    def test_validate_invalid_name_format(self):
        """测试验证无效名称格式"""
        parser = ManifestParser()
        manifest = parser.load("tests/fixtures/invalid_name.yaml")
        errors = parser.validate(manifest)
        
        assert any("kebab-case" in e for e in errors)
```

### 8.3 集成测试

**覆盖场景**:
- Langfuse 连接测试
- STOP Protocol 端到端
- CI 集成测试

**示例**:

```python
# tests/integration/test_langfuse_connection.py
import pytest
import os

from skill_observability_toolkit.langfuse_integration.client import LangfuseClient


class TestLangfuseIntegration:
    """Langfuse 集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """设置环境变量"""
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "test_key")
        os.environ.setdefault("LANGFUSE_SECRET_KEY", "test_secret")
    
    def test_langfuse_client_initialization(self):
        """测试 Langfuse 客户端初始化"""
        client = LangfuseClient.get_instance()
        assert client is not None
    
    def test_trace_creation(self):
        """测试 Trace 创建"""
        from langfuse import Langfuse
        
        langfuse = Langfuse()
        trace = langfuse.trace(name="test-trace")
        
        assert trace is not None
        assert trace.id is not None
```

### 8.4 端到端测试

**覆盖场景**:
- 完整 CI → Skill → MCP 链路
- 真实环境集成

**示例**:

```python
# tests/e2e/test_complete_workflow.py
import subprocess
import pytest


class TestCompleteWorkflow:
    """完整工作流端到端测试"""
    
    def test_ci_to_skill_to_mcp_trace_propagation(self):
        """测试 Trace ID 跨层传播"""
        # 1. 启动 CI Pipeline
        result = subprocess.run(
            ["python", "examples/complete-workflow/ci_pipeline.py"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        # 2. 验证 Trace ID 传播
        assert "ci_trace_id" in result.stdout
        assert "skill_trace_id" in result.stdout
        assert "mcp_trace_id" in result.stdout
        
        # 3. 验证 Langfuse 上报
        # (需要实际 Langfuse 环境)
```

### 8.5 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| stop/ | 95% |
| langfuse_integration/ | 90% |
| ci/ | 90% |
| cli/ | 85% |
| **整体** | **90%** |

---

## 9. 部署方案

### 9.1 开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/langfuse/langfuse-examples.git
cd langfuse-examples/skill-observability-toolkit

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 配置 Langfuse API Keys

# 5. 运行测试
pytest tests/ -v --cov=src

# 6. 验证安装
stop doctor
```

### 9.2 CI/CD 集成

#### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests with tracing
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        run: |
          python -m pytest tests/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

#### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - report

test:
  stage: test
  image: python:3.10
  script:
    - pip install -r requirements.txt
    - pip install -r requirements-dev.txt
    - python -m pytest tests/ -v --cov=src
  coverage: '/TOTAL.*\s+([0-9]+)%/'

report:
  stage: report
  script:
    - stop report --last 10 --format html
  artifacts:
    paths:
      - report.html
```

### 9.3 生产部署

#### PyPI 发布

```bash
# 1. 更新版本号
# 编辑 pyproject.toml

# 2. 构建
python -m build

# 3. 测试发布
python -m twine upload --repository testpypi dist/*

# 4. 正式发布
python -m twine upload dist/*
```

#### Docker 部署 (可选)

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY examples/ ./examples/

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "skill_observability_toolkit.cli"]
```

### 9.4 监控和运维

#### 健康检查

```bash
# 检查环境
stop doctor

# 输出示例:
# ✅ Python version: 3.10.12
# ✅ Langfuse credentials: configured
# ✅ STOP Protocol: L2 enabled
# ✅ CI Platform: GitHub Actions detected
```

#### 日志配置

```python
# logging_config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.sop/logs/skill-observability.log'),
        logging.StreamHandler()
    ]
)
```

---

## 10. 风险评估与应对

### 10.1 技术风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| Langfuse API 变更 | 中 | 高 | 封装客户端,隔离变更 |
| STOP Protocol 更新 | 中 | 中 | 版本化实现,支持多版本 |
| CI 平台差异 | 高 | 中 | 抽象适配层,支持多平台 |
| 性能开销 | 中 | 中 | 异步发送,采样率配置 |

### 10.2 项目风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 进度延期 | 中 | 中 | 分阶段交付,MVP优先 |
| 需求变更 | 中 | 中 | 敏捷开发,快速迭代 |
| 资源不足 | 低 | 高 | 复用现有代码,减少重复开发 |

---

## 11. 成功指标

### 11.1 技术指标

- [ ] 单元测试覆盖率 >90%
- [ ] 集成测试通过率 100%
- [ ] 性能开销 <5%
- [ ] 文档完整度 100%

### 11.2 业务指标

- [ ] PyPI 下载量 >1000
- [ ] GitHub Stars >100
- [ ] 社区贡献者 >10
- [ ] 企业用户 >5

---

## 12. 附录

### 12.1 参考文档

- [STOP Protocol Specification](https://agentskills.io)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/)

### 12.2 相关项目

- [mcp-with-tracing](../mcp-with-tracing/) - MCP Server 可观测性
- [smart-customer-service](../smart-customer-service/) - 智能客服系统

### 12.3 术语表

| 术语 | 定义 |
|------|------|
| STOP | Skill Transparency & Observability Protocol |
| Trace | 一次完整执行的追踪记录 |
| Span | Trace 中的单个操作单元 |
| Trust Score | 基于历史断言通过率的信任评分 |
| Manifest | Skill 能力声明文件 (skill.yaml) |

---

**文档版本**: 1.0.0  
**最后更新**: 2026-04-23  
**维护者**: skill-observability-toolkit Team