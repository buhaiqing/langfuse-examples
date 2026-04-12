#!/usr/bin/env python3
"""
Test script for alerting system.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability.alerting import (
    AlertSeverity, AlertChannel, AlertManager, AlertRule, Alert,
    get_alert_manager,
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
        ("Alert Statistics", test_alert_statistics()),
    ]
    passed = sum(1 for _, r in results if r)
    print(f"Total: {passed}/{len(results)} tests passed")
    return passed == len(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
