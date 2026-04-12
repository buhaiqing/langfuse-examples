"""
Unit tests for smart alert manager.

Tests cover SmartAlertManager initialization, detection cycles,
alert creation, and monitoring thread management.
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.observability.smart_alerting import SmartAlertManager
from src.observability.alerting import AlertSeverity, AlertChannel
from src.observability.anomaly_detector import AnomalyDetector
from src.observability.metrics_collector import MetricsCollector


class TestSmartAlertManager:
    """Tests for SmartAlertManager."""

    @pytest.fixture
    def mock_components(self):
        """Provide mocked components."""
        with patch('src.observability.smart_alerting.MetricsCollector') as mock_mc, \
             patch('src.observability.smart_alerting.AnomalyDetector') as mock_ad:
            
            # Configure mocks
            mock_collector = Mock(spec=MetricsCollector)
            mock_detector = Mock(spec=AnomalyDetector)
            
            mock_mc.return_value = mock_collector
            mock_ad.return_value = mock_detector
            
            yield mock_collector, mock_detector

    def test_initialization(self, mock_components):
        """Test SmartAlertManager initialization."""
        mock_collector, mock_detector = mock_components
        
        manager = SmartAlertManager(detection_interval_minutes=10)
        
        assert manager.detection_interval == 10
        assert manager.metrics_collector is not None
        assert manager.anomaly_detector is not None
        assert manager._last_detection_time is None
        assert manager._monitoring_thread is None

    def test_run_detection_cycle_first_time(self, mock_components):
        """Test first detection cycle (with model training)."""
        mock_collector, mock_detector = mock_components
        
        # Mock anomaly detection results
        mock_detector.detect_anomalies.return_value = []
        
        manager = SmartAlertManager()
        manager._run_detection_cycle()
        
        # Should train models on first run
        mock_detector.train_all_models.assert_called_once()
        assert manager._last_detection_time is not None

    def test_run_detection_cycle_with_anomalies(self, mock_components):
        """Test detection cycle that finds anomalies."""
        mock_collector, mock_detector = mock_components
        
        # Mock detected anomalies
        mock_anomaly = {
            'type': 'univariate',
            'metric': 'success_rate',
            'current_value': 0.75,
            'is_anomaly': True,
            'expected_range': (0.90, 1.0),
            'deviation_score': 2.5,
            'severity': AlertSeverity.WARNING,
            'expected_value': 0.95
        }
        mock_detector.detect_anomalies.return_value = [mock_anomaly]
        
        manager = SmartAlertManager()
        manager._run_detection_cycle()
        
        # Should create alert
        assert len(manager._alerts) == 1
        alert = manager._alerts[0]
        assert 'ml-anomaly-success_rate' in alert.rule.name
        assert alert.rule.severity == AlertSeverity.WARNING

    def test_create_smart_alert_univariate(self, mock_components):
        """Test creating alert for univariate anomaly."""
        mock_collector, mock_detector = mock_components
        
        manager = SmartAlertManager()
        
        anomaly = {
            'type': 'univariate',
            'metric': 'latency_p95',
            'current_value': 800.0,
            'is_anomaly': True,
            'expected_range': (100.0, 300.0),
            'deviation_score': 3.5,
            'severity': AlertSeverity.CRITICAL,
            'expected_value': 200.0
        }
        
        manager._create_smart_alert(anomaly)
        
        assert len(manager._alerts) == 1
        alert = manager._alerts[0]
        assert 'ml-anomaly-latency_p95' in alert.rule.name
        assert alert.rule.severity == AlertSeverity.CRITICAL
        assert 'ML检测到单指标异常' in alert.message
        assert 'latency_p95' in alert.message

    def test_create_smart_alert_multivariate(self, mock_components):
        """Test creating alert for multivariate anomaly."""
        mock_collector, mock_detector = mock_components
        
        manager = SmartAlertManager()
        
        anomaly = {
            'type': 'multivariate',
            'features': {
                'success_rate': 0.70,
                'latency_p95': 600.0,
                'request_rate': 5.0,
                'satisfaction': 2.5
            },
            'is_anomaly': True,
            'anomaly_score': 0.85,
            'severity': AlertSeverity.CRITICAL
        }
        
        manager._create_smart_alert(anomaly)
        
        assert len(manager._alerts) == 1
        alert = manager._alerts[0]
        assert 'ml-anomaly-multivariate' in alert.rule.name
        assert 'ML检测到多维异常' in alert.message
        assert '成功率' in alert.message

    def test_get_ml_alert_statistics(self, mock_components):
        """Test ML-specific alert statistics."""
        mock_collector, mock_detector = mock_components
        
        manager = SmartAlertManager()
        
        # Create some ML alerts
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
        
        stats = manager.get_ml_alert_statistics()
        
        assert stats['total_ml_alerts'] == 2
        assert 'univariate' in stats['by_type']
        assert 'multivariate' in stats['by_type']
        assert 'success_rate' in stats['by_metric']

    def test_monitoring_thread_start_stop(self, mock_components):
        """Test starting and stopping monitoring thread."""
        mock_collector, mock_detector = mock_components
        
        # Mock detection to return no anomalies quickly
        mock_detector.detect_anomalies.return_value = []
        
        manager = SmartAlertManager(detection_interval_minutes=1)
        
        # Start monitoring
        manager.start_monitoring()
        
        assert manager._monitoring_thread is not None
        assert manager._monitoring_thread.is_alive()
        
        # Let it run briefly
        time.sleep(2)
        
        # Stop monitoring
        manager.stop_monitoring()
        
        # Thread should stop (with timeout)
        manager._monitoring_thread.join(timeout=5)
        assert not manager._monitoring_thread.is_alive()

    def test_monitoring_thread_already_running(self, mock_components):
        """Test that starting monitoring twice doesn't create multiple threads."""
        mock_collector, mock_detector = mock_components
        
        mock_detector.detect_anomalies.return_value = []
        
        manager = SmartAlertManager(detection_interval_minutes=1)
        
        # Start once
        manager.start_monitoring()
        first_thread = manager._monitoring_thread
        
        # Try to start again
        manager.start_monitoring()
        
        # Should be the same thread
        assert manager._monitoring_thread is first_thread
        
        # Cleanup
        manager.stop_monitoring()

    def test_detection_cycle_exception_handling(self, mock_components):
        """Test that exceptions in detection cycle are handled gracefully."""
        mock_collector, mock_detector = mock_components
        
        # Mock detection to raise exception
        mock_detector.detect_anomalies.side_effect = Exception("Test error")
        
        manager = SmartAlertManager()
        
        # Should not raise exception
        manager._run_detection_cycle()
        
        # Last detection time should still be set
        assert manager._last_detection_time is not None

    def test_periodic_retraining(self, mock_components):
        """Test that models are retrained periodically."""
        mock_collector, mock_detector = mock_components
        
        mock_detector.detect_anomalies.return_value = []
        
        manager = SmartAlertManager()
        
        # First run - trains models
        manager._run_detection_cycle()
        train_call_count_1 = mock_detector.train_all_models.call_count
        
        # Simulate time passing (> 1 hour)
        from datetime import timedelta
        manager._last_detection_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Second run - should retrain
        manager._run_detection_cycle()
        train_call_count_2 = mock_detector.train_all_models.call_count
        
        assert train_call_count_2 > train_call_count_1


