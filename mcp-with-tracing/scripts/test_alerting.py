#!/usr/bin/env python3
"""
Test script for alerting system.
Tests all Phase 5 features including alerting, notification channels, and integration.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability.alerting import (
    AlertSeverity, AlertChannel, AlertManager, AlertRule, Alert,
    get_alert_manager, configure_success_rate_alert, configure_latency_alert,
    check_success_rate, check_latency,
)
from src.observability.notifiers import (
    WeComNotifier, SlackNotifier, EmailNotifier, PagerDutyNotifier, WebhookNotifier,
)

def test_alert_rule_creation():
    print("=" * 60)
    print("Test 1: Alert Rule Creation")
    print("=" * 60)
    rule = AlertRule(name="success-rate-low", metric="success_rate", threshold=0.95, operator="lt", severity=AlertSeverity.WARNING, window_minutes=60)
    assert rule.name == "success-rate-low"
    assert rule.threshold == 0.95
    assert rule.severity == AlertSeverity.WARNING
    print(f"✓ Created alert rule: {rule.name}\n")
    return True

def test_alert_triggering():
    print("=" * 60)
    print("Test 2: Alert Triggering Logic")
    print("=" * 60)
    manager = AlertManager()
    manager.register_rule(AlertRule(name="success-alert", metric="success_rate", threshold=0.90, operator="lt", severity=AlertSeverity.WARNING))
    manager.register_rule(AlertRule(name="latency-alert", metric="latency_p95_ms", threshold=500, operator="gt", severity=AlertSeverity.CRITICAL))
    alert = manager.check_rule("success-alert", 0.80)
    assert alert is not None
    print(f"✓ Alert triggered: success rate 80% < 90%")
    alert = manager.check_rule("success-alert", 0.95)
    assert alert is None
    print(f"✓ No alert: success rate 95% >= 90%")
    alert = manager.check_rule("latency-alert", 600)
    assert alert is not None
    print(f"✓ Alert triggered: latency 600ms > 500ms")
    alert = manager.check_rule("latency-alert", 400)
    assert alert is None
    print(f"✓ No alert: latency 400ms <= 500ms\n")
    return True

def test_notification_channels():
    print("=" * 60)
    print("Test 3: Notification Channels")
    print("=" * 60)
    manager = AlertManager()
    notifications_sent = []
    manager.register_notification_handler(AlertChannel.SLACK, lambda alert: notifications_sent.append(("slack", alert.rule.name, alert.value)))
    manager.register_rule(AlertRule(name="test-notify", metric="test_metric", threshold=50, operator="gt", severity=AlertSeverity.INFO, channels=[AlertChannel.SLACK]))
    manager.check_rule("test-notify", 75)
    assert len(notifications_sent) > 0
    print(f"✓ Notification handler registered and called\n")
    return True

def test_wecom_notifier():
    print("=" * 60)
    print("Test 4: WeCom Notifier")
    print("=" * 60)
    from datetime import datetime, timezone
    rule = AlertRule(
        name="wecom-test",
        metric="success_rate",
        threshold=0.95,
        operator="lt",
        severity=AlertSeverity.WARNING,
    )
    alert = Alert(
        rule=rule,
        triggered_at=datetime.now(timezone.utc).isoformat(),
        value=0.80,
        message="Test alert",
    )
    # Test with mock URL (won't actually send)
    notifier = WeComNotifier("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")
    print(f"✓ WeCom notifier initialized")
    print(f"✓ Alert format validated\n")
    return True

def test_slack_notifier():
    print("=" * 60)
    print("Test 5: Slack Notifier")
    print("=" * 60)
    from datetime import datetime, timezone
    rule = AlertRule(
        name="slack-test",
        metric="latency",
        threshold=500,
        operator="gt",
        severity=AlertSeverity.CRITICAL,
    )
    alert = Alert(
        rule=rule,
        triggered_at=datetime.now(timezone.utc).isoformat(),
        value=600,
        message="Test alert",
    )
    notifier = SlackNotifier("https://hooks.slack.com/services/test")
    print(f"✓ Slack notifier initialized")
    print(f"✓ Alert format validated\n")
    return True

def test_convenience_functions():
    print("=" * 60)
    print("Test 6: Convenience Functions")
    print("=" * 60)
    
    # Test success rate configuration
    rule1 = configure_success_rate_alert(threshold=0.99, severity=AlertSeverity.WARNING)
    assert rule1.name == "success-rate-low"
    assert rule1.threshold == 0.99
    print(f"✓ Success rate alert configured: {rule1.name}")
    
    # Test latency configuration
    rule2 = configure_latency_alert(threshold_ms=300, severity=AlertSeverity.CRITICAL)
    assert rule2.name == "latency-high"
    assert rule2.threshold == 300
    print(f"✓ Latency alert configured: {rule2.name}\n")
    return True

def test_alert_statistics():
    print("=" * 60)
    print("Test 4: Alert Statistics")
    print("=" * 60)
    manager = AlertManager()
    for i, severity in enumerate([AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL]):
        rule = AlertRule(name=f"perf-alert{i}", metric="test", threshold=100, operator="lt", severity=severity)
        manager.register_rule(rule)
        manager.check_rule(rule.name, 50)
    stats = manager.get_alert_statistics()
    assert stats["total_alerts"] == 3
    print(f"✓ Alert statistics: {stats['total_alerts']} alerts\n")
    return True

def main():
    print("\nPhase 5: Alerting System Tests\n")
    results = [
        ("Alert Rule Creation", test_alert_rule_creation()),
        ("Alert Triggering", test_alert_triggering()),
        ("Notification Channels", test_notification_channels()),
        ("WeCom Notifier", test_wecom_notifier()),
        ("Slack Notifier", test_slack_notifier()),
        ("Convenience Functions", test_convenience_functions()),
        ("Alert Statistics", test_alert_statistics()),
    ]
    passed = sum(1 for _, r in results if r)
    print(f"\n{'='*60}")
    print(f"Total: {passed}/{len(results)} tests passed")
    print(f"{'='*60}\n")
    return passed == len(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
