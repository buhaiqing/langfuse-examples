"""
Alerting system tests for MCP Langfuse Observability.

Tests cover alert rule management, threshold checking, notification channels,
and alert statistics.
"""

import pytest
import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.observability.alerting import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertChannel,
    get_alert_manager,
    configure_success_rate_alert,
    configure_latency_alert,
    check_success_rate,
    check_latency,
)


class TestAlertRule:
    """AlertRule dataclass tests."""

    def test_create_basic_rule(self):
        """Test creating a basic alert rule."""
        rule = AlertRule(
            name="test-rule",
            metric="success_rate",
            threshold=0.95,
            operator="lt",
            severity=AlertSeverity.WARNING,
        )

        assert rule.name == "test-rule"
        assert rule.metric == "success_rate"
        assert rule.threshold == 0.95
        assert rule.operator == "lt"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.window_minutes == 60  # default
        assert rule.enabled is True  # default
        assert rule.channels == []  # default
        assert rule.metadata == {}  # default

    def test_create_rule_with_options(self):
        """Test creating an alert rule with all options."""
        rule = AlertRule(
            name="latency-alert",
            metric="latency_p95_ms",
            threshold=500,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
            window_minutes=30,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            enabled=False,
            metadata={"team": "backend"},
        )

        assert rule.window_minutes == 30
        assert len(rule.channels) == 2
        assert AlertChannel.SLACK in rule.channels
        assert rule.enabled is False
        assert rule.metadata["team"] == "backend"


class TestAlertManager:
    """AlertManager core functionality tests."""

    @pytest.fixture
    def manager(self):
        """Provide a fresh AlertManager instance."""
        return AlertManager()

    def test_register_and_get_rule(self, manager):
        """Test registering and retrieving alert rules."""
        rule = AlertRule(
            name="test-rule",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
        )

        manager.register_rule(rule)
        retrieved = manager.get_rule("test-rule")

        assert retrieved is not None
        assert retrieved.name == "test-rule"
        assert retrieved.threshold == 100

    def test_unregister_rule(self, manager):
        """Test unregistering an alert rule."""
        rule = AlertRule(
            name="temp-rule",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
        )

        manager.register_rule(rule)
        assert manager.get_rule("temp-rule") is not None

        result = manager.unregister_rule("temp-rule")
        assert result is True
        assert manager.get_rule("temp-rule") is None

    def test_unregister_nonexistent_rule(self, manager):
        """Test unregistering a rule that doesn't exist."""
        result = manager.unregister_rule("nonexistent")
        assert result is False

    def test_list_rules(self, manager):
        """Test listing all registered rules."""
        rule1 = AlertRule(name="rule1", metric="m1", threshold=1, operator="gt", severity=AlertSeverity.INFO)
        rule2 = AlertRule(name="rule2", metric="m2", threshold=2, operator="gt", severity=AlertSeverity.INFO)

        manager.register_rule(rule1)
        manager.register_rule(rule2)

        rules = manager.list_rules()
        assert len(rules) == 2
        assert "rule1" in rules
        assert "rule2" in rules


