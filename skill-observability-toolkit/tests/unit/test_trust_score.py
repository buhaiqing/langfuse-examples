"""Tests for Trust Score Calculator."""

import pytest
from skill_observability_toolkit.stop.trust_score import TrustScoreCalculator, TrustScoreConfig


def test_trust_score_calculator_initialization():
    """Test TrustScoreCalculator can be initialized."""
    config = TrustScoreConfig(window_size=30)
    calculator = TrustScoreCalculator(config)
    assert calculator.config.window_size == 30


def test_trust_score_calculation_basic():
    """Test basic trust score calculation."""
    config = TrustScoreConfig(window_size=10, min_samples=5)
    calculator = TrustScoreCalculator(config)

    # Add 8 passing, 2 failing checks
    for _ in range(8):
        calculator.record_check(passed=True)
    for _ in range(2):
        calculator.record_check(passed=False)

    score = calculator.get_current_score()
    assert abs(score - 0.8) < 0.01


def test_trust_score_neutral_when_insufficient_samples():
    """Test trust score returns 0.5 when not enough samples."""
    config = TrustScoreConfig(window_size=10, min_samples=5)
    calculator = TrustScoreCalculator(config)

    # Add only 3 checks (less than min_samples)
    for _ in range(3):
        calculator.record_check(passed=True)

    score = calculator.get_current_score()
    assert score == 0.5


def test_trust_score_with_weights():
    """Test trust score with weighted checks."""
    config = TrustScoreConfig(window_size=10, min_samples=2)
    calculator = TrustScoreCalculator(config)

    calculator.record_check(passed=True, weight=2.0)
    calculator.record_check(passed=False, weight=1.0)

    # Weighted: 2 passing, 1 failing = 2/3 = 0.667
    score = calculator.get_current_score()
    assert abs(score - 0.667) < 0.01


def test_trust_score_reset():
    """Test trust score reset clears all data."""
    config = TrustScoreConfig(window_size=10, min_samples=5)
    calculator = TrustScoreCalculator(config)

    # Add checks
    for _ in range(10):
        calculator.record_check(passed=True)

    assert calculator.get_current_score() > 0.5

    calculator.reset()

    # Should return neutral score after reset
    assert calculator.get_current_score() == 0.5


def test_trust_score_get_stats():
    """Test get_stats returns correct statistics."""
    config = TrustScoreConfig(window_size=10, min_samples=5)
    calculator = TrustScoreCalculator(config)

    for _ in range(7):
        calculator.record_check(passed=True)
    for _ in range(3):
        calculator.record_check(passed=False)

    stats = calculator.get_stats()

    assert stats["total_checks"] == 10
    assert stats["passing_checks"] == 7
    assert stats["failing_checks"] == 3
    assert abs(stats["current_score"] - 0.7) < 0.01
    assert stats["min_samples_required"] == 5