class TestSmartAlertManagerIntegration:
    """Integration tests for SmartAlertManager with real components."""

    def test_full_workflow_simulation(self):
        """Simulate complete workflow with mocked Langfuse."""
        with patch('src.observability.smart_alerting.MetricsCollector') as mock_mc, \
             patch('src.observability.smart_alerting.AnomalyDetector') as mock_ad:
            
            # Setup mocks
            mock_collector = Mock()
            mock_detector = Mock()
            
            mock_mc.return_value = mock_collector
            mock_ad.return_value = mock_detector
            
            # Mock historical data for training
            import pandas as pd
            import numpy as np
            dates = pd.date_range(start='2024-01-01', periods=100, freq='10min')
            mock_df = pd.DataFrame({
                'ds': dates,
                'y': np.random.randn(100) + 100
            })
            mock_collector.get_historical_data.return_value = mock_df
            
            # Mock current metrics
            mock_collector.collect_success_rate.return_value = 0.95
            mock_collector.collect_latency_p95.return_value = 200.0
            mock_collector.collect_request_rate.return_value = 10.0
            mock_collector.collect_avg_satisfaction.return_value = 4.5
            
            # Mock anomaly detection
            mock_detector.detect_anomalies.return_value = [{
                'type': 'univariate',
                'metric': 'success_rate',
                'current_value': 0.75,
                'is_anomaly': True,
                'expected_range': (0.90, 1.0),
                'deviation_score': 2.5,
                'severity': AlertSeverity.WARNING,
                'expected_value': 0.95
            }]
            
            # Create manager and run
            manager = SmartAlertManager()
            manager._run_detection_cycle()
            
            # Verify
            assert len(manager._alerts) == 1
            assert manager._last_detection_time is not None
