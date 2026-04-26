"""
Notification channel implementations for alerting.

Implements WeCom (企业微信), Email, PagerDuty notification handlers.
"""

import logging
from typing import Optional
import json
import urllib.request
from src.observability.alerting import Alert, AlertChannel, AlertSeverity

logger = logging.getLogger(__name__)


class WeComNotifier:
    """企业微信机器人 webhook notification handler."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def __call__(self, alert: Alert) -> None:
        """Send alert to WeCom chat."""
        # 企业微信使用 markdown 格式
        if alert.rule.severity == AlertSeverity.CRITICAL:
            emoji = "🚨"
            color = "warning"
        elif alert.rule.severity == AlertSeverity.WARNING:
            emoji = "⚠️"
            color = "warning"
        else:
            emoji = "ℹ️"
            color = "info"

        content = f"""{emoji} **告警通知**

**告警名称**: {alert.rule.name}
**严重级别**: {alert.rule.severity.value.upper()}
**监控指标**: {alert.rule.metric}
**当前值**: `{alert.value}`
**阈值条件**: `{alert.rule.operator} {alert.rule.threshold}`
**时间窗口**: {alert.rule.window_minutes} 分钟
**触发时间**: {alert.triggered_at}

**详细信息**: {alert.message}"""

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
            "mentioned_list": [],
        }
        self._send(payload)

    def _send(self, payload: dict) -> None:
        """Send payload to WeCom webhook."""
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            logger.error("Failed to send WeCom notification: %s", e)


class SlackNotifier:
    """Slack webhook notification handler."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def __call__(self, alert: Alert) -> None:
        """Send alert to Slack."""
        color = {
            "info": "good",
            "warning": "warning",
            "critical": "danger",
        }.get(alert.rule.severity.value, "warning")

        payload = {
            "text": f"🚨 {alert.rule.severity.value.upper()}: {alert.rule.name}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {"title": "Metric", "value": alert.rule.metric, "short": True},
                        {"title": "Value", "value": str(alert.value), "short": True},
                        {
                            "title": "Threshold",
                            "value": f"{alert.rule.operator} {alert.rule.threshold}",
                            "short": True,
                        },
                        {
                            "title": "Window",
                            "value": f"{alert.rule.window_minutes} minutes",
                            "short": True,
                        },
                    ],
                    "footer": alert.rule.name,
                    "ts": int(
                        alert.triggered_at.split(".")[0]
                        .replace("-", "")
                        .replace("T", "")
                        .replace(":", "")
                    ),
                }
            ],
        }

        self._send(payload)

    def _send(self, payload: dict) -> None:
        """Send payload to Slack webhook."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            logger.error("Failed to send Slack notification: %s", e)


class EmailNotifier:
    """Email notification handler."""

    def __init__(self, smtp_host: str, smtp_port: int, sender: str, recipients: list[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients

    def __call__(self, alert: Alert) -> None:
        """Send alert via email."""
        subject = f"[{alert.rule.severity.value.upper()}] {alert.rule.name}"
        body = f"""
Alert: {alert.rule.name}
Metric: {alert.rule.metric}
Severity: {alert.rule.severity.value}
Value: {alert.value}
Threshold: {alert.rule.operator} {alert.rule.threshold}
Window: {alert.rule.window_minutes} minutes
Triggered: {alert.triggered_at}
Message: {alert.message}
"""
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.recipients)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.sendmail(self.sender, self.recipients, msg.as_string())
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)


class PagerDutyNotifier:
    """PagerDuty notification handler."""

    def __init__(self, routing_key: str):
        self.routing_key = routing_key

    def __call__(self, alert: Alert) -> None:
        """Trigger PagerDuty incident."""
        severity = {
            "info": "info",
            "warning": "warning",
            "critical": "critical",
        }.get(alert.rule.severity.value, "warning")

        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": alert.rule.name,
            "payload": {
                "summary": alert.message,
                "severity": severity,
                "source": "mcp-observability",
                "component": alert.rule.metric,
                "custom_details": {
                    "rule_name": alert.rule.name,
                    "value": alert.value,
                    "threshold": f"{alert.rule.operator} {alert.rule.threshold}",
                    "window_minutes": alert.rule.window_minutes,
                },
            },
        }

        self._send(payload)

    def _send(self, payload: dict) -> None:
        """Send payload to PagerDuty."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://events.pagerduty.com/v2/enqueue",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            logger.error("Failed to send PagerDuty notification: %s", e)


class WebhookNotifier:
    """Generic webhook notification handler."""

    def __init__(self, webhook_url: str, headers: Optional[dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers: dict[str, str] = headers or {"Content-Type": "application/json"}

    def __call__(self, alert: Alert) -> None:
        """Send alert to webhook."""
        payload = {
            "alert_name": alert.rule.name,
            "metric": alert.rule.metric,
            "severity": alert.rule.severity.value,
            "value": alert.value,
            "threshold": alert.rule.threshold,
            "operator": alert.rule.operator,
            "window_minutes": alert.rule.window_minutes,
            "triggered_at": alert.triggered_at,
            "message": alert.message,
        }
        self._send(payload)

    def _send(self, payload: dict) -> None:
        """Send payload to webhook."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.webhook_url, data=data, headers=self.headers)
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            logger.error("Failed to send webhook notification: %s", e)


def notifiers() -> dict[str, type]:
    """Export all notification classes."""
    return {
        "WeComNotifier": WeComNotifier,
        "SlackNotifier": SlackNotifier,
        "EmailNotifier": EmailNotifier,
        "PagerDutyNotifier": PagerDutyNotifier,
        "WebhookNotifier": WebhookNotifier,
    }
