"""
Trust Score Calculator with real-time updates.

Provides real-time Trust Score calculation using sliding window algorithm
with exponential decay for recent events.
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrustScoreConfig:
    """Configuration for Trust Score calculation."""

    window_size: int = 30  # Number of recent checks to consider
    decay_factor: float = 0.95  # Decay factor for older results
    update_interval: float = 1.0  # Minimum seconds between score updates
    min_samples: int = 5  # Minimum samples before reporting score


@dataclass
class CheckRecord:
    """Record of a single check."""

    timestamp: float
    passed: bool
    weight: float = 1.0


class TrustScoreCalculator:
    """
    Real-time Trust Score calculator.

    Calculates skill reliability score (0.0-1.0) based on recent
    assertion check results using sliding window with exponential decay.

    Example:
        config = TrustScoreConfig(window_size=30)
        calculator = TrustScoreCalculator(config)

        calculator.record_check(passed=True)
        calculator.record_check(passed=False)

        score = calculator.get_current_score()  # Returns 0.0-1.0
    """

    def __init__(self, config: TrustScoreConfig | None = None):
        """
        Initialize the calculator.

        Args:
            config: Trust score configuration
        """
        self.config = config or TrustScoreConfig()
        self._checks: list[CheckRecord] = []
        self._last_update: float = 0.0
        self._cached_score: float | None = None

    def record_check(self, passed: bool, weight: float = 1.0):
        """
        Record a check result.

        Args:
            passed: Whether the check passed
            weight: Weight of this check (default 1.0)
        """
        current_time = time.time()
        self._checks.append(CheckRecord(timestamp=current_time, passed=passed, weight=weight))

        # Invalidate cache if update_interval has passed
        if current_time - self._last_update >= self.config.update_interval:
            self._cached_score = None
            self._last_update = current_time

        # Trim old checks beyond window
        self._trim_old_checks()

    def _trim_old_checks(self):
        """Remove checks outside the sliding window."""
        if not self._checks:
            return

        current_time = time.time()
        cutoff = current_time - (self.config.window_size * 10)  # Rough window estimate

        # Keep checks within reasonable time window
        self._checks = [c for c in self._checks if c.timestamp > cutoff]

    def get_current_score(self) -> float:
        """
        Get the current trust score.

        Returns:
            Trust score between 0.0 and 1.0

        Raises:
            ValueError: If not enough samples
        """
        # Check cache
        if self._cached_score is not None:
            return self._cached_score

        if len(self._checks) < self.config.min_samples:
            # Not enough data - return neutral score
            return 0.5

        # Calculate weighted score with exponential decay
        current_time = time.time()
        total_weight = 0.0
        weighted_sum = 0.0

        for check in self._checks:
            # Calculate decay based on age
            age = current_time - check.timestamp
            decay = self.config.decay_factor ** (age / self.config.update_interval)

            weight = check.weight * decay
            total_weight += weight

            if check.passed:
                weighted_sum += weight

        if total_weight == 0:
            return 0.5

        score = weighted_sum / total_weight
        self._cached_score = score

        return score

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the trust score calculation."""
        return {
            "total_checks": len(self._checks),
            "current_score": self.get_current_score(),
            "passing_checks": sum(1 for c in self._checks if c.passed),
            "failing_checks": sum(1 for c in self._checks if not c.passed),
            "min_samples_required": self.config.min_samples,
        }

    def reset(self):
        """Reset all recorded checks."""
        self._checks.clear()
        self._cached_score = None
        self._last_update = 0.0
