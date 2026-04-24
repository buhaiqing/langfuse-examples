"""Tests for compare command."""

import json
import tempfile
from pathlib import Path

import pytest

from skill_observability_toolkit.cli.compare import (
    calculate_percentiles,
    compare_metrics,
    compute_summary_metrics,
    format_json_output,
    format_table_output,
    load_trace_metrics,
)


class TestLoadTraceMetrics:
    """Test load_trace_metrics function."""

    def test_load_empty_directory(self):
        """Test loading from non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics = load_trace_metrics(Path(tmpdir))
            assert metrics["total_traces"] == 0
            assert metrics["success_count"] == 0

    def test_load_with_valid_traces(self):
        """Test loading valid NDJSON traces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "trace.ndjson"
            trace_content = [
                json.dumps({
                    "trace_id": "t1",
                    "span_id": "s1",
                    "start_time": "2026-04-24T10:00:00Z",
                    "status": "success",
                    "duration_ms": 100.0,
                }),
                json.dumps({
                    "trace_id": "t2",
                    "span_id": "s2",
                    "start_time": "2026-04-24T11:00:00Z",
                    "status": "success",
                    "duration_ms": 200.0,
                }),
                json.dumps({
                    "trace_id": "t3",
                    "span_id": "s3",
                    "start_time": "2026-04-24T12:00:00Z",
                    "status": "error",
                    "duration_ms": 50.0,
                }),
            ]
            trace_file.write_text("\n".join(trace_content))

            metrics = load_trace_metrics(Path(tmpdir))

            assert metrics["total_traces"] == 3
            assert metrics["success_count"] == 2
            assert metrics["error_count"] == 1
            assert len(metrics["durations"]) == 3

    def test_load_with_old_traces(self):
        """Test filtering old traces by days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "trace.ndjson"
            trace_content = [
                json.dumps({
                    "trace_id": "t1",
                    "span_id": "s1",
                    "start_time": "2026-04-10T10:00:00Z",
                    "status": "success",
                    "duration_ms": 100.0,
                }),
            ]
            trace_file.write_text("\n".join(trace_content))

            metrics = load_trace_metrics(Path(tmpdir), days=7)

            assert metrics["total_traces"] == 0


class TestCalculatePercentiles:
    """Test calculate_percentiles function."""

    def test_empty_list(self):
        """Test with empty input."""
        result = calculate_percentiles([])
        assert result["p50"] == 0
        assert result["p95"] == 0
        assert result["p99"] == 0

    def test_single_value(self):
        """Test with single value."""
        result = calculate_percentiles([100.0])
        assert result["p50"] == 100.0
        assert result["p95"] == 100.0
        assert result["p99"] == 100.0

    def test_sorted_values(self):
        """Test with sorted values."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        result = calculate_percentiles(values)

        assert result["p50"] == pytest.approx(55.0, rel=0.01)
        assert result["p95"] == pytest.approx(95.5, rel=0.1)
        assert result["p99"] == pytest.approx(99.1, rel=0.1)


class TestComputeSummaryMetrics:
    """Test compute_summary_metrics function."""

    def test_empty_metrics(self):
        """Test with empty raw metrics."""
        raw = {
            "total_traces": 0,
            "success_count": 0,
            "error_count": 0,
            "durations": [],
        }
        result = compute_summary_metrics(raw)

        assert result["total_traces"] == 0
        assert result["success_rate"] == 0.0
        assert result["error_rate"] == 0.0
        assert result["avg_duration_ms"] == 0.0

    def test_with_valid_metrics(self):
        """Test with valid raw metrics."""
        raw = {
            "total_traces": 10,
            "success_count": 8,
            "error_count": 2,
            "durations": [100.0, 200.0, 150.0, 300.0],
        }
        result = compute_summary_metrics(raw)

        assert result["total_traces"] == 10
        assert result["success_rate"] == 0.8
        assert result["error_rate"] == 0.2
        assert result["avg_duration_ms"] == 187.5


class TestCompareMetrics:
    """Test compare_metrics function."""

    def test_improved_success_rate(self):
        """Test success rate improvement detection."""
        m1 = {"success_rate": 0.80, "total_traces": 100}
        m2 = {"success_rate": 0.90, "total_traces": 120}

        result = compare_metrics(m1, m2)

        assert result["success_rate"]["improved"] is True
        assert result["success_rate"]["change_pct"] == pytest.approx(12.5, rel=0.1)

    def test_improved_latency(self):
        """Test latency improvement detection."""
        m1 = {"avg_duration_ms": 500.0, "total_traces": 100}
        m2 = {"avg_duration_ms": 400.0, "total_traces": 100}

        result = compare_metrics(m1, m2)

        assert result["avg_duration_ms"]["improved"] is True
        assert result["avg_duration_ms"]["change_pct"] == pytest.approx(-20.0, rel=0.1)

    def test_improved_error_rate(self):
        """Test error rate improvement detection."""
        m1 = {"error_rate": 0.20, "total_traces": 100}
        m2 = {"error_rate": 0.10, "total_traces": 100}

        result = compare_metrics(m1, m2)

        assert result["error_rate"]["improved"] is True


class TestFormatOutput:
    """Test output formatting functions."""

    def test_format_json_output(self):
        """Test JSON output formatting."""
        m1 = {"total_traces": 100, "success_rate": 0.85}
        m2 = {"total_traces": 120, "success_rate": 0.92}
        changes = {
            "total_traces": {"old": 100, "new": 120, "change_pct": 20.0, "change_str": "+20.0%"},
            "success_rate": {"old": 0.85, "new": 0.92, "change_pct": 8.2, "change_str": "+8.2%"},
        }

        result = format_json_output(m1, m2, changes)
        parsed = json.loads(result)

        assert "comparison" in parsed
        assert parsed["comparison"]["metric_a"]["total_traces"] == 100
        assert parsed["comparison"]["metric_b"]["total_traces"] == 120

    def test_format_table_output(self):
        """Test table output formatting."""
        m1 = {"total_traces": 100, "success_rate": 0.85}
        m2 = {"total_traces": 120, "success_rate": 0.92}
        changes = {
            "total_traces": {"old": 100, "new": 120, "change_pct": 20.0, "change_str": "+20.0%", "improved": True},
            "success_rate": {"old": 0.85, "new": 0.92, "change_pct": 8.2, "change_str": "+8.2%", "improved": True},
        }

        result = format_table_output("v1", "v2", m1, m2, changes)

        assert "Comparing: v1  vs  v2" in result
        assert "Total Traces" in result
        assert "Success Rate" in result
        assert "✅" in result