class TestAlertTriggering:
    """Alert triggering logic tests."""

    @pytest.fixture
    def manager(self):
        """Provide a fresh AlertManager instance."""
        return AlertManager()

    def test_trigger_gt_operator(self, manager):
        """Test triggering with greater-than operator."""
        rule = AlertRule(
            name="high-latency",
            metric="latency_p95_ms",
            threshold=500,
            operator="gt",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        # Should trigger (600 > 500)
        alert = manager.check_rule("high-latency", 600)
        assert alert is not None
        assert alert.value == 600
        assert alert.rule.name == "high-latency"

        # Should not trigger (400 <= 500)
        alert = manager.check_rule("high-latency", 400)
        assert alert is None

    def test_trigger_lt_operator(self, manager):
        """Test triggering with less-than operator."""
        rule = AlertRule(
            name="low-success-rate",
            metric="success_rate",
            threshold=0.95,
            operator="lt",
            severity=AlertSeverity.CRITICAL,
        )
        manager.register_rule(rule)

        # Should trigger (0.80 < 0.95)
        alert = manager.check_rule("low-success-rate", 0.80)
        assert alert is not None
        assert alert.value == 0.80

        # Should not trigger (0.98 >= 0.95)
        alert = manager.check_rule("low-success-rate", 0.98)
        assert alert is None

    def test_trigger_gte_operator(self, manager):
        """Test triggering with greater-than-or-equal operator."""
        rule = AlertRule(
            name="error-count",
            metric="error_count",
            threshold=10,
            operator="gte",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        # Should trigger (10 >= 10)
        alert = manager.check_rule("error-count", 10)
        assert alert is not None

        # Should not trigger (9 < 10)
        alert = manager.check_rule("error-count", 9)
        assert alert is None

    def test_trigger_lte_operator(self, manager):
        """Test triggering with less-than-or-equal operator."""
        rule = AlertRule(
            name="available-memory",
            metric="memory_mb",
            threshold=100,
            operator="lte",
            severity=AlertSeverity.CRITICAL,
        )
        manager.register_rule(rule)

        # Should trigger (50 <= 100)
        alert = manager.check_rule("available-memory", 50)
        assert alert is not None

        # Should not trigger (200 > 100)
        alert = manager.check_rule("available-memory", 200)
        assert alert is None

    def test_trigger_eq_operator(self, manager):
        """Test triggering with equal operator."""
        rule = AlertRule(
            name="exact-match",
            metric="status_code",
            threshold=500,
            operator="eq",
            severity=AlertSeverity.CRITICAL,
        )
        manager.register_rule(rule)

        # Should trigger (500 == 500)
        alert = manager.check_rule("exact-match", 500)
        assert alert is not None

        # Should not trigger (404 != 500)
        alert = manager.check_rule("exact-match", 404)
        assert alert is None

    def test_disabled_rule_does_not_trigger(self, manager):
        """Test that disabled rules don't trigger alerts."""
        rule = AlertRule(
            name="disabled-rule",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            enabled=False,
        )
        manager.register_rule(rule)

        alert = manager.check_rule("disabled-rule", 200)
        assert alert is None

    def test_check_nonexistent_rule(self, manager):
        """Test checking a rule that doesn't exist."""
        alert = manager.check_rule("nonexistent", 100)
        assert alert is None

    def test_alert_contains_correct_metadata(self, manager):
        """Test that triggered alerts contain correct metadata."""
        rule = AlertRule(
            name="test-alert",
            metric="test_metric",
            threshold=50,
            operator="gt",
            severity=AlertSeverity.WARNING,
            window_minutes=30,
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-alert", 75)

        assert alert is not None
        assert alert.rule.name == "test-alert"
        assert alert.value == 75
        assert alert.rule.threshold == 50
        assert alert.rule.operator == "gt"
        assert alert.rule.window_minutes == 30
        assert alert.triggered_at is not None
        assert "test-alert" in alert.message


class TestNotificationChannels:
    """Notification channel tests."""

    @pytest.fixture
    def manager(self):
        """Provide a fresh AlertManager instance."""
        return AlertManager()

    def test_register_notification_handler(self, manager):
        """Test registering a notification handler."""
        mock_handler = Mock()

        manager.register_notification_handler(AlertChannel.SLACK, mock_handler)

        rule = AlertRule(
            name="test-notify",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
            channels=[AlertChannel.SLACK],
        )
        manager.register_rule(rule)

        manager.check_rule("test-notify", 150)

        mock_handler.assert_called_once()
        alert_arg = mock_handler.call_args[0][0]
        assert isinstance(alert_arg, Alert)
        assert alert_arg.rule.name == "test-notify"

    def test_multiple_notification_channels(self, manager):
        """Test sending notifications to multiple channels."""
        slack_handler = Mock()
        email_handler = Mock()

        manager.register_notification_handler(AlertChannel.SLACK, slack_handler)
        manager.register_notification_handler(AlertChannel.EMAIL, email_handler)

        rule = AlertRule(
            name="multi-channel",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
        )
        manager.register_rule(rule)

        manager.check_rule("multi-channel", 150)

        assert slack_handler.call_count == 1
        assert email_handler.call_count == 1

    def test_notification_handler_exception_handling(self, manager, caplog):
        """Test that notification handler exceptions are caught gracefully."""
        failing_handler = Mock(side_effect=Exception("Notification failed"))

        manager.register_notification_handler(AlertChannel.WEBHOOK, failing_handler)

        rule = AlertRule(
            name="failing-notify",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
            channels=[AlertChannel.WEBHOOK],
        )
        manager.register_rule(rule)

        with caplog.at_level(logging.ERROR, logger="src.observability.alerting"):
            manager.check_rule("failing-notify", 150)
        
        assert "Failed to send webhook notification" in caplog.text


class TestAlertStatistics:
    """Alert statistics tests."""

    @pytest.fixture
    def manager(self):
        """Provide a fresh AlertManager instance."""
        return AlertManager()

    def test_empty_statistics(self, manager):
        """Test statistics when no alerts have been triggered."""
        stats = manager.get_alert_statistics()

        assert stats["total_alerts"] == 0
        assert stats["by_severity"] == {}
        assert stats["by_rule"] == {}

    def test_statistics_by_severity(self, manager):
        """Test statistics grouped by severity."""
        for i, severity in enumerate([AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL]):
            rule = AlertRule(
                name=f"alert-{i}",
                metric="metric1",
                threshold=100,
                operator="lt",
                severity=severity,
            )
            manager.register_rule(rule)
            manager.check_rule(f"alert-{i}", 50)

        stats = manager.get_alert_statistics()

        assert stats["total_alerts"] == 3
        assert stats["by_severity"]["info"] == 1
        assert stats["by_severity"]["warning"] == 1
        assert stats["by_severity"]["critical"] == 1

    def test_statistics_by_rule(self, manager):
        """Test statistics grouped by rule."""
        rule = AlertRule(
            name="repeated-alert",
            metric="metric1",
            threshold=100,
            operator="lt",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        # Trigger the same rule multiple times
        for _ in range(5):
            manager.check_rule("repeated-alert", 50)

        stats = manager.get_alert_statistics()

        assert stats["total_alerts"] == 5
        assert stats["by_rule"]["repeated-alert"] == 5

    def test_get_triggered_alerts_all(self, manager):
        """Test getting all triggered alerts."""
        rule1 = AlertRule(name="rule1", metric="m1", threshold=100, operator="lt", severity=AlertSeverity.INFO)
        rule2 = AlertRule(name="rule2", metric="m2", threshold=100, operator="lt", severity=AlertSeverity.WARNING)

        manager.register_rule(rule1)
        manager.register_rule(rule2)

        manager.check_rule("rule1", 50)
        manager.check_rule("rule2", 50)

        all_alerts = manager.get_triggered_alerts()
        assert len(all_alerts) == 2

    def test_get_triggered_alerts_filtered(self, manager):
        """Test getting alerts filtered by rule name."""
        rule1 = AlertRule(name="rule1", metric="m1", threshold=100, operator="lt", severity=AlertSeverity.INFO)
        rule2 = AlertRule(name="rule2", metric="m2", threshold=100, operator="lt", severity=AlertSeverity.WARNING)

        manager.register_rule(rule1)
        manager.register_rule(rule2)

        manager.check_rule("rule1", 50)
        manager.check_rule("rule2", 50)
        manager.check_rule("rule1", 40)

        rule1_alerts = manager.get_triggered_alerts(rule_name="rule1")
        assert len(rule1_alerts) == 2

        rule2_alerts = manager.get_triggered_alerts(rule_name="rule2")
        assert len(rule2_alerts) == 1


class TestConvenienceFunctions:
    """Test convenience functions for common alert configurations."""

    def test_configure_success_rate_alert(self):
        """Test configuring a success rate alert."""
        manager = AlertManager()
        with patch("src.observability.alerting._alert_manager", manager):
            rule = configure_success_rate_alert(threshold=0.99, severity=AlertSeverity.CRITICAL)

            assert rule.name == "success-rate-low"
            assert rule.metric == "success_rate"
            assert rule.threshold == 0.99
            assert rule.operator == "lt"
            assert rule.severity == AlertSeverity.CRITICAL

    def test_configure_latency_alert(self):
        """Test configuring a latency alert."""
        manager = AlertManager()
        with patch("src.observability.alerting._alert_manager", manager):
            rule = configure_latency_alert(threshold_ms=300, severity=AlertSeverity.CRITICAL)

            assert rule.name == "latency-high"
            assert rule.metric == "latency_p95_ms"
            assert rule.threshold == 300
            assert rule.operator == "gt"
            assert rule.severity == AlertSeverity.CRITICAL

    def test_check_success_rate_helper(self):
        """Test the check_success_rate convenience function."""
        manager = AlertManager()
        configure_success_rate_alert(threshold=0.95, severity=AlertSeverity.WARNING)
        manager.register_rule(
            AlertRule(
                name="success-rate-low",
                metric="success_rate",
                threshold=0.95,
                operator="lt",
                severity=AlertSeverity.WARNING,
            )
        )

        with patch("src.observability.alerting._alert_manager", manager):
            alert = check_success_rate(0.80)
            assert alert is not None

            alert = check_success_rate(0.98)
            assert alert is None

    def test_check_latency_helper(self):
        """Test the check_latency convenience function."""
        manager = AlertManager()
        configure_latency_alert(threshold_ms=500, severity=AlertSeverity.WARNING)
        manager.register_rule(
            AlertRule(
                name="latency-high",
                metric="latency_p95_ms",
                threshold=500,
                operator="gt",
                severity=AlertSeverity.WARNING,
            )
        )

        with patch("src.observability.alerting._alert_manager", manager):
            alert = check_latency(600)
            assert alert is not None

            alert = check_latency(400)
            assert alert is None


class TestGlobalAlertManager:
    """Test global alert manager singleton."""

    def test_get_alert_manager_returns_singleton(self):
        """Test that get_alert_manager returns the same instance."""
        manager1 = get_alert_manager()
        manager2 = get_alert_manager()

        assert manager1 is manager2

    def test_get_alert_manager_creates_instance(self):
        """Test that get_alert_manager creates an instance if none exists."""
        import src.observability.alerting as alerting_module

        # Reset global state
        original = alerting_module._alert_manager
        alerting_module._alert_manager = None

        try:
            manager = get_alert_manager()
            assert manager is not None
            assert isinstance(manager, AlertManager)
        finally:
            # Restore original state
            alerting_module._alert_manager = original
