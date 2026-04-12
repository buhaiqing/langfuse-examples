#!/usr/bin/env python3
"""
Test script for notification channels configuration.

This script tests all configured notification channels to ensure they are
properly set up and can receive alerts.
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def test_wecom_notification(manager, webhook_url):
    """Test WeCom notification channel."""
    print("\n" + "=" * 60)
    print("Testing WeCom Notification")
    print("=" * 60)
    
    try:
        notifier = WeComNotifier(webhook_url)
        manager.register_notification_handler(AlertChannel.WEBHOOK, notifier)
        
        # Create test rule
        rule = AlertRule(
            name="test-wecom",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.WEBHOOK],
        )
        manager.register_rule(rule)
        
        # Trigger alert
        alert = manager.check_rule("test-wecom", 150)
        
        if alert:
            print("✓ WeCom notification sent successfully")
            print(f"  Alert: {alert.rule.name}")
            print(f"  Value: {alert.value}")
            return True
        else:
            print("✗ Failed to trigger WeCom alert")
            return False
            
    except Exception as e:
        print(f"✗ WeCom notification failed: {e}")
        return False


def test_slack_notification(manager, webhook_url):
    """Test Slack notification channel."""
    print("\n" + "=" * 60)
    print("Testing Slack Notification")
    print("=" * 60)
    
    try:
        notifier = SlackNotifier(webhook_url)
        manager.register_notification_handler(AlertChannel.SLACK, notifier)
        
        # Create test rule
        rule = AlertRule(
            name="test-slack",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK],
        )
        manager.register_rule(rule)
        
        # Trigger alert
        alert = manager.check_rule("test-slack", 150)
        
        if alert:
            print("✓ Slack notification sent successfully")
            print(f"  Alert: {alert.rule.name}")
            print(f"  Value: {alert.value}")
            return True
        else:
            print("✗ Failed to trigger Slack alert")
            return False
            
    except Exception as e:
        print(f"✗ Slack notification failed: {e}")
        return False


def test_email_notification(manager, email_config):
    """Test Email notification channel."""
    print("\n" + "=" * 60)
    print("Testing Email Notification")
    print("=" * 60)
    
    try:
        notifier = EmailNotifier(
            smtp_host=email_config["smtp_host"],
            smtp_port=email_config["smtp_port"],
            sender=email_config["sender"],
            recipients=email_config["recipients"],
        )
        manager.register_notification_handler(AlertChannel.EMAIL, notifier)
        
        # Create test rule
        rule = AlertRule(
            name="test-email",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.INFO,
            channels=[AlertChannel.EMAIL],
        )
        manager.register_rule(rule)
        
        # Trigger alert
        alert = manager.check_rule("test-email", 150)
        
        if alert:
            print("✓ Email notification sent successfully")
            print(f"  Alert: {alert.rule.name}")
            print(f"  Recipients: {', '.join(email_config['recipients'])}")
            return True
        else:
            print("✗ Failed to trigger Email alert")
            return False
            
    except Exception as e:
        print(f"✗ Email notification failed: {e}")
        return False


def test_pagerduty_notification(manager, routing_key):
    """Test PagerDuty notification channel."""
    print("\n" + "=" * 60)
    print("Testing PagerDuty Notification")
    print("=" * 60)
    
    try:
        notifier = PagerDutyNotifier(routing_key)
        manager.register_notification_handler(AlertChannel.PAGERDUTY, notifier)
        
        # Create test rule
        rule = AlertRule(
            name="test-pagerduty",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.PAGERDUTY],
        )
        manager.register_rule(rule)
        
        # Trigger alert
        alert = manager.check_rule("test-pagerduty", 150)
        
        if alert:
            print("✓ PagerDuty notification sent successfully")
            print(f"  Alert: {alert.rule.name}")
            print(f"  Routing Key: {routing_key[:8]}...")
            return True
        else:
            print("✗ Failed to trigger PagerDuty alert")
            return False
            
    except Exception as e:
        print(f"✗ PagerDuty notification failed: {e}")
        return False


def test_webhook_notification(manager, webhook_url):
    """Test generic Webhook notification channel."""
    print("\n" + "=" * 60)
    print("Testing Generic Webhook Notification")
    print("=" * 60)
    
    try:
        notifier = WebhookNotifier(webhook_url)
        manager.register_notification_handler(AlertChannel.WEBHOOK, notifier)
        
        # Create test rule
        rule = AlertRule(
            name="test-webhook",
            metric="test_metric",
            threshold=100,
            operator="gt",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.WEBHOOK],
        )
        manager.register_rule(rule)
        
        # Trigger alert
        alert = manager.check_rule("test-webhook", 150)
        
        if alert:
            print("✓ Webhook notification sent successfully")
            print(f"  Alert: {alert.rule.name}")
            print(f"  URL: {webhook_url}")
            return True
        else:
            print("✗ Failed to trigger Webhook alert")
            return False
            
    except Exception as e:
        print(f"✗ Webhook notification failed: {e}")
        return False


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("Notification Channels Configuration Test")
    print("=" * 60)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    
    # Load configuration
    config = load_env_config()
    
    if not config:
        print("\n⚠️  No notification channels configured!")
        print("\nPlease configure at least one notification channel in .env file:")
        print("  - WECOM_WEBHOOK_URL")
        print("  - SLACK_WEBHOOK_URL")
        print("  - ALERT_EMAIL_SMTP_HOST, ALERT_EMAIL_SENDER, etc.")
        print("  - PAGERDUTY_ROUTING_KEY")
        print("\nSee docs/notification-channels-setup.md for details.")
        return False
    
    print(f"\nFound {len(config)} configured channel(s):")
    for channel in config.keys():
        print(f"  ✓ {channel.upper()}")
    
    # Initialize alert manager
    manager = get_alert_manager()
    
    # Run tests
    results = []
    
    if "wecom" in config:
        result = test_wecom_notification(manager, config["wecom"])
        results.append(("WeCom", result))
    
    if "slack" in config:
        result = test_slack_notification(manager, config["slack"])
        results.append(("Slack", result))
    
    if "email" in config:
        result = test_email_notification(manager, config["email"])
        results.append(("Email", result))
    
    if "pagerduty" in config:
        result = test_pagerduty_notification(manager, config["pagerduty"])
        results.append(("PagerDuty", result))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20s} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All notification channels are working correctly!")
        return True
    else:
        print(f"\n⚠️  {total - passed} channel(s) failed. Check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
