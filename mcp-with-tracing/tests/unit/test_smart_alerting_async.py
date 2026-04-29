"""
Unit tests for SmartAlertManager async monitoring architecture.

Tests verify:
- AsyncIOScheduler integration (replaces threading)
- Start/stop lifecycle
- Detection cycle execution
- Status reporting
"""

from unittest.mock import MagicMock, patch


class TestSmartAlertManagerAsyncArchitecture:
    """Test SmartAlertManager uses AsyncIOScheduler instead of threading."""

    def test_scheduler_initialization(self):
        """Test that scheduler is properly initialized."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager(detection_interval_minutes=10)

        assert manager._scheduler is None
        assert manager._is_running is False
        assert manager.detection_interval == 10

    @patch("src.observability.smart_alerting.AsyncIOScheduler")
    def test_start_monitoring_creates_scheduler(self, mock_scheduler_class):
        """Test that start_monitoring creates and starts AsyncIOScheduler."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager(detection_interval_minutes=10)
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        manager.start_monitoring()

        # Verify scheduler was created
        mock_scheduler_class.assert_called_once()
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()

        # Verify manager state
        assert manager._is_running is True
        assert manager._scheduler is mock_scheduler

    @patch("src.observability.smart_alerting.AsyncIOScheduler")
    def test_start_monitoring_prevents_duplicate(self, mock_scheduler_class):
        """Test that starting twice doesn't create duplicate schedulers."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager()
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        # Start once
        manager.start_monitoring()
        assert mock_scheduler_class.call_count == 1

        # Try to start again
        manager.start_monitoring()
        # Should not create another scheduler
        assert mock_scheduler_class.call_count == 1

    @patch("src.observability.smart_alerting.AsyncIOScheduler")
    def test_stop_monitoring_shuts_down_scheduler(self, mock_scheduler_class):
        """Test that stop_monitoring properly shuts down scheduler."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager()
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        # Start
        manager.start_monitoring()
        assert manager._is_running is True

        # Stop
        manager.stop_monitoring()
        mock_scheduler.shutdown.assert_called_once_with(wait=True)
        assert manager._is_running is False

    def test_stop_monitoring_when_not_running(self):
        """Test that stopping when not running does nothing."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager()
        manager._scheduler = None
        manager._is_running = False

        # Should not raise
        manager.stop_monitoring()

    @patch("src.observability.smart_alerting.AsyncIOScheduler")
    def test_scheduler_job_configuration(self, mock_scheduler_class):
        """Test that scheduler job is configured correctly."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager(detection_interval_minutes=15)
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        manager.start_monitoring()

        # Verify job configuration
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "smart_alert_detection"
        assert call_kwargs["max_instances"] == 1
        assert call_kwargs["replace_existing"] is True

    def test_get_status_when_not_running(self):
        """Test status reporting when scheduler is not running."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager(detection_interval_minutes=10)

        status = manager.get_status()

        assert status["is_running"] is False
        assert status["detection_interval_minutes"] == 10
        assert status["last_detection"] is None
        assert status["scheduler_jobs"] == 0

    @patch("src.observability.smart_alerting.AsyncIOScheduler")
    def test_get_status_when_running(self, mock_scheduler_class):
        """Test status reporting when scheduler is running."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager(detection_interval_minutes=10)
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_scheduler.get_jobs.return_value = [MagicMock()]

        manager.start_monitoring()

        status = manager.get_status()

        assert status["is_running"] is True
        assert status["scheduler_jobs"] == 1


class TestSmartAlertManagerDetectionCycle:
    """Test detection cycle execution."""

    @patch("src.observability.smart_alerting.AnomalyDetector")
    @patch("src.observability.smart_alerting.MetricsCollector")
    def test_detection_cycle_runs_successfully(self, mock_collector, mock_detector):
        """Test that detection cycle executes without errors."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager()
        manager.anomaly_detector = mock_detector.return_value
        mock_detector.return_value.detect_anomalies.return_value = []

        # Should not raise
        manager._run_detection_cycle()

        # Verify detection was called
        mock_detector.return_value.detect_anomalies.assert_called_once()

    @patch("src.observability.smart_alerting.AnomalyDetector")
    @patch("src.observability.smart_alerting.MetricsCollector")
    def test_detection_cycle_creates_alerts(self, mock_collector, mock_detector):
        """Test that detection cycle creates alerts for anomalies."""
        from src.observability.alerting import AlertSeverity
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager()
        manager.anomaly_detector = mock_detector.return_value

        # Mock anomaly
        mock_detector.return_value.detect_anomalies.return_value = [
            {
                "type": "univariate",
                "metric": "success_rate",
                "current_value": 0.5,
                "expected_range": [0.8, 0.95],
                "deviation_score": 2.5,
                "severity": AlertSeverity.WARNING,
            }
        ]

        manager._run_detection_cycle()

        # Verify alert was created
        assert len(manager._alerts) == 1
        assert "ml-anomaly-success_rate" in manager._alerts[0].rule.name


class TestSmartAlertManagerNoThreading:
    """Verify that threading is no longer used."""

    def test_no_threading_import(self):
        """Test that smart_alerting.py does not import threading."""
        import inspect

        import src.observability.smart_alerting as module

        source = inspect.getsource(module)

        # Should not import threading
        assert "import threading" not in source
        assert "from threading" not in source

    def test_no_threading_attributes(self):
        """Test that SmartAlertManager has no threading-related attributes."""
        from src.observability.smart_alerting import SmartAlertManager

        manager = SmartAlertManager()

        # Should not have threading attributes
        assert not hasattr(manager, "_monitoring_thread")
        assert not hasattr(manager, "_stop_monitoring")

        # Should have scheduler attributes
        assert hasattr(manager, "_scheduler")
        assert hasattr(manager, "_is_running")
