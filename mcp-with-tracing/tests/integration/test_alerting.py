"""
Integration tests for alerting system.

Tests cover end-to-end alerting scenarios including rule creation,
triggering, notification channels, and statistics.
"""

import pytest
from src.observability.alerting import (
    AlertSeverity,
    AlertChannel,
    AlertManager,
    AlertRule,
    Alert,
    get_alert_manager,
)


@pytest.mark.integration
class TestAlertingIntegration:
    """Integration tests for the alerting system."""

    def test_alert_rule_creation(self):
        """Test creating alert rules with various configurations."""
        rule = AlertRule(
            name="success-rate-low",
            metric="success_rate",
            threshold=0.95,
            operator="lt",
            severity=AlertSeverity.WARNING,
            window_minutes=60,
        )
        assert rule.name == "success-rate-low"
        assert rule.threshold == 0.95
        assert rule.severity == AlertSeverity.WARNING

    def test_alert_triggering_logic(self):
        """Test alert triggering with different operators and values."""
        manager = AlertManager()
        manager.register_rule(
            AlertRule(
                name="success-alert",
                metric="success_rate",
                threshold=0.90,
                operator="lt",
                severity=AlertSeverity.WARNING,
            )
        )
        manager.register_rule(
            AlertRule(
                name="latency-alert",
                metric="latency_p95_ms",
                threshold=500,
                operator="gt",
                severity=AlertSeverity.CRITICAL,
            )
        )

        # Test success rate alert
        alert = manager.check_rule("success-alert", 0.80)
        assert alert is not None

        alert = manager.check_rule("success-alert", 0.95)
        assert alert is None

        # Test latency alert
        alert = manager.check_rule("latency-alert", 600)
        assert alert is not None

        alert = manager.check_rule("latency-alert", 400)
        assert alert is None

    def test_notification_channels(self):
        """Test notification channel registration and invocation."""
        manager = AlertManager()
        notifications_sent = []

        manager.register_notification_handler(
            AlertChannel.SLACK,
            lambda alert: notifications_sent.append(
                ("slack", alert.rule.name, alert.value)
            ),
        )

        manager.register_rule(
            AlertRule(
                name="test-notify",
                metric="test_metric",
                threshold=50,
                operator="gt",
                severity=AlertSeverity.INFO,
                channels=[AlertChannel.SLACK],
            )
        )

        manager.check_rule("test-notify", 75)
        assert len(notifications_sent) > 0

    def test_alert_statistics(self):
        """Test alert statistics aggregation."""
        manager = AlertManager()

        for i, severity in enumerate(
            [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL]
        ):
            rule = AlertRule(
                name=f"perf-alert{i}",
                metric="test",
                threshold=100,
                operator="lt",
                severity=severity,
            )
            manager.register_rule(rule)
            manager.check_rule(rule.name, 50)

        stats = manager.get_alert_statistics()
        assert stats["total_alerts"] == 3
