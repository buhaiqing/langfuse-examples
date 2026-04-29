"""
Global pytest fixtures for MCP with Tracing project.

Provides auto-mocking for external dependencies (Langfuse, ML libraries)
to ensure tests can run without network connectivity or API keys.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_langfuse_client():
    """
    Automatically mock Langfuse client for all tests.

    This fixture patches the global Langfuse client instance to prevent
    tests from making real API calls. Tests that need real API connectivity
    should use @pytest.mark.requires_api decorator.

    Yields:
        MagicMock: The mocked Langfuse client.
    """
    mock_client = MagicMock()

    # Mock trace context manager
    mock_trace = MagicMock()
    mock_trace.__enter__ = MagicMock(return_value=mock_trace)
    mock_trace.__exit__ = MagicMock(return_value=False)
    mock_client.trace.return_value = mock_trace

    # Mock span context manager
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_client.start_as_current_observation.return_value = mock_span

    # Mock API methods
    mock_client.get_traces.return_value = MagicMock(data=[])
    mock_client.score_current_trace.return_value = None

    with patch(
        "src.observability.instrumentation._langfuse_client",
        mock_client,
    ):
        yield mock_client


@pytest.fixture
def mock_prophet_model():
    """
    Mock Prophet time series forecasting model.

    Returns:
        MagicMock: Mocked Prophet model with predict() method.
    """
    import pandas as pd

    mock_model = MagicMock()

    # Mock predict to return empty DataFrame with expected columns
    mock_prediction = pd.DataFrame(
        {
            "ds": pd.date_range("2024-01-01", periods=10, freq="h"),
            "yhat": [0.5] * 10,
            "yhat_lower": [0.4] * 10,
            "yhat_upper": [0.6] * 10,
        }
    )
    mock_model.predict.return_value = mock_prediction
    mock_model.fit.return_value = mock_model

    return mock_model


@pytest.fixture
def mock_pyod_detector():
    """
    Mock PyOD anomaly detector (Isolation Forest, LOF).

    Returns:
        MagicMock: Mocked PyOD detector with fit() and predict() methods.
    """
    import numpy as np

    mock_detector = MagicMock()

    # Mock predict to return normal labels (0 = normal, 1 = anomaly)
    mock_detector.fit.return_value = mock_detector
    mock_detector.predict.return_value = np.zeros(10)
    mock_detector.decision_function.return_value = np.zeros(10)

    return mock_detector


@pytest.fixture
def mock_feedback_collector():
    """
    Mock FeedbackCollector to prevent real database/file operations.

    Returns:
        MagicMock: Mocked feedback collector.
    """
    mock_collector = MagicMock()
    mock_collector.get_average_rating.return_value = 4.2
    mock_collector.get_feedback_count.return_value = 100
    mock_collector.get_rating_distribution.return_value = {
        1: 5,
        2: 10,
        3: 20,
        4: 35,
        5: 30,
    }

    with patch(
        "src.observability.feedback.get_feedback_collector",
        return_value=mock_collector,
    ):
        yield mock_collector


@pytest.fixture
def sample_trace_data():
    """
    Provide sample trace data for testing.

    Returns:
        list[MagicMock]: List of mock trace objects with common attributes.
    """
    traces = []
    for i in range(10):
        trace = MagicMock()
        trace.id = f"trace_{i}"
        trace.status = "OK" if i < 8 else "ERROR"  # 80% success rate
        trace.duration = 100 + i * 50  # 100ms to 550ms
        trace.session_id = "test_session"
        trace.user_id = "test_user"
        trace.timestamp = f"2024-01-01T00:{i:02d}:00Z"
        traces.append(trace)

    return traces


@pytest.fixture
def sample_anomaly_result():
    """
    Provide sample anomaly detection result.

    Returns:
        dict: Sample univariate anomaly result.
    """
    from src.observability.alerting import AlertSeverity

    return {
        "type": "univariate",
        "metric": "success_rate",
        "current_value": 0.65,
        "expected_range": [0.85, 0.95],
        "deviation_score": 2.8,
        "severity": AlertSeverity.WARNING,
    }


@pytest.fixture
def sample_multivariate_anomaly():
    """
    Provide sample multivariate anomaly detection result.

    Returns:
        dict: Sample multivariate anomaly result.
    """
    from src.observability.alerting import AlertSeverity

    return {
        "type": "multivariate",
        "anomaly_score": 0.92,
        "features": {
            "success_rate": 0.65,
            "latency_p95": 450.0,
            "request_rate": 15.5,
            "satisfaction": 2.8,
        },
        "severity": AlertSeverity.CRITICAL,
    }


def pytest_configure(config):
    """
    Register custom pytest markers.

    Adds @pytest.mark.requires_api marker for tests that need real API access.
    """
    config.addinivalue_line(
        "markers",
        "requires_api: marks tests as requiring real API access (deselect with '-m \"not requires_api\"')",
    )
