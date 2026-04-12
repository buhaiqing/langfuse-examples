# Integration Patterns

> **Purpose**: Complete code examples for Langfuse integration with MCP Server  
> **Last Updated**: 2026-04-08

---

## 📋 Table of Contents

1. [Decorator-Based Tool Instrumentation](#pattern-1-decorator-based-tool-instrumentation)
2. [Context Manager for Complex Flows](#pattern-2-context-manager-for-complex-flows)
3. [Session Tracing with Context Propagation](#pattern-3-session-tracing-with-context-propagation)
4. [Prompt Version Tracking](#pattern-4-prompt-version-tracking)
5. [Feedback Collection](#pattern-5-feedback-collection)
6. [Alerting Configuration](#pattern-6-alerting-configuration)

---

## Pattern 1: Decorator-Based Tool Instrumentation

**Use Case**: Auto-trace MCP tool functions without modifying logic

**Code**:
```python
from langfuse import observe, propagate_attributes

@observe(name="mcp-get-prompt", as_type="span")
def mcp_get_prompt(prompt_name: str, user_id: str, session_id: str, prompt_version: str = None):
    with propagate_attributes(user_id=user_id, session_id=session_id, version=prompt_version):
        content = fetch_prompt_from_store(prompt_name, prompt_version)
    return content

def fetch_prompt_from_store(name, version):
    # Placeholder for actual prompt retrieval logic
    return f"Prompt {name} version {version or 'latest'} content"
```

**Benefits**:
- Minimal code change
- Automatic input/output capture
- Exception tracking included
- Easy to apply across codebase

**Integration Points**:
- Apply to all MCP tool handlers
- Use in FastMCP tool decorators
- Combine with session context for full observability

---

## Pattern 2: Context Manager for Complex Flows

**Use Case**: Instrument multi-step operations with nested spans

**Code**:
```python
from langfuse import get_client, propagate_attributes

langfuse = get_client()

def handle_user_request(user_id: str, session_id: str, request_payload: dict):
    with langfuse.start_as_current_observation(
        as_type="span",
        name="user-request",
        input=request_payload
    ) as root:
        with propagate_attributes(session_id=session_id, user_id=user_id):
            # Step 1: Fetch prompt
            prompt = mcp_fetch_prompt("order-status", user_id, session_id, prompt_version="v3")

            # Step 2: Call LLM (nested span)
            with langfuse.start_as_current_observation(as_type="generation", name="llm-call") as gen:
                resp = call_llm(prompt)
                gen.update(output=resp)

            # Step 3: Process response
            result = process_response(resp)

            root.update(output={"result": result})
    return result
```

**Benefits**:
- Explicit control over span hierarchy
- Supports complex multi-step workflows
- Fine-grained timing for each step
- Easy to add custom metadata

**Integration Points**:
- Use for complex tool execution flows
- Instrument request handlers with multiple steps
- Track LLM calls within tool execution

---

## Pattern 3: Session Tracing with Context Propagation

**Use Case**: Ensure all calls in a session are linked

**Code**:
```python
from langfuse import propagate_attributes
from contextvars import ContextVar

# Session context stored in context variable
_current_session: ContextVar[dict] = ContextVar('current_session', default={})

class SessionContext:
    @staticmethod
    def set_session(session_id: str, user_id: str, tenant_id: str = None):
        _current_session.set({
            'session_id': session_id,
            'user_id': user_id,
            'tenant_id': tenant_id
        })

    @staticmethod
    def get_session_id():
        return _current_session.get().get('session_id')

    @staticmethod
    def propagate():
        """Propagate session attributes to Langfuse"""
        ctx = _current_session.get()
        return propagate_attributes(
            session_id=ctx.get('session_id'),
            user_id=ctx.get('user_id'),
            metadata={'tenant_id': ctx.get('tenant_id')}
        )

# Usage in MCP request handler
def handle_mcp_request(request):
    session_id = request.metadata.get('session_id')
    user_id = request.metadata.get('user_id')

    SessionContext.set_session(session_id, user_id)

    with SessionContext.propagate():
        # All nested calls will have session context
        result = process_request(request)

    return result
```

**Benefits**:
- Automatic session propagation
- Thread-safe (using contextvars)
- Works across async boundaries
- Centralized session management

**Integration Points**:
- MCP request middleware
- Authentication layer
- Multi-tenant isolation

---

## Pattern 4: Prompt Version Tracking

**Use Case**: Track which prompt version was used for each call

**Code**:
```python
from langfuse import propagate_attributes

class PromptVersionManager:
    _versions = {}  # prompt_id -> active_version

    @classmethod
    def get_version(cls, prompt_id: str) -> str:
        return cls._versions.get(prompt_id, 'default')

    @classmethod
    def set_version(cls, prompt_id: str, version: str):
        cls._versions[prompt_id] = version

def execute_with_prompt(prompt_id: str, user_input: str, session_id: str, user_id: str):
    version = PromptVersionManager.get_version(prompt_id)

    with propagate_attributes(
        version=version,
        prompt_id=prompt_id,
        session_id=session_id,
        user_id=user_id
    ):
        prompt = load_prompt(prompt_id, version)
        response = call_llm(prompt, user_input)

        # Track prompt effectiveness metrics
        track_prompt_usage(prompt_id, version, success=True)

        return response
```

**Benefits**:
- Version metadata attached to all traces
- Easy to switch versions for A/B testing
- Enables version comparison queries
- Tracks prompt evolution history

**Integration Points**:
- Prompt template management
- A/B testing framework
- Prompt effectiveness analytics

---

## Pattern 5: Feedback Collection

**Use Case**: Capture user satisfaction signals and attach to traces

**Code**:
```python
from langfuse import get_client

langfuse = get_client()

class FeedbackCollector:
    @staticmethod
    def record_acceptance(trace_id: str, user_id: str):
        """User accepted the response"""
        langfuse.score(
            trace_id=trace_id,
            name="user_feedback",
            value=1,
            comment="Accepted",
            user_id=user_id
        )

    @staticmethod
    def record_rejection(trace_id: str, user_id: str, reason: str = None):
        """User rejected the response"""
        langfuse.score(
            trace_id=trace_id,
            name="user_feedback",
            value=0,
            comment=reason or "Rejected",
            user_id=user_id
        )

    @staticmethod
    def record_rating(trace_id: str, user_id: str, rating: int, comment: str = None):
        """User provided a rating (1-5)"""
        langfuse.score(
            trace_id=trace_id,
            name="user_rating",
            value=rating,
            comment=comment,
            user_id=user_id
        )

# Usage
def handle_user_feedback(trace_id: str, feedback: dict, user_id: str):
    if feedback['accepted']:
        FeedbackCollector.record_acceptance(trace_id, user_id)
    else:
        FeedbackCollector.record_rejection(trace_id, user_id, feedback.get('reason'))
```

**Benefits**:
- Feedback linked to specific traces
- Enables satisfaction rate calculations
- Supports both binary and scaled feedback
- Optional comments for qualitative insights

**Integration Points**:
- Response delivery layer
- User feedback UI/API
- Training data pipeline

---

## Pattern 6: Alerting Configuration

**Use Case**: Configure proactive anomaly detection

**Code**:
```python
from typing import Dict, List
from enum import Enum

class AlertSeverity(Enum):
    WARNING = "warning"
    CRITICAL = "critical"

class AlertManager:
    def __init__(self):
        self.alert_rules = []
        self.notification_channels = []

    def configure_success_rate_alert(
        self,
        threshold: float = 0.99,
        duration_minutes: int = 5,
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """Configure success rate alerting"""
        rule = {
            "name": "low_success_rate",
            "condition": f"success_rate < {threshold}",
            "duration": f"{duration_minutes}m",
            "severity": severity.value,
            "channels": self.notification_channels
        }
        self.alert_rules.append(rule)
        return rule

    def configure_latency_alert(
        self,
        p95_threshold_ms: int = 500,
        duration_minutes: int = 10,
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """Configure latency alerting"""
        rule = {
            "name": "high_latency",
            "condition": f"p95_latency > {p95_threshold_ms}ms",
            "duration": f"{duration_minutes}m",
            "severity": severity.value,
            "channels": self.notification_channels
        }
        self.alert_rules.append(rule)
        return rule

    def add_notification_channel(self, channel_type: str, config: Dict):
        """Add notification channel"""
        channel = {
            "type": channel_type,  # "slack", "email", "pagerduty"
            "config": config
        }
        self.notification_channels.append(channel)
        return channel

# Usage
alert_manager = AlertManager()

# Add Slack notification
alert_manager.add_notification_channel("slack", {
    "webhook_url": "https://hooks.slack.com/services/...",
    "channel": "#alerts"
})

# Configure success rate alert
alert_manager.configure_success_rate_alert(
    threshold=0.99,
    duration_minutes=5,
    severity=AlertSeverity.WARNING
)

# Configure latency alert
alert_manager.configure_latency_alert(
    p95_threshold_ms=500,
    duration_minutes=10
)
```

**Benefits**:
- Proactive issue detection
- Configurable thresholds
- Multi-channel notifications
- Alert fatigue prevention

**Integration Points**:
- Langfuse alerting configuration
- External notification services
- Incident management systems

---

## Integration Checklist

Before deploying to production, ensure:

- [ ] All MCP tools decorated with `@observe`
- [ ] Session context propagation implemented
- [ ] Prompt version tracking enabled
- [ ] Feedback collection API ready
- [ ] Alert rules configured
- [ ] Notification channels tested
- [ ] Dashboards created in Langfuse
- [ ] Runbook documented

---

**Related Documentation**:
- [Backend Standards](backend-standards.md) - Python coding standards
- [Monitoring Guide](monitoring-guide.md) - Dashboard and metrics design
- [Best Practices](best-practices.md) - Performance and security guidelines