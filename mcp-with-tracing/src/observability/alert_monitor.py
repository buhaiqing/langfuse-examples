"""
Background alert monitoring scheduler.

Periodically checks alert rules against current metrics and triggers alerts
when thresholds are exceeded. Uses APScheduler for reliable task scheduling.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.observability.alerting import AlertRule, get_alert_manager
from src.observability.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


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
            logger.warning("Alert monitor is already running")
            return

        logger.info("Starting alert monitor (interval: %dmin)...", self.check_interval)

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

        logger.info("Alert monitor started successfully (interval: %dmin)", self.check_interval)

    def stop(self) -> None:
        """Stop the background monitoring scheduler."""
        if self.scheduler and self._is_running:
            logger.info("Stopping alert monitor...")
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Alert monitor stopped")

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
                logger.warning("No alert rules registered, skipping check")
                return

            logger.info("Running alert check (%d rules)...", len(rules))

            triggered_count = 0

            for rule_name in rules:
                rule = manager.get_rule(rule_name)
                if not rule or not rule.enabled:
                    continue

                try:
                    # Get current metric value
                    current_value = await self._get_metric_value(rule)

                    if current_value is None:
                        logger.debug("%s: No data available", rule_name)
                        continue

                    # Check rule
                    alert = manager.check_rule(rule_name, current_value)

                    if alert:
                        triggered_count += 1
                        logger.warning(
                            "%s: TRIGGERED (value=%s, threshold=%s %s)",
                            rule_name, current_value, rule.operator, rule.threshold,
                        )
                    else:
                        logger.debug("%s: OK (value=%s)", rule_name, current_value)

                except Exception as e:
                    logger.error("%s: Check failed - %s", rule_name, e)

            logger.info("Alert check complete: %d alert(s) triggered", triggered_count)

        except Exception as e:
            logger.error("Alert check cycle failed: %s", e, exc_info=True)

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
                logger.warning("P99 latency not implemented, using P95")
                return self.metrics_collector.collect_latency_p95()

            elif metric == "avg_rating":
                rating = self.metrics_collector.collect_avg_satisfaction()
                return float(rating) if rating is not None else None

            elif metric == "error_rate":
                # Error rate = 1 - success_rate
                success_rate = self.metrics_collector.collect_success_rate()
                return 1.0 - success_rate

            else:
                logger.warning("Unknown metric '%s', returning None", metric)
                return None

        except Exception as e:
            logger.warning("Failed to collect metric '%s': %s", metric, e)
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
