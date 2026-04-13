"""
Background alert monitoring scheduler.

Periodically checks alert rules against current metrics and triggers alerts
when thresholds are exceeded. Uses APScheduler for reliable task scheduling.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.observability.alerting import AlertRule, get_alert_manager
from src.observability.metrics_collector import MetricsCollector


class AlertMonitorScheduler:
    """
    Background scheduler that periodically monitors alert rules.

    Fetches metrics from Langfuse and checks them against configured
    alert rules. Triggers notifications when thresholds are exceeded.
    """

    def __init__(self, check_interval_minutes: int = 5):
        """
        Initialize the alert monitor scheduler.

        Args:
            check_interval_minutes: How often to check alert rules (in minutes).
        """
        self.check_interval = check_interval_minutes
        self.scheduler: AsyncIOScheduler | None = None
        self.metrics_collector = MetricsCollector(window_minutes=check_interval_minutes)
        self._is_running = False

    def start(self) -> None:
        """
        Start the background monitoring scheduler.

        Registers periodic jobs to check all enabled alert rules.
        """
        if self._is_running:
            print("⚠️  Alert monitor is already running")
            return

        print(f"\n🔄 Starting alert monitor (interval: {self.check_interval}min)...")

        self.scheduler = AsyncIOScheduler()

        # Register job to check all alert rules
        self.scheduler.add_job(
            func=self._check_all_rules,
            trigger=IntervalTrigger(minutes=self.check_interval),
            id="alert_rule_checker",
            name="Check all alert rules",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
        )

        self.scheduler.start()
        self._is_running = True

        print("✅ Alert monitor started successfully")
        print(f"   - Check interval: {self.check_interval} minutes")
        print(f"   - Next check in: {self.check_interval} minutes")

    def stop(self) -> None:
        """Stop the background monitoring scheduler."""
        if self.scheduler and self._is_running:
            print("\n🛑 Stopping alert monitor...")
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            print("✅ Alert monitor stopped")

    async def _check_all_rules(self) -> None:
        """
        Check all registered alert rules against current metrics.

        This method is called periodically by the scheduler.
        It fetches current metric values and checks them against
        each rule's threshold.
        """
        try:
            manager = get_alert_manager()
            rules = manager.list_rules()

            if not rules:
                print("⚠️  No alert rules registered, skipping check")
                return

            print(f"\n🔍 Running alert check ({len(rules)} rules)...")

            triggered_count = 0

            for rule_name in rules:
                rule = manager.get_rule(rule_name)
                if not rule or not rule.enabled:
                    continue

                try:
                    # Get current metric value
                    current_value = await self._get_metric_value(rule)

                    if current_value is None:
                        print(f"   ⊘ {rule_name}: No data available")
                        continue

                    # Check rule
                    alert = manager.check_rule(rule_name, current_value)

                    if alert:
                        triggered_count += 1
                        print(
                            f"   🚨 {rule_name}: TRIGGERED (value={current_value}, threshold={rule.operator} {rule.threshold})"
                        )
                    else:
                        print(f"   ✓ {rule_name}: OK (value={current_value})")

                except Exception as e:
                    print(f"   ❌ {rule_name}: Check failed - {e}")

            print(f"\n✅ Alert check complete: {triggered_count} alert(s) triggered\n")

        except Exception as e:
            print(f"❌ Alert check cycle failed: {e}")
            import traceback

            traceback.print_exc()

    async def _get_metric_value(self, rule: AlertRule) -> float | None:
        """
        Get current value for a metric.

        Args:
            rule: The alert rule containing metric name.

        Returns:
            Current metric value, or None if unavailable.
        """
        metric = rule.metric.lower()

        try:
            if metric == "success_rate":
                return self.metrics_collector.collect_success_rate()

            elif metric == "latency_p95_ms":
                return self.metrics_collector.collect_latency_p95()

            elif metric == "latency_p99_ms":
                # P99 not yet implemented, use P95 as fallback
                print("   ⚠️  P99 latency not implemented, using P95")
                return self.metrics_collector.collect_latency_p95()

            elif metric == "avg_rating":
                rating = self.metrics_collector.collect_avg_satisfaction()
                return float(rating) if rating is not None else None

            elif metric == "error_rate":
                # Error rate = 1 - success_rate
                success_rate = self.metrics_collector.collect_success_rate()
                return 1.0 - success_rate

            else:
                # Unknown metric - could be extended with custom metrics
                print(f"   ⚠️  Unknown metric '{metric}', returning None")
                return None

        except Exception as e:
            print(f"   ⚠️  Failed to collect metric '{metric}': {e}")
            return None

    def get_status(self) -> dict:
        """
        Get current scheduler status.

        Returns:
            Dictionary with scheduler status information.
        """
        return {
            "is_running": self._is_running,
            "check_interval_minutes": self.check_interval,
            "registered_rules": len(get_alert_manager().list_rules()) if self._is_running else 0,
            "scheduler_jobs": len(self.scheduler.get_jobs()) if self.scheduler else 0,
        }


# Global scheduler instance
_alert_monitor: AlertMonitorScheduler | None = None


def get_alert_monitor() -> AlertMonitorScheduler:
    """Get or create the global alert monitor scheduler."""
    global _alert_monitor
    if _alert_monitor is None:
        _alert_monitor = AlertMonitorScheduler()
    return _alert_monitor


def start_alert_monitor(check_interval_minutes: int = 5) -> AlertMonitorScheduler:
    """
    Convenience function to start the alert monitor.

    Args:
        check_interval_minutes: Check interval in minutes.

    Returns:
        The AlertMonitorScheduler instance.
    """
    global _alert_monitor
    _alert_monitor = AlertMonitorScheduler(check_interval_minutes)
    _alert_monitor.start()
    return _alert_monitor


def stop_alert_monitor() -> None:
    """Convenience function to stop the alert monitor."""
    global _alert_monitor
    if _alert_monitor:
        _alert_monitor.stop()
