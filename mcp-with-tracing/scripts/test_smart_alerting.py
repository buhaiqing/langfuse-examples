"""
智能告警系统演示脚本

Demonstrates the ML-based smart alerting system with real-time monitoring.
Shows how to configure, start, and monitor anomalies using Prophet and PyOD.
"""

import time
import sys
from datetime import datetime

from src.observability.smart_alerting import SmartAlertManager
from src.observability.alerting import AlertChannel
from src.observability.notifiers import WeComNotifier, SlackNotifier


def print_header():
    """Print demo header."""
    print("=" * 70)
    print("🤖 智能告警系统演示 (ML-Based Smart Alerting Demo)")
    print("=" * 70)
    print()


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def demo_basic_usage():
    """Demonstrate basic smart alerting usage."""
    print_section("1. 基本用法演示")
    
    # Initialize smart alert manager
    print("\n初始化智能告警管理器...")
    manager = SmartAlertManager(detection_interval_minutes=5)
    print("✓ 智能告警管理器已创建")
    print(f"  - 检测间隔: {manager.detection_interval} 分钟")
    print(f"  - 指标收集窗口: {manager.metrics_collector.window_minutes} 分钟")
    
    return manager


def demo_notification_setup(manager: SmartAlertManager):
    """Demonstrate notification channel setup."""
    print_section("2. 配置通知渠道")
    
    # Note: Replace with actual webhook URLs for real notifications
    wecom_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    slack_webhook = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    
    print("\n注册通知渠道...")
    
    # Register WeCom notifier (commented out - needs real webhook)
    # try:
    #     wecom_notifier = WeComNotifier(wecom_webhook)
    #     manager.register_notification_handler(AlertChannel.WEBHOOK, wecom_notifier)
    #     print("✓ 企业微信通知器已注册")
    # except Exception as e:
    #     print(f"✗ 企业微信通知器注册失败: {e}")
    
    # Register Slack notifier (commented out - needs real webhook)
    # try:
    #     slack_notifier = SlackNotifier(slack_webhook)
    #     manager.register_notification_handler(AlertChannel.SLACK, slack_notifier)
    #     print("✓ Slack 通知器已注册")
    # except Exception as e:
    #     print(f"✗ Slack 通知器注册失败: {e}")
    
    print("ℹ️  注意: 需要配置真实的 Webhook URL 才能发送通知")
    print("   请参考 docs/wecom-alert-setup.md 进行配置")


def demo_manual_detection(manager: SmartAlertManager):
    """Demonstrate manual anomaly detection."""
    print_section("3. 手动执行异常检测")
    
    print("\n执行单次检测周期...")
    
    try:
        # Run one detection cycle
        manager._run_detection_cycle()
        
        # Show results
        stats = manager.get_ml_alert_statistics()
        print(f"\n检测结果:")
        print(f"  - ML 告警总数: {stats['total_ml_alerts']}")
        print(f"  - 按类型: {stats['by_type']}")
        print(f"  - 按指标: {stats['by_metric']}")
        print(f"  - 最后检测时间: {stats['last_detection']}")
        
        if stats['total_ml_alerts'] > 0:
            print(f"\n⚠️  检测到 {stats['total_ml_alerts']} 个异常!")
            for i, alert in enumerate(manager._alerts, 1):
                print(f"\n告警 #{i}:")
                print(f"  规则: {alert.rule.name}")
                print(f"  严重程度: {alert.rule.severity.value.upper()}")
                print(f"  消息: {alert.message[:100]}...")
        else:
            print("\n✓ 未检测到异常")
            
    except Exception as e:
        print(f"✗ 检测失败: {e}")
        import traceback
        traceback.print_exc()


def demo_monitoring_mode(manager: SmartAlertManager):
    """Demonstrate continuous monitoring mode."""
    print_section("4. 持续监控模式")
    
    print("\n启动后台监控线程...")
    print("监控将每 {} 分钟执行一次异常检测".format(manager.detection_interval))
    print("\n按 Ctrl+C 停止监控\n")
    
    try:
        # Start monitoring
        manager.start_monitoring()
        
        # Monitor for a while
        iteration = 0
        while iteration < 3:  # Run for 3 cycles for demo
            iteration += 1
            time.sleep(10)  # Wait 10 seconds between checks
            
            stats = manager.get_ml_alert_statistics()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            print(f"[{timestamp}] 检测周期 #{iteration}")
            print(f"  ML 告警数: {stats['total_ml_alerts']}")
            print(f"  最后检测: {stats['last_detection']}")
            print()
        
    except KeyboardInterrupt:
        print("\n\n用户中断监控")
    finally:
        print("\n停止监控...")
        manager.stop_monitoring()
        print("✓ 监控已停止")


def demo_alert_history(manager: SmartAlertManager):
    """Display alert history and statistics."""
    print_section("5. 告警历史与统计")
    
    # Overall statistics
    overall_stats = manager.get_alert_statistics()
    print("\n总体告警统计:")
    print(f"  总告警数: {overall_stats['total_alerts']}")
    print(f"  按严重程度: {overall_stats['by_severity']}")
    print(f"  按规则: {overall_stats['by_rule']}")
    
    # ML-specific statistics
    ml_stats = manager.get_ml_alert_statistics()
    print("\nML 告警统计:")
    print(f"  ML 告警总数: {ml_stats['total_ml_alerts']}")
    print(f"  按类型: {ml_stats['by_type']}")
    print(f"  按指标: {ml_stats['by_metric']}")
    
    # Show recent alerts
    if manager._alerts:
        print(f"\n最近 {min(5, len(manager._alerts))} 条告警:")
        for alert in manager._alerts[-5:]:
            print(f"\n  [{alert.triggered_at[:19]}] {alert.rule.name}")
            print(f"    严重程度: {alert.rule.severity.value.upper()}")
            print(f"    值: {alert.value:.2f}")
            print(f"    消息: {alert.message[:80]}...")


def main():
    """Main demo function."""
    print_header()
    
    try:
        # Step 1: Basic setup
        manager = demo_basic_usage()
        
        # Step 2: Configure notifications
        demo_notification_setup(manager)
        
        # Step 3: Manual detection
        demo_manual_detection(manager)
        
        # Step 4: Continuous monitoring (optional - comment out if not needed)
        # Uncomment the next line to enable continuous monitoring demo
        # demo_monitoring_mode(manager)
        
        # Step 5: Show statistics
        demo_alert_history(manager)
        
        print_section("演示完成")
        print("\n✓ 智能告警系统演示成功完成!")
        print("\n下一步:")
        print("  1. 配置真实的 Langfuse API 密钥")
        print("  2. 设置通知渠道 Webhook URL")
        print("  3. 启动持续监控: manager.start_monitoring()")
        print("  4. 查看文档: docs/smart-alerting-guide.md")
        
    except Exception as e:
        print(f"\n✗ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
