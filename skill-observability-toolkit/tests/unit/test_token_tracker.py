"""Tests for Token Tracker."""

import pytest
from skill_observability_toolkit.integrations.token_tracker import (
    LLMProvider,
    TokenStats,
    TokenTracker,
    TokenUsage,
)


def test_token_usage_initialization():
    """Test TokenUsage can be initialized."""
    usage = TokenUsage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost=0.006,
    )
    assert usage.provider == LLMProvider.OPENAI
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150


def test_token_tracker_initialization():
    """Test TokenTracker can be initialized."""
    tracker = TokenTracker()
    assert tracker is not None
    assert tracker.get_stats().request_count == 0


def test_record_usage():
    """Test recording token usage."""
    tracker = TokenTracker()
    usage = tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
    )

    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150
    assert usage.cost > 0


def test_cost_calculation_gpt4():
    """Test cost calculation for GPT-4."""
    tracker = TokenTracker()
    usage = tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    expected_cost = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
    assert abs(usage.cost - expected_cost) < 0.0001


def test_cost_calculation_claude():
    """Test cost calculation for Claude."""
    tracker = TokenTracker()
    usage = tracker.record_usage(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-opus",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    expected_cost = (1000 / 1000) * 0.015 + (500 / 1000) * 0.075
    assert abs(usage.cost - expected_cost) < 0.0001


def test_get_stats():
    """Test getting aggregated stats."""
    tracker = TokenTracker()
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
    )
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=200,
        completion_tokens=100,
    )

    stats = tracker.get_stats()
    assert stats.total_prompt_tokens == 300
    assert stats.total_completion_tokens == 150
    assert stats.total_tokens == 450
    assert stats.request_count == 2


def test_get_model_stats():
    """Test per-model statistics."""
    tracker = TokenTracker()
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
    )
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-3.5-turbo",
        prompt_tokens=200,
        completion_tokens=100,
    )

    model_stats = tracker.get_model_stats()
    assert len(model_stats) == 2
    assert "openai:gpt-4" in model_stats
    assert "openai:gpt-3.5-turbo" in model_stats


def test_get_top_models():
    """Test getting top models by usage."""
    tracker = TokenTracker()
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-3.5-turbo",
        prompt_tokens=100,
        completion_tokens=50,
    )

    top_models = tracker.get_top_models(limit=1)
    assert len(top_models) == 1
    assert top_models[0][0] == "openai:gpt-4"


def test_reset():
    """Test resetting tracker data."""
    tracker = TokenTracker()
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
    )

    tracker.reset()

    stats = tracker.get_stats()
    assert stats.total_tokens == 0
    assert stats.request_count == 0
    assert len(tracker.get_model_stats()) == 0


def test_estimate_quota_usage():
    """Test quota usage estimation."""
    tracker = TokenTracker()
    tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=500,
        completion_tokens=250,
    )

    quota_info = tracker.estimate_quota_usage(daily_quota=1000, current_usage=750)

    assert quota_info["quota"] == 1000
    assert quota_info["used"] == 750
    assert abs(quota_info["percentage"] - 75.0) < 0.1
    assert quota_info["remaining"] == 250
    assert not quota_info["exceeded"]


def test_quota_exceeded():
    """Test quota exceeded detection."""
    tracker = TokenTracker()

    quota_info = tracker.estimate_quota_usage(daily_quota=1000, current_usage=1200)

    assert quota_info["exceeded"] is True
    assert quota_info["remaining"] == 0


def test_unknown_model_cost():
    """Test cost calculation for unknown model."""
    tracker = TokenTracker()
    usage = tracker.record_usage(
        provider=LLMProvider.OPENAI,
        model="unknown-model",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    assert usage.cost == 0.0


def test_unknown_provider_cost():
    """Test cost calculation for unknown provider."""
    tracker = TokenTracker()

    from enum import Enum

    class FakeProvider(Enum):
        FAKE = "fake"

    usage = tracker.record_usage(
        provider=FakeProvider.FAKE,
        model="fake-model",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    assert usage.cost == 0.0


def test_token_stats_add_usage():
    """Test TokenStats.add_usage method."""
    stats = TokenStats()
    usage = TokenUsage(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost=0.006,
    )

    stats.add_usage(usage)

    assert stats.total_prompt_tokens == 100
    assert stats.total_completion_tokens == 50
    assert stats.total_tokens == 150
    assert abs(stats.total_cost - 0.006) < 0.0001
    assert stats.request_count == 1
