"""
Unit tests for alert deduplication mechanism.

Tests cover cooldown periods, rate limiting, and alert throttling.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.observability.alerting import (
    AlertManager,
    AlertRule,
    AlertSeverity,
)


class TestAlertCooldown:
    """Test alert cooldown mechanism."""

    @pytest.fixture
    def manager(self):
        """Provide AlertManager with short cooldown for testing."""
        return AlertManager(default_cooldown_minutes=5)

    def test_first_alert_allowed(self, manager):
        """Test that first alert is always allowed."""
        rule = AlertRule(
            name="test-rule",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-rule", 150)
        assert alert is not None
        assert alert.value == 150

    def test_second_alert_blocked_by_cooldown(self, manager):
        """Test that second alert within cooldown is blocked."""
        rule = AlertRule(
            name="test-rule",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        # First alert
        alert1 = manager.check_rule("test-rule", 150)
        assert alert1 is not None

        # Second alert immediately (should be blocked)
        alert2 = manager.check_rule("test-rule", 200)
        assert alert2 is None

    def test_alert_allowed_after_cooldown(self, manager):
        """Test that alert is allowed after cooldown expires."""
        rule = AlertRule(
            name="test-rule",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        # First alert
        alert1 = manager.check_rule("test-rule", 150)
        assert alert1 is not None

        # Simulate cooldown expiry by manipulating internal state
        manager._last_alert_time["test-rule"] = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Should be allowed now
        alert2 = manager.check_rule("test-rule", 200)
        assert alert2 is not None
        assert alert2.value == 200

    def test_custom_cooldown_per_rule(self, manager):
        """Test custom cooldown from rule metadata."""
        rule = AlertRule(
            name="custom-cooldown",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            metadata={"cooldown_minutes": 2},
        )
        manager.register_rule(rule)

        # First alert
        alert1 = manager.check_rule("custom-cooldown", 150)
        assert alert1 is not None

        # Second alert within 2 minutes (should be blocked)
        alert2 = manager.check_rule("custom-cooldown", 200)
        assert alert2 is None

        # Simulate 3 minutes passing
        manager._last_alert_time["custom-cooldown"] = datetime.now(timezone.utc) - timedelta(
            minutes=3
        )

        # Should be allowed
        alert3 = manager.check_rule("custom-cooldown", 250)
        assert alert3 is not None


class TestAlertRateLimiting:
    """Test alert rate limiting (max alerts per hour)."""

    @pytest.fixture
    def manager(self):
        """Provide AlertManager with no default cooldown."""
        return AlertManager(default_cooldown_minutes=0)

    def test_max_alerts_per_hour_enforced(self, manager):
        """Test that max_alerts_per_hour limit is enforced."""
        rule = AlertRule(
            name="rate-limited",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            metadata={"max_alerts_per_hour": 3},
        )
        manager.register_rule(rule)

        # Trigger 3 alerts (should all succeed)
        for i in range(3):
            alert = manager.check_rule("rate-limited", 150 + i)
            assert alert is not None

        # 4th alert should be blocked
        alert = manager.check_rule("rate-limited", 200)
        assert alert is None

    def test_rate_limit_resets_after_hour(self, manager):
        """Test that rate limit resets after 1 hour."""
        rule = AlertRule(
            name="rate-limited",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            metadata={"max_alerts_per_hour": 2},
        )
        manager.register_rule(rule)

        # Trigger 2 alerts
        manager.check_rule("rate-limited", 150)
        manager.check_rule("rate-limited", 160)

        # 3rd alert should be blocked
        alert = manager.check_rule("rate-limited", 170)
        assert alert is None

        # Simulate 1 hour passing
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        manager._alert_counts["rate-limited"] = [one_hour_ago - timedelta(minutes=10)]

        # Should be allowed now
        alert = manager.check_rule("rate-limited", 180)
        assert alert is not None

    def test_no_rate_limit_when_not_configured(self, manager):
        """Test that alerts are not rate limited when max_alerts_per_hour is not set."""
        rule = AlertRule(
            name="no-limit",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
        )
        manager.register_rule(rule)

        # Trigger many alerts (all should succeed)
        for i in range(10):
            alert = manager.check_rule("no-limit", 150 + i)
            assert alert is not None


class TestAlertDeduplicationIntegration:
    """Test deduplication in realistic scenarios."""

    @pytest.fixture
    def manager(self):
        """Provide AlertManager with realistic settings."""
        return AlertManager(default_cooldown_minutes=30)

    def test_combined_cooldown_and_rate_limit(self, manager):
        """Test that both cooldown and rate limit work together."""
        rule = AlertRule(
            name="combined",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            metadata={
                "cooldown_minutes": 10,
                "max_alerts_per_hour": 5,
            },
        )
        manager.register_rule(rule)

        # Trigger alerts with cooldown simulation
        alert1 = manager.check_rule("combined", 150)
        assert alert1 is not None

        # Immediately blocked by cooldown
        alert2 = manager.check_rule("combined", 160)
        assert alert2 is None

        # Simulate cooldown expiry
        manager._last_alert_time["combined"] = datetime.now(timezone.utc) - timedelta(minutes=15)

        # Now allowed (rate limit not reached)
        alert3 = manager.check_rule("combined", 170)
        assert alert3 is not None

    def test_different_rules_independent(self, manager):
        """Test that different rules have independent cooldowns."""
        rule1 = AlertRule(
            name="rule-1",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
        )
        rule2 = AlertRule(
            name="rule-2",
            metric="metric2",
            threshold=200,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
        )
        manager.register_rule(rule1)
        manager.register_rule(rule2)

        # Trigger rule-1
        alert1 = manager.check_rule("rule-1", 150)
        assert alert1 is not None

        # rule-2 should not be affected
        alert2 = manager.check_rule("rule-2", 250)
        assert alert2 is not None

        # rule-1 should still be in cooldown
        alert3 = manager.check_rule("rule-1", 160)
        assert alert3 is None

    def test_disabled_rule_not_affected_by_cooldown(self, manager):
        """Test that disabled rules don't trigger regardless of cooldown."""
        rule = AlertRule(
            name="disabled",
            metric="metric1",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            enabled=False,
        )
        manager.register_rule(rule)

        alert = manager.check_rule("disabled", 150)
        assert alert is None

    def test_nonexistent_rule_returns_none(self, manager):
        """Test checking nonexistent rule returns None."""
        alert = manager.check_rule("nonexistent", 150)
        assert alert is None
