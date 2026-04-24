"""Advanced Assertion functionality."""

from dataclasses import dataclass
from typing import Any

from skill_observability_toolkit.stop.assertions import AssertionEngine, AssertionResult


@dataclass
class CompoundAssertion:
    """Compound assertion that combines multiple assertions."""

    logic: str  # "all", "any", "none"
    assertions: list[dict[str, Any]]
    engine: AssertionEngine

    def evaluate(self, context: dict[str, Any] = None) -> AssertionResult:
        """Evaluate all assertions with specified logic."""
        results = []

        for assertion in self.assertions:
            result = self.engine.execute_assertion(assertion, context)
            results.append(result)

        # Apply logic
        if self.logic == "all":
            passed = all(r.passed for r in results)
        elif self.logic == "any":
            passed = any(r.passed for r in results)
        elif self.logic == "none":
            passed = not any(r.passed for r in results)
        else:
            passed = False

        return AssertionResult(
            passed=passed,
            assertion=f"compound({self.logic})",
            message=f"Compound assertion with logic '{self.logic}'",
            details={"individual_results": [{"passed": r.passed, "assertion": r.assertion, "message": r.message, "details": r.details} for r in results]},
        )


class JSONSchemaAssertion:
    """JSON Schema validation assertion."""

    def __init__(self, schema: dict[str, Any]):
        self.schema = schema

    def execute(self, context: dict[str, Any], engine: AssertionEngine) -> AssertionResult:
        """Validate data against JSON Schema."""
        try:
            import jsonschema

            # Get value from context
            value = context.get("value", context.get("response", {}))

            # Validate
            jsonschema.validate(value, self.schema)

            return AssertionResult(
                passed=True,
                assertion="json_schema_valid",
                message="Value conforms to schema"
            )
        except ImportError:
            return AssertionResult(
                passed=False,
                assertion="json_schema_valid",
                message="jsonschema package not installed"
            )
        except Exception as e:
            return AssertionResult(
                passed=False,
                assertion="json_schema_valid",
                message=str(e)
            )


class PerformancePercentileAssertion:
    """Performance percentile checking."""

    def __init__(self, percentile: int = 95, threshold_ms: float = 2000):
        self.percentile = percentile
        self.threshold_ms = threshold_ms

    def check(self, history: list[float]) -> bool:
        """Check if percentile is within threshold."""
        if not history:
            return True

        try:
            import numpy as np
            p_value = np.percentile(history, self.percentile)
            return p_value <= self.threshold_ms
        except ImportError:
            # Fallback without numpy
            sorted_history = sorted(history)
            idx = int(len(sorted_history) * self.percentile / 100)
            p_value = sorted_history[min(idx, len(sorted_history) - 1)]
            return p_value <= self.threshold_ms

    def execute(self, context: dict[str, Any]) -> AssertionResult:
        """Execute percentile check."""
        history = context.get("latency_history", [])
        passed = self.check(history)

        return AssertionResult(
            passed=passed,
            assertion=f"performance_percentile_{self.percentile}",
            message=f"P{self.percentile} latency {'within' if passed else 'exceeds'} threshold ({self.threshold_ms}ms)"
        )
