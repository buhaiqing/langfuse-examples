"""
Smart alert manager with ML-based anomaly detection.

Extends the base AlertManager with intelligent anomaly detection
using Prophet and PyOD for proactive monitoring.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time
import threading

from src.observability.alerting import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertChannel,
)
from src.observability.metrics_collector import MetricsCollector
from src.observability.anomaly_detector import AnomalyDetector

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
        self.metrics_collector = MetricsCollector(
            window_minutes=detection_interval_minutes
        )
        self.anomaly_detector = AnomalyDetector(self.metrics_collector)
        self.detection_interval = detection_interval_minutes
        self._last_detection_time: Optional[datetime] = None
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False

    def start_monitoring(self) -> None:
        """
        Start background monitoring thread.
        
        Launches a daemon thread that periodically runs anomaly detection
        and triggers alerts when anomalies are detected.
        """
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Monitoring is already running")
            return

        self._stop_monitoring = False

        def monitoring_loop():
            """Background monitoring loop."""
            while not self._stop_monitoring:
                try:
                    self._run_detection_cycle()
                except Exception as e:
                    logger.error("Detection cycle failed: %s", e)
                
                # Sleep in small increments to allow quick shutdown
                for _ in range(self.detection_interval * 60):
                    if self._stop_monitoring:
                        break
                    time.sleep(1)

        self._monitoring_thread = threading.Thread(
            target=monitoring_loop,
            daemon=True,
            name="SmartAlertMonitor"
        )
        self._monitoring_thread.start()
        logger.info("Smart alert monitoring started (interval: %dmin)", self.detection_interval)

    def stop_monitoring(self) -> None:
        """Stop the background monitoring thread."""
        self._stop_monitoring = True
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=30)
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

    def _create_smart_alert(self, anomaly: Dict[str, Any]) -> None:
        """
        Create an alert from anomaly detection results.
        
        Args:
            anomaly: Anomaly detection result dictionary.
        """
        if anomaly['type'] == 'univariate':
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
            threshold_value = anomaly.get('deviation_score', 0)
            
        elif anomaly['type'] == 'multivariate':
            rule_name = "ml-anomaly-multivariate"
            features = anomaly['features']
            message = (
                f"🤖 ML检测到多维异常\n"
                f"异常分数: {anomaly['anomaly_score']:.2f}\n"
                f"成功率: {features['success_rate']:.2%}\n"
                f"P95延迟: {features['latency_p95']:.2f}ms\n"
                f"请求率: {features['request_rate']:.2f}/s\n"
                f"满意度: {features['satisfaction']:.2f}\n"
                f"严重程度: {anomaly['severity'].value.upper()}"
            )
            threshold_value = anomaly.get('anomaly_score', 0)
        else:
            return

        # Create alert rule
        rule = AlertRule(
            name=rule_name,
            metric="ml_anomaly_score",
            threshold=threshold_value,
            operator="gt",
            severity=anomaly['severity'],
            window_minutes=self.detection_interval,
            channels=[AlertChannel.SLACK, AlertChannel.WEBHOOK],
            metadata={
                "ml_detected": True,
                "anomaly_type": anomaly['type'],
                "detection_method": "prophet_pyod"
            }
        )

        # Create and store alert
        alert = Alert(
            rule=rule,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            value=threshold_value,
            message=message,
            context=anomaly
        )

        self._alerts.append(alert)
        
        # Send notifications
        self._send_notifications(alert)
        
        logger.warning("Alert created: %s (%s)", rule_name, anomaly['severity'].value)

    def get_ml_alert_statistics(self) -> Dict[str, Any]:
        """
        Get statistics specific to ML-detected alerts.
        
        Returns:
            Dictionary with ML alert statistics.
        """
        ml_alerts = [
            alert for alert in self._alerts
            if alert.rule.metadata.get('ml_detected', False)
        ]

        by_type = {}
        by_metric = {}
        
        for alert in ml_alerts:
            anomaly_type = alert.rule.metadata.get('anomaly_type', 'unknown')
            by_type[anomaly_type] = by_type.get(anomaly_type, 0) + 1
            
            if anomaly_type == 'univariate':
                metric = alert.context.get('metric', 'unknown')
                by_metric[metric] = by_metric.get(metric, 0) + 1

        return {
            "total_ml_alerts": len(ml_alerts),
            "by_type": by_type,
            "by_metric": by_metric,
            "last_detection": (
                self._last_detection_time.isoformat()
                if self._last_detection_time
                else None
            )
        }
