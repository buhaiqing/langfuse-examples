"""
Alerting and notification management for MCP Langfuse Observability.

Provides alert rule configuration, threshold monitoring, and notification channels.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


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
    Includes alert deduplication with configurable cooldown periods.
    """

    def __init__(self, default_cooldown_minutes: int = 30):
        """
        Initialize AlertManager.

        Args:
            default_cooldown_minutes: Default cooldown period between alerts (minutes).
        """
        self._rules: dict[str, AlertRule] = {}
        self._alerts: list[Alert] = []
        self._notification_handlers: dict[AlertChannel, Callable] = {}
        self._cooldown_minutes: int = default_cooldown_minutes
        self._last_alert_time: dict[str, datetime] = {}  # Rule name -> last alert time
        self._alert_counts: dict[str, list[datetime]] = {}  # Rule name -> list of alert times

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.name] = rule

    def get_rule(self, name: str) -> AlertRule | None:
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

    def check_rule(self, rule_name: str, current_value: float) -> Alert | None:
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

        # Check cooldown period
        if not self._is_alert_allowed(rule_name, rule):
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
            self._record_alert_time(rule_name)
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
                    logger.error("Failed to send %s notification: %s", channel.value, e)

    def _is_alert_allowed(self, rule_name: str, rule: AlertRule) -> bool:
        """
        Check if an alert is allowed based on cooldown and rate limits.

        Args:
            rule_name: Name of the rule.
            rule: AlertRule instance.

        Returns:
            True if alert is allowed, False if in cooldown or rate limited.
        """
        now = datetime.now(timezone.utc)

        # Check cooldown period
        last_time = self._last_alert_time.get(rule_name)
        if last_time:
            cooldown = rule.metadata.get("cooldown_minutes", self._cooldown_minutes)
            elapsed = (now - last_time).total_seconds() / 60
            if elapsed < cooldown:
                logger.debug(
                    "Alert '%s' in cooldown (%.1fmin remaining)",
                    rule_name,
                    cooldown - elapsed,
                )
                return False

        # Check max alerts per hour
        max_per_hour = rule.metadata.get("max_alerts_per_hour")
        if max_per_hour:
            recent_alerts = self._alert_counts.get(rule_name, [])
            # Count alerts in the last hour
            one_hour_ago = now - timedelta(hours=1)
            recent_count = sum(1 for t in recent_alerts if t > one_hour_ago)

            if recent_count >= max_per_hour:
                logger.debug(
                    "Alert '%s' rate limited (%d/%d per hour)",
                    rule_name,
                    recent_count,
                    max_per_hour,
                )
                return False

        return True

    def _record_alert_time(self, rule_name: str) -> None:
        """Record the time an alert was triggered."""
        now = datetime.now(timezone.utc)
        self._last_alert_time[rule_name] = now

        if rule_name not in self._alert_counts:
            self._alert_counts[rule_name] = []
        self._alert_counts[rule_name].append(now)

        # Clean up old entries (keep only last 2 hours)
        cutoff = now - timedelta(hours=2)
        self._alert_counts[rule_name] = [t for t in self._alert_counts[rule_name] if t > cutoff]

    def get_triggered_alerts(self, rule_name: str | None = None) -> list[Alert]:
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


_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def configure_success_rate_alert(
    threshold: float = 0.99,
    severity: AlertSeverity = AlertSeverity.WARNING,
    channels: list[AlertChannel] | None = None,
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
    channels: list[AlertChannel] | None = None,
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


def check_success_rate(current_rate: float) -> Alert | None:
    """Check success rate against configured threshold."""
    return get_alert_manager().check_rule("success-rate-low", current_rate)


def check_latency(current_latency_ms: float) -> Alert | None:
    """Check latency against configured threshold."""
    return get_alert_manager().check_rule("latency-high", current_latency_ms)
