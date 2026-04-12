"""
Alerting and notification management for MCP Langfuse Observability.

Provides alert rule configuration, threshold monitoring, and notification channels.
"""

from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Notification channel types."""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertRule:
    """Represents an alert rule configuration."""
    name: str
    metric: str
    threshold: float
    operator: str  # gt, lt, gte, lte, eq
    severity: AlertSeverity
    window_minutes: int = 60
    channels: list[AlertChannel] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Represents a triggered alert."""
    rule: AlertRule
    triggered_at: str
    value: float
    message: str
    context: dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """
    Manages alert rules and notifications.
    
    Handles rule configuration, threshold checking, and multi-channel notifications.
    """

    def __init__(self):
        self._rules: dict[str, AlertRule] = {}
        self._alerts: list[Alert] = []
        self._notification_handlers: dict[AlertChannel, Callable] = {}

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.name] = rule

    def get_rule(self, name: str) -> Optional[AlertRule]:
        """Get a specific alert rule."""
        return self._rules.get(name)

    def unregister_rule(self, name: str) -> bool:
        """Unregister an alert rule."""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def list_rules(self) -> list[str]:
        """List all registered rule names."""
        return list(self._rules.keys())

    def register_notification_handler(
        self,
        channel: AlertChannel,
        handler: Callable[[Alert], None],
    ) -> None:
        """Register a notification handler for a channel."""
        self._notification_handlers[channel] = handler

    def check_rule(self, rule_name: str, current_value: float) -> Optional[Alert]:
        """
        Check if a rule should trigger.
        
        Args:
            rule_name: Name of the rule to check.
            current_value: Current metric value.
            
        Returns:
            Alert if triggered, None otherwise.
        """
        rule = self.get_rule(rule_name)
        if not rule or not rule.enabled:
            return None

        triggered = False
        if rule.operator == "gt" and current_value > rule.threshold:
            triggered = True
        elif rule.operator == "lt" and current_value < rule.threshold:
            triggered = True
        elif rule.operator == "gte" and current_value >= rule.threshold:
            triggered = True
        elif rule.operator == "lte" and current_value <= rule.threshold:
            triggered = True
        elif rule.operator == "eq" and current_value == rule.threshold:
            triggered = True

        if triggered:
            alert = Alert(
                rule=rule,
                triggered_at=datetime.now(timezone.utc).isoformat(),
                value=current_value,
                message=f"Alert '{rule.name}': {rule.metric} = {current_value} (threshold: {rule.operator} {rule.threshold})",
                context={"rule_name": rule_name, "current_value": current_value},
            )
            self._alerts.append(alert)
            self._send_notifications(alert)
            return alert

        return None

    def _send_notifications(self, alert: Alert) -> None:
        """Send notifications for an alert."""
        for channel in alert.rule.channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    handler(alert)
                except Exception as e:
                    print(f"Failed to send {channel.value} notification: {e}")

    def get_triggered_alerts(self, rule_name: Optional[str] = None) -> list[Alert]:
        """Get previously triggered alerts."""
        if rule_name:
            return [a for a in self._alerts if a.rule.name == rule_name]
        return self._alerts

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert statistics."""
        by_severity = {}
        by_rule = {}

        for alert in self._alerts:
            severity = alert.rule.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

            rule_name = alert.rule.name
            by_rule[rule_name] = by_rule.get(rule_name, 0) + 1

        return {
            "total_alerts": len(self._alerts),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }


_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def configure_success_rate_alert(
    threshold: float = 0.99,
    severity: AlertSeverity = AlertSeverity.WARNING,
    channels: Optional[list[AlertChannel]] = None,
) -> AlertRule:
    """Configure a success rate alert."""
    rule = AlertRule(
        name="success-rate-low",
        metric="success_rate",
        threshold=threshold,
        operator="lt",
        severity=severity,
        window_minutes=60,
        channels=channels or [],
    )
    get_alert_manager().register_rule(rule)
    return rule


def configure_latency_alert(
    threshold_ms: float = 500,
    severity: AlertSeverity = AlertSeverity.WARNING,
    channels: Optional[list[AlertChannel]] = None,
) -> AlertRule:
    """Configure a latency alert (P95)."""
    rule = AlertRule(
        name="latency-high",
        metric="latency_p95_ms",
        threshold=threshold_ms,
        operator="gt",
        severity=severity,
        window_minutes=60,
        channels=channels or [],
    )
    get_alert_manager().register_rule(rule)
    return rule


def check_success_rate(current_rate: float) -> Optional[Alert]:
    """Check success rate against configured threshold."""
    return get_alert_manager().check_rule("success-rate-low", current_rate)


def check_latency(current_latency_ms: float) -> Optional[Alert]:
    """Check latency against configured threshold."""
    return get_alert_manager().check_rule("latency-high", current_latency_ms)
