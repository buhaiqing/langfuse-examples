"""
Integration tests for notification channels configuration.

Tests all configured notification channels to ensure they are
properly set up and can receive alerts.
"""

import os
import pytest
from datetime import datetime, timezone
from src.observability.alerting import (
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertChannel,
    get_alert_manager,
)
from src.observability.notifiers import (
    WeComNotifier,
    SlackNotifier,
    EmailNotifier,
    PagerDutyNotifier,
    WebhookNotifier,
)


def load_env_config():
    """Load notification channel configurations from environment variables."""
    config = {}

    # WeCom
    wecom_url = os.getenv("WECOM_WEBHOOK_URL")
    if wecom_url:
        config["wecom"] = wecom_url

    # Slack
    slack_url = os.getenv("SLACK_WEBHOOK_URL")
    if slack_url:
        config["slack"] = slack_url

    # Email
    smtp_host = os.getenv("ALERT_EMAIL_SMTP_HOST")
    smtp_port = os.getenv("ALERT_EMAIL_SMTP_PORT")
    email_sender = os.getenv("ALERT_EMAIL_SENDER")
    email_recipients = os.getenv("ALERT_EMAIL_RECIPIENTS")

    if all([smtp_host, smtp_port, email_sender, email_recipients]):
        config["email"] = {
            "smtp_host": smtp_host,
            "smtp_port": int(smtp_port),
            "sender": email_sender,
            "recipients": email_recipients.split(","),
        }

    # PagerDuty
    pagerduty_key = os.getenv("PAGERDUTY_ROUTING_KEY")
    if pagerduty_key:
        config["pagerduty"] = pagerduty_key

    return config


@pytest.mark.integration
class TestNotificationChannels:
    """Integration tests for notification channels."""

    @pytest.fixture
    def manager(self):
        """Provide a fresh AlertManager instance."""
        return AlertManager()

    @pytest.fixture
    def config(self):
        """Load notification channel configuration."""
        return load_env_config()

    def test_wecom_notification(self, manager, config):
        """Test WeCom notification channel."""
        if "wecom" not in config:
            pytest.skip("WeCom not configured (set WECOM_WEBHOOK_URL)")

        notifier = WeComNotifier(config["wecom"])
        manager.register_notification_handler(AlertChannel.WEBHOOK, notifier)

        rule = AlertRule(
            name="test-wecom",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.WEBHOOK],
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-wecom", 150)
        assert alert is not None, "Failed to trigger WeCom alert"

    def test_slack_notification(self, manager, config):
        """Test Slack notification channel."""
        if "slack" not in config:
            pytest.skip("Slack not configured (set SLACK_WEBHOOK_URL)")

        notifier = SlackNotifier(config["slack"])
        manager.register_notification_handler(AlertChannel.SLACK, notifier)

        rule = AlertRule(
            name="test-slack",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK],
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-slack", 150)
        assert alert is not None, "Failed to trigger Slack alert"

    def test_email_notification(self, manager, config):
        """Test Email notification channel."""
        if "email" not in config:
            pytest.skip("Email not configured (set ALERT_EMAIL_*)")

        email_config = config["email"]
        notifier = EmailNotifier(
            smtp_host=email_config["smtp_host"],
            smtp_port=email_config["smtp_port"],
            sender=email_config["sender"],
            recipients=email_config["recipients"],
        )
        manager.register_notification_handler(AlertChannel.EMAIL, notifier)

        rule = AlertRule(
            name="test-email",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
            channels=[AlertChannel.EMAIL],
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-email", 150)
        assert alert is not None, "Failed to trigger Email alert"

    def test_pagerduty_notification(self, manager, config):
        """Test PagerDuty notification channel."""
        if "pagerduty" not in config:
            pytest.skip("PagerDuty not configured (set PAGERDUTY_ROUTING_KEY)")

        notifier = PagerDutyNotifier(config["pagerduty"])
        manager.register_notification_handler(AlertChannel.PAGERDUTY, notifier)

        rule = AlertRule(
            name="test-pagerduty",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.PAGERDUTY],
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-pagerduty", 150)
        assert alert is not None, "Failed to trigger PagerDuty alert"

    def test_webhook_notification(self, manager, config):
        """Test generic Webhook notification channel."""
        # Use WeCom URL as generic webhook if available
        if "wecom" not in config:
            pytest.skip("Webhook not configured (set WECOM_WEBHOOK_URL)")

        notifier = WebhookNotifier(config["wecom"])
        manager.register_notification_handler(AlertChannel.WEBHOOK, notifier)

        rule = AlertRule(
            name="test-webhook",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.WEBHOOK],
        )
        manager.register_rule(rule)

        alert = manager.check_rule("test-webhook", 150)
        assert alert is not None, "Failed to trigger Webhook alert"
