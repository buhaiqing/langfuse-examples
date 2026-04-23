"""
Unit tests for Assertion Engine.
"""

from skill_observability_toolkit.stop.assertions import (
    AssertionConfig,
    AssertionEngine,
    AssertionResult,
)
from skill_observability_toolkit.stop.assertions import (
    AssertionError as AssertionError,
)


class TestAssertionResult:
    """Tests for AssertionResult dataclass."""

    def test_init(self):
        """Test assertion result initialization."""
        result = AssertionResult(
            passed=True,
            assertion="test_check",
            message="Test passed",
        )

        assert result.passed is True
        assert result.assertion == "test_check"
        assert result.message == "Test passed"
        assert result.details is None

    def test_init_with_details(self):
        """Test with details."""
        result = AssertionResult(
            passed=False,
            assertion="file_exists",
            message="File not found",
            details={"path": "/nonexistent/file.txt"},
        )

        assert result.passed is False
        assert result.details == {"path": "/nonexistent/file.txt"}

    def test_str(self):
        """Test string representation."""
        result = AssertionResult(
            passed=True,
            assertion="string_not_empty",
            message="String is not empty",
        )

        result_str = str(result)
        assert "AssertionResult" in result_str
        assert "passed=True" in result_str


class TestAssertionConfig:
    """Tests for AssertionConfig dataclass."""

    def test_init_default_type(self):
        """Test default type is pre."""
        config = AssertionConfig(check="test", message="Test config")

        assert config.check == "test"
        assert config.message == "Test config"
        assert config.path is None
        assert config.condition is None
        assert config.type_ == "pre"

    def test_init_with_type(self):
        """Test with explicit type."""
        config = AssertionConfig(
            check="test",
            type_="post",
            message="Post-check",
        )

        assert config.type_ == "post"


class TestAssertionEngineInit:
    """Tests for AssertionEngine initialization."""

    def test_init(self):
        """Test engine initialization."""
        engine = AssertionEngine()

        assert len(engine.check_functions) > 0
        assert engine.context == {}

    def test_register_check(self):
        """Test registering custom check."""
        engine = AssertionEngine()

        def custom_check(x: int) -> AssertionResult:
            return AssertionResult(
                passed=x > 0,
                assertion="custom_check",
                message="Custom check",
            )

        engine.register_check("custom_check", custom_check)

        assert "custom_check" in engine.check_functions

    def test_unregister_check(self):
        """Test unregistering check."""
        engine = AssertionEngine()

        initial_count = len(engine.check_functions)

        engine.unregister_check("string_not_empty")

        assert len(engine.check_functions) == initial_count - 1
        assert "string_not_empty" not in engine.check_functions


