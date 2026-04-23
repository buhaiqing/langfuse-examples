"""
Data Drift Detector for monitoring data quality changes.

Provides statistical drift detection using multiple tests
(KS-test, Chi-square, population stability index).
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DriftStatus(Enum):
    """Drift detection status."""

    NO_DRIFT = "no_drift"
    WARNING = "warning"
    DRIFT_DETECTED = "drift_detected"
    ERROR = "error"


class DriftMethod(Enum):
    """Drift detection method."""

    KS_TEST = "ks_test"
    PSI = "psi"
    CHI_SQUARE = "chi_square"
    EUCLIDEAN = "euclidean"


@dataclass
class DriftResult:
    """Result of drift detection."""

    status: DriftStatus
    method: DriftMethod
    statistic: float
    threshold: float
    p_value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def has_drift(self) -> bool:
        """Check if drift was detected."""
        return self.status == DriftStatus.DRIFT_DETECTED


@dataclass
class DriftStats:
    """Aggregated drift detection statistics."""

    total_tests: int = 0
    detections: int = 0
    warnings: int = 0
    by_feature: dict[str, DriftResult] = field(default_factory=dict)

    @property
    def drift_rate(self) -> float:
        """Get drift detection rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.detections / self.total_tests) * 100


class DriftDetector:
    """
    Statistical drift detector for data quality monitoring.

    Detects changes in data distributions using various statistical
    tests including KS-test, PSI, and Chi-square.

    Example:
        detector = DriftDetector()
        baseline = [1.2, 1.5, 1.3, 1.4, 1.6, 1.2, 1.5, 1.3]
        current = [2.1, 2.3, 2.0, 2.2, 2.4, 2.1, 2.3, 2.0]
        
        result = detector.detect(baseline, current, method=DriftMethod.KS_TEST)
        if result.has_drift:
            print("Drift detected!")
    """

    def __init__(
        self,
        warning_threshold: float = 0.1,
        drift_threshold: float = 0.25,
        alpha: float = 0.05,
    ):
        """
        Initialize the drift detector.

        Args:
            warning_threshold: PSI threshold for warning (0.1 = 10%)
            drift_threshold: PSI threshold for drift (0.25 = 25%)
            alpha: Significance level for statistical tests
        """
        self.warning_threshold = warning_threshold
        self.drift_threshold = drift_threshold
        self.alpha = alpha
        self._baseline: dict[str, list[float]] = {}
        self._stats = DriftStats()

    def set_baseline(self, name: str, data: list[float]):
        """
        Set baseline data for comparison.

        Args:
            name: Feature name
            data: Baseline data points
        """
        self._baseline[name] = data

    def get_baseline(self, name: str) -> list[float] | None:
        """
        Get baseline data for a feature.

        Args:
            name: Feature name

        Returns:
            Baseline data or None
        """
        return self._baseline.get(name)

    def detect(
        self,
        baseline: list[float],
        current: list[float],
        method: DriftMethod = DriftMethod.PSI,
    ) -> DriftResult:
        """
        Detect drift between baseline and current data.

        Args:
            baseline: Baseline data
            current: Current data
            method: Drift detection method

        Returns:
            DriftResult with status and statistics
        """
        if not baseline or not current:
            return DriftResult(
                status=DriftStatus.ERROR,
                method=method,
                statistic=0.0,
                threshold=self.drift_threshold,
                details={"error": "Empty data"},
            )

        try:
            if method == DriftMethod.PSI:
                return self._detect_psi(baseline, current)
            elif method == DriftMethod.KS_TEST:
                return self._detect_ks_test(baseline, current)
            elif method == DriftMethod.CHI_SQUARE:
                return self._detect_chi_square(baseline, current)
            elif method == DriftMethod.EUCLIDEAN:
                return self._detect_euclidean(baseline, current)
            else:
                return DriftResult(
                    status=DriftStatus.ERROR,
                    method=method,
                    statistic=0.0,
                    threshold=self.drift_threshold,
                    details={"error": f"Unknown method: {method.value}"},
                )
        except Exception as e:
            return DriftResult(
                status=DriftStatus.ERROR,
                method=method,
                statistic=0.0,
                threshold=self.drift_threshold,
                details={"error": str(e)},
            )

    def _detect_psi(self, baseline: list[float], current: list[float]) -> DriftResult:
        """
        Detect drift using Population Stability Index.

        PSI < 0.1: No drift
        0.1 <= PSI < 0.25: Warning
        PSI >= 0.25: Drift detected
        """
        psi_value = self._calculate_psi(baseline, current)

        if psi_value >= self.drift_threshold:
            status = DriftStatus.DRIFT_DETECTED
        elif psi_value >= self.warning_threshold:
            status = DriftStatus.WARNING
        else:
            status = DriftStatus.NO_DRIFT

        self._stats.total_tests += 1
        if status == DriftStatus.DRIFT_DETECTED:
            self._stats.detections += 1
        elif status == DriftStatus.WARNING:
            self._stats.warnings += 1

        return DriftResult(
            status=status,
            method=DriftMethod.PSI,
            statistic=psi_value,
            threshold=self.drift_threshold,
            details={
                "warning_threshold": self.warning_threshold,
                "interpretation": self._interpret_psi(psi_value),
            },
        )

    def _detect_ks_test(
        self, baseline: list[float], current: list[float]
    ) -> DriftResult:
        """
        Detect drift using Kolmogorov-Smirnov test.

        Returns the maximum distance between empirical CDFs.
        """
        ks_statistic, p_value = self._ks_test(baseline, current)

        if p_value < self.alpha:
            status = DriftStatus.DRIFT_DETECTED
        else:
            status = DriftStatus.NO_DRIFT

        self._stats.total_tests += 1
        if status == DriftStatus.DRIFT_DETECTED:
            self._stats.detections += 1

        return DriftResult(
            status=status,
            method=DriftMethod.KS_TEST,
            statistic=ks_statistic,
            threshold=self.alpha,
            p_value=p_value,
            details={"significant": p_value < self.alpha},
        )

    def _detect_chi_square(
        self, baseline: list[float], current: list[float]
    ) -> DriftResult:
        """Detect drift using Chi-square test on binned data."""
        chi2_statistic, p_value = self._chi_square_test(baseline, current)

        if p_value < self.alpha:
            status = DriftStatus.DRIFT_DETECTED
        else:
            status = DriftStatus.NO_DRIFT

        self._stats.total_tests += 1
        if status == DriftStatus.DRIFT_DETECTED:
            self._stats.detections += 1

        return DriftResult(
            status=status,
            method=DriftMethod.CHI_SQUARE,
            statistic=chi2_statistic,
            threshold=self.alpha,
            p_value=p_value,
        )

    def _detect_euclidean(
        self, baseline: list[float], current: list[float]
    ) -> DriftResult:
        """Detect drift using Euclidean distance between means."""
        mean_baseline = sum(baseline) / len(baseline)
        mean_current = sum(current) / len(current)

        std_baseline = (
            math.sqrt(sum((x - mean_baseline) ** 2 for x in baseline) / len(baseline))
            if len(baseline) > 1
            else 1.0
        )

        distance = abs(mean_current - mean_baseline) / max(std_baseline, 1e-10)

        if distance >= self.drift_threshold:
            status = DriftStatus.DRIFT_DETECTED
        elif distance >= self.warning_threshold:
            status = DriftStatus.WARNING
        else:
            status = DriftStatus.NO_DRIFT

        self._stats.total_tests += 1
        if status == DriftStatus.DRIFT_DETECTED:
            self._stats.detections += 1

        return DriftResult(
            status=status,
            method=DriftMethod.EUCLIDEAN,
            statistic=distance,
            threshold=self.drift_threshold,
        )

    def _calculate_psi(self, expected: list[float], actual: list[float]) -> float:
        """Calculate Population Stability Index."""
        breakpoints = self._get_percentile_breakpoints(expected)
        expected_bins = self._bin_data(expected, breakpoints)
        actual_bins = self._bin_data(actual, breakpoints)

        psi = 0.0
        for exp_count, act_count in zip(expected_bins, actual_bins):
            exp_pct = (exp_count + 1e-10) / (len(expected) + 1e-10)
            act_pct = (act_count + 1e-10) / (len(actual) + 1e-10)
            psi += (act_pct - exp_pct) * math.log(act_pct / exp_pct)

        return psi

    def _get_percentile_breakpoints(self, data: list[float]) -> list[float]:
        """Get decile breakpoints for binning."""
        if len(data) < 10:
            # Use simple min/mid/max for small datasets
            return [min(data), (min(data) + max(data)) / 2, max(data)]

        sorted_data = sorted(data)
        return [sorted_data[min(int(len(data) * p / 10), len(sorted_data) - 1)] for p in range(11)]

    def _bin_data(self, data: list[float], breakpoints: list[float]) -> list[int]:
        """Bin data into intervals defined by breakpoints."""
        bins = [0] * (len(breakpoints) - 1)
        
        if len(breakpoints) < 2:
            return bins

        for value in data:
            for i in range(len(breakpoints) - 1):
                if breakpoints[i] <= value <= breakpoints[i + 1]:
                    bins[i] += 1
                    break
            else:
                # Handle edge case where value is exactly at max
                if value >= breakpoints[-1]:
                    bins[-1] += 1

        return bins

    def _ks_test(
        self, sample1: list[float], sample2: list[float]
    ) -> tuple[float, float]:
        """
        Two-sample Kolmogorov-Smirnov test.

        Returns (statistic, p-value).
        """
        sorted1 = sorted(sample1)
        sorted2 = sorted(sample2)

        all_values = sorted(set(sample1 + sample2))
        n1, n2 = len(sample1), len(sample2)

        max_diff = 0.0
        for val in all_values:
            cdf1 = sum(1 for x in sorted1 if x <= val) / n1
            cdf2 = sum(1 for x in sorted2 if x <= val) / n2
            diff = abs(cdf1 - cdf2)
            max_diff = max(max_diff, diff)

        n = (n1 * n2) / (n1 + n2)
        lambda_val = max_diff * math.sqrt(n)

        p_value = 2 * math.exp(-2 * lambda_val**2)
        p_value = min(1.0, max(0.0, p_value))

        return max_diff, p_value

    def _chi_square_test(
        self, expected: list[float], observed: list[float]
    ) -> tuple[float, float]:
        """Chi-square test on binned data."""
        breakpoints = self._get_percentile_breakpoints(expected)
        exp_bins = self._bin_data(expected, breakpoints)
        obs_bins = self._bin_data(observed, breakpoints)

        chi2 = 0.0
        for exp, obs in zip(exp_bins, obs_bins):
            if exp > 0:
                chi2 += ((obs - exp) ** 2) / exp

        df = len(exp_bins) - 1
        p_value = self._chi2_p_value(chi2, df)

        return chi2, p_value

    def _chi2_p_value(self, chi2: float, df: int) -> float:
        """Approximate p-value for chi-square distribution."""
        if df <= 0 or chi2 < 0:
            return 1.0

        x = chi2
        k = df / 2.0

        if x < k + 1:
            return self._series_expansion(x, k)
        else:
            return self._continued_fraction(x, k)

    def _series_expansion(self, x: float, k: float) -> float:
        """Series expansion for incomplete gamma function."""
        if k <= 0 or x < 0:
            return 1.0
            
        sum_val = 1.0 / k
        term = 1.0 / k
        for n in range(1, 200):
            term *= x / (k + n)
            sum_val += term
            if abs(term) < 1e-10:
                break

        try:
            return sum_val * math.exp(-x + k * math.log(x) - self._log_gamma(k))
        except (ValueError, OverflowError):
            return 1.0

    def _continued_fraction(self, x: float, k: float) -> float:
        """Continued fraction for incomplete gamma function."""
        b = x + 1 - k
        c = 1e30
        d = 1 / b
        h = d

        for i in range(1, 200):
            an = -i * (i - k)
            b += 2
            d = an * d + b
            if abs(d) < 1e-30:
                d = 1e-30
            c = b + an / c
            if abs(c) < 1e-30:
                c = 1e-30
            d = 1 / d
            delta = d * c
            h *= delta
            if abs(delta - 1) < 1e-10:
                break

        return 1 - h * math.exp(-x + k * math.log(x) - self._log_gamma(k))

    def _log_gamma(self, x: float) -> float:
        """Log gamma function approximation (Stirling's formula)."""
        if x <= 0:
            return 0.0
        
        if x < 0.001:
            return -math.log(x)

        c = [
            76.18009172947146,
            -86.50532032941677,
            24.01409824083091,
            -1.231739572450155,
            0.1208650973866179e-2,
            -0.5395239384953e-5,
        ]

        tmp = x + 5.5
        tmp -= (x + 0.5) * math.log(tmp)

        ser = 1.000000000190015
        for j in range(6):
            ser += c[j] / (x + j + 1)

        return -tmp + math.log(2.5066282746310005 * ser / x)

    def _interpret_psi(self, psi: float) -> str:
        """Interpret PSI value."""
        if psi < 0.1:
            return "No significant drift"
        elif psi < 0.2:
            return "Minor drift detected"
        elif psi < 0.25:
            return "Moderate drift detected"
        else:
            return "Significant drift detected"

    def get_stats(self) -> DriftStats:
        """Get drift detection statistics."""
        return self._stats

    def reset_stats(self):
        """Reset statistics."""
        self._stats = DriftStats()

    def clear_baseline(self, name: str | None = None):
        """Clear baseline data."""
        if name:
            self._baseline.pop(name, None)
        else:
            self._baseline.clear()
