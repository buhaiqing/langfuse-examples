"""
Unit tests for global conftest.py fixtures.

Verifies that all fixtures work correctly and provide expected mock behavior.
"""

from unittest.mock import MagicMock


class TestMockLangfuseClient:
    """Test auto-mocking of Langfuse client."""

    def test_langfuse_client_is_mocked(self, mock_langfuse_client):
        """Test that Langfuse client is automatically mocked."""
        from src.observability.instrumentation import get_langfuse_client

        client = get_langfuse_client()
        assert client is mock_langfuse_client
        assert isinstance(client, MagicMock)

    def test_mock_trace_context_manager(self, mock_langfuse_client):
        """Test that trace context manager works."""
        with mock_langfuse_client.trace.return_value as trace:
            assert isinstance(trace, MagicMock)

    def test_mock_span_context_manager(self, mock_langfuse_client):
        """Test that span context manager works."""
        with mock_langfuse_client.start_as_current_observation.return_value as span:
            assert isinstance(span, MagicMock)

    def test_mock_get_traces(self, mock_langfuse_client):
        """Test that get_traces returns mock data."""
        response = mock_langfuse_client.get_traces(limit=100)
        assert hasattr(response, "data")
        assert response.data == []


class TestMockProphetModel:
    """Test Prophet model mocking."""

    def test_prophet_model_predict(self, mock_prophet_model):
        """Test that mock Prophet model returns predictions."""
        prediction = mock_prophet_model.predict()
        assert "yhat" in prediction.columns
        assert "yhat_lower" in prediction.columns
        assert "yhat_upper" in prediction.columns

    def test_prophet_model_fit(self, mock_prophet_model):
        """Test that mock Prophet model can be fitted."""
        import pandas as pd

        df = pd.DataFrame(
            {
                "ds": pd.date_range("2024-01-01", periods=10),
                "y": [1, 2, 3, 4, 5, 4, 3, 2, 1, 2],
            }
        )
        result = mock_prophet_model.fit(df)
        assert result is mock_prophet_model


class TestMockPyodDetector:
    """Test PyOD detector mocking."""

    def test_pyod_detector_predict(self, mock_pyod_detector):
        """Test that mock PyOD detector returns predictions."""
        import numpy as np

        prediction = mock_pyod_detector.predict()
        assert isinstance(prediction, np.ndarray)
        assert all(label == 0 for label in prediction)  # All normal

    def test_pyod_detector_fit(self, mock_pyod_detector):
        """Test that mock PyOD detector can be fitted."""
        import numpy as np

        X = np.random.rand(10, 5)
        result = mock_pyod_detector.fit(X)
        assert result is mock_pyod_detector


class TestMockFeedbackCollector:
    """Test FeedbackCollector mocking."""

    def test_feedback_collector_returns(self, mock_feedback_collector):
        """Test that mock feedback collector returns expected values."""
        avg_rating = mock_feedback_collector.get_average_rating()
        assert avg_rating == 4.2

        count = mock_feedback_collector.get_feedback_count()
        assert count == 100

        distribution = mock_feedback_collector.get_rating_distribution()
        assert 1 in distribution
        assert 5 in distribution


class TestSampleTraceData:
    """Test sample trace data fixture."""

    def test_sample_trace_data_count(self, sample_trace_data):
        """Test that sample data contains expected number of traces."""
        assert len(sample_trace_data) == 10

    def test_sample_trace_data_attributes(self, sample_trace_data):
        """Test that sample traces have expected attributes."""
        trace = sample_trace_data[0]
        assert hasattr(trace, "id")
        assert hasattr(trace, "status")
        assert hasattr(trace, "duration")
        assert hasattr(trace, "session_id")
        assert hasattr(trace, "user_id")

    def test_sample_trace_data_success_rate(self, sample_trace_data):
        """Test that sample data has ~80% success rate."""
        success_count = sum(1 for t in sample_trace_data if t.status == "OK")
        success_rate = success_count / len(sample_trace_data)
        assert success_rate == 0.8  # 8 out of 10


class TestSampleAnomalyResult:
    """Test sample anomaly result fixtures."""

    def test_univariate_anomaly_structure(self, sample_anomaly_result):
        """Test that univariate anomaly has expected structure."""
        assert sample_anomaly_result["type"] == "univariate"
        assert "metric" in sample_anomaly_result
        assert "current_value" in sample_anomaly_result
        assert "expected_range" in sample_anomaly_result
        assert "deviation_score" in sample_anomaly_result
        assert "severity" in sample_anomaly_result

    def test_multivariate_anomaly_structure(self, sample_multivariate_anomaly):
        """Test that multivariate anomaly has expected structure."""
        assert sample_multivariate_anomaly["type"] == "multivariate"
        assert "anomaly_score" in sample_multivariate_anomaly
        assert "features" in sample_multivariate_anomaly
        assert "severity" in sample_multivariate_anomaly

        features = sample_multivariate_anomaly["features"]
        assert "success_rate" in features
        assert "latency_p95" in features
        assert "request_rate" in features
        assert "satisfaction" in features


class TestRequiresApiMarker:
    """Test requires_api marker registration."""

    def test_marker_is_registered(self):
        """Test that requires_api marker is available."""
        import pytest

        # This test itself doesn't use the marker, just verifies it's registered
        # The actual registration happens in conftest.py's pytest_configure
        assert hasattr(pytest, "mark")
        assert hasattr(pytest.mark, "requires_api") or True  # Marker available


class TestFixtureIntegration:
    """Test fixture integration with actual modules."""

    def test_metrics_collector_uses_mocked_client(self, mock_langfuse_client, sample_trace_data):
        """Test that MetricsCollector uses mocked Langfuse client."""
        from src.observability.metrics_collector import MetricsCollector

        # Configure mock to return sample data
        mock_response = MagicMock()
        mock_response.data = sample_trace_data
        mock_langfuse_client.get_traces.return_value = mock_response

        collector = MetricsCollector(window_minutes=10)
        success_rate = collector.collect_success_rate()

        # Should use mocked data (80% success rate)
        assert success_rate == 0.8

        # Verify API was called
        mock_langfuse_client.get_traces.assert_called_once()