class TestBuiltinChecks:
    """Tests for built-in check functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AssertionEngine()

    def test_file_exists_with_existing_file(self, tmp_path):
        """Test file_exists with existing file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test content")

        result = self.engine._check_file_exists(str(file_path))

        assert result.passed is True
        assert "exists" in result.message

    def test_file_exists_with_nonexistent_file(self):
        """Test file_exists with nonexistent file."""
        result = self.engine._check_file_exists("/nonexistent/path/file.txt")

        assert result.passed is False
        assert "does not exist" in result.message

    def test_string_not_empty_valid(self):
        """Test string_not_empty with valid string."""
        result = self.engine._check_string_not_empty("hello")

        assert result.passed is True
        assert "not empty" in result.message

    def test_string_not_empty_empty(self):
        """Test string_not_empty with empty string."""
        result = self.engine._check_string_not_empty("")

        assert result.passed is False
        assert "empty" in result.message

    def test_string_not_empty_whitespace(self):
        """Test string_not_empty with whitespace only."""
        result = self.engine._check_string_not_empty("   ")

        # Whitespace-only should be considered not empty (after strip check)
        # Actually the current implementation checks len(value.strip()) > 0
        # So '   ' becomes '' after strip, and should be considered empty
        assert result.passed is False

    def test_string_empty_valid(self):
        """Test string_empty with empty string."""
        result = self.engine._check_string_empty("")

        assert result.passed is True
        assert "empty" in result.message

    def test_list_not_empty_valid(self):
        """Test list_not_empty with non-empty list."""
        result = self.engine._check_list_not_empty([1, 2, 3])

        assert result.passed is True
        assert "3 items" in result.message

    def test_list_not_empty_empty(self):
        """Test list_not_empty with empty list."""
        result = self.engine._check_list_not_empty([])

        assert result.passed is False
        assert "empty" in result.message

    def test_value_equal_valid(self):
        """Test value_equal with equal values."""
        result = self.engine._check_value_equal(5, 5)

        assert result.passed is True
        assert "==" in result.message

    def test_value_equal_invalid(self):
        """Test value_equal with non-equal values."""
        result = self.engine._check_value_equal(5, 10)

        assert result.passed is False
        assert "!=" in result.message

    def test_value_greater_than_valid(self):
        """Test value_greater_than with valid comparison."""
        result = self.engine._check_value_greater_than(10, 5)

        assert result.passed is True
        assert ">" in result.message

    def test_value_less_than_valid(self):
        """Test value_less_than with valid comparison."""
        result = self.engine._check_value_less_than(5, 10)

        assert result.passed is True
        assert "<" in result.message

    def test_value_in_range_valid(self):
        """Test value_in_range with value in range."""
        result = self.engine._check_value_in_range(50, 0, 100)

        assert result.passed is True
        assert "True" in result.message

    def test_value_in_range_invalid(self):
        """Test value_in_range with value out of range."""
        result = self.engine._check_value_in_range(150, 0, 100)

        assert result.passed is False
        assert "False" in result.message

    def test_type_is_valid(self):
        """Test type_is with valid type."""
        result = self.engine._check_type_is("hello", "str")

        assert result.passed is True
        assert "is str" in result.message

    def test_type_is_invalid(self):
        """Test type_is with invalid type."""
        result = self.engine._check_type_is(123, "str")

        assert result.passed is False
        assert "is not str" in result.message

    def test_key_exists_valid(self):
        """Test key_exists with existing key."""
        data = {"key1": "value1", "key2": "value2"}
        result = self.engine._check_key_exists(data, "key1")

        assert result.passed is True
        assert "exists" in result.message

    def test_key_exists_invalid(self):
        """Test key_exists with nonexistent key."""
        data = {"key1": "value1"}
        result = self.engine._check_key_exists(data, "key3")

        assert result.passed is False
        assert "does not exist" in result.message

    def test_output_exists_valid(self):
        """Test output_exists with valid output."""
        result = self.engine._check_output_exists({"success": True})

        assert result.passed is True

    def test_output_not_empty_valid(self):
        """Test output_not_empty with non-empty output."""
        result = self.engine._check_output_not_empty({"data": "value"})

        assert result.passed is True

    def test_output_success_valid(self):
        """Test output_success with success=True."""
        result = self.engine._check_output_success({"success": True})

        assert result.passed is True

    def test_output_success_with_string(self):
        """Test output_success with success as string."""
        result = self.engine._check_output_success({"success": "true"})

        assert result.passed is True

    def test_performance_valid(self):
        """Test performance with duration under threshold."""
        result = self.engine._check_performance(100, threshold_ms=5000)

        assert result.passed is True
        assert "100ms < 5000ms" in result.message

    def test_cost_within_budget_valid(self):
        """Test cost_within_budget with cost under budget."""
        result = self.engine._check_cost_within_budget(50, budget=100)

        assert result.passed is True


class TestRunAssertions:
    """Tests for run_assertions method."""

    def test_run_assertions_all_pass(self):
        """Test running assertions when all pass."""
        engine = AssertionEngine()

        assertions = [
            {"check": "string_not_empty", "value": "hello"},
            {"check": "value_equal", "value": 5, "expected": 5},
        ]

        results = engine.run_assertions(assertions)

        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_run_assertions_some_fail(self):
        """Test running assertions when some fail."""
        engine = AssertionEngine()

        assertions = [
            {"check": "string_not_empty", "value": "hello"},
            {"check": "value_equal", "value": 5, "expected": 10},
        ]

        results = engine.run_assertions(assertions)

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    def test_run_assertions_with_error(self):
        """Test running assertions with execution error."""
        engine = AssertionEngine()

        assertions = [
            {"check": "nonexistent_check", "value": "test"},
        ]

        results = engine.run_assertions(assertions)

        assert len(results) == 1
        assert results[0].passed is False
        assert "unknown check function" in results[0].message.lower()


