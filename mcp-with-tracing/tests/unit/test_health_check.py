"""
Unit tests for health check module.

Verifies that health status endpoint returns correct information
for all system components.
"""

from unittest.mock import MagicMock, patch


class TestHealthCheck:
    """Test health check functionality."""

    def test_get_health_status_healthy(self):
        """Test health status when all components are healthy."""
        from src.observability.health import get_health_status

        # Mock all dependencies
        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch("src.observability.alerting.get_alert_manager") as mock_alert_mgr,
            patch("src.observability.alert_monitor.get_alert_monitor") as mock_monitor,
        ):
            # Configure mocks
            mock_client.return_value = MagicMock()

            mock_manager = MagicMock()
            mock_manager.list_rules.return_value = [MagicMock(), MagicMock()]
            mock_alert_mgr.return_value = mock_manager

            mock_monitor_instance = MagicMock()
            mock_monitor_instance.get_status.return_value = {
                "is_running": True,
                "check_interval_minutes": 5,
            }
            mock_monitor.return_value = mock_monitor_instance

            # Get health status
            status = get_health_status()

            # Verify overall status
            assert status["status"] == "healthy"
            assert "timestamp" in status
            assert "uptime_seconds" in status
            assert status["uptime_seconds"] >= 0

            # Verify components
            assert "components" in status
            assert status["components"]["langfuse"]["status"] == "connected"
            assert status["components"]["langfuse"]["available"] is True

            assert status["components"]["alert_manager"]["status"] == "healthy"
            assert status["components"]["alert_manager"]["rules_loaded"] == 2

            assert status["components"]["alert_monitor"]["status"] == "running"
            assert status["components"]["alert_monitor"]["is_running"] is True

    def test_get_health_status_langfuse_disconnected(self):
        """Test health status when Langfuse is disconnected."""
        from src.observability.health import get_health_status

        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch("src.observability.alerting.get_alert_manager") as mock_alert_mgr,
            patch("src.observability.alert_monitor.get_alert_monitor") as mock_monitor,
        ):
            mock_client.return_value = None

            mock_manager = MagicMock()
            mock_manager.list_rules.return_value = []
            mock_alert_mgr.return_value = mock_manager

            mock_monitor_instance = MagicMock()
            mock_monitor_instance.get_status.return_value = {
                "is_running": False,
                "check_interval_minutes": 5,
            }
            mock_monitor.return_value = mock_monitor_instance

            status = get_health_status()

            # Should be degraded
            assert status["status"] == "degraded"
            assert status["components"]["langfuse"]["status"] == "disconnected"
            assert status["components"]["langfuse"]["available"] is False

    def test_get_health_status_langfuse_error(self):
        """Test health status when Langfuse check fails."""
        from src.observability.health import get_health_status

        with patch(
            "src.observability.instrumentation.get_langfuse_client",
            side_effect=Exception("Connection failed"),
        ):
            status = get_health_status()

            assert status["status"] == "degraded"
            assert status["components"]["langfuse"]["status"] == "error"
            assert "error" in status["components"]["langfuse"]

    def test_get_health_status_alert_manager_error(self):
        """Test health status when alert manager check fails."""
        from src.observability.health import get_health_status

        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch(
                "src.observability.alerting.get_alert_manager",
                side_effect=Exception("Manager error"),
            ),
        ):
            mock_client.return_value = MagicMock()

            status = get_health_status()

            assert status["status"] == "degraded"
            assert status["components"]["alert_manager"]["status"] == "error"
            assert "error" in status["components"]["alert_manager"]

    def test_get_health_status_monitor_error(self):
        """Test health status when alert monitor check fails."""
        from src.observability.health import get_health_status

        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch("src.observability.alerting.get_alert_manager") as mock_alert_mgr,
            patch(
                "src.observability.alert_monitor.get_alert_monitor",
                side_effect=Exception("Monitor error"),
            ),
        ):
            mock_client.return_value = MagicMock()
            mock_alert_mgr.return_value = MagicMock()

            status = get_health_status()

            assert status["status"] == "degraded"
            assert status["components"]["alert_monitor"]["status"] == "error"

    def test_get_health_status_smart_alert_manager(self):
        """Test health status includes smart alert manager."""
        from src.observability.health import get_health_status

        smart_manager = MagicMock()
        smart_manager.get_status.return_value = {
            "is_running": True,
            "detection_interval_minutes": 10,
            "last_detection": "2024-01-01T00:00:00",
        }

        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch("src.observability.alerting.get_alert_manager") as mock_alert_mgr,
            patch("src.observability.alert_monitor.get_alert_monitor") as mock_monitor,
            patch(
                "src.observability.smart_alerting.SmartAlertManager",
                return_value=smart_manager,
            ),
        ):
            mock_client.return_value = MagicMock()
            mock_alert_mgr.return_value = MagicMock()
            mock_monitor.return_value = MagicMock()

            status = get_health_status()

            assert "smart_alert_manager" in status["components"]
            assert status["components"]["smart_alert_manager"]["status"] == "running"
            assert status["components"]["smart_alert_manager"]["is_running"] is True
            assert status["components"]["smart_alert_manager"]["detection_interval_minutes"] == 10

    def test_get_health_status_metrics_cache(self):
        """Test health status includes metrics cache statistics."""
        from src.observability.health import get_health_status

        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch("src.observability.alerting.get_alert_manager") as mock_alert_mgr,
            patch("src.observability.alert_monitor.get_alert_monitor") as mock_monitor,
            patch(
                "src.observability.metrics_collector.MetricsCollector",
            ) as mock_collector_cls,
        ):
            mock_client.return_value = MagicMock()
            mock_alert_mgr.return_value = MagicMock()
            mock_monitor.return_value = MagicMock()

            mock_collector = MagicMock()
            mock_collector.get_cache_stats.return_value = {
                "hit_rate": 0.85,
                "size": 32,
                "ttl_seconds": 300,
            }
            mock_collector_cls.return_value = mock_collector

            status = get_health_status()

            assert "metrics_cache" in status["components"]
            assert status["components"]["metrics_cache"]["status"] == "healthy"
            assert status["components"]["metrics_cache"]["hit_rate"] == 0.85
            assert status["components"]["metrics_cache"]["size"] == 32
            assert status["components"]["metrics_cache"]["ttl_seconds"] == 300

    def test_health_status_uptime_increases(self):
        """Test that uptime increases over time."""
        import time

        from src.observability.health import get_health_status

        with (
            patch("src.observability.instrumentation.get_langfuse_client") as mock_client,
            patch("src.observability.alerting.get_alert_manager") as mock_alert_mgr,
            patch("src.observability.alert_monitor.get_alert_monitor") as mock_monitor,
        ):
            mock_client.return_value = MagicMock()
            mock_alert_mgr.return_value = MagicMock()
            mock_monitor.return_value = MagicMock()

            status1 = get_health_status()
            time.sleep(0.1)
            status2 = get_health_status()

            assert status2["uptime_seconds"] >= status1["uptime_seconds"]
