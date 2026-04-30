"""
Tests for new performance metrics: P50/P99 latency, active sessions,
error breakdown, and tool-specific metrics.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestLatencyP50:
    """Tests for P50 (median) latency calculation."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_p50_latency_calculation(self, mock_get_client):
        """Test P50 latency calculation with multiple traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        traces = []
        for i in range(100):
            t = MagicMock()
            t.duration = float(i + 1)
            traces.append(t)
        mock_response.data = traces
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_latency_p50()

        assert result > 0
        # P50 of 1-100 should be around 50.5
        assert result == pytest.approx(50.5, rel=0.01)

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_p50_latency_no_traces(self, mock_get_client):
        """Test P50 latency returns 0 when no traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_latency_p50()

        assert result == 0.0

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_p50_latency_no_durations(self, mock_get_client):
        """Test P50 latency with traces that have no duration."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.duration = None
        mock_response.data = [trace1]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_latency_p50()

        assert result == 0.0


class TestLatencyP99:
    """Tests for P99 (tail) latency calculation."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_p99_latency_calculation(self, mock_get_client):
        """Test P99 latency calculation with multiple traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        traces = []
        for i in range(100):
            t = MagicMock()
            t.duration = float(i + 1)
            traces.append(t)
        mock_response.data = traces
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_latency_p99()

        assert result > 0
        # P99 of 1-100 should be around 99.01
        assert result == pytest.approx(99.01, rel=0.01)

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_p99_latency_no_traces(self, mock_get_client):
        """Test P99 latency returns 0 when no traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_latency_p99()

        assert result == 0.0


class TestActiveSessions:
    """Tests for active session counting."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_count_active_sessions(self, mock_get_client):
        """Test counting unique active sessions."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        traces = []
        for i in range(10):
            t = MagicMock()
            t.session_id = f"session_{i % 3}"  # 3 unique sessions
            traces.append(t)
        mock_response.data = traces
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.count_active_sessions()

        assert result == 3

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_count_active_sessions_no_traces(self, mock_get_client):
        """Test counting sessions when no traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.count_active_sessions()

        assert result == 0

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_count_active_sessions_missing_session_id(self, mock_get_client):
        """Test counting sessions when some traces lack session_id."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.session_id = "session_1"
        trace2 = MagicMock()
        trace2.session_id = None
        trace3 = MagicMock()
        del trace3.session_id  # No session_id attribute
        mock_response.data = [trace1, trace2, trace3]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.count_active_sessions()

        assert result == 1


class TestErrorBreakdown:
    """Tests for error breakdown by category."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_error_breakdown_by_metadata(self, mock_get_client):
        """Test error breakdown using metadata error_type."""
        mock_client = MagicMock()
        mock_response = MagicMock()

        trace1 = MagicMock()
        trace1.status = "ERROR"
        trace1.metadata = {"error_type": "timeout"}

        trace2 = MagicMock()
        trace2.status = "ERROR"
        trace2.metadata = {"error_type": "timeout"}

        trace3 = MagicMock()
        trace3.status = "ERROR"
        trace3.metadata = {"error_type": "validation_error"}

        mock_response.data = [trace1, trace2, trace3]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_error_breakdown()

        assert result["timeout"] == 2
        assert result["validation_error"] == 1

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_error_breakdown_by_trace_name(self, mock_get_client):
        """Test error breakdown using trace name patterns."""
        mock_client = MagicMock()
        mock_response = MagicMock()

        trace1 = MagicMock()
        trace1.status = "ERROR"
        trace1.name = "api_call_timeout"
        trace1.metadata = {}

        trace2 = MagicMock()
        trace2.status = "ERROR"
        trace2.name = "rate_limit_exceeded"
        trace2.metadata = {}

        mock_response.data = [trace1, trace2]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_error_breakdown()

        assert result["timeout"] == 1
        assert result["rate_limit"] == 1

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_error_breakdown_no_errors(self, mock_get_client):
        """Test error breakdown when no errors exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.status = "OK"
        mock_response.data = [trace1]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_error_breakdown()

        assert result == {}

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_error_breakdown_no_traces(self, mock_get_client):
        """Test error breakdown when no traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_error_breakdown()

        assert result == {}


class TestToolMetrics:
    """Tests for tool-specific metrics collection."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_collect_tool_metrics(self, mock_get_client):
        """Test collecting metrics for a specific tool."""
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create 10 traces for tool_a
        traces = []
        for i in range(10):
            t = MagicMock()
            t.name = "tool_a_call"
            t.status = "OK" if i < 8 else "ERROR"
            t.duration = 100.0 + i * 10
            traces.append(t)

        # Add 5 traces for tool_b (should be filtered out)
        for _ in range(5):
            t = MagicMock()
            t.name = "tool_b_call"
            t.status = "OK"
            t.duration = 50.0
            traces.append(t)

        mock_response.data = traces
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_tool_metrics("tool_a")

        assert result["tool_name"] == "tool_a"
        assert result["call_count"] == 10
        assert result["error_count"] == 2
        assert result["success_rate"] == pytest.approx(0.8, rel=0.01)
        assert result["p50_latency_ms"] > 0
        assert result["p95_latency_ms"] > 0
        assert result["p99_latency_ms"] > 0

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_collect_tool_metrics_no_matching_traces(self, mock_get_client):
        """Test collecting metrics when tool has no traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.name = "other_tool"
        trace1.status = "OK"
        trace1.duration = 100.0
        mock_response.data = [trace1]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_tool_metrics("nonexistent_tool")

        assert result["tool_name"] == "nonexistent_tool"
        assert result["call_count"] == 0
        assert result["success_rate"] == 1.0
        assert result["p50_latency_ms"] == 0.0

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_collect_tool_metrics_no_traces(self, mock_get_client):
        """Test collecting metrics when no traces at all."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        result = collector.collect_tool_metrics("any_tool")

        assert result["call_count"] == 0
        assert result["success_rate"] == 1.0


class TestMetricsCollectorIntegration:
    """Integration tests for all new metrics together."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_all_latency_percentiles(self, mock_get_client):
        """Test that P50 < P95 < P99 always holds."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        traces = []
        for i in range(100):
            t = MagicMock()
            t.duration = float(i + 1)
            traces.append(t)
        mock_response.data = traces
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        p50 = collector.collect_latency_p50()
        p95 = collector.collect_latency_p95()
        p99 = collector.collect_latency_p99()

        assert p50 < p95 < p99
