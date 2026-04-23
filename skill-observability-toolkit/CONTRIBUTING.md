# skill-observability-toolkit

End-to-end Agent Skill Observability Platform

## Project Status

**Phase**: Phase 1 - Skill Layer Foundation (in progress)  
**Python Version**: 3.10+  
**License**: MIT

## Quick Links

- [Design Document](docs/DESIGN.md) - Complete technical design
- [README](README.md) - Project overview and value proposition
- [API Reference](docs/api-reference.md) - API documentation (to be written)

## Documentation

- [Design Document](docs/DESIGN.md) - Complete technical design
- [Quick Start](docs/quick-start.md) - Getting started guide (to be written)
- [API Reference](docs/api-reference.md) - API documentation (to be written)
- [CI Integration](docs/ci-integration.md) - GitHub Actions / GitLab CI guide (to be written)
- [Troubleshooting](docs/troubleshooting.md) - Common issues (to be written)

## Development

### Prerequisites

- Python 3.10+
- pip or uv

### Installation

```bash
# Using pip
pip install -e .

# Using uv
uv pip install -e .
```

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# or with uv
uv pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_manifest.py -v
```

### Code Quality

```bash
# Formatting
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Format and lint together
ruff format src/ tests/
ruff check --fix src/ tests/
```

### Pre-commit Hooks (optional)

```bash
# Install pre-commit
pip install pre-commit
pre-commit install
```

## Project Structure

```
skill-observability-toolkit/
├── src/
│   └── skill_observability_toolkit/
│       ├── stop/              # STOP Protocol implementation
│       ├── langfuse_integration/  # Langfuse SDK integration
│       ├── ci/                # CI/CD tracing
│       └── cli/               # CLI tools
├── examples/                  # Example skills
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures
├── docs/                      # Documentation
│   ├── DESIGN.md              # This design document
│   ├── api-reference.md       # API documentation
│   └── ...
├── .sop/                      # STOP Protocol runtime data
│   └── logs/                  # Application logs
├── pyproject.toml             # Project configuration
├── README.md                  # Project overview
└── LICENSE                    # MIT License
```

## Implementation Phases

### Phase 1: Skill Layer Foundation (Current) 🚧
- [ ] Task 1.1: Project Skeleton (current task)
- [ ] Task 1.2: STOP Manifest Parser
- [ ] Task 1.3: STOP Tracer
- [ ] Task 1.4: Assertion Engine
- [ ] Task 1.5: Langfuse Client
- [ ] Task 1.6: Tracing Decorators
- [ ] Task 1.7: Trace ID Context
- [ ] Task 1.8: CLI init command
- [ ] Task 1.9: CLI validate command
- [ ] Task 1.10: Basic Example

### Phase 2: CI/CD Layer (Planned)
- [ ] CI/CD Tracing
- [ ] Build Profiler
- [ ] GitHub Actions / GitLab CI support

### Phase 3: End-to-End Correlation (Planned)
- [ ] Trace ID propagation across layers
- [ ] Unified view in Langfuse Dashboard

### Phase 4: Integration with mcp-with-tracing (Planned)
- [ ] Alert system integration
- [ ] Feedback system integration

### Phase 5: Release and Ecosystem (Planned)
- [ ] PyPI release
- [ ] Documentation website
- [ ] Community推广

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on [STOP Protocol](https://agentskills.io)
- Powered by [Langfuse](https://langfuse.com)
