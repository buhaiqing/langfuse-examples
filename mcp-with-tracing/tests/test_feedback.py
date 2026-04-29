"""
Tests for feedback collection.
"""

import pytest

from src.observability.feedback import (
    FeedbackCollector,
    FeedbackType,
    get_acceptance_rate,
    get_feedback_collector,
    get_feedback_statistics,
    record_acceptance,
    record_rating,
    record_rejection,
)


class TestFeedbackCollector:
    """Tests for FeedbackCollector class."""

    def setup_method(self):
        """Create fresh collector for each test."""
        self.collector = FeedbackCollector()

    def test_record_acceptance(self):
        """Test recording acceptance."""
        feedback = self.collector.record_acceptance(
            trace_id="trace-123",
            user_id="user-456",
            comment="Great response!",
        )

        assert feedback.trace_id == "trace-123"
        assert feedback.feedback_type == FeedbackType.ACCEPT
        assert feedback.value == 1
        assert feedback.user_id == "user-456"
        assert feedback.comment == "Great response!"

    def test_record_rejection(self):
        """Test recording rejection."""
        feedback = self.collector.record_rejection(
            trace_id="trace-123",
            user_id="user-456",
            reason="inaccurate",
            comment="Wrong information",
        )

        assert feedback.trace_id == "trace-123"
        assert feedback.feedback_type == FeedbackType.REJECT
        assert feedback.value == 0
        assert feedback.metadata["rejection_reason"] == "inaccurate"

    def test_record_rating(self):
        """Test recording rating."""
        feedback = self.collector.record_rating(
            trace_id="trace-123",
            rating=4,
            user_id="user-456",
            scale=5,
        )

        assert feedback.trace_id == "trace-123"
        assert feedback.feedback_type == FeedbackType.RATING
        assert feedback.value == 4
        assert feedback.metadata["scale"] == 5

    def test_record_comment(self):
        """Test recording comment."""
        feedback = self.collector.record_comment(
            trace_id="trace-123",
            comment="This was helpful",
            user_id="user-456",
        )

        assert feedback.trace_id == "trace-123"
        assert feedback.feedback_type == FeedbackType.COMMENT
        assert feedback.comment == "This was helpful"
        assert feedback.value is None

    def test_get_feedback_for_trace(self):
        """Test getting feedback for specific trace."""
        self.collector.record_acceptance("trace-1")
        self.collector.record_rejection("trace-1")
        self.collector.record_acceptance("trace-2")

        feedback_trace_1 = self.collector.get_feedback_for_trace("trace-1")
        feedback_trace_2 = self.collector.get_feedback_for_trace("trace-2")

        assert len(feedback_trace_1) == 2
        assert len(feedback_trace_2) == 1

    def test_get_acceptance_rate(self):
        """Test acceptance rate calculation."""
        self.collector.record_acceptance("trace-1")
        self.collector.record_acceptance("trace-2")
        self.collector.record_rejection("trace-3")
        self.collector.record_rejection("trace-4")

        rate = self.collector.get_acceptance_rate()
        assert rate == 50.0

    def test_get_acceptance_rate_empty(self):
        """Test acceptance rate with no feedback."""
        rate = self.collector.get_acceptance_rate()
        assert rate == 100.0

    def test_get_average_rating(self):
        """Test average rating calculation."""
        self.collector.record_rating("trace-1", 3)
        self.collector.record_rating("trace-2", 4)
        self.collector.record_rating("trace-3", 5)

        avg = self.collector.get_average_rating()
        assert avg == 4.0

    def test_get_average_rating_none(self):
        """Test average rating with no ratings."""
        avg = self.collector.get_average_rating()
        assert avg is None

    def test_get_feedback_statistics(self):
        """Test comprehensive statistics."""
        self.collector.record_acceptance("trace-1")
        self.collector.record_rejection("trace-2")
        self.collector.record_rating("trace-3", 4)
        self.collector.record_comment("trace-4", "Nice!")

        stats = self.collector.get_feedback_statistics()

        assert stats["total_feedback"] == 4
        assert stats["acceptance_rate"] == 50.0
        assert stats["accepts"] == 1
        assert stats["rejects"] == 1
        assert stats["ratings_count"] == 1
        assert stats["comments_count"] == 1
        assert stats["average_rating"] == 4.0


class TestGlobalFeedbackCollector:
    """Tests for global feedback collector functions."""

    def test_get_feedback_collector_singleton(self):
        """Test that collector is singleton."""
        c1 = get_feedback_collector()
        c2 = get_feedback_collector()
        assert c1 is c2

    def test_record_acceptance_function(self):
        """Test global record_acceptance function."""
        collector = get_feedback_collector()
        initial_count = len(collector.get_all_feedback())

        record_acceptance("test-trace", "test-user")

        assert len(collector.get_all_feedback()) == initial_count + 1

    def test_record_rejection_function(self):
        """Test global record_rejection function."""
        collector = get_feedback_collector()
        initial_count = len(collector.get_all_feedback())

        record_rejection("test-trace", "test-user", "bad response")

        assert len(collector.get_all_feedback()) == initial_count + 1

    def test_record_rating_function(self):
        """Test global record_rating function."""
        collector = get_feedback_collector()
        initial_count = len(collector.get_all_feedback())

        record_rating("test-trace", 5, "test-user")

        assert len(collector.get_all_feedback()) == initial_count + 1

    def test_get_acceptance_rate_function(self):
        """Test global get_acceptance_rate function."""
        get_feedback_collector()._feedback.clear()

        record_acceptance("trace-1")
        record_acceptance("trace-2")
        record_rejection("trace-3")

        rate = get_acceptance_rate()
        assert rate == pytest.approx(66.67, rel=0.01)

    def test_get_feedback_statistics_function(self):
        """Test global get_feedback_statistics function."""
        get_feedback_collector()._feedback.clear()

        record_acceptance("trace-1")
        record_rejection("trace-2")

        stats = get_feedback_statistics()
        assert stats["total_feedback"] == 2
        assert stats["acceptance_rate"] == 50.0
