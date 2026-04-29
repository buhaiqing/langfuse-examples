"""
Integration tests for smart alerting system.

Tests end-to-end anomaly detection workflow with simulated data.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.observability.alerting import AlertSeverity
from src.observability.smart_alerting import SmartAlertManager


class TestEndToEndAnomalyDetection:
    """End-to-end tests for the complete anomaly detection pipeline."""

    @pytest.fixture
    def setup_smart_alert_manager(self):
        """Setup SmartAlertManager with mocked dependencies."""
        with patch('src.observability.smart_alerting.MetricsCollector') as mock_mc, \
             patch('src.observability.smart_alerting.AnomalyDetector') as mock_ad:

            mock_collector = Mock()
            mock_detector = Mock()

            mock_mc.return_value = mock_collector
            mock_ad.return_value = mock_detector

            yield mock_collector, mock_detector

    def test_end_to_end_anomaly_detection(self, setup_smart_alert_manager):
        """Test complete anomaly detection workflow."""
        mock_collector, mock_detector = setup_smart_alert_manager

        # 1. Setup historical data for training
        dates = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(hours=24),
            end=datetime.now(timezone.utc),
            freq='10min'
        )

        # Normal success rate data (around 0.95)
        normal_success_rates = np.random.normal(0.95, 0.02, len(dates))
        normal_success_rates = np.clip(normal_success_rates, 0.0, 1.0)

        mock_df = pd.DataFrame({
            'ds': dates,
            'y': normal_success_rates
        })
        mock_collector.get_historical_data.return_value = mock_df

        # 2. Setup current metrics (anomalous)
        mock_collector.collect_success_rate.return_value = 0.70  # Anomalously low
        mock_collector.collect_latency_p95.return_value = 200.0
        mock_collector.collect_request_rate.return_value = 10.0
        mock_collector.collect_avg_satisfaction.return_value = 4.5

        # 3. Mock anomaly detection to find anomaly
        mock_detector.detect_anomalies.return_value = [{
            'type': 'univariate',
            'metric': 'success_rate',
            'current_value': 0.70,
            'is_anomaly': True,
            'expected_range': (0.90, 1.0),
            'deviation_score': 3.0,
            'severity': AlertSeverity.CRITICAL,
            'expected_value': 0.95
        }]

        # 4. Create manager and run detection
        manager = SmartAlertManager(detection_interval_minutes=10)
        manager._run_detection_cycle()

        # 5. Verify results
        assert len(manager._alerts) == 1

        alert = manager._alerts[0]
        assert alert.rule.severity == AlertSeverity.CRITICAL
        assert 'ml-anomaly-success_rate' in alert.rule.name
        assert '0.70' in alert.message
        assert alert.context['type'] == 'univariate'
        assert alert.context['metric'] == 'success_rate'

    def test_multivariate_anomaly_detection(self, setup_smart_alert_manager):
        """Test multivariate anomaly detection workflow."""
        mock_collector, mock_detector = setup_smart_alert_manager

        # Setup historical data
        dates = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(hours=24),
            periods=100,
            freq='10min'
        )
        mock_df = pd.DataFrame({
            'ds': dates,
            'y': np.random.randn(100) + 100
        })
        mock_collector.get_historical_data.return_value = mock_df

        # Setup current metrics (all degraded)
        mock_collector.collect_success_rate.return_value = 0.70
        mock_collector.collect_latency_p95.return_value = 800.0
        mock_collector.collect_request_rate.return_value = 2.0
        mock_collector.collect_avg_satisfaction.return_value = 2.0

        # Mock multivariate anomaly
        mock_detector.detect_anomalies.return_value = [{
            'type': 'multivariate',
            'features': {
                'success_rate': 0.70,
                'latency_p95': 800.0,
                'request_rate': 2.0,
                'satisfaction': 2.0
            },
            'is_anomaly': True,
            'anomaly_score': 0.90,
            'severity': AlertSeverity.CRITICAL
        }]

        # Run detection
        manager = SmartAlertManager()
        manager._run_detection_cycle()

        # Verify
        assert len(manager._alerts) == 1
        alert = manager._alerts[0]
        assert 'ml-anomaly-multivariate' in alert.rule.name
        assert '多维异常' in alert.message
        assert '成功率' in alert.message
        assert 'P95延迟' in alert.message

    def test_no_anomaly_detected(self, setup_smart_alert_manager):
        """Test workflow when no anomalies are detected."""
        mock_collector, mock_detector = setup_smart_alert_manager

        # Setup normal data
        dates = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(hours=24),
            periods=100,
            freq='10min'
        )
        mock_df = pd.DataFrame({
            'ds': dates,
            'y': np.random.randn(100) + 100
        })
        mock_collector.get_historical_data.return_value = mock_df

        # Normal current metrics
        mock_collector.collect_success_rate.return_value = 0.98
        mock_collector.collect_latency_p95.return_value = 150.0
        mock_collector.collect_request_rate.return_value = 10.0
        mock_collector.collect_avg_satisfaction.return_value = 4.8

        # No anomalies detected
        mock_detector.detect_anomalies.return_value = []

        # Run detection
        manager = SmartAlertManager()
        manager._run_detection_cycle()

        # Verify no alerts created
        assert len(manager._alerts) == 0

    def test_multiple_anomalies_detected(self, setup_smart_alert_manager):
        """Test workflow with multiple simultaneous anomalies."""
        mock_collector, mock_detector = setup_smart_alert_manager

        # Setup historical data
        dates = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(hours=24),
            periods=100,
            freq='10min'
        )
        mock_df = pd.DataFrame({
            'ds': dates,
            'y': np.random.randn(100) + 100
        })
        mock_collector.get_historical_data.return_value = mock_df

        # Multiple anomalies
        anomalies = [
            {
                'type': 'univariate',
                'metric': 'success_rate',
                'current_value': 0.75,
                'is_anomaly': True,
                'expected_range': (0.90, 1.0),
                'deviation_score': 2.5,
                'severity': AlertSeverity.WARNING,
                'expected_value': 0.95
            },
            {
                'type': 'univariate',
                'metric': 'latency_p95',
                'current_value': 600.0,
                'is_anomaly': True,
                'expected_range': (100.0, 300.0),
                'deviation_score': 2.0,
                'severity': AlertSeverity.WARNING,
                'expected_value': 200.0
            }
        ]

        mock_detector.detect_anomalies.return_value = anomalies

        # Run detection
        manager = SmartAlertManager()
        manager._run_detection_cycle()

        # Verify both alerts created
        assert len(manager._alerts) == 2

        metrics_alerted = [alert.context['metric'] for alert in manager._alerts]
        assert 'success_rate' in metrics_alerted
        assert 'latency_p95' in metrics_alerted


class TestSmartAlertWithRealLangfuseData:
    """Tests using real Langfuse data (requires valid credentials)."""

    @pytest.mark.skip(reason="Requires valid Langfuse credentials")
    def test_smart_alert_with_real_langfuse_data(self):
        """Test with actual Langfuse API data."""
        import os

        # Skip if credentials not configured
        if not os.getenv('LANGFUSE_PUBLIC_KEY'):
            pytest.skip("LANGFUSE_PUBLIC_KEY not set")

        # This would use real Langfuse client
        # For now, just verify the structure works
        manager = SmartAlertManager(detection_interval_minutes=10)

        # Would need real data to train models
        # manager.anomaly_detector.train_all_models(hours_of_history=24)
        # anomalies = manager.anomaly_detector.detect_anomalies()

        assert manager is not None


class TestSmartAlertManagerStatistics:
    """Tests for ML alert statistics."""

    @pytest.fixture
    def manager_with_alerts(self):
        """Create manager with some alerts."""
        with patch('src.observability.smart_alerting.MetricsCollector') as mock_mc, \
             patch('src.observability.smart_alerting.AnomalyDetector') as mock_ad:

            mock_collector = Mock()
            mock_detector = Mock()

            mock_mc.return_value = mock_collector
            mock_ad.return_value = mock_detector

            manager = SmartAlertManager()

            # Add some ML alerts
            anomaly1 = {
                'type': 'univariate',
                'metric': 'success_rate',
                'current_value': 0.80,
                'is_anomaly': True,
                'expected_range': (0.90, 1.0),
                'deviation_score': 2.0,
                'severity': AlertSeverity.WARNING,
                'expected_value': 0.95
            }

            anomaly2 = {
                'type': 'multivariate',
                'features': {
                    'success_rate': 0.75,
                    'latency_p95': 500.0,
                    'request_rate': 8.0,
                    'satisfaction': 3.0
                },
                'is_anomaly': True,
                'anomaly_score': 0.75,
                'severity': AlertSeverity.WARNING
            }

            manager._create_smart_alert(anomaly1)
            manager._create_smart_alert(anomaly2)

            return manager

    def test_ml_alert_statistics_structure(self, manager_with_alerts):
        """Test ML alert statistics structure."""
        stats = manager_with_alerts.get_ml_alert_statistics()

        assert 'total_ml_alerts' in stats
        assert 'by_type' in stats
        assert 'by_metric' in stats
        assert 'last_detection' in stats

    def test_ml_alert_statistics_counts(self, manager_with_alerts):
        """Test ML alert statistics counts."""
        stats = manager_with_alerts.get_ml_alert_statistics()

        assert stats['total_ml_alerts'] == 2
        assert stats['by_type']['univariate'] == 1
        assert stats['by_type']['multivariate'] == 1
        assert stats['by_metric']['success_rate'] == 1

    def test_empty_ml_statistics(self):
        """Test statistics when no ML alerts exist."""
        with patch('src.observability.smart_alerting.MetricsCollector') as mock_mc, \
             patch('src.observability.smart_alerting.AnomalyDetector') as mock_ad:

            mock_mc.return_value = Mock()
            mock_ad.return_value = Mock()

            manager = SmartAlertManager()
            stats = manager.get_ml_alert_statistics()

            assert stats['total_ml_alerts'] == 0
            assert stats['by_type'] == {}
            assert stats['by_metric'] == {}
