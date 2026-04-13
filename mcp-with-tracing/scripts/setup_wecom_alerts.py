#!/usr/bin/env python3
"""
Setup WeCom (企业微信) webhook notification for MCP alerts.

This script helps configure and test WeCom robot notifications.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.observability.alerting import (
    get_alert_manager,
    AlertSeverity,
    AlertRule,
    AlertChannel,
)
from src.observability.notifiers import WeComNotifier


def load_env():
    """Load environment variables from .env file."""
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
    else:
        print(f"⚠ Warning: .env file not found at {env_path}")


def check_wecom_config() -> bool:
    """Check if WeCom webhook URL is configured."""
    webhook_url = os.getenv("WECOM_WEBHOOK_URL", "").strip()
    
    if not webhook_url:
        print("\n❌ 错误: 未配置企业微信 Webhook URL")
        print("\n请按以下步骤配置:")
        print("1. 在企业微信群聊中添加机器人")
        print("2. 获取 Webhook URL (格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx)")
        print("3. 将 URL 添加到 .env 文件:")
        print("   WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY")
        print("\n详细文档: docs/wecom-alert-setup.md")
        return False
    
    # Validate URL format
    if not webhook_url.startswith("https://qyapi.weixin.qq.com"):
        print(f"\n⚠ 警告: Webhook URL 格式可能不正确")
        print(f"   当前值: {webhook_url}")
        print(f"   应为: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx")
        return False
    
    print(f"✓ 企业微信 Webhook URL 已配置")
    print(f"  URL: {webhook_url[:50]}...")
    return True


def setup_wecom_alerts() -> None:
    """Setup WeCom alert configuration."""
    webhook_url = os.getenv("WECOM_WEBHOOK_URL", "").strip()
    
    if not webhook_url:
        print("❌ 无法配置告警: Webhook URL 未设置")
        sys.exit(1)
    
    manager = get_alert_manager()
    
    # Register WeCom notifier
    wecom_notifier = WeComNotifier(webhook_url)
    manager.register_notification_handler(AlertChannel.WEBHOOK, wecom_notifier)
    print("✓ 企业微信通知处理器已注册")
    
    # Configure success rate alert
    manager.register_rule(AlertRule(
        name="success-rate-low",
        metric="success_rate",
        threshold=0.95,
        operator="lt",
        severity=AlertSeverity.WARNING,
        window_minutes=60,
        channels=[AlertChannel.WEBHOOK],
    ))
    print("✓ 成功率告警规则已配置 (阈值: < 95%)")
    
    # Configure latency alert
    manager.register_rule(AlertRule(
        name="latency-high",
        metric="latency_p95_ms",
        threshold=500,
        operator="gt",
        severity=AlertSeverity.CRITICAL,
        window_minutes=30,
        channels=[AlertChannel.WEBHOOK],
    ))
    print("✓ 延迟告警规则已配置 (阈值: > 500ms)")


def test_wecom_notification() -> bool:
    """Test WeCom notification by triggering a test alert."""
    print("\n📤 发送测试告警...")
    
    manager = get_alert_manager()
    
    # Trigger a test alert
    alert = manager.check_rule("success-rate-low", 0.80)
    
    if alert:
        print("✓ 测试告警已触发并发送")
        print(f"  告警名称: {alert.rule.name}")
        print(f"  严重级别: {alert.rule.severity.value.upper()}")
        print(f"  当前值: {alert.value}")
        print(f"  阈值: {alert.rule.operator} {alert.rule.threshold}")
        
        # Check if message was sent successfully
        print("\n✓ 请检查企业微信群聊是否收到告警消息")
        return True
    else:
        print("❌ 测试告警未能触发")
        return False


def main():
    """Main setup flow."""
    print("=" * 60)
    print("  MCP Langfuse Observability - 企业微信告警配置")
    print("=" * 60)
    
    # Step 1: Load environment
    print("\n[1/4] 加载环境变量...")
    load_env()
    
    # Step 2: Check configuration
    print("\n[2/4] 检查配置...")
    if not check_wecom_config():
        sys.exit(1)
    
    # Step 3: Setup alerts
    print("\n[3/4] 配置告警规则...")
    setup_wecom_alerts()
    
    # Step 4: Test notification
    print("\n[4/4] 测试通知...")
    success = test_wecom_notification()
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✅ 配置完成！企业微信告警已就绪")
        print("\n下一步:")
        print("- 查看告警规则: python scripts/query_alert_rules.py")
        print("- 查看事件响应手册: docs/event-response-runbook.md")
        print("- 自定义告警规则: 参考 docs/wecom-alert-setup.md")
    else:
        print("❌ 配置未完成，请检查上述错误")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
