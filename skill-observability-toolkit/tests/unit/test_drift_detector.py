"""Tests for Drift Detector."""

import pytest
from skill_observability_toolkit.integrations.drift_detector import (
    DriftDetector,
    DriftMethod,
    DriftResult,
    DriftStats,
    DriftStatus,
)


def test_drift_result_is_valid():
    """Test DriftResult.has_drift property."""
    result = DriftResult(
        status=DriftStatus.DRIFT_DETECTED,
        method=DriftMethod.PSI,
        statistic=0.3,
        threshold=0.25,
    )
    assert result.has_drift is True

    result = DriftResult(
        status=DriftStatus.NO_DRIFT,
        method=DriftMethod.PSI,
        statistic=0.05,
        threshold=0.25,
    )
    assert result.has_drift is False


def test_drift_stats_drift_rate():
    """Test DriftStats.drift_rate property."""
    stats = DriftStats(total_tests=10, detections=3)
    assert stats.drift_rate == 30.0

    stats = DriftStats(total_tests=0)
    assert stats.drift_rate == 0.0


def test_drift_detector_initialization():
    """Test DriftDetector can be initialized."""
    detector = DriftDetector()
    assert detector is not None
    assert detector.warning_threshold == 0.1
    assert detector.drift_threshold == 0.25
    assert detector.alpha == 0.05


def test_set_baseline():
    """Test setting baseline data."""
    detector = DriftDetector()
    baseline = [1.0, 2.0, 3.0, 4.0, 5.0]

    detector.set_baseline("feature1", baseline)
    assert detector.get_baseline("feature1") == baseline


def test_get_baseline_not_exists():
    """Test getting non-existent baseline."""
    detector = DriftDetector()
    assert detector.get_baseline("nonexistent") is None


def test_detect_empty_data():
    """Test drift detection with empty data."""
    detector = DriftDetector()
    result = detector.detect([], [1.0, 2.0, 3.0])

    assert result.status == DriftStatus.ERROR
    assert "error" in result.details


def test_detect_psi_no_drift():
    """Test PSI drift detection - no drift."""
    detector = DriftDetector()
    baseline = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5] * 10
    current = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5] * 10

    result = detector.detect(baseline, current, method=DriftMethod.PSI)

    assert result.method == DriftMethod.PSI
    assert result.status in [DriftStatus.NO_DRIFT, DriftStatus.WARNING]


def test_detect_psi_drift():
    """Test PSI drift detection - significant drift."""
    detector = DriftDetector()
    baseline = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5] * 20
    current = [5.0, 5.1, 5.2, 5.3, 5.4, 5.5] * 20

    result = detector.detect(baseline, current, method=DriftMethod.PSI)

    assert result.has_drift or result.status == DriftStatus.WARNING


def test_detect_ks_test():
    """Test KS-test drift detection."""
    detector = DriftDetector()
    baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
    current = [1.0, 2.0, 3.0, 4.0, 5.0] * 10

    result = detector.detect(baseline, current, method=DriftMethod.KS_TEST)

    assert result.method == DriftMethod.KS_TEST
    assert result.p_value is not None


def test_detect_chi_square():
    """Test Chi-square drift detection."""
    detector = DriftDetector()
    baseline = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 10
    current = baseline.copy()

    result = detector.detect(baseline, current, method=DriftMethod.CHI_SQUARE)

    assert result.method == DriftMethod.CHI_SQUARE
    assert result.p_value is not None


def test_detect_euclidean():
    """Test Euclidean distance drift detection."""
    detector = DriftDetector()
    baseline = [10.0] * 100
    current = [10.5] * 100

    result = detector.detect(baseline, current, method=DriftMethod.EUCLIDEAN)

    assert result.method == DriftMethod.EUCLIDEAN
    assert result.statistic >= 0.0


def test_detect_unknown_method():
    """Test drift detection with unknown method."""
    detector = DriftDetector()

    from enum import Enum

    class FakeMethod(Enum):
        FAKE = "fake"

    result = detector.detect([1.0, 2.0], [3.0, 4.0], method=FakeMethod.FAKE)

    assert result.status == DriftStatus.ERROR
    assert "error" in result.details


def test_get_stats():
    """Test getting drift statistics."""
    detector = DriftDetector()
    detector.detect([1.0, 2.0], [1.0, 2.0])
    detector.detect([1.0, 2.0], [5.0, 6.0])

    stats = detector.get_stats()

    assert isinstance(stats, DriftStats)
    assert stats.total_tests >= 0


def test_reset_stats():
    """Test resetting statistics."""
    detector = DriftDetector()
    detector.detect([1.0, 2.0], [1.0, 2.0])
    detector.reset_stats()

    stats = detector.get_stats()
    assert stats.total_tests == 0
    assert stats.detections == 0


def test_clear_baseline_specific():
    """Test clearing specific baseline."""
    detector = DriftDetector()
    detector.set_baseline("f1", [1.0, 2.0])
    detector.set_baseline("f2", [3.0, 4.0])

    detector.clear_baseline("f1")

    assert detector.get_baseline("f1") is None
    assert detector.get_baseline("f2") is not None


def test_clear_baseline_all():
    """Test clearing all baselines."""
    detector = DriftDetector()
    detector.set_baseline("f1", [1.0, 2.0])
    detector.set_baseline("f2", [3.0, 4.0])

    detector.clear_baseline()

    assert len(detector._baseline) == 0


def test_psi_interpretation():
    """Test PSI value interpretation."""
    detector = DriftDetector()

    assert "No significant drift" in detector._interpret_psi(0.05)
    assert "drift" in detector._interpret_psi(0.15).lower()
    assert "Significant drift" in detector._interpret_psi(0.3)


def test_ks_test_same_distribution():
    """Test KS-test with identical distributions."""
    detector = DriftDetector()
    data = [1.0, 2.0, 3.0, 4.0, 5.0] * 20

    statistic, p_value = detector._ks_test(data, data)

    assert statistic == 0.0
    assert p_value == 1.0


def test_chi_square_same_distribution():
    """Test Chi-square with identical distributions."""
    detector = DriftDetector()
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 20

    statistic, p_value = detector._chi_square_test(data, data)

    assert p_value > 0.05


def test_detect_with_exception_handling():
    """Test drift detection exception handling."""
    detector = DriftDetector()

    result = detector.detect([None], [None])

    assert result.status == DriftStatus.ERROR
    assert "error" in result.details


def test_custom_thresholds():
    """Test detector with custom thresholds."""
    detector = DriftDetector(warning_threshold=0.05, drift_threshold=0.15, alpha=0.01)

    assert detector.warning_threshold == 0.05
    assert detector.drift_threshold == 0.15
    assert detector.alpha == 0.01


def test_drift_result_with_p_value():
    """Test DriftResult with p-value."""
    result = DriftResult(
        status=DriftStatus.DRIFT_DETECTED,
        method=DriftMethod.KS_TEST,
        statistic=0.5,
        threshold=0.05,
        p_value=0.001,
    )

    assert result.has_drift is True
    assert result.p_value == 0.001
    assert result.details == {}
