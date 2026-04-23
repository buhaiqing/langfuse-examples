"""
Assertion Engine for STOP Protocol.

This module provides assertion checking capabilities for Skills,
supporting both pre-execution and post-execution validations.
"""

from dataclasses import dataclass
from typing import Any


class AssertionError(Exception):
    """Base exception for assertion errors."""
    pass


class AssertionExecutionError(AssertionError):
    """Error executing an assertion."""
    pass


class AssertionSyntaxError(AssertionError):
    """Syntax error in assertion definition."""
    pass


@dataclass
class AssertionResult:
    """
    Result of an assertion execution.

    Attributes:
        passed: Whether the assertion passed
        assertion: The assertion that was executed
        message: Optional message explaining the result
        details: Additional details about the assertion
    """
    passed: bool
    assertion: str
    message: str = ""
    details: dict[str, Any] = None


@dataclass
class AssertionConfig:
    """
    Configuration for an assertion.

    Attributes:
        check: Assertion name or expression
        path: Optional path to check
        condition: Optional condition expression
        message: Error message if assertion fails
        type_: Assertion type ("pre" or "post")
    """
    check: str
    path: str | None = None
    condition: str | None = None
    message: str = ""
    type_: str = "pre"  # "pre" or "post"


class AssertionEngine:
    """
    Engine for executing Skill assertions.

    Supports:
    - Pre-execution checks (validate inputs)
    - Post-execution checks (validate outputs)
    - Custom check functions
    - Conditional assertions based on expressions

    Attributes:
        check_functions: Registry of available check functions
        context: Context for assertion evaluation
    """

    def __init__(self):
        """Initialize the assertion engine."""
        self.check_functions: dict[str, Any] = {}
        self.context: dict[str, Any] = {}
        self._register_builtin_checks()

    def _register_builtin_checks(self) -> None:
        """Register built-in check functions."""
        self.check_functions.update({
            "file_exists": self._check_file_exists,
            "string_not_empty": self._check_string_not_empty,
            "string_empty": self._check_string_empty,
            "list_not_empty": self._check_list_not_empty,
            "list_empty": self._check_list_empty,
            "value_equal": self._check_value_equal,
            "value_not_equal": self._check_value_not_equal,
            "value_greater_than": self._check_value_greater_than,
            "value_less_than": self._check_value_less_than,
            "value_in_range": self._check_value_in_range,
            "type_is": self._check_type_is,
            "type_is_not": self._check_type_is_not,
            "key_exists": self._check_key_exists,
            "key_not_exists": self._check_key_not_exists,
            "output_exists": self._check_output_exists,
            "output_not_empty": self._check_output_not_empty,
            "output_success": self._check_output_success,
            "performance": self._check_performance,
            "cost_within_budget": self._check_cost_within_budget,
            "input_valid": self._check_input_valid,
            "output_valid": self._check_output_valid,
        })

    def _check_file_exists(self, path: str, **kwargs) -> AssertionResult:
        """Check if a file exists."""
        from pathlib import Path

        file_path = Path(path)
        passed = file_path.exists() and file_path.is_file()

        return AssertionResult(
            passed=passed,
            assertion="file_exists",
            message=f"File {path} {'exists' if passed else 'does not exist'}",
        )

    def _check_string_not_empty(self, value: str, **kwargs) -> AssertionResult:
        """Check if a string is not empty."""
        passed = bool(value) and len(value.strip()) > 0

        return AssertionResult(
            passed=passed,
            assertion="string_not_empty",
            message=f"String {repr(value)} is {'not empty' if passed else 'empty'}",
        )

    def _check_string_empty(self, value: str, **kwargs) -> AssertionResult:
        """Check if a string is empty."""
        passed = not bool(value) or len(value.strip()) == 0

        return AssertionResult(
            passed=passed,
            assertion="string_empty",
            message=f"String {repr(value)} is {'empty' if passed else 'not empty'}",
        )

    def _check_list_not_empty(self, value: list, **kwargs) -> AssertionResult:
        """Check if a list is not empty."""
        passed = bool(value) and len(value) > 0

        return AssertionResult(
            passed=passed,
            assertion="list_not_empty",
            message=f"List has {len(value)} items {'(not empty)' if passed else '(empty)'}",
        )

    def _check_list_empty(self, value: list, **kwargs) -> AssertionResult:
        """Check if a list is empty."""
        passed = not bool(value) or len(value) == 0

        return AssertionResult(
            passed=passed,
            assertion="list_empty",
            message=f"List has {len(value)} items {'(empty)' if passed else '(not empty)'}",
        )

    def _check_value_equal(self, value: Any, expected: Any, **kwargs) -> AssertionResult:
        """Check if value equals expected."""
        passed = value == expected

        return AssertionResult(
            passed=passed,
            assertion="value_equal",
            message=f"Value {repr(value)} {'==' if passed else '!='} {repr(expected)}",
        )

    def _check_value_not_equal(self, value: Any, expected: Any, **kwargs) -> AssertionResult:
        """Check if value does not equal expected."""
        passed = value != expected

        return AssertionResult(
            passed=passed,
            assertion="value_not_equal",
            message=f"Value {repr(value)} {'!=' if passed else '=='} {repr(expected)}",
        )

    def _check_value_greater_than(self, value: int | float, threshold: int | float, **kwargs) -> AssertionResult:
        """Check if value is greater than threshold."""
        passed = bool(value) and value > threshold

        return AssertionResult(
            passed=passed,
            assertion="value_greater_than",
            message=f"{value} {'>' if passed else '<='} {threshold}",
        )

    def _check_value_less_than(self, value: int | float, threshold: int | float, **kwargs) -> AssertionResult:
        """Check if value is less than threshold."""
        passed = bool(value) and value < threshold

        return AssertionResult(
            passed=passed,
            assertion="value_less_than",
            message=f"{value} {'<' if passed else '>='} {threshold}",
        )

    def _check_value_in_range(self, value: int | float, min_val: int | float, max_val: int | float, **kwargs) -> AssertionResult:
        """Check if value is within range."""
        passed = bool(value) and min_val <= value <= max_val

        return AssertionResult(
            passed=passed,
            assertion="value_in_range",
            message=f"{min_val} <= {value} <= {max_val} is {'True' if passed else 'False'}",
        )

    def _check_type_is(self, value: Any, expected_type: str, **kwargs) -> AssertionResult:
        """Check if value is of expected type."""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "NoneType": type(None),
        }

        expected_cls = type_mapping.get(expected_type, None)
        if expected_cls is None:
            return AssertionResult(
                passed=False,
                assertion="type_is",
                message=f"Unknown type: {expected_type}",
            )

        passed = isinstance(value, expected_cls)

        return AssertionResult(
            passed=passed,
            assertion="type_is",
            message=f"{repr(value)} {'is' if passed else 'is not'} {expected_type}",
        )

    def _check_type_is_not(self, value: Any, unexpected_type: str, **kwargs) -> AssertionResult:
        """Check if value is not of unexpected type."""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "NoneType": type(None),
        }

        unexpected_cls = type_mapping.get(unexpected_type, None)
        if unexpected_cls is None:
            return AssertionResult(
                passed=False,
                assertion="type_is_not",
                message=f"Unknown type: {unexpected_type}",
            )

        passed = not isinstance(value, unexpected_cls)

        return AssertionResult(
            passed=passed,
            assertion="type_is_not",
            message=f"{repr(value)} {'is not' if passed else 'is'} {unexpected_type}",
        )

    def _check_key_exists(self, data: dict, key: str, **kwargs) -> AssertionResult:
        """Check if key exists in dict."""
        passed = isinstance(data, dict) and key in data

        return AssertionResult(
            passed=passed,
            assertion="key_exists",
            message=f"Key '{key}' {'exists' if passed else 'does not exist'} in dict",
        )

    def _check_key_not_exists(self, data: dict, key: str, **kwargs) -> AssertionResult:
        """Check if key does not exist in dict."""
        passed = not isinstance(data, dict) or key not in data

        return AssertionResult(
            passed=passed,
            assertion="key_not_exists",
            message=f"Key '{key}' {'does not exist' if passed else 'exists'} in dict",
        )

    def _check_output_exists(self, result: dict, **kwargs) -> AssertionResult:
        """Check if output exists."""
        passed = bool(result) and isinstance(result, dict)

        return AssertionResult(
            passed=passed,
            assertion="output_exists",
            message=f"Output {'exists' if passed else 'does not exist'}",
        )

    def _check_output_not_empty(self, result: dict, **kwargs) -> AssertionResult:
        """Check if output is not empty."""
        passed = bool(result) and isinstance(result, dict) and len(result) > 0

        return AssertionResult(
            passed=passed,
            assertion="output_not_empty",
            message=f"Output {'is not empty' if passed else 'is empty'}",
        )

    def _check_output_success(self, result: dict, **kwargs) -> AssertionResult:
        """Check if output indicates success."""
        success = result.get("success", False) if isinstance(result, dict) else False
        passed = success is True or success == "true" or success == "1"

        return AssertionResult(
            passed=passed,
            assertion="output_success",
            message=f"Output success {'is True' if passed else 'is False'}",
        )

    def _check_performance(self, duration_ms: int | float, threshold_ms: int | float = 5000, **kwargs) -> AssertionResult:
        """Check if performance is within threshold."""
        passed = bool(duration_ms) and duration_ms < threshold_ms

        return AssertionResult(
            passed=passed,
            assertion="performance",
            message=f"Duration {duration_ms}ms {'<' if passed else '>='} {threshold_ms}ms",
        )

    def _check_cost_within_budget(self, cost: int | float, budget: int | float, **kwargs) -> AssertionResult:
        """Check if cost is within budget."""
        passed = bool(cost) and cost <= budget

        return AssertionResult(
            passed=passed,
            assertion="cost_within_budget",
            message=f"Cost {cost} {'<=' if passed else '>'} budget {budget}",
        )

    def _check_input_valid(self, value: Any, **kwargs) -> AssertionResult:
        """Generic input validation check."""
        passed = value is not None and value != ""

        return AssertionResult(
            passed=passed,
            assertion="input_valid",
            message=f"Input {'is valid' if passed else 'is invalid'}",
        )

    def _check_output_valid(self, result: dict, **kwargs) -> AssertionResult:
        """Generic output validation check."""
        passed = isinstance(result, dict)

        return AssertionResult(
            passed=passed,
            assertion="output_valid",
            message=f"Output {'is valid' if passed else 'is invalid'}",
        )

    def register_check(self, name: str, func: Any) -> None:
        """
        Register a custom check function.

        Args:
            name: Check name
            func: Check function that returns AssertionResult
        """
        self.check_functions[name] = func

    def unregister_check(self, name: str) -> None:
        """
        Unregister a check function.

        Args:
            name: Check name to remove
        """
        if name in self.check_functions:
            del self.check_functions[name]

    def execute_assertion(
        self,
        assertion: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AssertionResult:
        """
        Execute a single assertion.

        Args:
            assertion: Assertion configuration dict
            context: Context for evaluation

        Returns:
            AssertionResult
        """
        check_name = assertion.get("check", "")
        params = assertion.copy()
        del params["check"]

        # Get check function
        check_func = self.check_functions.get(check_name, None)
        if check_func is None:
            raise AssertionExecutionError(f"Unknown check function: {check_name}")

        # Execute check
        try:
            result = check_func(**params)
        except Exception as e:
            raise AssertionExecutionError from e(f"Error executing check '{check_name}': {e}")

        return result

    def execute_assertions(
        self,
        assertions: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> list[AssertionResult]:
        """
        Execute multiple assertions.

        Args:
            assertions: List of assertion configs
            context: Context for evaluation

        Returns:
            List of AssertionResult
        """
        results = []
        for assertion in assertions:
            result = self.execute_assertion(assertion, context)
            results.append(result)
        return results

    def calculate_trust_score(self, results: list[AssertionResult]) -> float:
        """
        Calculate Trust Score from assertion results.

        Args:
            results: List of AssertionResult

        Returns:
            Trust Score (0.0 - 1.0)
        """
        if not results:
            return 1.0

        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)

        return passed_count / total_count

    def validate(
        self,
        assertions: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Validate all assertions pass.

        Args:
            assertions: List of assertion configs
            context: Context for evaluation

        Returns:
            True if all assertions pass, False otherwise
        """
        results = self.execute_assertions(assertions, context)

        return all(r.passed for r in results)

    def run_assertions(
        self,
        assertions: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> list[AssertionResult]:
        """
        Run assertions with error handling.

        Args:
            assertions: List of assertion configs
            context: Context for evaluation

        Returns:
            List of AssertionResult
        """
        results = []

        for assertion in assertions:
            try:
                result = self.execute_assertion(assertion, context)
                results.append(result)
            except AssertionExecutionError as e:
                # Assertion execution failed, mark as not passed
                results.append(AssertionResult(
                    passed=False,
                    assertion=assertion.get("check", "unknown"),
                    message=f"Execution error: {e}",
                ))

        return results

    def validate_assertions(
        self,
        assertions: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Validate all assertions pass with error handling.

        Args:
            assertions: List of assertion configs
            context: Context for evaluation

        Returns:
            True if all assertions pass or can be executed, False otherwise
        """
        results = self.run_assertions(assertions, context)

        # Check if all results passed
        return all(r.passed for r in results)

    def get_assertions_by_type(
        self,
        assertions: list[dict[str, Any]],
        type_: str,
    ) -> list[dict[str, Any]]:
        """
        Filter assertions by type (pre or post).

        Args:
            assertions: List of assertion configs
            type_: Assertion type ("pre" or "post")

        Returns:
            Filtered list of assertions
        """
        return [a for a in assertions if a.get("type", a.get("type_", "pre")) == type_]

    def apply_conditions(
        self,
        condition: str | None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Evaluate condition expressions.

        Args:
            condition: Condition expression (e.g., "${inputs.value} > 10")
            context: Context for evaluation

        Returns:
            True if condition passes, False otherwise
        """
        if not condition:
            return True

        # Simple condition parsing
        # Support basic operators: ==, !=, >, <, >=, <=, in, not in
        context = context or {}

        try:
            # Replace ${...} with context values
            import re

            def replace_var(match):
                path = match.group(1)  # e.g., "inputs.value"
                keys = path.split(".")
                value = context

                for key in keys:
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        return None

                return str(value) if value is not None else "None"

            # Replace variables
            processed = re.sub(r"\$\{([^}]+)\}", replace_var, condition)

            # Basic expression evaluation
            # Parse and evaluate
            if ">=" in processed:
                parts = processed.split(">=")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) >= self._safe_eval(parts[1])

            if "<=" in processed:
                parts = processed.split("<=")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) <= self._safe_eval(parts[1])

            if "==" in processed:
                parts = processed.split("==")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) == self._safe_eval(parts[1])

            if "!=" in processed:
                parts = processed.split("!=")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) != self._safe_eval(parts[1])

            if ">" in processed:
                parts = processed.split(">")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) > self._safe_eval(parts[1])

            if "<" in processed:
                parts = processed.split("<")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) < self._safe_eval(parts[1])

            if " in " in processed:
                parts = processed.split(" in ")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) in self._safe_eval(parts[1])

            if " not in " in processed:
                parts = processed.split(" not in ")
                if len(parts) == 2:
                    return self._safe_eval(parts[0]) not in self._safe_eval(parts[1])

            # If no operator, evaluate as boolean
            return bool(self._safe_eval(processed))

        except Exception:
            return False

    def _safe_eval(self, expr: str) -> Any:
        """
        Safely evaluate an expression.

        Args:
            expr: Expression string

        Returns:
            Evaluated value
        """
        try:
            # Simple type conversion
            expr = expr.strip()

            if expr.lower() == "true":
                return True
            if expr.lower() == "false":
                return False
            if expr.lower() == "null" or expr.lower() == "none":
                return None

            try:
                return int(expr)
            except ValueError:
                pass

            try:
                return float(expr)
            except ValueError:
                pass

            # Try as string
            if expr.startswith("'") and expr.endswith("'"):
                return expr[1:-1]
            if expr.startswith('"') and expr.endswith('"'):
                return expr[1:-1]

            return expr

        except Exception:
            return expr
