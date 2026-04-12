# Analysis and dashboard module

from analysis.ab_testing import (
    ABTestExperiment,
    ExperimentGroup,
    ExperimentResult,
    calculate_required_sample_size,
    compare_experiment_results,
    interpret_effect_size,
)
from analysis.dashboard import Dashboard, DashboardMetrics

__all__ = [
    "ABTestExperiment",
    "ExperimentResult",
    "ExperimentGroup",
    "compare_experiment_results",
    "calculate_required_sample_size",
    "interpret_effect_size",
    "Dashboard",
    "DashboardMetrics",
]
