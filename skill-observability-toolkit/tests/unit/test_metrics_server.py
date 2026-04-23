"""Tests for Metrics Server."""

import time

import pytest
from skill_observability_toolkit.integrations.metrics_server import MetricsServer


def test_metrics_server_initialization():
    """Test MetricsServer can be initialized."""
    server = MetricsServer(port=9091)
    assert server.port == 9091
    assert server.exporter is not None


def test_metrics_server_default_port():
    """Test default port is 9090."""
    server = MetricsServer()
    assert server.port == 9090


def test_exporter_namespace():
    """Test exporter uses correct namespace."""
    server = MetricsServer()
    assert server.exporter.namespace == "skill_obs"


def test_context_manager():
    """Test context manager start/stop."""
    server = MetricsServer(port=9092)

    with server:
        # Server should be running
        assert server._server is not None

    # Server should be stopped after context exit
    assert server._server is None


def test_start_stop_lifecycle():
    """Test explicit start/stop."""
    server = MetricsServer(port=9093)

    server.start()
    assert server._server is not None

    time.sleep(0.1)  # Allow server to start

    server.stop()
    assert server._server is None


def test_exporter_accessible():
    """Test exporter can be used to set metrics."""
    server = MetricsServer()
    server.exporter.set_gauge("test_metric", 42.5)

    metrics = server.exporter.to_prometheus_format()
    assert "test_metric" in metrics
    assert "42.5" in metrics
