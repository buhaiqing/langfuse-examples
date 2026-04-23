"""
Alert System Integration.

This module provides integration with the alert system from mcp-with-tracing.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertSeverity(Enum):
    """Alert severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    description: str
    severity: AlertSeverity
    expression: str  # e.g., "duration_ms > 5000"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "expression": self.expression,
            "enabled": self.enabled,
            "tags": self.tags,
            "annotations": self.annotations,
        }


@dataclass
class Alert:
    """An alert instance."""
    id: str
    name: str
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    tags: list[str] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "annotations": self.annotations,
            "context": self.context,
        }


class AlertManager:
    """
    Manage alerting system.

    Provides functionality to:
    - Load alert rules from YAML
    - Evaluate alert conditions
    - Trigger alerts
    - Send notifications
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize the alert manager.

        Args:
            config_path: Path to alert config YAML file
        """
        self._rules: dict[str, AlertRule] = {}
        self._active_alerts: dict[str, Alert] = {}
        self._config_path = config_path

        # Try to load config
        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str) -> "AlertManager":
        """
        Load alert rules from YAML config.

        Args:
            config_path: Path to config file

        Returns:
            Self for method chaining
        """
        try:
            import yaml
            from pathlib import Path
            
            config_file = Path(config_path)
            if not config_file.exists():
                self._rules = self._load_default_rules()
                return self
            
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            if not config or "rules" not in config:
                self._rules = self._load_default_rules()
                return self
            
            # Parse rules from config
            for rule_data in config.get("rules", []):
                rule = AlertRule(
                    name=rule_data.get("name", ""),
                    description=rule_data.get("description", ""),
                    severity=AlertSeverity(rule_data.get("severity", "warning")),
                    expression=rule_data.get("expression", ""),
                    enabled=rule_data.get("enabled", True),
                    tags=rule_data.get("tags", []),
                    annotations=rule_data.get("annotations", {}),
                )
                self._rules[rule.name] = rule
            
        except Exception:
            # Fallback to default rules on error
            self._rules = self._load_default_rules()
        
        return self

    def _load_default_rules(self) -> dict[str, AlertRule]:
        """Load default alert rules."""
        return {
            "high_latency": AlertRule(
                name="High Latency",
                description="Response time exceeds threshold",
                severity=AlertSeverity.WARNING,
                expression="duration_ms > 5000",
                enabled=True,
                tags=["performance", "latency"],
                annotations={
                    "runbook_url": "https://runbooks.example.com/high-latency",
                    "contact": "platform-team@example.com",
                },
            ),
            "high_error_rate": AlertRule(
                name="High Error Rate",
                description="Error rate exceeds threshold",
                severity=AlertSeverity.CRITICAL,
                expression="error_count > 100",
                enabled=True,
                tags=["reliability", "errors"],
                annotations={
                    "runbook_url": "https://runbooks.example.com/high-error-rate",
                    "contact": "platform-team@example.com",
                },
            ),
            "memory_pressure": AlertRule(
                name="Memory Pressure",
                description="Memory usage exceeds threshold",
                severity=AlertSeverity.WARNING,
                expression="memory_mb > 512",
                enabled=True,
                tags=["resources", "memory"],
                annotations={
                    "runbook_url": "https://runbooks.example.com/memory-pressure",
                    "contact": "platform-team@example.com",
                },
            ),
        }

    def register_rule(self, rule: AlertRule) -> "AlertManager":
        """
        Register a new alert rule.

        Args:
            rule: Alert rule to register

        Returns:
            Self for method chaining
        """
        self._rules[rule.name] = rule
        return self

    def unregister_rule(self, rule_name: str) -> "AlertManager":
        """
        Remove an alert rule.

        Args:
            rule_name: Name of rule to remove

        Returns:
            Self for method chaining
        """
        if rule_name in self._rules:
            del self._rules[rule_name]
        return self

    def evaluate(self, rule_name: str, context: dict[str, Any]) -> Alert | None:
        """
        Evaluate an alert rule against context.

        Args:
            rule_name: Name of rule to evaluate
            context: Context data to evaluate against

        Returns:
            Alert if triggered, None otherwise
        """
        rule = self._rules.get(rule_name)

        if not rule:
            return None

        if not rule.enabled:
            return None

        # Parse and evaluate expression
        if self._evaluate_expression(rule.expression, context):
            # Generate alert
            alert = Alert(
                id=self._generate_alert_id(rule_name),
                name=rule.name,
                rule_name=rule_name,
                severity=rule.severity,
                message=self._generate_alert_message(rule, context),
                timestamp=self._current_timestamp(),
                tags=rule.tags.copy(),
                annotations=rule.annotations.copy(),
                context=context,
            )

            self._active_alerts[alert.id] = alert

            return alert

        return None

    def _evaluate_expression(
        self,
        expression: str,
        context: dict[str, Any],
    ) -> bool:
        """
        Evaluate alert expression against context.

        Args:
            expression: Alert expression (e.g., "duration_ms > 5000")
            context: Context data

        Returns:
            True if expression evaluates to True
        """
        # Parse simple expression (field operator value)
        # e.g., "duration_ms > 5000"
        match = re.match(r"(\w+)\s*([<>=!]+)\s*([\d.]+)", expression)

        if not match:
            return False

        field_name, operator, value = match.groups()
        value = float(value)

        field_value = context.get(field_name)

        if field_value is None:
            return False

        field_value = float(field_value)

        if operator == ">":
            return field_value > value
        elif operator == "<":
            return field_value < value
        elif operator == ">=":
            return field_value >= value
        elif operator == "<=":
            return field_value <= value
        elif operator == "==":
            return field_value == value
        elif operator == "!=":
            return field_value != value

        return False

    def _generate_alert_id(self, rule_name: str) -> str:
        """Generate unique alert ID."""
        import uuid
        return f"alert_{rule_name}_{uuid.uuid4().hex[:8]}"

    def _generate_alert_message(
        self,
        rule: AlertRule,
        context: dict[str, Any],
    ) -> str:
        """Generate alert message."""
        # Extract values from context
        values = []
        for key, value in context.items():
            values.append(f"{key}={value}")

        return f"{rule.name}: {' | '.join(values)}"

    def _current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()

    def get_rule(self, rule_name: str) -> AlertRule | None:
        """Get an alert rule."""
        return self._rules.get(rule_name)

    def get_active_alerts(self) -> dict[str, Alert]:
        """Get all active alerts."""
        return self._active_alerts.copy()

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if resolved
        """
        if alert_id in self._active_alerts:
            del self._active_alerts[alert_id]
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rules": {name: rule.to_dict() for name, rule in self._rules.items()},
            "active_alerts": {
                id: alert.to_dict() for id, alert in self._active_alerts.items()
            },
        }


# Global alert manager instance
_alert_manager = AlertManager()


def load_alert_config(config_path: str) -> AlertManager:
    """Load alert config (convenience function)."""
    return _alert_manager.load_config(config_path)


def evaluate_alert(
    rule_name: str,
    context: dict[str, Any],
) -> Alert | None:
    """Evaluate alert rule (convenience function)."""
    return _alert_manager.evaluate(rule_name, context)


def get_alert_manager() -> AlertManager:
    """Get global alert manager (convenience function)."""
    return _alert_manager