class TestValidateAssertions:
    """Tests for validate_assertions method."""

    def test_validate_assertions_all_pass(self):
        """Test validating assertions when all pass."""
        engine = AssertionEngine()

        assertions = [
            {"check": "string_not_empty", "value": "hello"},
            {"check": "value_equal", "value": 5, "expected": 5},
        ]

        result = engine.validate_assertions(assertions)

        assert result is True

    def test_validate_assertions_some_fail(self):
        """Test validating assertions when some fail."""
        engine = AssertionEngine()

        assertions = [
            {"check": "string_not_empty", "value": "hello"},
            {"check": "value_equal", "value": 5, "expected": 10},
        ]

        result = engine.validate_assertions(assertions)

        assert result is False


class TestGetAssertionsByType:
    """Tests for get_assertions_by_type method."""

    def test_get_pre_assertions(self):
        """Test filtering pre assertions."""
        engine = AssertionEngine()

        assertions = [
            {"check": "check1", "type": "pre"},
            {"check": "check2", "type": "post"},
            {"check": "check3"},  # Default is pre
        ]

        pre = engine.get_assertions_by_type(assertions, "pre")

        assert len(pre) == 2
        assert all(a.get("type", "pre") == "pre" for a in pre)

    def test_get_post_assertions(self):
        """Test filtering post assertions."""
        engine = AssertionEngine()

        assertions = [
            {"check": "check1", "type": "pre"},
            {"check": "check2", "type": "post"},
            {"check": "check3", "type": "post"},
        ]

        post = engine.get_assertions_by_type(assertions, "post")

        assert len(post) == 2
        assert all(a.get("type") == "post" for a in post)


class TestConditionEvaluation:
    """Tests for apply_conditions method."""

    def test_apply_conditions_simple(self):
        """Test simple condition evaluation."""
        engine = AssertionEngine()

        condition = "10 > 5"
        result = engine.apply_conditions(condition)

        assert result is True

    def test_apply_conditions_with_context(self):
        """Test condition with context variables."""
        engine = AssertionEngine()

        condition = "${value} > 5"
        context = {"value": 10}
        result = engine.apply_conditions(condition, context)

        assert result is True

    def test_apply_conditions_equal(self):
        """Test condition with equality check."""
        engine = AssertionEngine()

        condition = "${value} == 10"
        context = {"value": 10}
        result = engine.apply_conditions(condition, context)

        assert result is True

    def test_apply_conditions_no_condition(self):
        """Test with no condition."""
        engine = AssertionEngine()

        result = engine.apply_conditions(None)

        assert result is True


class TestIntegrationWithTracer:
    """Tests for integration with STOPTracer."""

    def test_assertions_with_tracer_context(self):
        """Test assertions can use tracer context."""
        from skill_observability_toolkit.stop.tracer import STOPTracer

        tracer = STOPTracer()
        tracer.start_trace("test_trace")

        engine = AssertionEngine()

        with tracer.start_span(name="pre_assertions") as span:
            assertions = [
                {"check": "value_equal", "value": 5, "expected": 5},
            ]

            results = engine.run_assertions(assertions)

            assert len(results) == 1
            assert results[0].passed is True

            # Record results as score
            trust_score = engine.calculate_trust_score(results)
            span.score("assertions_passed", trust_score, "NUMERIC")
            span.end()

        trace_data = tracer.end_trace()

        # Verify score recorded
        assert len(trace_data["spans"]) == 2
        span0 = trace_data["spans"][1]
        assert len(span0.get("scores", [])) >= 1
