"""
Integration tests for feedback collection and Langfuse integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.observability.feedback import (
    FeedbackType,
    FeedbackCollector,
    get_feedback_collector,
)
from src.observability.langfuse_client import LangfuseObserver


class TestFeedbackLangfuseIntegration:
    """Test feedback integration with Langfuse."""

    def setup_method(self):
        """Setup fresh collector for each test."""
        self.collector = FeedbackCollector()

    @patch("src.observability.langfuse_client.Langfuse")
    @pytest.mark.integration
    def test_acceptance_sent_to_langfuse(self, mock_langfuse_class):
        """Test that acceptance feedback is sent to Langfuse."""
        # Setup mock
        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        # Create observer with mocked client
        from src.observability.config import ObservabilityConfig
        config = ObservabilityConfig(
            langfuse_public_key="test_key",
            langfuse_secret_key="test_secret",
            enabled=True,
        )
        observer = LangfuseObserver(config)

        # Record acceptance
        feedback = self.collector.record_acceptance(
            trace_id="trace-123",
            user_id="user-456",
            comment="Great!",
            send_to_langfuse=False,  # Don't auto-send in this test
        )

        # Manually send to Langfuse
        observer.record_feedback_to_langfuse(
            trace_id=feedback.trace_id,
            feedback_type=FeedbackType.ACCEPT,
            value=1,
            user_id=feedback.user_id,
            comment=feedback.comment,
            metadata=feedback.metadata,
        )

        # Verify score was called
        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["name"] == "user-feedback"
        assert call_kwargs["value"] == 1.0
        assert call_kwargs["comment"] == "Great!"

    @patch("src.observability.langfuse_client.Langfuse")
    @pytest.mark.integration
    def test_rejection_sent_to_langfuse(self, mock_langfuse_class):
        """Test that rejection feedback is sent to Langfuse."""
        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        from src.observability.config import ObservabilityConfig
        config = ObservabilityConfig(
            langfuse_public_key="test_key",
            langfuse_secret_key="test_secret",
            enabled=True,
        )
        observer = LangfuseObserver(config)

        feedback = self.collector.record_rejection(
            trace_id="trace-124",
            user_id="user-456",
            reason="inaccurate",
            comment="Wrong info",
            send_to_langfuse=False,
        )

        observer.record_feedback_to_langfuse(
            trace_id=feedback.trace_id,
            feedback_type=FeedbackType.REJECT,
            value=0,
            user_id=feedback.user_id,
            comment=feedback.comment,
            metadata=feedback.metadata,
        )

        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args[1]
        assert call_kwargs["trace_id"] == "trace-124"
        assert call_kwargs["name"] == "user-feedback"
        assert call_kwargs["value"] == 0.0
        assert call_kwargs["metadata"]["rejection_reason"] == "inaccurate"

    @patch("src.observability.langfuse_client.Langfuse")
    @pytest.mark.integration
    def test_rating_sent_to_langfuse(self, mock_langfuse_class):
        """Test that rating feedback is sent to Langfuse."""
        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        from src.observability.config import ObservabilityConfig
        config = ObservabilityConfig(
            langfuse_public_key="test_key",
            langfuse_secret_key="test_secret",
            enabled=True,
        )
        observer = LangfuseObserver(config)

        feedback = self.collector.record_rating(
            trace_id="trace-125",
            rating=4,
            user_id="user-456",
            scale=5,
            send_to_langfuse=False,
        )

        observer.record_feedback_to_langfuse(
            trace_id=feedback.trace_id,
            feedback_type=FeedbackType.RATING,
            value=4,
            user_id=feedback.user_id,
            metadata=feedback.metadata,
        )

        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args[1]
        assert call_kwargs["trace_id"] == "trace-125"
        assert call_kwargs["name"] == "user-satisfaction"
        assert call_kwargs["value"] == 4.0

    @patch("src.observability.langfuse_client.Langfuse")
    @pytest.mark.integration
    def test_comment_sent_to_langfuse(self, mock_langfuse_class):
        """Test that comment feedback is sent to Langfuse."""
        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        from src.observability.config import ObservabilityConfig
        config = ObservabilityConfig(
            langfuse_public_key="test_key",
            langfuse_secret_key="test_secret",
            enabled=True,
        )
        observer = LangfuseObserver(config)

        feedback = self.collector.record_comment(
            trace_id="trace-126",
            comment="Very helpful response",
            user_id="user-456",
            send_to_langfuse=False,
        )

        observer.record_feedback_to_langfuse(
            trace_id=feedback.trace_id,
            feedback_type=FeedbackType.COMMENT,
            value=None,
            user_id=feedback.user_id,
            comment=feedback.comment,
            metadata=feedback.metadata,
        )

        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args[1]
        assert call_kwargs["trace_id"] == "trace-126"
        assert call_kwargs["name"] == "user-comment"
        assert call_kwargs["value"] == 1.0
        assert call_kwargs["comment"] == "Very helpful response"

    @pytest.mark.integration

    def test_score_trace_without_client(self):
        """Test scoring when Langfuse client is not initialized."""
        with patch("src.observability.langfuse_client.get_langfuse_client", return_value=None):
            observer = LangfuseObserver()

            observer.score_trace(
                trace_id="trace-123",
                name="test-score",
                value=1,
            )

    @pytest.mark.integration

    def test_record_feedback_without_client(self):
        """Test recording feedback when Langfuse client is not initialized."""
        with patch("src.observability.langfuse_client.get_langfuse_client", return_value=None):
            observer = LangfuseObserver()

            observer.record_feedback_to_langfuse(
                trace_id="trace-123",
                feedback_type=FeedbackType.ACCEPT,
                value=1,
            )

    @patch("src.observability.langfuse_client.Langfuse")
    @pytest.mark.integration
    def test_score_trace_error_handling(self, mock_langfuse_class):
        """Test error handling when scoring fails."""
        mock_client = Mock()
        mock_client.score.side_effect = Exception("API Error")
        mock_langfuse_class.return_value = mock_client

        from src.observability.config import ObservabilityConfig
        config = ObservabilityConfig(
            langfuse_public_key="test_key",
            langfuse_secret_key="test_secret",
            enabled=True,
        )
        observer = LangfuseObserver(config)

        # Should not raise exception, just print error
        observer.score_trace(
            trace_id="trace-123",
            name="test-score",
            value=1,
        )

        mock_client.score.assert_called_once()


class TestFeedbackFunctions:
    """Test feedback core functions."""

    @pytest.mark.integration

    def test_record_acceptance_function(self):
        """Test record_acceptance function."""
        from src.observability.feedback import record_acceptance

        feedback = record_acceptance(
            trace_id="trace-123",
            user_id="test-user",
            comment="Great response!",
            send_to_langfuse=False,
        )

        assert feedback.trace_id == "trace-123"
        assert feedback.feedback_type.value == "accept"
        assert feedback.comment == "Great response!"

    @pytest.mark.integration

    def test_record_rejection_function(self):
        """Test record_rejection function."""
        from src.observability.feedback import record_rejection

        feedback = record_rejection(
            trace_id="trace-124",
            user_id="test-user",
            reason="inaccurate",
            comment="Wrong information",
            send_to_langfuse=False,
        )

        assert feedback.trace_id == "trace-124"
        assert feedback.feedback_type.value == "reject"
        assert feedback.metadata["rejection_reason"] == "inaccurate"

    @pytest.mark.integration

    def test_record_rating_function(self):
        """Test record_rating function."""
        from src.observability.feedback import record_rating

        feedback = record_rating(
            trace_id="trace-125",
            rating=4,
            user_id="test-user",
            comment="Good response",
            send_to_langfuse=False,
        )

        assert feedback.trace_id == "trace-125"
        assert feedback.feedback_type.value == "rating"
        assert feedback.value == 4

    @pytest.mark.integration

    def test_record_comment_function(self):
        """Test record_comment function."""
        from src.observability.feedback import record_comment

        feedback = record_comment(
            trace_id="trace-127",
            comment="This was very helpful",
            user_id="test-user",
            send_to_langfuse=False,
        )

        assert feedback.trace_id == "trace-127"
        assert feedback.feedback_type.value == "comment"
        assert feedback.comment == "This was very helpful"


class TestFeedbackStatistics:
    """Test feedback statistics and aggregation."""

    @pytest.mark.integration

    def test_comprehensive_statistics(self):
        """Test comprehensive feedback statistics."""
        collector = FeedbackCollector()

        # Add various types of feedback
        collector.record_acceptance("trace-1")
        collector.record_acceptance("trace-2")
        collector.record_rejection("trace-3")
        collector.record_rejection("trace-4", reason="inaccurate")
        collector.record_rating("trace-5", 4)
        collector.record_rating("trace-6", 5)
        collector.record_comment("trace-7", "Great!")

        stats = collector.get_feedback_statistics()

        assert stats["total_feedback"] == 7
        assert stats["acceptance_rate"] == 50.0  # 2 accepts out of 4 scored
        assert stats["accepts"] == 2
        assert stats["rejects"] == 2
        assert stats["ratings_count"] == 2
        assert stats["comments_count"] == 1
        assert stats["average_rating"] == 4.5

    @pytest.mark.integration

    def test_empty_statistics(self):
        """Test statistics with no feedback."""
        collector = FeedbackCollector()
        stats = collector.get_feedback_statistics()

        assert stats["total_feedback"] == 0
        assert stats["acceptance_rate"] == 100.0
        assert stats["accepts"] == 0
        assert stats["rejects"] == 0
        assert stats["ratings_count"] == 0
        assert stats["comments_count"] == 0
        assert "average_rating" not in stats

    @pytest.mark.integration

    def test_rating_distribution(self):
        """Test rating distribution calculation."""
        collector = FeedbackCollector()

        collector.record_rating("trace-1", 1)
        collector.record_rating("trace-2", 2)
        collector.record_rating("trace-3", 3)
        collector.record_rating("trace-4", 4)
        collector.record_rating("trace-5", 5)
        collector.record_rating("trace-6", 4)
        collector.record_rating("trace-7", 5)

        stats = collector.get_feedback_statistics()

        assert "rating_distribution" in stats
        assert stats["rating_distribution"]["1"] == 1
        assert stats["rating_distribution"]["2"] == 1
        assert stats["rating_distribution"]["3"] == 1
        assert stats["rating_distribution"]["4"] == 2
        assert stats["rating_distribution"]["5"] == 2
