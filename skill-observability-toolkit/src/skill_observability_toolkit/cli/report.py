"""CLI command for generating tracing reports."""

import json
from pathlib import Path
from datetime import datetime

import typer
from typing import List, Dict, Any

app = typer.Typer(help="Generate tracing report from trace.ndjson")


def load_traces(trace_file: str) -> List[Dict[str, Any]]:
    """Load traces from NDJSON file."""
    traces = []
    with open(trace_file, 'r') as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    return traces


def calculate_metrics(traces: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate metrics from traces."""
    if not traces:
        return {}
    
    durations = [t.get('duration_ms', 0) for t in traces if 'duration_ms' in t]
    statuses = [t.get('status', 'unknown') for t in traces]
    
    # Calculate latency percentiles
    sorted_durations = sorted(durations)
    p50_idx = int(len(sorted_durations) * 0.5)
    p95_idx = int(len(sorted_durations) * 0.95)
    p99_idx = int(len(sorted_durations) * 0.99)
    
    # Calculate success rate
    success_count = sum(1 for s in statuses if s == 'success')
    success_rate = success_count / len(statuses) if statuses else 0
    
    return {
        "total_traces": len(traces),
        "success_rate": f"{success_rate:.2%}",
        "latency_p50_ms": sorted_durations[p50_idx] if sorted_durations else 0,
        "latency_p95_ms": sorted_durations[p95_idx] if sorted_durations else 0,
        "latency_p99_ms": sorted_durations[p99_idx] if sorted_durations else 0,
        "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
    }


@app.command()
def generate(
    input: str = typer.Option("trace.ndjson", "--input", "-i", help="Input trace file"),
    output: str = typer.Option("report.md", "--output", "-o", help="Output report file"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown/html)"),
):
    """Generate a tracing report."""
    input_path = Path(input)
    
    if not input_path.exists():
        typer.echo(f"❌ Trace file not found: {input}", err=True)
        raise typer.Exit(1)
    
    # Load and analyze traces
    traces = load_traces(str(input_path))
    metrics = calculate_metrics(traces)
    
    # Generate report
    if format == "markdown":
        report = f"""# Tracing Report

**Generated**: {datetime.now().isoformat()}

## Summary

| Metric | Value |
|--------|-------|
| Total Traces | {metrics.get('total_traces', 0)} |
| Success Rate | {metrics.get('success_rate', 'N/A')} |
| P50 Latency | {metrics.get('latency_p50_ms', 0)} ms |
| P95 Latency | {metrics.get('latency_p95_ms', 0)} ms |
| P99 Latency | {metrics.get('latency_p99_ms', 0)} ms |
| Average Duration | {metrics.get('avg_duration_ms', 0):.2f} ms |

## Details

Total traces analyzed: {len(traces)}
"""
    else:
        typer.echo("HTML format not implemented yet", err=True)
        raise typer.Exit(1)
    
    # Write report
    output_path = Path(output)
    with open(output_path, 'w') as f:
        f.write(report)
    
    typer.echo(f"✅ Report generated: {output}")


if __name__ == "__main__":
    app()
