"""CLI command for generating tracing reports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(help="Generate tracing report from trace.ndjson")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STOP Protocol Trace Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            color: #666;
            margin-top: 8px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .status-success {{ background: #22c55e22; color: #16a34a; }}
        .status-error {{ background: #ef444422; color: #dc2626; }}
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 20px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 STOP Protocol Trace Report</h1>
            <p>Generated: {generated_at}</p>
        </div>

        <div class="card">
            <h2>📈 Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_traces}</div>
                    <div class="metric-label">Total Traces</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{success_rate}</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{avg_duration}ms</div>
                    <div class="metric-label">Avg Duration</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{p95_duration}ms</div>
                    <div class="metric-label">P95 Latency</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📊 Performance Distribution</h2>
            <div class="chart-container">
                <canvas id="latencyChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>📋 Status Distribution</h2>
            <div class="chart-container">
                <canvas id="statusChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>🔍 Recent Traces</h2>
            <table>
                <thead>
                    <tr>
                        <th>Trace ID</th>
                        <th>Span</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {trace_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>STOP Protocol Observability Platform</p>
        </div>
    </div>

    <script>
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        new Chart(latencyCtx, {{
            type: 'bar',
            data: {{
                labels: ['P50', 'P95', 'P99'],
                datasets: [{{
                    label: 'Latency (ms)',
                    data: [{p50}, {p95}, {p99}],
                    backgroundColor: ['#667eea', '#764ba2', '#f59e0b'],
                    borderRadius: 8,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'doughnut',
            data: {{
                labels: {status_labels},
                datasets: [{{
                    data: {status_values},
                    backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'],
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
            }}
        }});
    </script>
</body>
</html>
"""


def load_traces(trace_file: str) -> list[dict[str, Any]]:
    """Load traces from NDJSON file."""
    traces = []
    with open(trace_file) as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    return traces


def calculate_metrics(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate metrics from traces."""
    if not traces:
        return {
            "total_traces": 0,
            "success_rate": "0%",
            "avg_duration_ms": 0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "by_status": {},
        }

    durations = [t.get('duration_ms', 0) for t in traces if 'duration_ms' in t]
    statuses = [t.get('status', 'unknown') for t in traces]

    sorted_durations = sorted(durations)
    p50_idx = int(len(sorted_durations) * 0.5) if sorted_durations else 0
    p95_idx = int(len(sorted_durations) * 0.95) if sorted_durations else 0
    p99_idx = int(len(sorted_durations) * 0.99) if sorted_durations else 0

    success_count = sum(1 for s in statuses if s == 'success')
    success_rate = f"{(success_count / len(statuses) * 100):.1f}%" if statuses else "0%"

    by_status = {}
    for s in statuses:
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total_traces": len(traces),
        "success_rate": success_rate,
        "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
        "p50_latency_ms": sorted_durations[p50_idx] if sorted_durations else 0,
        "p95_latency_ms": sorted_durations[p95_idx] if sorted_durations else 0,
        "p99_latency_ms": sorted_durations[p99_idx] if sorted_durations else 0,
        "by_status": by_status,
        "recent_traces": traces[-20:] if len(traces) > 20 else traces,
    }


def generate_html_report(metrics: dict[str, Any], generated_at: str) -> str:
    """Generate HTML report."""
    status_labels = list(metrics["by_status"].keys())
    status_values = list(metrics["by_status"].values())

    trace_rows = []
    for trace in metrics.get("recent_traces", []):
        status = trace.get('status', 'unknown')
        status_class = 'status-success' if status == 'success' else 'status-error'
        trace_rows.append(f"""
            <tr>
                <td>{trace.get('trace_id', 'N/A')}</td>
                <td>{trace.get('span_id', 'N/A')}</td>
                <td><span class="status-badge {status_class}">{status}</span></td>
                <td>{trace.get('duration_ms', 0):.1f}ms</td>
                <td>{trace.get('start_time', 'N/A')}</td>
            </tr>
        """)

    return HTML_TEMPLATE.format(
        generated_at=generated_at,
        total_traces=metrics.get('total_traces', 0),
        success_rate=metrics.get('success_rate', '0%'),
        avg_duration=metrics.get('avg_duration_ms', 0),
        p50=metrics.get('p50_latency_ms', 0),
        p95=metrics.get('p95_latency_ms', 0),
        p99=metrics.get('p99_latency_ms', 0),
        p95_duration=metrics.get('p95_latency_ms', 0),
        status_labels=status_labels,
        status_values=status_values,
        trace_rows="".join(trace_rows),
    )


def generate_markdown_report(metrics: dict[str, Any], generated_at: str) -> str:
    """Generate Markdown report."""
    return f"""# Tracing Report

**Generated**: {generated_at}

## Summary

| Metric | Value |
|--------|-------|
| Total Traces | {metrics.get('total_traces', 0)} |
| Success Rate | {metrics.get('success_rate', 'N/A')} |
| P50 Latency | {metrics.get('p50_latency_ms', 0):.1f} ms |
| P95 Latency | {metrics.get('p95_latency_ms', 0):.1f} ms |
| P99 Latency | {metrics.get('p99_latency_ms', 0):.1f} ms |
| Average Duration | {metrics.get('avg_duration_ms', 0):.1f} ms |

## Status Distribution

{json.dumps(metrics.get('by_status', {}), indent=2)}

## Recent Traces

| Trace ID | Span | Status | Duration | Time |
|----------|------|--------|----------|------|
""" + "\n".join([
        f"| {t.get('trace_id', 'N/A')} | {t.get('span_id', 'N/A')} | {t.get('status', 'unknown')} | {t.get('duration_ms', 0):.1f}ms | {t.get('start_time', 'N/A')} |"
        for t in metrics.get("recent_traces", [])[-10:]
    ])


@app.command()
def generate(
    input: str = typer.Option("trace.ndjson", "--input", "-i", help="Input trace file"),
    output: str = typer.Option("report.html", "--output", "-o", help="Output report file"),
    format: str = typer.Option("html", "--format", "-f", help="Output format (html, markdown)"),
):
    """
    Generate a tracing report.

    Examples:
        stop report generate -i trace.ndjson -o report.html --format html
        stop report generate -i trace.ndjson -o report.md --format markdown
    """
    input_path = Path(input)

    if not input_path.exists():
        typer.echo(f"❌ Trace file not found: {input}", err=True)
        raise typer.Exit(1)

    traces = load_traces(str(input_path))
    metrics = calculate_metrics(traces)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if format == "html":
        report = generate_html_report(metrics, generated_at)
    elif format == "markdown":
        report = generate_markdown_report(metrics, generated_at)
    else:
        typer.echo(f"❌ Unknown format: {format}", err=True)
        raise typer.Exit(1)

    output_path = Path(output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    typer.echo(f"✅ Report generated: {output}")


if __name__ == "__main__":
    app()
