"""
Tests for MetricsCollector and LangfuseObserver fixes.

Covers:
- MetricsCollector uses get_langfuse_client() (not self._langfuse.client.trace.list())
- MetricsCollector uses client.get_traces() (correct API chain)
- LangfuseObserver uses shared client from get_langfuse_client()
- LangfuseObserver.trace_tool_call creates real trace+span
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.observability.metrics_collector import MetricsCollector, MetricPoint
from src.observability.langfuse_client import LangfuseObserver, get_observer, init_observer
from src.observability.session import clear_session


class TestMetricsCollectorClientUsage:
    """Tests that MetricsCollector uses the shared Langfuse client correctly."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_uses_shared_client_not_own_instance(self, mock_get_client):
        """Test MetricsCollector uses get_langfuse_client() instead of creating its own."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector(window_minutes=10)
        result = collector.collect_success_rate()

        mock_get_client.assert_called()
        mock_client.get_traces.assert_called_once()

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_uses_get_traces_not_client_trace_list(self, mock_get_client):
        """Test MetricsCollector calls client.get_traces() not client.trace.list().

        This is the fix for the API call chain bug:
        OLD (broken): self._langfuse.client.trace.list()
        NEW (correct): client.get_traces()
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()
        collector.collect_success_rate()

        mock_client.get_traces.assert_called_once()
        mock_client.trace.assert_not_called()

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_returns_empty_when_no_client(self, mock_get_client):
        """Test MetricsCollector handles missing client gracefully."""
        mock_get_client.return_value = None

        collector = MetricsCollector()

        assert collector.collect_success_rate() == 1.0
        assert collector.collect_latency_p95() == 0.0
        assert collector.collect_request_rate() == 0.0

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_handles_api_exception_gracefully(self, mock_get_client):
        """Test MetricsCollector handles API exceptions without crashing."""
        mock_client = MagicMock()
        mock_client.get_traces.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()

        assert collector.collect_success_rate() == 1.0
        assert collector.collect_latency_p95() == 0.0
        assert collector.collect_request_rate() == 0.0


class TestMetricsCollectorSuccessRate:
    """Tests for success rate calculation."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_success_rate_all_success(self, mock_get_client):
        """Test success rate when all traces succeeded."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.status = "OK"
        trace2 = MagicMock()
        trace2.status = "OK"
        mock_response.data = [trace1, trace2]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()
        result = collector.collect_success_rate()

        assert result == 1.0

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_success_rate_with_errors(self, mock_get_client):
        """Test success rate when some traces have errors."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.status = "OK"
        trace2 = MagicMock()
        trace2.status = "ERROR"
        trace3 = MagicMock()
        trace3.status = "OK"
        trace4 = MagicMock()
        trace4.status = "ERROR"
        mock_response.data = [trace1, trace2, trace3, trace4]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()
        result = collector.collect_success_rate()

        assert result == 0.5

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_success_rate_empty_traces(self, mock_get_client):
        """Test success rate with no traces returns 1.0 (no errors)."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()
        result = collector.collect_success_rate()

        assert result == 1.0


class TestMetricsCollectorLatency:
    """Tests for latency calculation."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_latency_p95_calculation(self, mock_get_client):
        """Test P95 latency calculation."""
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

        collector = MetricsCollector()
        result = collector.collect_latency_p95()

        assert result > 0
        assert result == pytest.approx(95.05, rel=0.01)

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_latency_p95_no_durations(self, mock_get_client):
        """Test P95 latency with traces that have no duration."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        trace1 = MagicMock()
        trace1.duration = None
        mock_response.data = [trace1]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()
        result = collector.collect_latency_p95()

        assert result == 0.0


class TestMetricsCollectorRequestRate:
    """Tests for request rate calculation."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_request_rate_calculation(self, mock_get_client):
        """Test QPS calculation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock() for _ in range(60)]
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector(window_minutes=10)
        result = collector.collect_request_rate()

        expected_qps = 60 / (10 * 60)
        assert result == pytest.approx(expected_qps)


class TestMetricsCollectorSatisfaction:
    """Tests for satisfaction score collection."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    @patch("src.observability.feedback.get_feedback_collector")
    def test_satisfaction_uses_feedback_collector(self, mock_get_fc, mock_get_client):
        """Test satisfaction uses FeedbackCollector instead of broken score API."""
        mock_collector = MagicMock()
        mock_collector.get_average_rating.return_value = 4.2
        mock_get_fc.return_value = mock_collector
        mock_get_client.return_value = MagicMock()

        collector = MetricsCollector()
        result = collector.collect_avg_satisfaction()

        assert result == 4.2
        mock_collector.get_average_rating.assert_called_once()

    @patch("src.observability.metrics_collector.get_langfuse_client")
    @patch("src.observability.feedback.get_feedback_collector")
    def test_satisfaction_returns_none_on_error(self, mock_get_fc, mock_get_client):
        """Test satisfaction returns None when feedback collector fails."""
        mock_get_fc.side_effect = Exception("No feedback")
        mock_get_client.return_value = MagicMock()

        collector = MetricsCollector()
        result = collector.collect_avg_satisfaction()

        assert result is None


class TestMetricsCollectorSessionFilter:
    """Tests for session-based filtering."""

    @patch("src.observability.metrics_collector.get_langfuse_client")
    def test_fetch_traces_with_session_id(self, mock_get_client):
        """Test _fetch_traces passes session_id to get_traces."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.get_traces.return_value = mock_response
        mock_get_client.return_value = mock_client

        collector = MetricsCollector()
        collector._fetch_traces(session_id="session-123")

        call_kwargs = mock_client.get_traces.call_args[1]
        assert call_kwargs["session_id"] == "session-123"


