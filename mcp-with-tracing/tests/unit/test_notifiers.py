"""
Notification channels tests for MCP Langfuse Observability.

Tests cover WeCom, Slack, Email, PagerDuty, and Webhook notifiers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timezone

from src.observability.alerting import (
    AlertRule,
    Alert,
    AlertSeverity,
)
from src.observability.notifiers import (
    WeComNotifier,
    SlackNotifier,
    EmailNotifier,
    PagerDutyNotifier,
    WebhookNotifier,
)


@pytest.fixture
def sample_alert():
    """Provide a sample alert for testing."""
    rule = AlertRule(
        name="test-alert",
        metric="success_rate",
        threshold=0.95,
        operator="lt",
        severity=AlertSeverity.WARNING,
        window_minutes=60,
    )
    return Alert(
        rule=rule,
        triggered_at=datetime.now(timezone.utc).isoformat(),
        value=0.80,
        message="Alert 'test-alert': success_rate = 0.8 (threshold: lt 0.95)",
        context={"rule_name": "test-alert", "current_value": 0.80},
    )


class TestWeComNotifier:
    """WeCom notifier tests."""

    def test_wecom_notifier_initialization(self):
        """Test WeCom notifier initialization."""
        webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        notifier = WeComNotifier(webhook_url)
        assert notifier.webhook_url == webhook_url

    @patch("urllib.request.urlopen")
    def test_wecom_notifier_send_warning(self, mock_urlopen, sample_alert):
        """Test sending a warning alert to WeCom."""
        webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        notifier = WeComNotifier(webhook_url)
        
        notifier(sample_alert)
        
        # Verify the request was made
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Verify it's a POST request with JSON
        assert request.data is not None
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["msgtype"] == "markdown"
        assert "markdown" in payload
        assert "content" in payload["markdown"]
        assert "⚠️" in payload["markdown"]["content"]
        assert "test-alert" in payload["markdown"]["content"]

    @patch("urllib.request.urlopen")
    def test_wecom_notifier_send_critical(self, mock_urlopen):
        """Test sending a critical alert to WeCom."""
        rule = AlertRule(
            name="critical-alert",
            metric="latency",
            threshold=500,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
        )
        alert = Alert(
            rule=rule,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            value=600,
            message="Critical alert triggered",
        )
        
        webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        notifier = WeComNotifier(webhook_url)
        notifier(alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))
        assert "🚨" in payload["markdown"]["content"]

    @patch("urllib.request.urlopen")
    def test_wecom_notifier_send_info(self, mock_urlopen):
        """Test sending an info alert to WeCom."""
        rule = AlertRule(
            name="info-alert",
            metric="metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
        )
        alert = Alert(
            rule=rule,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            value=150,
            message="Info alert",
        )
        
        webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        notifier = WeComNotifier(webhook_url)
        notifier(alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))
        assert "ℹ️" in payload["markdown"]["content"]

    @patch("urllib.request.urlopen", side_effect=Exception("Network error"))
    def test_wecom_notifier_handles_exception(self, mock_urlopen, sample_alert, capsys):
        """Test that WeCom notifier handles exceptions gracefully."""
        webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        notifier = WeComNotifier(webhook_url)
        
        # Should not raise exception
        notifier(sample_alert)
        
        captured = capsys.readouterr()
        assert "Failed to send WeCom notification" in captured.out


class TestSlackNotifier:
    """Slack notifier tests."""

    def test_slack_notifier_initialization(self):
        """Test Slack notifier initialization."""
        webhook_url = "https://hooks.slack.com/services/test"
        notifier = SlackNotifier(webhook_url)
        assert notifier.webhook_url == webhook_url

    @patch("urllib.request.urlopen")
    def test_slack_notifier_send_warning(self, mock_urlopen, sample_alert):
        """Test sending a warning alert to Slack."""
        webhook_url = "https://hooks.slack.com/services/test"
        notifier = SlackNotifier(webhook_url)
        
        notifier(sample_alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))
        
        assert "text" in payload
        assert "WARNING" in payload["text"]
        assert "attachments" in payload
        assert len(payload["attachments"]) > 0
        
        attachment = payload["attachments"][0]
        assert attachment["color"] == "warning"

    @patch("urllib.request.urlopen")
    def test_slack_notifier_send_critical(self, mock_urlopen):
        """Test sending a critical alert to Slack."""
        rule = AlertRule(
            name="critical-alert",
            metric="latency",
            threshold=500,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
        )
        alert = Alert(
            rule=rule,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            value=600,
            message="Critical alert",
        )
        
        webhook_url = "https://hooks.slack.com/services/test"
        notifier = SlackNotifier(webhook_url)
        notifier(alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))
        
        attachment = payload["attachments"][0]
        assert attachment["color"] == "danger"

    @patch("urllib.request.urlopen")
    def test_slack_notifier_send_info(self, mock_urlopen):
        """Test sending an info alert to Slack."""
        rule = AlertRule(
            name="info-alert",
            metric="metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
        )
        alert = Alert(
            rule=rule,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            value=150,
            message="Info alert",
        )
        
        webhook_url = "https://hooks.slack.com/services/test"
        notifier = SlackNotifier(webhook_url)
        notifier(alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))
        
        attachment = payload["attachments"][0]
        assert attachment["color"] == "good"

    @patch("urllib.request.urlopen", side_effect=Exception("Network error"))
    def test_slack_notifier_handles_exception(self, mock_urlopen, sample_alert, capsys):
        """Test that Slack notifier handles exceptions gracefully."""
        webhook_url = "https://hooks.slack.com/services/test"
        notifier = SlackNotifier(webhook_url)
        
        notifier(sample_alert)
        
        captured = capsys.readouterr()
        assert "Failed to send Slack notification" in captured.out


class TestEmailNotifier:
    """Email notifier tests."""

    def test_email_notifier_initialization(self):
        """Test Email notifier initialization."""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="alerts@example.com",
            recipients=["admin@example.com"],
        )
        assert notifier.smtp_host == "smtp.example.com"
        assert notifier.smtp_port == 587
        assert notifier.sender == "alerts@example.com"
        assert notifier.recipients == ["admin@example.com"]

    @patch("smtplib.SMTP")
    def test_email_notifier_send(self, mock_smtp, sample_alert):
        """Test sending an alert via email."""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="alerts@example.com",
            recipients=["admin@example.com"],
        )
        
        notifier(sample_alert)
        
        # Verify SMTP was used
        assert mock_smtp.called
        mock_smtp_instance = mock_smtp.return_value.__enter__.return_value
        assert mock_smtp_instance.sendmail.called

    @patch("smtplib.SMTP", side_effect=Exception("SMTP error"))
    def test_email_notifier_handles_exception(self, mock_smtp, sample_alert, capsys):
        """Test that Email notifier handles exceptions gracefully."""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender="alerts@example.com",
            recipients=["admin@example.com"],
        )
        
        notifier(sample_alert)
        
        captured = capsys.readouterr()
        assert "Failed to send email notification" in captured.out


class TestPagerDutyNotifier:
    """PagerDuty notifier tests."""

    def test_pagerduty_notifier_initialization(self):
        """Test PagerDuty notifier initialization."""
        routing_key = "test_routing_key"
        notifier = PagerDutyNotifier(routing_key)
        assert notifier.routing_key == routing_key

    @patch("urllib.request.urlopen")
    def test_pagerduty_notifier_send(self, mock_urlopen, sample_alert):
        """Test sending an alert to PagerDuty."""
        routing_key = "test_routing_key"
        notifier = PagerDutyNotifier(routing_key)
        
        notifier(sample_alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Verify URL
        assert request.full_url == "https://events.pagerduty.com/v2/enqueue"
        
        # Verify payload
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["routing_key"] == routing_key
        assert payload["event_action"] == "trigger"
        assert payload["dedup_key"] == sample_alert.rule.name
        assert payload["payload"]["severity"] == "warning"

    @patch("urllib.request.urlopen", side_effect=Exception("Network error"))
    def test_pagerduty_notifier_handles_exception(self, mock_urlopen, sample_alert, capsys):
        """Test that PagerDuty notifier handles exceptions gracefully."""
        routing_key = "test_routing_key"
        notifier = PagerDutyNotifier(routing_key)
        
        notifier(sample_alert)
        
        captured = capsys.readouterr()
        assert "Failed to send PagerDuty notification" in captured.out


class TestWebhookNotifier:
    """Generic webhook notifier tests."""

    def test_webhook_notifier_initialization(self):
        """Test Webhook notifier initialization."""
        webhook_url = "https://example.com/webhook"
        notifier = WebhookNotifier(webhook_url)
        assert notifier.webhook_url == webhook_url
        assert notifier.headers == {"Content-Type": "application/json"}

    def test_webhook_notifier_with_custom_headers(self):
        """Test Webhook notifier with custom headers."""
        webhook_url = "https://example.com/webhook"
        custom_headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        notifier = WebhookNotifier(webhook_url, headers=custom_headers)
        assert notifier.headers == custom_headers

    @patch("urllib.request.urlopen")
    def test_webhook_notifier_send(self, mock_urlopen, sample_alert):
        """Test sending an alert to webhook."""
        webhook_url = "https://example.com/webhook"
        notifier = WebhookNotifier(webhook_url)
        
        notifier(sample_alert)
        
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Verify payload
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["alert_name"] == sample_alert.rule.name
        assert payload["metric"] == sample_alert.rule.metric
        assert payload["severity"] == sample_alert.rule.severity.value
        assert payload["value"] == sample_alert.value
        assert payload["threshold"] == sample_alert.rule.threshold
        assert payload["operator"] == sample_alert.rule.operator

    @patch("urllib.request.urlopen", side_effect=Exception("Network error"))
    def test_webhook_notifier_handles_exception(self, mock_urlopen, sample_alert, capsys):
        """Test that Webhook notifier handles exceptions gracefully."""
        webhook_url = "https://example.com/webhook"
        notifier = WebhookNotifier(webhook_url)
        
        notifier(sample_alert)
        
        captured = capsys.readouterr()
        assert "Failed to send webhook notification" in captured.out


class TestNotifiersExport:
    """Test the notifiers export function."""

    def test_notifiers_function(self):
        """Test that notifiers() returns all notifier classes."""
        from src.observability.notifiers import notifiers
        
        result = notifiers()
        
        assert "WeComNotifier" in result
        assert "SlackNotifier" in result
        assert "EmailNotifier" in result
        assert "PagerDutyNotifier" in result
        assert "WebhookNotifier" in result
        
        # Verify they are classes
        assert callable(result["WeComNotifier"])
        assert callable(result["SlackNotifier"])
