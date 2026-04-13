"""
Alert monitor scheduler tests.

Tests cover background monitoring, periodic rule checking,
and scheduler lifecycle management.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from src.observability.alert_monitor import (
    AlertMonitorScheduler,
    start_alert_monitor,
    stop_alert_monitor,
    get_alert_monitor,
)
from src.observability.alerting import (
    AlertRule,
    AlertSeverity,
    AlertChannel,
    Alert,
)


class TestAlertMonitorScheduler:
    """AlertMonitorScheduler class tests."""

    def test_init_default_interval(self):
        """Test initialization with default interval."""
        scheduler = AlertMonitorScheduler()
        
        assert scheduler.check_interval == 5
        assert scheduler.scheduler is None
        assert scheduler._is_running is False

    def test_init_custom_interval(self):
        """Test initialization with custom interval."""
        scheduler = AlertMonitorScheduler(check_interval_minutes=10)
        
        assert scheduler.check_interval == 10
        assert scheduler._is_running is False

    @patch('src.observability.alert_monitor.AsyncIOScheduler')
    def test_start_scheduler(self, mock_scheduler_class):
        """Test starting the scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = AlertMonitorScheduler(check_interval_minutes=5)
        scheduler.start()
        
        assert scheduler._is_running is True
        assert scheduler.scheduler is not None
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()

    @patch('src.observability.alert_monitor.AsyncIOScheduler')
    def test_stop_scheduler(self, mock_scheduler_class):
        """Test stopping the scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = AlertMonitorScheduler()
        scheduler.start()
        scheduler.stop()
        
        assert scheduler._is_running is False
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_check_all_rules_no_rules(self, capsys):
        """Test checking when no rules are registered."""
        with patch('src.observability.alert_monitor.get_alert_manager') as mock_get_mgr:
            mock_manager = MagicMock()
            mock_manager.list_rules.return_value = []
            mock_get_mgr.return_value = mock_manager
            
            scheduler = AlertMonitorScheduler()
            await scheduler._check_all_rules()
            
            captured = capsys.readouterr()
            assert "No alert rules registered" in captured.out

    @pytest.mark.asyncio
    async def test_check_all_rules_disabled_rule(self, capsys):
        """Test checking with disabled rule."""
        with patch('src.observability.alert_monitor.get_alert_manager') as mock_get_mgr:
            mock_manager = MagicMock()
            
            disabled_rule = AlertRule(
                name='disabled-rule',
                metric='success_rate',
                threshold=0.95,
                operator='lt',
                severity=AlertSeverity.WARNING,
                enabled=False,
            )
            
            mock_manager.list_rules.return_value = ['disabled-rule']
            mock_manager.get_rule.return_value = disabled_rule
            mock_get_mgr.return_value = mock_manager
            
            scheduler = AlertMonitorScheduler()
            await scheduler._check_all_rules()
            
            # Should skip disabled rules
            captured = capsys.readouterr()
            assert 'TRIGGERED' not in captured.out

    @pytest.mark.asyncio
    async def test_check_all_rules_triggers_alert(self):
        """Test that alerts are triggered when threshold exceeded."""
        with patch('src.observability.alert_monitor.get_alert_manager') as mock_get_mgr:
            mock_manager = MagicMock()
            
            rule = AlertRule(
                name='test-rule',
                metric='success_rate',
                threshold=0.95,
                operator='lt',
                severity=AlertSeverity.WARNING,
                enabled=True,
            )
            
            # Create a sample alert
            alert = Alert(
                rule=rule,
                triggered_at=datetime.now(timezone.utc).isoformat(),
                value=0.85,
                message="Test alert",
            )
            
            mock_manager.list_rules.return_value = ['test-rule']
            mock_manager.get_rule.return_value = rule
            mock_manager.check_rule.return_value = alert
            mock_get_mgr.return_value = mock_manager
            
            scheduler = AlertMonitorScheduler()
            
            # Mock _get_metric_value to return a value
            with patch.object(scheduler, '_get_metric_value', return_value=0.85):
                await scheduler._check_all_rules()
            
            # Verify check_rule was called
            mock_manager.check_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metric_value_success_rate(self):
        """Test getting success_rate metric."""
        scheduler = AlertMonitorScheduler()
        
        rule = AlertRule(
            name='test',
            metric='success_rate',
            threshold=0.95,
            operator='lt',
            severity=AlertSeverity.WARNING,
        )
        
        with patch.object(scheduler.metrics_collector, 'collect_success_rate', return_value=0.92):
            value = await scheduler._get_metric_value(rule)
            
            assert value == 0.92

    @pytest.mark.asyncio
    async def test_get_metric_value_latency_p95(self):
        """Test getting latency_p95_ms metric."""
        scheduler = AlertMonitorScheduler()
        
        rule = AlertRule(
            name='test',
            metric='latency_p95_ms',
            threshold=500,
            operator='gt',
            severity=AlertSeverity.WARNING,
        )
        
        with patch.object(scheduler.metrics_collector, 'collect_latency_p95', return_value=450.0):
            value = await scheduler._get_metric_value(rule)
            
            assert value == 450.0

    @pytest.mark.asyncio
    async def test_get_metric_value_avg_rating(self):
        """Test getting avg_rating metric."""
        scheduler = AlertMonitorScheduler()
        
        rule = AlertRule(
            name='test',
            metric='avg_rating',
            threshold=3.5,
            operator='lt',
            severity=AlertSeverity.WARNING,
        )
        
        with patch.object(scheduler.metrics_collector, 'collect_avg_satisfaction', return_value=4.2):
            value = await scheduler._get_metric_value(rule)
            
            assert value == 4.2

    @pytest.mark.asyncio
    async def test_get_metric_value_error_rate(self):
        """Test getting error_rate metric."""
        scheduler = AlertMonitorScheduler()
        
        rule = AlertRule(
            name='test',
            metric='error_rate',
            threshold=0.05,
            operator='gt',
            severity=AlertSeverity.WARNING,
        )
        
        with patch.object(scheduler.metrics_collector, 'collect_success_rate', return_value=0.95):
            value = await scheduler._get_metric_value(rule)
            
            # error_rate = 1 - success_rate (allow floating point tolerance)
            assert abs(value - 0.05) < 0.0001

    @pytest.mark.asyncio
    async def test_get_metric_value_unknown_metric(self, capsys):
        """Test getting unknown metric returns None."""
        scheduler = AlertMonitorScheduler()
        
        rule = AlertRule(
            name='test',
            metric='unknown_metric',
            threshold=100,
            operator='gt',
            severity=AlertSeverity.WARNING,
        )
        
        value = await scheduler._get_metric_value(rule)
        
        assert value is None
        captured = capsys.readouterr()
        assert "Unknown metric" in captured.out

    def test_get_status_not_running(self):
        """Test status when scheduler is not running."""
        scheduler = AlertMonitorScheduler()
        status = scheduler.get_status()
        
        assert status['is_running'] is False
        assert status['check_interval_minutes'] == 5

    @patch('src.observability.alert_monitor.AsyncIOScheduler')
    def test_get_status_running(self, mock_scheduler_class):
        """Test status when scheduler is running."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [MagicMock()]
        mock_scheduler_class.return_value = mock_scheduler
        
        with patch('src.observability.alert_monitor.get_alert_manager') as mock_get_mgr:
            mock_manager = MagicMock()
            mock_manager.list_rules.return_value = ['rule1']
            mock_get_mgr.return_value = mock_manager
            
            scheduler = AlertMonitorScheduler()
            scheduler.start()
            status = scheduler.get_status()
            
            assert status['is_running'] is True
            assert status['check_interval_minutes'] == 5