class TestLangfuseObserverSharedClient:
    """Tests that LangfuseObserver uses shared client."""

    def setup_method(self):
        clear_session()

    def teardown_method(self):
        clear_session()

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_observer_uses_shared_client_by_default(self, mock_get_client):
        """Test LangfuseObserver falls back to shared client when no config."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        assert observer.client is mock_client
        mock_get_client.assert_called()

    @patch("src.observability.langfuse_client.Langfuse")
    def test_observer_uses_own_client_with_config(self, mock_langfuse_cls):
        """Test LangfuseObserver uses dedicated client when config provided."""
        from src.observability.config import ObservabilityConfig

        mock_client = MagicMock()
        mock_langfuse_cls.return_value = mock_client

        config = ObservabilityConfig(
            enabled=True,
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        observer = LangfuseObserver(config)

        assert observer.client is mock_client
        mock_langfuse_cls.assert_called_once()

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_observer_client_returns_none_when_unavailable(self, mock_get_client):
        """Test observer.client returns None when no client available."""
        mock_get_client.return_value = None

        observer = LangfuseObserver()
        assert observer.client is None


class TestLangfuseObserverTraceToolCall:
    """Tests for LangfuseObserver.trace_tool_call creating real traces."""

    def setup_method(self):
        clear_session()

    def teardown_method(self):
        clear_session()

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_creates_trace_and_span(self, mock_get_client):
        """Test trace_tool_call creates a real Langfuse trace with span."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.__enter__ = Mock(return_value=mock_trace)
        mock_trace.__exit__ = Mock(return_value=False)
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_trace.span.return_value = mock_span
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        with observer.trace_tool_call(
            tool_name="test_tool",
            input_args={"x": 1},
            session_id="session-123",
            user_id="user-456",
        ) as span:
            pass

        mock_client.trace.assert_called_once()
        trace_kwargs = mock_client.trace.call_args[1]
        assert trace_kwargs["name"] == "test_tool"
        assert trace_kwargs["session_id"] == "session-123"
        assert trace_kwargs["user_id"] == "user-456"
        mock_trace.span.assert_called_once()

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_records_error(self, mock_get_client):
        """Test trace_tool_call records errors in span."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.__enter__ = Mock(return_value=mock_trace)
        mock_trace.__exit__ = Mock(return_value=False)
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_trace.span.return_value = mock_span
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        with pytest.raises(ValueError):
            with observer.trace_tool_call(
                tool_name="failing_tool",
                input_args={},
            ) as span:
                raise ValueError("Tool failed")

        mock_span.update.assert_called_once_with(
            level="ERROR",
            status_message="Tool failed",
        )

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_yields_none_when_no_client(self, mock_get_client):
        """Test trace_tool_call yields None when no client available."""
        mock_get_client.return_value = None

        observer = LangfuseObserver()
        with observer.trace_tool_call(
            tool_name="test_tool",
            input_args={},
        ) as span:
            assert span is None


class TestLangfuseObserverScoreTrace:
    """Tests for LangfuseObserver.score_trace."""

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_score_trace_calls_client_score(self, mock_get_client):
        """Test score_trace calls client.score() directly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        observer.score_trace(
            trace_id="trace-123",
            name="user-feedback",
            value=1.0,
            comment="Great",
        )

        mock_client.score.assert_called_once_with(
            trace_id="trace-123",
            name="user-feedback",
            value=1.0,
            comment="Great",
        )

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_score_trace_handles_error(self, mock_get_client):
        """Test score_trace handles errors gracefully."""
        mock_client = MagicMock()
        mock_client.score.side_effect = Exception("Score API error")
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        observer.score_trace(trace_id="trace-123", name="test", value=1.0)


class TestGetObserverSingleton:
    """Tests for get_observer/init_observer singleton."""

    def setup_method(self):
        import src.observability.langfuse_client as mod
        mod._observer = None

    def test_get_observer_creates_default(self):
        """Test get_observer creates a default observer."""
        observer = get_observer()
        assert isinstance(observer, LangfuseObserver)

    def test_get_observer_returns_same_instance(self):
        """Test get_observer returns the same instance."""
        obs1 = get_observer()
        obs2 = get_observer()
        assert obs1 is obs2

    @patch("src.observability.langfuse_client.Langfuse")
    def test_init_observer_creates_new_instance(self, mock_langfuse_cls):
        """Test init_observer creates a new observer with config."""
        from src.observability.config import ObservabilityConfig

        mock_client = MagicMock()
        mock_langfuse_cls.return_value = mock_client

        config = ObservabilityConfig(
            enabled=True,
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        observer = init_observer(config)

        assert isinstance(observer, LangfuseObserver)
        assert observer.client is mock_client
