# MCP Server Langfuse Observability Platform

> **Project Type**: Production LLM Observability Platform  
> **Target**: External SaaS Customers (1K-10K calls/day)  
> **Tech Stack**: Python + FastMCP Framework + Langfuse Cloud  
> **Created**: 2026-04-08

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Requirements Analysis](#requirements-analysis)
3. [Architecture Design](#architecture-design)
4. [Implementation Guide](#implementation-guide)
5. [Development Standards](#development-standards)
6. [Best Practices](#best-practices)
7. [References](#references)

---

## 🎯 Project Overview

### Problem Statement

Design and implement a comprehensive Langfuse-based observability platform for MCP Server applications that provides:

- **Call Success Rate Monitoring**: Track MCP tool invocation success/failure rates in real-time
- **Prompt Path Tracking**: Monitor different prompt versions and their invocation paths
- **Performance Observability**: Latency tracking, response time analysis
- **User Satisfaction**: Acceptance/rejection signal collection and analysis
- **Prompt Effectiveness**: A/B testing, variant comparison, prompt optimization insights

### Business Objectives

1. **Proactive Failure Detection**: Automated alerting on anomalies and failures
2. **Prompt Optimization**: Data-driven prompt engineering and variant testing
3. **Service Quality Monitoring**: SLA tracking and performance benchmarking
4. **User Behavior Analytics**: Understand how users interact with MCP tools
5. **Cost/Performance Optimization**: Identify expensive or slow operations

### Target Metrics

| Metric Category | Specific Metrics | Target |
|----------------|------------------|--------|
| Availability | Tool call success rate | >99.5% |
| Performance | P95 latency | <500ms |
| Quality | User acceptance rate | >85% |
| Observability | Trace completeness | 100% |
| Cost | Token usage per call | Optimize by prompt version |

---

## 🔍 Requirements Analysis

### Functional Requirements

#### 1. MCP Tool Call Logging

**Requirement**: Capture every MCP tool invocation with full context

**Details**:
- Log tool name, input parameters, output, execution time
- Track tool call hierarchy (parent/child relationships)
- Capture errors and exceptions with stack traces
- Support both sync and async tool invocations

**Integration Points**:
- FastMCP tool handler decorators
- MCP request/response middleware
- Error handling hooks

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md) for complete instrumentation patterns.

#### 2. MCP Request/Response Tracking

**Requirement**: Monitor MCP protocol interactions end-to-end

**Details**:
- Track MCP protocol messages (initialize, tools/list, tools/call, etc.)
- Capture request metadata (session ID, user ID, client info)
- Log response payloads with size tracking
- Monitor request/response timing

**Integration Points**:
- MCP server middleware layer
- Protocol message handlers
- Session management layer

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#request-response-tracking).

#### 3. Session Tracing

**Requirement**: Link multiple tool calls into end-to-end user sessions

**Details**:
- Generate or propagate session IDs across calls
- Track user journey through multiple tool invocations
- Support session grouping for multi-tenant scenarios
- Enable session replay and analysis

**Integration Points**:
- Session context propagation
- User authentication/authorization layer
- Client session management

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#session-tracing).

#### 4. Prompt Versioning & Comparison

**Requirement**: Track and compare different prompt versions

**Details**:
- Attach prompt version metadata to traces
- Support A/B testing workflows
- Compare success rates across versions
- Track prompt evolution over time

**Integration Points**:
- Prompt template management
- Prompt selection logic
- Version metadata injection

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#prompt-versioning).

#### 5. Feedback Collection

**Requirement**: Capture user satisfaction signals

**Details**:
- Accept/reject signals from user interactions
- Optional feedback comments or ratings
- Feedback propagation to traces
- Feedback aggregation and analysis

**Integration Points**:
- Response delivery layer
- User feedback UI/API
- Feedback processing pipeline

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#feedback-collection).

#### 6. Alerting & Notification

**Requirement**: Proactive anomaly detection and alerting

**Details**:
- Define alert rules (success rate thresholds, latency spikes)
- Support multi-channel notifications (email, Slack, PagerDuty)
- Alert fatigue prevention (grouping, deduplication)
- Escalation policies

**Integration Points**:
- Langfuse alerting configuration
- External notification services
- Incident management integration

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#alerting).

### Non-Functional Requirements

#### Performance

- **Overhead**: <5% latency increase per instrumented call
- **Throughput**: Support 10K+ calls/day with real-time trace ingestion
- **Scalability**: Handle burst traffic (10x normal load)

#### Reliability

- **Trace Completeness**: 100% of tool calls must be traced
- **Data Durability**: No trace data loss (Langfuse cloud SLA)
- **Graceful Degradation**: Continue operation if observability fails

#### Security

- **Data Privacy**: No PII in traces unless explicitly allowed
- **Access Control**: Role-based access to observability data
- **API Security**: Secure Langfuse API key management

> 📖 **详细要求**: See [docs/security-guide.md](docs/security-guide.md) for complete security standards.

---

## 🏗️ Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Clients                              │
│              (Claude Desktop, IDE Extensions, etc.)             │
└────────────────────────┬────────────────────────────────────────┘
                         │ MCP Protocol
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Layer                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastMCP Framework                             │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │        Instrumentation Middleware                   │  │  │
│  │  │  - Request/Response Tracking                        │  │  │
│  │  │  - Session Context Propagation                      │  │  │
│  │  │  - Error Capture & Exception Handling              │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │           Tool Handlers (Decorated)                 │  │  │
│  │  │  @observe - Auto-tracing                            │  │  │
│  │  │  @track_session - Session binding                   │  │  │
│  │  │  @track_prompt_version - Version tracking          │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LLM Provider Layer                              │
│         (OpenAI, Anthropic, Custom Models, etc.)                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Observability Layer (Langfuse)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Langfuse SDK (Python)                                     │  │
│  │  - Trace/Span Management                                   │  │
│  │  - Session Tracking                                        │  │
│  │  - Prompt Versioning                                       │  │
│  │  - Feedback Collection                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Langfuse Cloud                                            │  │
│  │  - Trace Storage & Querying                                │  │
│  │  - Dashboards & Analytics                                  │  │
│  │  - Alerting Engine                                         │  │
│  │  - Prompt Management                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Client Request
   ↓
2. MCP Protocol Handler (Instrumented)
   → Create Root Span
   → Attach Session Context
   → Log Request Metadata
   ↓
3. Tool Selection & Execution (Decorated)
   → Create Child Span
   → Attach Prompt Version
   → Track Execution Time
   → Capture Output
   ↓
4. LLM Invocation (Traced)
   → Create Generation Span
   → Track Token Usage
   → Log Model/Parameters
   → Capture LLM Response
   ↓
5. Response Delivery
   → Update Root Span Output
   → Calculate Total Duration
   → Flush to Langfuse
   ↓
6. User Feedback (Optional, Async)
   → Update Trace with Feedback
   → Or Create Feedback Observation
```

### Component Breakdown

#### 1. Instrumentation Layer

**File**: `src/observability/instrumentation.py`

**Responsibilities**:
- Initialize Langfuse client
- Configure trace sampling (if needed)
- Set up context propagation
- Provide instrumentation decorators

**Key APIs**:
- `init_observability(config: ObservabilityConfig)`
- `@observe_tool(name, as_type="span")`
- `@track_session(session_id, user_id)`
- `@track_prompt_version(version, prompt_id)`

#### 2. Session Management

**File**: `src/observability/session.py`

**Responsibilities**:
- Generate/propagate session IDs
- Maintain session context across calls
- Track user identity
- Support multi-tenant isolation

**Key APIs**:
- `SessionContext.get_session_id()`
- `SessionContext.set_session(session_id, user_id)`
- `SessionContext.clear()`

#### 3. Prompt Versioning

**File**: `src/observability/prompt_versioning.py`

**Responsibilities**:
- Track prompt template versions
- Inject version metadata into traces
- Support prompt comparison queries
- Manage prompt evolution history

**Key APIs**:
- `PromptVersionManager.get_version(prompt_id)`
- `PromptVersionManager.set_active_version(prompt_id, version)`
- `attach_version_metadata(span, prompt_id, version)`

#### 4. Feedback Collection

**File**: `src/observability/feedback.py`

**Responsibilities**:
- Collect acceptance/rejection signals
- Attach feedback to traces
- Support optional comments/ratings
- Aggregate feedback for analysis

**Key APIs**:
- `FeedbackCollector.record_acceptance(trace_id, user_id)`
- `FeedbackCollector.record_rejection(trace_id, user_id, reason)`
- `FeedbackCollector.attach_comment(trace_id, comment)`

#### 5. Metrics & Alerting

**File**: `src/observability/alerting.py`

**Responsibilities**:
- Define success rate thresholds
- Configure latency alerting rules
- Set up notification channels
- Handle alert escalation

**Key APIs**:
- `AlertManager.configure_success_rate_alert(threshold=0.99)`
- `AlertManager.configure_latency_alert(p95_threshold_ms=500)`
- `AlertManager.add_notification_channel(channel_type, config)`

---

## 🛠️ Implementation Guide

### Phase 1: Core Instrumentation (Week 1)

**Objective**: Establish basic trace collection for all MCP tool calls

**Tasks**:
1. Install Langfuse SDK and configure connection
2. Create instrumentation module with decorators
3. Apply `@observe` decorator to all MCP tool handlers
4. Verify traces appear in Langfuse dashboard
5. Set up basic success rate monitoring

**Deliverables**:
- [ ] `src/observability/instrumentation.py` implemented
- [ ] All tool handlers decorated with `@observe`
- [ ] Langfuse dashboard showing tool call traces
- [ ] Basic success/failure tracking working

**Verification**:
```bash
# Run test tool call
python -m pytest tests/test_instrumentation.py

# Verify trace in Langfuse
curl https://cloud.langfuse.com/api/public/traces?limit=1
```

> 📖 **详细实现**: See [docs/backend-standards.md](docs/backend-standards.md#instrumentation).

### Phase 2: Session Tracing (Week 2)

**Objective**: Link tool calls into end-to-end user sessions

**Tasks**:
1. Implement session context management
2. Propagate session_id through MCP requests
3. Use `propagate_attributes` to attach session/user metadata
4. Create session-scoped dashboards in Langfuse
5. Test multi-session scenarios

**Deliverables**:
- [ ] `src/observability/session.py` implemented
- [ ] Session ID propagation working across calls
- [ ] Langfuse session views functional
- [ ] Session replay capability demonstrated

**Verification**:
```bash
# Test session propagation
python -m pytest tests/test_session_tracing.py -v

# Verify session linkage in Langfuse
# Check that multiple tool calls show same session_id
```

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#session-tracing).

### Phase 3: Prompt Versioning (Week 3)

**Objective**: Track and compare different prompt versions

**Tasks**:
1. Implement prompt version metadata injection
2. Attach `version` attribute to traces
3. Create version comparison queries
4. Build prompt effectiveness dashboard
5. Test A/B switching scenarios

**Deliverables**:
- [ ] `src/observability/prompt_versioning.py` implemented
- [ ] Version metadata visible in traces
- [ ] Comparison queries working
- [ ] Prompt dashboard created

**Verification**:
```bash
# Test prompt version tracking
python -m pytest tests/test_prompt_versioning.py -v

# Query traces by version in Langfuse
# Verify version field appears in trace attributes
```

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#prompt-versioning).

### Phase 4: Feedback Collection (Week 4)

**Objective**: Capture and analyze user satisfaction signals

**Tasks**:
1. Implement feedback collection API
2. Create feedback observation patterns
3. Build feedback aggregation queries
4. Create user satisfaction dashboard
5. Integrate with client feedback mechanisms

**Deliverables**:
- [ ] `src/observability/feedback.py` implemented
- [ ] Accept/reject signals captured in traces
- [ ] Feedback aggregation working
- [ ] Satisfaction dashboard created

**Verification**:
```bash
# Test feedback collection
python -m pytest tests/test_feedback.py -v

# Verify feedback appears in traces
# Check aggregated satisfaction metrics
```

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#feedback-collection).

### Phase 5: Alerting & Notification (Week 5)

**Objective**: Proactive anomaly detection and alerting

**Tasks**:
1. Configure success rate alerts
2. Set up latency monitoring alerts
3. Configure notification channels (Slack, Email)
4. Test alert triggering
5. Document escalation procedures

**Deliverables**:
- [ ] `src/observability/alerting.py` implemented
- [ ] Alert rules configured in Langfuse
- [ ] Notification channels tested
- [ ] Runbook for incident response

**Verification**:
```bash
# Simulate failure to trigger alert
python scripts/trigger_test_alert.py

# Verify alert received in configured channels
```

> 📖 **详细实现**: See [docs/integration-patterns.md](docs/integration-patterns.md#alerting).

---

## 🔧 Development Standards

> **CRITICAL**: All code development MUST strictly follow these standards. Non-compliance will result in code rejection during review.

### Backend Development

**Technology Stack**: Python 3.11+ with FastMCP Framework

**Core Standards**:
- ✅ Use `black` for formatting, `isort` for imports, `ruff` for linting
- ✅ Complete type annotations for ALL functions
- ✅ Docstrings (Google style) for all public functions/classes
- ✅ Minimum 90% test coverage, 95% for critical paths

> 📖 **详细规范**: See [docs/backend-standards.md](docs/backend-standards.md) for:
> - Code style and formatting requirements
> - Error handling patterns
> - Configuration management
> - Logging standards

### Frontend Development

**Technology Stack**: React 18.3+ with TypeScript, Ant Design 5.x, Vite 5.x

**Core Standards**:
- ✅ Functional components with hooks only (no class components)
- ✅ TypeScript interfaces for ALL props
- ✅ Zustand for client state, React Query for server state
- ✅ Minimum 80% test coverage for components

> 📖 **详细规范**: See [docs/frontend-standards.md](docs/frontend-standards.md) for:
> - Component development patterns
> - State management architecture
> - API integration standards
> - Performance optimization requirements

### Testing Standards

**Mandatory Requirements**:
- **Unit Tests**: pytest + React Testing Library
- **Integration Tests**: testcontainers for external dependencies
- **E2E Tests**: Cypress for critical user flows
- **Coverage**: 90% overall, 95% for critical paths

> 📖 **详细规范**: See [docs/testing-guide.md](docs/testing-guide.md) for:
> - Test structure and organization
> - Mocking patterns
> - Test data management
> - CI/CD test automation

### Security Standards

**Mandatory Requirements**:
- ✅ Environment variables for ALL secrets
- ✅ PII redaction before logging/tracing
- ✅ Input validation with Pydantic models
- ✅ JWT-based authentication with role-based authorization

> 📖 **详细规范**: See [docs/security-guide.md](docs/security-guide.md) for:
> - Secrets management patterns
> - Data privacy and PII handling
> - Input validation requirements
> - Security scanning automation

### Code Review Standards

**Mandatory Workflow**:
1. Create feature branch
2. Implement changes with tests
3. Run ALL tests locally (must pass)
4. Run linting and security scans (must pass)
5. Create Pull Request with description
6. CI/CD pipeline runs (must pass)
7. At least 2 reviewers assigned
8. Address ALL review comments
9. Final approval from tech lead
10. Squash and merge to main

> 📖 **详细规范**: See [docs/code-review-guide.md](docs/code-review-guide.md) for:
> - Review criteria checklist
> - Reviewer responsibilities
> - Comment format standards
> - Automated check requirements

---

## 📊 Monitoring & Metrics

### Key Metrics Dashboard

#### 1. Success Rate Monitoring

**Metric**: `tool_call_success_rate`

**Formula**: 
```
success_rate = (successful_calls / total_calls) * 100
```

**Visualization**:
- Time series chart showing success rate over time
- Threshold lines (warning at 99%, critical at 95%)
- Breakdown by tool name

**Alert Rule**:
```yaml
alert: tool_success_rate_low
expr: tool_call_success_rate < 99
for: 5m
severity: warning
channels: [slack-alerts]
```

#### 2. Latency Tracking

**Metrics**:
- `tool_call_duration_p50`
- `tool_call_duration_p95`
- `tool_call_duration_p99`

**Visualization**:
- Heatmap of latency distribution
- Percentile lines over time
- Breakdown by tool and prompt version

**Alert Rule**:
```yaml
alert: tool_latency_high
expr: tool_call_duration_p95 > 500ms
for: 10m
severity: warning
```

#### 3. User Satisfaction

**Metric**: `user_acceptance_rate`

**Formula**:
```
acceptance_rate = (accepted_responses / total_responses_with_feedback) * 100
```

**Visualization**:
- Gauge showing current acceptance rate
- Trend over time
- Breakdown by prompt version

#### 4. Prompt Effectiveness

**Metrics**:
- `prompt_version_success_rate`
- `prompt_version_acceptance_rate`
- `prompt_version_avg_latency`

**Visualization**:
- Comparison table of prompt versions
- Bar chart comparing key metrics
- Trend lines for version evolution

> 📖 **详细实现**: See [docs/monitoring-guide.md](docs/monitoring-guide.md) for complete dashboard designs and alert configurations.

---

## ✅ Best Practices

### Instrumentation Best Practices

1. **Always Use Session Context**
   - Ensure every trace has session_id and user_id
   - Use contextvars for automatic propagation
   - Never hardcode session IDs

2. **Attach Prompt Version Metadata**
   - Version all prompts explicitly
   - Include prompt_id alongside version
   - Track version in prompt registry

3. **Handle Errors Gracefully**
   - Let Langfuse capture exceptions automatically
   - Add custom error metadata when needed
   - Don't suppress exceptions for tracing

4. **Balance Granularity vs Overhead**
   - One span per logical operation
   - Avoid over-nesting (max 3-4 levels)
   - Use events for fine-grained logging within spans

### Performance Best Practices

1. **Minimize Synchronous Overhead**
   - Langfuse SDK is async-friendly
   - Use background flush for batch ingestion
   - Don't block on trace submission

2. **Optimize Trace Size**
   - Avoid logging large payloads (>10KB)
   - Truncate large strings in inputs/outputs
   - Use metadata for summary info

3. **Configure Sampling (if needed)**
   - Default: 100% sampling for critical paths
   - Consider sampling for high-volume, low-value paths
   - Never sample below 10% for observability data

### Security Best Practices

1. **Protect Sensitive Data**
   - Redact PII before logging
   - Use env vars for API keys
   - Restrict Langfuse access with RBAC

2. **Secure API Keys**
   - Never commit keys to git
   - Rotate keys periodically
   - Use different keys for dev/staging/prod

3. **Data Retention**
   - Configure retention policies in Langfuse
   - Delete traces after retention period
   - Comply with data privacy regulations (GDPR, CCPA)

> 📖 **详细实践**: See [docs/best-practices.md](docs/best-practices.md) for comprehensive guidelines.

---

## 📚 References

### Official Documentation

- **Langfuse Documentation**: https://langfuse.com/docs
- **Langfuse Python SDK**: https://langfuse.com/docs/sdk/python
- **FastMCP Framework**: https://github.com/anthropics/mcp-server-python
- **MCP Protocol Spec**: https://spec.modelcontextprotocol.io/

### Key Concepts

- **Traces**: End-to-end view of a single operation
- **Spans**: Individual operations within a trace
- **Sessions**: Group of related traces (user session)
- **Scores**: User feedback attached to traces
- **Observations**: General term for traces/spans/generations

### Community Resources

- **Langfuse Discord**: https://discord.gg/langfuse
- **Langfuse GitHub**: https://github.com/langfuse/langfuse
- **Example Implementations**: See `/examples` directory

### Project Documentation

- 📖 [Integration Patterns](docs/integration-patterns.md) - Complete code examples for all integration scenarios
- 📖 [Backend Standards](docs/backend-standards.md) - Python development standards and best practices
- 📖 [Frontend Standards](docs/frontend-standards.md) - React development standards and best practices
- 📖 [Testing Guide](docs/testing-guide.md) - Testing standards and patterns
- 📖 [Security Guide](docs/security-guide.md) - Security requirements and patterns
- 📖 [Code Review Guide](docs/code-review-guide.md) - Code review process and standards
- 📖 [Monitoring Guide](docs/monitoring-guide.md) - Dashboard designs and alert configurations
- 📖 [Best Practices](docs/best-practices.md) - Comprehensive best practices guide

---

## 📝 Implementation Status

**Current Phase**: Planning Complete, Ready for Implementation

**Next Steps**:
1. Set up development environment
2. Install dependencies (langfuse, fastmcp)
3. Begin Phase 1 implementation (Core Instrumentation)

**Estimated Timeline**: 5 weeks for complete implementation

---

## 🤝 Contributing

When contributing to this project:

1. Follow instrumentation patterns defined in this document
2. Ensure all new tools are decorated with `@observe`
3. Add tests for new instrumentation logic
4. Update this AGENTS.md with new patterns or best practices
5. Follow the [Code Review Guide](docs/code-review-guide.md) for all contributions

---

**Last Updated**: 2026-04-08  
**Maintained By**: Platform Team  
**Version**: 1.0.0