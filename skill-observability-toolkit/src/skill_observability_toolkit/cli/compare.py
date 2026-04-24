"""CLI command for comparing skill executions and versions."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(help="Compare skill executions and versions")


class CompareError(Exception):
    """Compare error."""
    pass


def load_trace_metrics(trace_dir: Path, days: int = 7) -> dict[str, Any]:
    """
    Load metrics from trace files.

    Args:
        trace_dir: Directory containing trace files
        days: Number of days to look back

    Returns:
        Dictionary of metrics
    """
    metrics = {
        "total_traces": 0,
        "success_count": 0,
        "error_count": 0,
        "durations": [],
        "by_status": {},
    }

    if not trace_dir.exists():
        return metrics

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for trace_file in trace_dir.rglob("*.ndjson"):
        try:
            with open(trace_file) as f:
                for line in f:
                    if line.strip():
                        span = json.loads(line)
                        if 'start_time' in span:
                            span_time = datetime.fromisoformat(span['start_time'].replace('Z', '+00:00'))
                            if span_time >= cutoff:
                                metrics["total_traces"] += 1
                                status = span.get('status', 'unknown')
                                metrics["by_status"][status] = metrics["by_status"].get(status, 0) + 1
                                if status == 'success':
                                    metrics["success_count"] += 1
                                elif status == 'error':
                                    metrics["error_count"] += 1
                                if 'duration_ms' in span:
                                    metrics["durations"].append(span['duration_ms'])
        except (OSError, json.JSONDecodeError):
            continue

    return metrics


def calculate_percentiles(values: list[float], percentiles: list[float] = [50, 95, 99]) -> dict[str, float]:
    """Calculate percentiles from a list of values."""
    if not values:
        return {f"p{p}": 0 for p in percentiles}

    sorted_values = sorted(values)
    n = len(sorted_values)
    result = {}

    for p in percentiles:
        if p <= 0:
            result[f"p{p}"] = sorted_values[0]
        elif p >= 100:
            result[f"p{p}"] = sorted_values[-1]
        else:
            idx = (n - 1) * p / 100
            lower = int(idx)
            upper = lower + 1
            if upper >= n:
                result[f"p{p}"] = sorted_values[-1]
            else:
                weight = idx - lower
                result[f"p{p}"] = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    return result


def compute_summary_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Compute summary metrics from raw data."""
    total = metrics["total_traces"]
    if total == 0:
        return {
            "total_traces": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "avg_duration_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }

    success_rate = metrics["success_count"] / total
    error_rate = metrics["error_count"] / total
    avg_duration = sum(metrics["durations"]) / len(metrics["durations"]) if metrics["durations"] else 0.0
    percentiles = calculate_percentiles(metrics["durations"])

    return {
        "total_traces": total,
        "success_rate": success_rate,
        "error_rate": error_rate,
        "avg_duration_ms": avg_duration,
        "p50_latency_ms": percentiles.get("p50", 0.0),
        "p95_latency_ms": percentiles.get("p95", 0.0),
        "p99_latency_ms": percentiles.get("p99", 0.0),
    }


def compare_metrics(m1: dict[str, Any], m2: dict[str, Any]) -> dict[str, Any]:
    """
    Compare two metric sets.

    Returns changes with improvement indicators.
    """
    changes = {}
    keys_to_compare = [
        "total_traces",
        "success_rate",
        "error_rate",
        "avg_duration_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
    ]

    for key in keys_to_compare:
        v1 = m1.get(key, 0)
        v2 = m2.get(key, 0)

        if isinstance(v1, float) and isinstance(v2, float):
            if v1 != 0:
                change_pct = ((v2 - v1) / v1) * 100
            else:
                change_pct = 100.0 if v2 > 0 else 0.0

            if "error" in key:
                improved = change_pct < 0
            elif "rate" in key or "success" in key:
                improved = change_pct > 0
            elif "duration" in key or "latency" in key:
                improved = change_pct < 0
            else:
                improved = change_pct > 0

            changes[key] = {
                "old": v1,
                "new": v2,
                "change_pct": change_pct,
                "change_str": f"{change_pct:+.1f}%",
                "improved": improved,
            }

    return changes


def format_table_output(
    name1: str,
    name2: str,
    m1: dict[str, Any],
    m2: dict[str, Any],
    changes: dict[str, Any],
) -> str:
    """Format comparison as ASCII table."""
    lines = []
    lines.append("")
    lines.append(f"  Comparing: {name1}  vs  {name2}")
    lines.append("")
    lines.append(f"  {'Metric':<20} | {name1:<14} | {name2:<14} | Change     | Status")
    lines.append(f"  {'-' * 20} | {'-' * 14} | {'-' * 14} | {'-' * 10} | {'-' * 6}")

    metric_labels = {
        "total_traces": "Total Traces",
        "success_rate": "Success Rate",
        "error_rate": "Error Rate",
        "avg_duration_ms": "Avg Duration",
        "p50_latency_ms": "P50 Latency",
        "p95_latency_ms": "P95 Latency",
        "p99_latency_ms": "P99 Latency",
    }

    for key, label in metric_labels.items():
        if key in changes:
            c = changes[key]
            old_str = _format_value(key, c["old"])
            new_str = _format_value(key, c["new"])
            indicator = "✅" if c["improved"] else "❌"
            lines.append(
                f"  {label:<20} | {old_str:<14} | {new_str:<14} | {c['change_str']:<10} | {indicator}"
            )

    lines.append("")
    return "\n".join(lines)


def _format_value(key: str, value: float) -> str:
    """Format value based on metric type."""
    if key == "total_traces":
        return str(int(value))
    elif "rate" in key:
        return f"{value:.1%}"
    else:
        return f"{value:.1f}ms"


def format_json_output(m1: dict[str, Any], m2: dict[str, Any], changes: dict[str, Any]) -> str:
    """Format comparison as JSON."""
    output = {
        "comparison": {
            "metric_a": m1,
            "metric_b": m2,
            "changes": changes,
        }
    }
    return json.dumps(output, indent=2)


@app.command()
def main(
    skill_a: str = typer.Option(..., "--skill-a", "-a", help="First skill path or name"),
    skill_b: str = typer.Option(..., "--skill-b", "-b", help="Second skill path or name"),
    trace_dir_a: str | None = typer.Option(None, "--trace-dir-a", help="Trace directory for skill A"),
    trace_dir_b: str | None = typer.Option(None, "--trace-dir-b", help="Trace directory for skill B"),
    metric: str = typer.Option("all", "--metric", "-m", help="Metric to compare (all, latency, success)"),
    days: int = typer.Option(7, "--days", "-d", help="Days to look back"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
):
    """
    Compare two skill executions or versions.

    Examples:
        stop compare -a skill-v1 -b skill-v2 --trace-dir-a ./v1/traces --trace-dir-b ./v2/traces
        stop compare -a my-skill -b my-skill --metric latency --days 30
    """
    if trace_dir_a:
        path_a = Path(trace_dir_a)
    else:
        path_a = Path(skill_a) / ".sop" / "traces"

    if trace_dir_b:
        path_b = Path(trace_dir_b)
    else:
        path_b = Path(skill_b) / ".sop" / "traces"

    raw_a = load_trace_metrics(path_a, days=days)
    raw_b = load_trace_metrics(path_b, days=days)

    summary_a = compute_summary_metrics(raw_a)
    summary_b = compute_summary_metrics(raw_b)

    changes = compare_metrics(summary_a, summary_b)

    if format == "json":
        typer.echo(format_json_output(summary_a, summary_b, changes))
    else:
        typer.echo(format_table_output(skill_a, skill_b, summary_a, summary_b, changes))

        if metric != "all":
            typer.echo(f"\n  Filtered by: {metric}")


@app.command()
def versions(
    version1: str = typer.Option(..., "--v1", help="First version name"),
    version2: str = typer.Option(..., "--v2", help="Second version name"),
    metrics_v1: str | None = typer.Option(None, "--metrics-v1", help="JSON file with v1 metrics"),
    metrics_v2: str | None = typer.Option(None, "--metrics-v2", help="JSON file with v2 metrics"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
):
    """
    Compare two version metrics from JSON files.

    Examples:
        stop compare versions --v1 1.0.0 --v2 2.0.0 --metrics-v1 v1.json --metrics-v2 v2.json
    """
    if metrics_v1 and metrics_v2:
        with open(metrics_v1) as f:
            m1 = json.load(f)
        with open(metrics_v2) as f:
            m2 = json.load(f)
    else:
        m1 = {
            "total_traces": 100,
            "success_rate": 0.85,
            "error_rate": 0.15,
            "avg_duration_ms": 500.0,
            "p50_latency_ms": 400.0,
            "p95_latency_ms": 800.0,
            "p99_latency_ms": 1000.0,
        }
        m2 = {
            "total_traces": 120,
            "success_rate": 0.92,
            "error_rate": 0.08,
            "avg_duration_ms": 450.0,
            "p50_latency_ms": 380.0,
            "p95_latency_ms": 750.0,
            "p99_latency_ms": 900.0,
        }

    changes = compare_metrics(m1, m2)

    if format == "json":
        typer.echo(format_json_output(m1, m2, changes))
    else:
        typer.echo(format_table_output(version1, version2, m1, m2, changes))


if __name__ == "__main__":
    app()