class TestConvenienceFunctions:
    """Module-level convenience function tests."""

    def teardown_method(self):
        """Clean up global monitor instance."""
        import src.observability.alert_monitor as monitor_module
        monitor_module._alert_monitor = None

    @patch('src.observability.alert_monitor.AlertMonitorScheduler')
    def test_start_alert_monitor(self, mock_scheduler_class):
        """Test start_alert_monitor function."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        monitor = start_alert_monitor(check_interval_minutes=10)
        
        assert monitor is not None
        mock_scheduler_class.assert_called_once_with(10)
        mock_scheduler.start.assert_called_once()

    @patch('src.observability.alert_monitor.AlertMonitorScheduler')
    def test_stop_alert_monitor(self, mock_scheduler_class):
        """Test stop_alert_monitor function."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        # Start first
        start_alert_monitor()
        
        # Then stop
        stop_alert_monitor()
        
        mock_scheduler.stop.assert_called_once()

    @patch('src.observability.alert_monitor.AlertMonitorScheduler')
    def test_get_alert_monitor_returns_instance(self, mock_scheduler_class):
        """Test get_alert_monitor returns the started instance."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        # Start to create instance
        start_alert_monitor()
        
        # Get instance
        monitor = get_alert_monitor()
        
        assert monitor is not None
        assert monitor == mock_scheduler
