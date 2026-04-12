"""
Example configuration for notification channels.

This module demonstrates how to configure and register multiple notification
channels for the alerting system.

Usage:
    from examples.notification_channels_example import setup_notification_channels
    setup_notification_channels()
"""

import os
from src.observability.alerting import (
    get_alert_manager,
    AlertRule,
    AlertSeverity,
    AlertChannel,
    configure_success_rate_alert,
    configure_latency_alert,
)
from src.observability.notifiers import (
    WeComNotifier,
    SlackNotifier,
    EmailNotifier,
    PagerDutyNotifier,
    WebhookNotifier,
)


def setup_wecom_notification():
    """Setup WeCom (企业微信) notification channel."""
    wecom_url = os.getenv("WECOM_WEBHOOK_URL")
    
    if not wecom_url:
        print("⚠️  WECOM_WEBHOOK_URL not configured, skipping WeCom setup")
        return False
    
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.WEBHOOK,
        WeComNotifier(wecom_url)
    )
    
    print("✓ WeCom notification channel configured")
    return True


def setup_slack_notification():
    """Setup Slack notification channel."""
    slack_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not slack_url:
        print("⚠️  SLACK_WEBHOOK_URL not configured, skipping Slack setup")
        return False
    
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.SLACK,
        SlackNotifier(slack_url)
    )
    
    print("✓ Slack notification channel configured")
    return True


def setup_email_notification():
    """Setup Email notification channel."""
    smtp_host = os.getenv("ALERT_EMAIL_SMTP_HOST")
    smtp_port = os.getenv("ALERT_EMAIL_SMTP_PORT")
    sender = os.getenv("ALERT_EMAIL_SENDER")
    recipients = os.getenv("ALERT_EMAIL_RECIPIENTS")
    
    if not all([smtp_host, smtp_port, sender, recipients]):
        print("⚠️  Email configuration incomplete, skipping Email setup")
        print("   Required: ALERT_EMAIL_SMTP_HOST, ALERT_EMAIL_SMTP_PORT,")
        print("             ALERT_EMAIL_SENDER, ALERT_EMAIL_RECIPIENTS")
        return False
    
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.EMAIL,
        EmailNotifier(
            smtp_host=smtp_host,
            smtp_port=int(smtp_port),
            sender=sender,
            recipients=recipients.split(","),
        )
    )
    
    print("✓ Email notification channel configured")
    return True


def setup_pagerduty_notification():
    """Setup PagerDuty notification channel."""
    routing_key = os.getenv("PAGERDUTY_ROUTING_KEY")
    
    if not routing_key:
        print("⚠️  PAGERDUTY_ROUTING_KEY not configured, skipping PagerDuty setup")
        return False
    
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.PAGERDUTY,
        PagerDutyNotifier(routing_key)
    )
    
    print("✓ PagerDuty notification channel configured")
    return True


def setup_custom_webhook():
    """Setup custom webhook notification channel."""
    webhook_url = os.getenv("CUSTOM_WEBHOOK_URL")
    
    if not webhook_url:
        print("⚠️  CUSTOM_WEBHOOK_URL not configured, skipping webhook setup")
        return False
    
    # Optional: Add authentication headers
    headers = {}
    auth_token = os.getenv("CUSTOM_WEBHOOK_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.WEBHOOK,
        WebhookNotifier(webhook_url, headers=headers)
    )
    
    print("✓ Custom webhook notification channel configured")
    return True


def setup_alert_rules():
    """Configure alert rules with appropriate notification channels."""
    manager = get_alert_manager()
    
    # Success rate alert - send to WeCom and Email
    success_rate_channels = []
    if os.getenv("WECOM_WEBHOOK_URL"):
        success_rate_channels.append(AlertChannel.WEBHOOK)
    if os.getenv("ALERT_EMAIL_SMTP_HOST"):
        success_rate_channels.append(AlertChannel.EMAIL)
    
    if success_rate_channels:
        configure_success_rate_alert(
            threshold=0.95,
            severity=AlertSeverity.WARNING,
            channels=success_rate_channels,
        )
        print("✓ Success rate alert configured")
    
    # Latency alert - send to all configured channels
    latency_channels = []
    if os.getenv("WECOM_WEBHOOK_URL"):
        latency_channels.append(AlertChannel.WEBHOOK)
    if os.getenv("SLACK_WEBHOOK_URL"):
        latency_channels.append(AlertChannel.SLACK)
    if os.getenv("ALERT_EMAIL_SMTP_HOST"):
        latency_channels.append(AlertChannel.EMAIL)
    if os.getenv("PAGERDUTY_ROUTING_KEY"):
        latency_channels.append(AlertChannel.PAGERDUTY)
    
    if latency_channels:
        configure_latency_alert(
            threshold_ms=500,
            severity=AlertSeverity.CRITICAL,
            channels=latency_channels,
        )
        print("✓ Latency alert configured")


def setup_notification_channels():
    """
    Setup all configured notification channels and alert rules.
    
    This is the main entry point for configuring the alerting system.
    Call this function during application initialization.
    """
    print("\n" + "=" * 60)
    print("Setting up Notification Channels")
    print("=" * 60)
    
    # Setup notification channels
    channels_configured = 0
    
    if setup_wecom_notification():
        channels_configured += 1
    
    if setup_slack_notification():
        channels_configured += 1
    
    if setup_email_notification():
        channels_configured += 1
    
    if setup_pagerduty_notification():
        channels_configured += 1
    
    if setup_custom_webhook():
        channels_configured += 1
    
    if channels_configured == 0:
        print("\n⚠️  No notification channels configured!")
        print("Please check your .env file and ensure at least one")
        print("notification channel is properly configured.")
        print("\nSee docs/notification-channels-setup.md for details.")
        return False
    
    print(f"\n✓ {channels_configured} notification channel(s) configured")
    
    # Setup alert rules
    print("\n" + "=" * 60)
    print("Configuring Alert Rules")
    print("=" * 60)
    setup_alert_rules()
    
    print("\n" + "=" * 60)
    print("Notification channels setup complete!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    """Run setup when executed directly."""
    setup_notification_channels()
