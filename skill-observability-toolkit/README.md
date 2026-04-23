# skill-observability-toolkit
End-to-end Agent Skill Observability Platform

## Project Status

**Phase**: Phase 1 - Skill Layer Foundation (in progress)  
**Status**: Project Skeleton Created ✅  
**Python Version**: 3.10+  
**License**: MIT

## Overview

This project implements **STOP Protocol** (Skill Transparency & Observability Protocol) with integration to **Langfuse** for end-to-end Agent Skill observability.

### What is STOP Protocol?

STOP Protocol is an open standard for making Agent Skills observable. It provides:

- **Manifest** (L0): Declare Skill capabilities in `skill.yaml`
- **Tracing** (L1): Record execution traces in NDJSON format
- **Assertions** (L2): Validate Skill execution with pre/post checks
- **Trust Score**: Quantify Skill reliability based on assertion history

### Integration with Langfuse

[Langfuse](https://langfuse.com) is the leading LLM observability platform. Our integration:

- Distributed tracing across Skill → CI/CD → Production
- Performance metrics and analytics
- User feedback collection
- Smart alerting (ML-based anomaly detection)

## Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **STOP Protocol** | L0-L3 specification implementation | 🚧 Phase 1 |
| **Manifest Parser** | skill.yaml validation and parsing | ⏳ To be implemented |
| **STOP Tracer** | NDJSON trace output | ⏳ To be implemented |
| **Assertion Engine** | Pre/post checks + Trust Score | ⏳ To be implemented |
| **Langfuse SDK** | Langfuse integration | ⏳ To be implemented |
| **Tracing Decorators** | @trace_skill_execution, @trace_tool_call | ⏳ To be implemented |
| **CI/CD Tracing** | Build step tracing | ⏳ To be implemented |
| **CLI Tools** | `stop init`, `stop validate`, `stop run` | ⏳ To be implemented |

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    End-to-End Observability                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: Skill Execution                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • STOP Protocol (skill.yaml)                                │   │
│  │ • Traces (NDJSON)                                           │   │
│  │ • Assertions (Pre/Post checks)                              │   │
│  │ • Langfuse SDK integration                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                        │
│  Layer 2: CI/CD Pipeline                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • @trace_ci_step decorator                                  │   │
│  │ • Build Profiler                                            │   │
│  │ • GitHub Actions / GitLab CI                                │   │
│  │ • Trace ID propagation                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                        │
│  Layer 3: Production (MCP Server / Application)                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • Repurposes mcp-with-tracing                               │   │
│  │ • Tool tracing                                              │   │
│  │ • Session management                                        │   │
│  │ • Alerting & Feedback                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                        │
│  Layer 4: Unified Visualization                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • Langfuse Dashboard                                        │   │
│  │ • Cross-layer trace correlation                             │   │
│  │ • Performance trends                                        │   │
│  │ • Cost tracking                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
# From source
cd skill-observability-toolkit
pip install -e .

# Or with uv
uv pip install -e .
```

### 2. Create a Skill

```bash
# Initialize a new Skill (CLI to be implemented)
stop init
```

This creates:
- `skill.yaml` - Manifest with inputs/outputs/assertions
- `src/main.py` - Entry point with tracing decorators

### 3. Run with Tracing

```python
from skill_observability_toolkit import trace_skill_execution, trace_tool_call

@trace_skill_execution(skill_name="my-skill", version="1.0.0")
def execute_skill(input_path: str) -> dict:
    """Execute the skill"""
    content = read_input_file(input_path)
    return process_content(content)

@trace_tool_call(tool_name="read_file")
def read_input_file(file_path: str) -> str:
    """Read input file"""
    with open(file_path, 'r') as f:
        return f.read()
```

### 4. View Traces

```bash
# View trace reports (CLI to be implemented)
stop report --last 10

# Or view in Langfuse Dashboard
# https://cloud.langfuse.com
```

## Project Structure

```
skill-observability-toolkit/
├── src/
│   └── skill_observability_toolkit/
│       ├── stop/                     # STOP Protocol
│       │   ├── __init__.py
│       │   ├── manifest.py          # skill.yaml parser
│       │   ├── tracer.py            # NDJSON trace output
│       │   ├── assertions.py        # Assertion engine
│       │   └── trust_score.py       # Trust Score calculator
│       │
│       ├── langfuse_integration/    # Langfuse SDK
│       │   ├── __init__.py
│       │   ├── client.py            # Langfuse client
│       │   ├── decorators.py        # Tracing decorators
│       │   └── context.py           # Trace ID context
│       │
│       ├── ci/                      # CI/CD tracing
│       │   ├── __init__.py
│       │   ├── decorators.py        # @trace_ci_step
│       │   ├── profiler.py          # BuildProfiler
│       │   ├── github_actions.py    # GitHub Actions adapter
│       │   └── gitlab_ci.py         # GitLab CI adapter
│       │
│       └── cli/                     # CLI tools
│           ├── __init__.py
│           ├── main.py              # CLI entry point
│           ├── init.py              # stop init
│           ├── validate.py          # stop validate
│           ├── run.py               # stop run
│           └── report.py            # stop report
│
├── examples/                        # Example Skills
│   ├── basic-skill/                 # Minimal example
│   ├── ci-integration/              # CI/CD example
│   └── complete-workflow/           # End-to-end example
│
├── tests/                           # Test Suite
│   ├── unit/                        # Unit tests
│   │   ├── test_manifest.py
│   │   ├── test_tracer.py
│   │   ├── test_assertions.py
│   │   ├── test_client.py
│   │   ├── test_decorators.py
│   │   ├── test_context.py
│   │   ├── test_init.py
│   │   ├── test_validate.py
│   │   └── test_example.py
│   │
│   ├── integration/                 # Integration tests
│   │   ├── test_langfuse_connection.py
│   │   ├── test_stop_protocol.py
│   │   └── test_ci_integration.py
│   │
│   └── fixtures/                    # Test fixtures
│       ├── valid_skill.yaml
│       └── invalid_skill.yaml
│
├── docs/                            # Documentation
│   ├── DESIGN.md                    # Design document
│   ├── api-reference.md             # API reference (to be written)
│   ├── quick-start.md               # Quick start guide
│   ├── ci-integration.md            # CI/CD guide
│   └── troubleshooting.md           # Troubleshooting
│
├── .sop/                            # STOP Protocol runtime data
│   └── logs/                        # Application logs
│
├── pyproject.toml                   # Project configuration
├── requirements.txt                 # Dependencies
├── requirements-dev.txt             # Dev dependencies
├── CONTRIBUTING.md                  # Contributing guide
└── README.md                        # This file
```

## Development

### Prerequisites

```bash
# Python 3.10+
python --version  # Should be 3.10, 3.11, or 3.12

# pip or uv
pip --version     # or uv --version
```

### Setup

```bash
# Clone repository
git clone https://github.com/langfuse/langfuse-examples.git
cd langfuse-examples/skill-observability-toolkit

# Install dependencies
pip install -e ".[dev]"
# or
uv pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your Langfuse credentials
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_manifest.py -v

# Run specific test class
pytest tests/unit/test_manifest.py::TestManifestParser -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/

# All checks
ruff format src/ tests/
ruff check src/ tests/
mypy src/
```

### Pre-commit Hooks

```bash
# Install
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## Implementation Phases

### Phase 1: Skill Layer Foundation (Current) 🚧

**Goal**: Implement STOP Protocol L0-L2 + Langfuse Tracing SDK

**Tasks**:
- [x] Task 1.1: Project Skeleton ✅ (current)
- [ ] Task 1.2: STOP Manifest Parser
- [ ] Task 1.3: STOP Tracer
- [ ] Task 1.4: Assertion Engine
- [ ] Task 1.5: Langfuse Client
- [ ] Task 1.6: Tracing Decorators
- [ ] Task 1.7: Trace ID Context
- [ ] Task 1.8: CLI init command
- [ ] Task 1.9: CLI validate command
- [ ] Task 1.10: Basic Example

**Timeline**: 2-3 weeks  
**Status**: Skeleton created, core modules to implement

### Phase 2: CI/CD Layer 📋

**Goal**: Implement CI/CD tracing + performance analysis

**Tasks**:
- [ ] CI/CD Step Tracing
- [ ] Build Profiler
- [ ] GitHub Actions support
- [ ] GitLab CI support

### Phase 3: End-to-End Correlation 📋

**Goal**: Trace ID propagation + unified visualization

**Tasks**:
- [ ] CI → Skill propagation
- [ ] Skill → MCP propagation
- [ ] Unified labels
- [ ] Dashboard integration

### Phase 4: Integration with mcp-with-tracing 📋

**Goal**: Reuse alerting and feedback systems

**Tasks**:
- [ ] Alert system integration
- [ ] Feedback system integration

### Phase 5: Release and Ecosystem 📋

**Goal**: PyPI release + community

**Tasks**:
- [ ] PyPI publication
- [ ] Documentation website
- [ ] Community promotion

## Contributing

We welcome all contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### How to Contribute

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow

1. Create feature branch from `main`
2. Implement feature with tests
3. Run tests: `pytest --cov=src`
4. Run linting: `ruff check src/ tests/`
5. Submit PR with clear description

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on [STOP Protocol](https://agentskills.io) - Skill Transparency & Observability Protocol
- Powered by [Langfuse](https://langfuse.com) - LLM observability platform

## Contact

- **Project Lead**: [Your Name] \<email@example.com\>
- **Discord**: [Join our Discord](https://discord.gg/example)
- **Twitter**: [@skill_observability](https://twitter.com/example)

## Roadmap

See the [open issues](https://github.com/langfuse/langfuse-examples/issues) for a list of proposed features (and known issues).

---

**Made with ❤️ by the skill-observability-toolkit Team**