"""
Smart alert manager with ML-based anomaly detection.

Extends the base AlertManager with intelligent anomaly detection
using Prophet and PyOD for proactive monitoring.
Uses APScheduler AsyncIOScheduler for async-native scheduling.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.observability.alerting import (
    Alert,
    AlertChannel,
    AlertManager,
    AlertRule,
)
from src.observability.anomaly_detector import AnomalyDetector
from src.observability.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class SmartAlertManager(AlertManager):
    """
    Smart alert manager integrating ML-based anomaly detection.

    Extends the base AlertManager with automated anomaly detection
    using time series forecasting and multivariate analysis.
    """

    def __init__(self, detection_interval_minutes: int = 10):
        """
        Initialize the smart alert manager.

        Args:
            detection_interval_minutes: Interval between detection cycles.
        """
        super().__init__()
        self.metrics_collector = MetricsCollector(window_minutes=detection_interval_minutes)
        self.anomaly_detector = AnomalyDetector(self.metrics_collector)
        self.detection_interval = detection_interval_minutes
        self._last_detection_time: datetime | None = None
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running = False

    def start_monitoring(self) -> None:
        """
        Start background monitoring using AsyncIOScheduler.

        Schedules periodic anomaly detection jobs using APScheduler's
        async-native scheduler instead of threading.
        Note: This should be called after the event loop is running.
        """
        if self._is_running:
            logger.warning("Monitoring is already running")
            return

        try:
            # Try to get current event loop
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Event loop is running, we can start AsyncIOScheduler
                self._do_start()
            else:
                # Event loop not running yet, defer startup
                logger.info("Event loop not running, scheduling deferred startup")
                async def deferred_start():
                    await asyncio.sleep(1)
                    self._do_start()
                loop.create_task(deferred_start())
        except RuntimeError:
            # No event loop exists yet
            logger.warning("No event loop available, smart monitoring will not start")

    def _do_start(self) -> None:
        """Actually start the scheduler (called when event loop is ready)."""
        self._scheduler = AsyncIOScheduler()

        # Schedule detection cycle
        self._scheduler.add_job(
            func=self._run_detection_cycle,
            trigger=IntervalTrigger(minutes=self.detection_interval),
            id="smart_alert_detection",
            name="ML anomaly detection cycle",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
        )

        self._scheduler.start()
        self._is_running = True
        logger.info(
            "Smart alert monitoring started (interval: %dmin)",
            self.detection_interval,
        )

    def stop_monitoring(self) -> None:
        """Stop the background monitoring scheduler."""
        if self._scheduler and self._is_running:
            logger.info("Stopping smart alert monitoring...")
            self._scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Smart alert monitoring stopped")

    def _run_detection_cycle(self) -> None:
        """Execute one detection cycle."""
        try:
            now = datetime.now(timezone.utc)

            # Train models on first run or periodically
            if self._last_detection_time is None:
                logger.info("Initial model training...")
                self.anomaly_detector.train_all_models(hours_of_history=24)
            elif (now - self._last_detection_time).total_seconds() > 3600:
                logger.info("Periodic model retraining...")
                self.anomaly_detector.train_all_models(hours_of_history=24)

            logger.info("Running anomaly detection...")
            anomalies = self.anomaly_detector.detect_anomalies()

            # Create alerts for detected anomalies
            for anomaly in anomalies:
                self._create_smart_alert(anomaly)

            self._last_detection_time = now

            if anomalies:
                logger.warning("Detected %d anomalies", len(anomalies))
            else:
                logger.debug("No anomalies detected")
        except Exception as e:
            logger.error("Detection cycle failed: %s", e, exc_info=True)
            self._last_detection_time = datetime.now(timezone.utc)

    def get_status(self) -> dict[str, Any]:
        """
        Get current monitoring status.

        Returns:
            Dictionary with scheduler and detection status.
        """
        return {
            "is_running": self._is_running,
            "detection_interval_minutes": self.detection_interval,
            "last_detection": (
                self._last_detection_time.isoformat() if self._last_detection_time else None
            ),
            "scheduler_jobs": (len(self._scheduler.get_jobs()) if self._scheduler else 0),
        }

    def _create_smart_alert(self, anomaly: dict[str, Any]) -> None:
        """
        Create an alert from anomaly detection results.

        Args:
            anomaly: Anomaly detection result dictionary.
        """
        if anomaly["type"] == "univariate":
            rule_name = f"ml-anomaly-{anomaly['metric']}"
            message = (
                f"🤖 ML检测到单指标异常\n"
                f"指标: {anomaly['metric']}\n"
                f"当前值: {anomaly['current_value']:.2f}\n"
                f"预期范围: {anomaly['expected_range'][0]:.2f} - "
                f"{anomaly['expected_range'][1]:.2f}\n"
                f"偏离分数: {anomaly['deviation_score']:.2f}\n"
                f"严重程度: {anomaly['severity'].value.upper()}"
            )
            threshold_value = anomaly.get("deviation_score", 0)

        elif anomaly["type"] == "multivariate":
            rule_name = "ml-anomaly-multivariate"
            features = anomaly["features"]
            message = (
                f"🤖 ML检测到多维异常\n"
                f"异常分数: {anomaly['anomaly_score']:.2f}\n"
                f"成功率: {features['success_rate']:.2%}\n"
                f"P95延迟: {features['latency_p95']:.2f}ms\n"
                f"请求率: {features['request_rate']:.2f}/s\n"
                f"满意度: {features['satisfaction']:.2f}\n"
                f"严重程度: {anomaly['severity'].value.upper()}"
            )
            threshold_value = anomaly.get("anomaly_score", 0)
        else:
            return

        # Create alert rule
        rule = AlertRule(
            name=rule_name,
            metric="ml_anomaly_score",
            threshold=threshold_value,
            operator="gt",
            severity=anomaly["severity"],
            window_minutes=self.detection_interval,
            channels=[AlertChannel.SLACK, AlertChannel.WEBHOOK],
            metadata={
                "ml_detected": True,
                "anomaly_type": anomaly["type"],
                "detection_method": "prophet_pyod",
            },
        )

        # Create and store alert
        alert = Alert(
            rule=rule,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            value=threshold_value,
            message=message,
            context=anomaly,
        )

        self._alerts.append(alert)

        # Send notifications
        self._send_notifications(alert)

        logger.warning("Alert created: %s (%s)", rule_name, anomaly["severity"].value)

    def get_ml_alert_statistics(self) -> dict[str, Any]:
        """
        Get statistics specific to ML-detected alerts.

        Returns:
            Dictionary with ML alert statistics.
        """
        ml_alerts = [
            alert for alert in self._alerts if alert.rule.metadata.get("ml_detected", False)
        ]

        by_type = {}
        by_metric = {}

        for alert in ml_alerts:
            anomaly_type = alert.rule.metadata.get("anomaly_type", "unknown")
            by_type[anomaly_type] = by_type.get(anomaly_type, 0) + 1

            if anomaly_type == "univariate":
                metric = alert.context.get("metric", "unknown")
                by_metric[metric] = by_metric.get(metric, 0) + 1

        return {
            "total_ml_alerts": len(ml_alerts),
            "by_type": by_type,
            "by_metric": by_metric,
            "last_detection": (
                self._last_detection_time.isoformat() if self._last_detection_time else None
            ),
        }
