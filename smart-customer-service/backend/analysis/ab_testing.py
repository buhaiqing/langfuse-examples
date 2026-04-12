"""
A/B Testing Framework for customer service experiments.

Provides deterministic experiment group assignment, statistical significance testing,
and comprehensive result comparison tools integrated with Langfuse tracing.

Key Features:
    - Deterministic user-to-group assignment based on user_id hash (MD5)
    - Integration with Langfuse trace metadata for experiment tracking
    - Statistical significance testing using Welch's t-test
    - Effect size calculation (Cohen's d) with interpretation
    - 95% confidence interval computation
    - Power analysis for sample size determination
    - Multi-experiment comparison and ranking

Usage Example:
    >>> from analysis.ab_testing import ABTestExperiment, ExperimentGroup
    >>>
    >>> # Create experiment
    >>> experiment = ABTestExperiment(
    ...     name="intent_recognition_v2",
    ...     description="Testing improved intent recognition model",
    ...     metric_name="user_satisfaction",
    ...     min_sample_size=50
    ... )
    >>>
    >>> # Assign users to groups (deterministic)
    >>> group = experiment.assign_experiment_group("user_123")
    >>>
    >>> # Record metrics
    >>> experiment.record_metric("user_123", 4.5)
    >>>
    >>> # Get Langfuse metadata
    >>> metadata = experiment.get_trace_metadata()
    >>> langfuse.update_current_trace(metadata=metadata)
    >>>
    >>> # Calculate statistical significance
    >>> result = experiment.calculate_statistical_significance()
    >>> print(result.summary())
    >>>
    >>> # Compare multiple experiments
    >>> from analysis.ab_testing import compare_experiment_results
    >>> ranked = compare_experiment_results([result1, result2], sort_by="p_value")

Dependencies:
    - numpy: Numerical computations
    - scipy: Statistical tests (t-test)
    - statsmodels: Power analysis (sample size calculation)
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from scipy import stats
from statsmodels.stats.power import TTestIndPower


class ExperimentGroup(Enum):
    """Enumeration for experiment groups."""

    CONTROL = "control"
    TREATMENT_A = "treatment_a"
    TREATMENT_B = "treatment_b"
    TREATMENT_C = "treatment_c"


@dataclass
class ExperimentResult:
    """
    Represents the results of an A/B test experiment.

    Attributes:
        experiment_name: Name of the experiment
        control_group: Statistics for control group
        treatment_group: Statistics for treatment group
        p_value: Statistical significance p-value
        effect_size: Cohen's d effect size
        confidence_interval: 95% confidence interval for difference in means
        sample_sizes: Sample sizes for each group
        statistically_significant: Whether result is statistically significant (p < 0.05)
        practical_significance: Whether effect size is practically meaningful
    """

    experiment_name: str
    control_mean: float
    control_std: float
    treatment_mean: float
    treatment_std: float
    p_value: float
    effect_size: float
    confidence_interval: tuple[float, float]
    control_sample_size: int
    treatment_sample_size: int
    statistically_significant: bool = False
    practical_significance: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.statistically_significant = self.p_value < 0.05
        # Practical significance: medium effect size or larger (Cohen's d >= 0.5)
        self.practical_significance = abs(self.effect_size) >= 0.5

    @property
    def improvement_percentage(self) -> float:
        """Calculate percentage improvement from control to treatment."""
        if self.control_mean == 0:
            return 0.0
        return ((self.treatment_mean - self.control_mean) / self.control_mean) * 100

    def summary(self) -> str:
        """Generate a human-readable summary of experiment results."""
        significance_marker = "*" if self.statistically_significant else ""
        practical_marker = "**" if self.practical_significance else ""

        summary_lines = [
            f"Experiment: {self.experiment_name}",
            f"{'='*60}",
            f"Control Group (n={self.control_sample_size}):",
            f"  Mean: {self.control_mean:.4f} +/- {self.control_std:.4f}",
            f"Treatment Group (n={self.treatment_sample_size}):",
            f"  Mean: {self.treatment_mean:.4f} +/- {self.treatment_std:.4f}",
            "",
            "Results:",
            f"  Difference: {self.treatment_mean - self.control_mean:.4f}",
            f"  Improvement: {self.improvement_percentage:+.2f}%",
            f"  Effect Size (Cohen's d): {self.effect_size:.4f}{practical_marker}",
            f"  P-value: {self.p_value:.6f}{significance_marker}",
            f"  95% CI: [{self.confidence_interval[0]:.4f}, {self.confidence_interval[1]:.4f}]",
            "",
            "Significance:",
            f"  Statistical: {'Yes' if self.statistically_significant else 'No'}{significance_marker}",
            f"  Practical: {'Yes' if self.practical_significance else 'No'}{practical_marker}",
        ]

        if self.metadata:
            summary_lines.append("\nMetadata:")
            for key, value in self.metadata.items():
                summary_lines.append(f"  {key}: {value}")

        return "\n".join(summary_lines)


class ABTestExperiment:
    """
    Manages a single A/B test experiment with deterministic group assignment
    and statistical analysis capabilities.

    This class provides:
    - Deterministic user-to-group assignment based on user_id hash
    - Integration with Langfuse trace metadata for experiment tracking
    - Statistical significance testing using t-tests
    - Effect size calculation (Cohen's d)
    - Confidence interval computation

    Attributes:
        name: Unique experiment identifier
        description: Human-readable experiment description
        groups: List of experiment groups being tested
        allocation_ratios: Ratio of users allocated to each group
        metric_name: Primary metric being measured
        min_sample_size: Minimum sample size per group for valid results
        started_at: Experiment start timestamp
        metadata: Additional experiment configuration metadata
    """

    def __init__(
        self,
        name: str,
        description: str,
        groups: list[ExperimentGroup] | None = None,
        allocation_ratios: dict[ExperimentGroup, float] | None = None,
        metric_name: str = "user_satisfaction",
        min_sample_size: int = 30,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize an A/B test experiment.

        Args:
            name: Unique experiment identifier (e.g., "intent_recognition_v2")
            description: Human-readable experiment description
            groups: List of experiment groups. Defaults to [CONTROL, TREATMENT_A]
            allocation_ratios: User allocation ratios per group. Must sum to 1.0.
                              Defaults to equal allocation.
            metric_name: Primary metric being measured
            min_sample_size: Minimum sample size per group for valid statistical tests
            metadata: Additional experiment configuration metadata

        Raises:
            ValueError: If allocation ratios don't sum to 1.0 or are invalid
        """
        self.name = name
        self.description = description
        self.groups = groups or [ExperimentGroup.CONTROL, ExperimentGroup.TREATMENT_A]
        self.metric_name = metric_name
        self.min_sample_size = min_sample_size
        self.started_at = None
        self.metadata = metadata or {}

        # Set default equal allocation if not provided
        if allocation_ratios is None:
            num_groups = len(self.groups)
            equal_ratio = 1.0 / num_groups
            self.allocation_ratios = dict.fromkeys(self.groups, equal_ratio)
        else:
            # Validate allocation ratios
            total_ratio = sum(allocation_ratios.values())
            if not np.isclose(total_ratio, 1.0, atol=1e-6):
                raise ValueError(f"Allocation ratios must sum to 1.0, got {total_ratio}")
            self.allocation_ratios = allocation_ratios

        # Storage for collected data
        self._group_data: dict[ExperimentGroup, list[float]] = {group: [] for group in self.groups}

    def assign_experiment_group(self, user_id: str) -> ExperimentGroup:
        """
        Deterministically assign a user to an experiment group based on user_id hash.

        Uses MD5 hashing of user_id to ensure consistent group assignment across
        multiple sessions for the same user. The hash is converted to a value
        between 0 and 1, then compared against cumulative allocation ratios.

        Args:
            user_id: Unique user identifier

        Returns:
            Assigned ExperimentGroup for this user

        Example:
            >>> experiment = ABTestExperiment("test_exp", "Test experiment")
            >>> group = experiment.assign_experiment_group("user_123")
            >>> print(group)
            ExperimentGroup.CONTROL
        """
        # Create deterministic hash from user_id and experiment name
        hash_input = f"{self.name}:{user_id}".encode()
        hash_digest = hashlib.md5(hash_input).hexdigest()

        # Convert hash to a value between 0 and 1
        hash_value = int(hash_digest[:8], 16) / 0xFFFFFFFF

        # Assign group based on cumulative allocation ratios
        cumulative_ratio = 0.0
        for group in self.groups:
            cumulative_ratio += self.allocation_ratios[group]
            if hash_value < cumulative_ratio:
                return group

        # Fallback to last group (should rarely happen due to floating point)
        return self.groups[-1]

    def record_metric(self, user_id: str, metric_value: float):
        """
        Record a metric value for a user in their assigned group.

        Args:
            user_id: User identifier
            metric_value: Observed metric value

        Example:
            >>> experiment.record_metric("user_123", 4.5)
        """
        group = self.assign_experiment_group(user_id)
        self._group_data[group].append(metric_value)

    def get_group_statistics(self, group: ExperimentGroup) -> dict[str, float]:
        """
        Calculate descriptive statistics for a specific group.

        Args:
            group: The experiment group to analyze

        Returns:
            Dictionary containing mean, std, count, min, max, median

        Raises:
            ValueError: If group has no data
        """
        data = self._group_data.get(group, [])
        if not data:
            raise ValueError(f"No data recorded for group {group.value}")

        array_data = np.array(data)
        return {
            "mean": float(np.mean(array_data)),
            "std": float(np.std(array_data, ddof=1)) if len(data) > 1 else 0.0,
            "count": len(data),
            "min": float(np.min(array_data)),
            "max": float(np.max(array_data)),
            "median": float(np.median(array_data)),
        }

    def calculate_statistical_significance(
        self,
        control_group: ExperimentGroup = ExperimentGroup.CONTROL,
        treatment_group: ExperimentGroup = ExperimentGroup.TREATMENT_A,
        alpha: float = 0.05,
        alternative: str = "two-sided",
    ) -> ExperimentResult:
        """
        Perform statistical significance testing between control and treatment groups.

        Uses independent samples t-test to determine if there is a statistically
        significant difference between group means. Also calculates Cohen's d
        effect size and 95% confidence interval.

        Args:
            control_group: The control group to compare against
            treatment_group: The treatment group to test
            alpha: Significance level (default: 0.05)
            alternative: Type of test: 'two-sided', 'less', or 'greater'

        Returns:
            ExperimentResult with comprehensive statistical analysis

        Raises:
            ValueError: If insufficient data in either group
            RuntimeError: If statistical test fails

        Example:
            >>> result = experiment.calculate_statistical_significance()
            >>> print(result.p_value)
            0.023
            >>> print(result.statistically_significant)
            True
        """
        control_data = self._group_data.get(control_group, [])
        treatment_data = self._group_data.get(treatment_group, [])

        if len(control_data) < self.min_sample_size:
            raise ValueError(
                f"Insufficient control group data: {len(control_data)} samples "
                f"(minimum: {self.min_sample_size})"
            )
        if len(treatment_data) < self.min_sample_size:
            raise ValueError(
                f"Insufficient treatment group data: {len(treatment_data)} samples "
                f"(minimum: {self.min_sample_size})"
            )

        control_array = np.array(control_data)
        treatment_array = np.array(treatment_data)

        # Perform independent samples t-test
        try:
            t_stat, p_value = stats.ttest_ind(
                treatment_array,
                control_array,
                equal_var=False,  # Welch's t-test (doesn't assume equal variance)
                alternative=alternative,
            )
        except Exception as e:
            raise RuntimeError(f"Statistical test failed: {str(e)}")

        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt((np.var(control_array, ddof=1) + np.var(treatment_array, ddof=1)) / 2)
        if pooled_std == 0:
            effect_size = 0.0
        else:
            effect_size = float((np.mean(treatment_array) - np.mean(control_array)) / pooled_std)

        # Calculate 95% confidence interval for difference in means
        mean_diff = np.mean(treatment_array) - np.mean(control_array)
        se_diff = np.sqrt(
            np.var(treatment_array, ddof=1) / len(treatment_array)
            + np.var(control_array, ddof=1) / len(control_array)
        )
        ci_lower = mean_diff - 1.96 * se_diff
        ci_upper = mean_diff + 1.96 * se_diff

        return ExperimentResult(
            experiment_name=self.name,
            control_mean=float(np.mean(control_array)),
            control_std=float(np.std(control_array, ddof=1)),
            treatment_mean=float(np.mean(treatment_array)),
            treatment_std=float(np.std(treatment_array, ddof=1)),
            p_value=float(p_value),
            effect_size=effect_size,
            confidence_interval=(float(ci_lower), float(ci_upper)),
            control_sample_size=len(control_data),
            treatment_sample_size=len(treatment_data),
            metadata={
                "metric_name": self.metric_name,
                "alpha": alpha,
                "test_type": "welch_ttest",
                "alternative": alternative,
                **self.metadata,
            },
        )

    def get_trace_metadata(self) -> dict[str, Any]:
        """
        Generate metadata dictionary for Langfuse trace integration.

        Returns experiment configuration that can be attached to traces
        for experiment tracking and analysis.

        Returns:
            Dictionary with experiment configuration suitable for trace metadata

        Example:
            >>> metadata = experiment.get_trace_metadata()
            >>> langfuse.update_current_trace(metadata=metadata)
        """
        return {
            "experiment_name": self.name,
            "experiment_description": self.description,
            "metric_name": self.metric_name,
            "groups": [g.value for g in self.groups],
            "allocation_ratios": {g.value: r for g, r in self.allocation_ratios.items()},
            "min_sample_size": self.min_sample_size,
            **self.metadata,
        }

    def get_experiment_status(self) -> dict[str, Any]:
        """
        Get current experiment status including sample sizes and readiness.

        Returns:
            Dictionary with experiment status information
        """
        status = {
            "name": self.name,
            "description": self.description,
            "status": "running",
            "groups": {},
            "total_samples": 0,
            "ready_for_analysis": True,
        }

        for group in self.groups:
            data = self._group_data.get(group, [])
            group_stats = {
                "sample_size": len(data),
                "sufficient_data": len(data) >= self.min_sample_size,
            }
            if data:
                array_data = np.array(data)
                group_stats["current_mean"] = float(np.mean(array_data))
                group_stats["current_std"] = (
                    float(np.std(array_data, ddof=1)) if len(data) > 1 else 0.0
                )

            status["groups"][group.value] = group_stats
            status["total_samples"] += len(data)

            if len(data) < self.min_sample_size:
                status["ready_for_analysis"] = False

        return status

    def reset_data(self):
        """Reset all collected data while preserving experiment configuration."""
        self._group_data = {group: [] for group in self.groups}


def compare_experiment_results(
    results: list[ExperimentResult], sort_by: str = "p_value", ascending: bool = True
) -> list[ExperimentResult]:
    """
    Compare and rank multiple experiment results.

    Sorts experiment results by specified criterion and provides
    comparative analysis.

    Args:
        results: List of ExperimentResult objects to compare
        sort_by: Sorting criterion: 'p_value', 'effect_size', 'improvement_percentage'
        ascending: Sort order (True for ascending, False for descending)

    Returns:
        Sorted list of ExperimentResult objects

    Raises:
        ValueError: If sort_by is not a valid criterion

    Example:
        >>> results = [result1, result2, result3]
        >>> ranked = compare_experiment_results(results, sort_by="effect_size", ascending=False)
        >>> for r in ranked:
        ...     print(r.summary())
    """
    valid_sort_keys = ["p_value", "effect_size", "improvement_percentage"]
    if sort_by not in valid_sort_keys:
        raise ValueError(f"Invalid sort_by: '{sort_by}'. Must be one of {valid_sort_keys}")

    sorted_results = sorted(results, key=lambda r: getattr(r, sort_by), reverse=not ascending)

    return sorted_results


def calculate_required_sample_size(
    baseline_mean: float,
    baseline_std: float,
    minimum_detectable_effect: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """
    Calculate required sample size per group for desired statistical power.

    Uses power analysis to determine the minimum sample size needed to detect
    a specified effect size with given power and significance level.

    Args:
        baseline_mean: Expected mean of control group
        baseline_std: Expected standard deviation
        minimum_detectable_effect: Minimum effect size to detect (absolute difference)
        power: Desired statistical power (default: 0.8)
        alpha: Significance level (default: 0.05)

    Returns:
        Required sample size per group

    Example:
        >>> n = calculate_required_sample_size(
        ...     baseline_mean=4.0,
        ...     baseline_std=1.0,
        ...     minimum_detectable_effect=0.3,
        ...     power=0.8
        ... )
        >>> print(f"Need {n} samples per group")
    """
    # Calculate Cohen's d
    cohens_d = minimum_detectable_effect / baseline_std if baseline_std > 0 else 0

    if cohens_d == 0:
        raise ValueError("Cannot calculate sample size with zero effect size")

    # Use statsmodels for power analysis
    effect_size = abs(cohens_d)
    power_analysis = TTestIndPower()
    sample_size = power_analysis.solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=1.0  # Equal sample sizes
    )

    return int(np.ceil(sample_size))


def interpret_effect_size(cohens_d: float) -> str:
    """
    Interpret Cohen's d effect size according to conventional thresholds.

    Args:
        cohens_d: Calculated Cohen's d effect size

    Returns:
        Human-readable interpretation string

    Reference:
        Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences.
    """
    abs_d = abs(cohens_d)

    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    elif abs_d < 1.2:
        return "large"
    else:
        return "very large"


# Export public API
__all__ = [
    "ABTestExperiment",
    "ExperimentResult",
    "ExperimentGroup",
    "assign_experiment_group",
    "calculate_statistical_significance",
    "compare_experiment_results",
    "calculate_required_sample_size",
    "interpret_effect_size",
]
