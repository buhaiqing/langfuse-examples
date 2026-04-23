"""CLI command for comparing skill versions."""

import json
from pathlib import Path
from typing import Dict, Any, List

import typer

app = typer.Typer(help="Compare skill versions")


def compare_versions(v1_metrics: Dict[str, Any], v2_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two version metrics."""
    changes = {}
    
    for key in v1_metrics:
        if key in v2_metrics:
            old_val = v1_metrics[key]
            new_val = v2_metrics[key]
            
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                if old_val != 0:
                    change_pct = ((new_val - old_val) / old_val) * 100
                    changes[key] = {
                        "old": old_val,
                        "new": new_val,
                        "change": f"{change_pct:+.2f}%",
                        "improved": change_pct > 0 if "success" in key or "score" in key else change_pct < 0
                    }
    
    return changes


@app.command()
def versions(
    version1: str = typer.Option(..., "--v1", help="First version"),
    version2: str = typer.Option(..., "--v2", help="Second version"),
    metric: str = typer.Option("all", "--metric", "-m", help="Metric to compare"),
    format: str = typer.Option("text", "--format", "-f", help="Output format"),
):
    """Compare two skill versions."""
    # Simulated metrics (in real impl, load from trace files)
    v1_metrics = {
        "success_rate": 0.85,
        "avg_latency_ms": 500,
        "p95_latency_ms": 800,
        "trust_score": 0.80,
    }
    
    v2_metrics = {
        "success_rate": 0.92,
        "avg_latency_ms": 450,
        "p95_latency_ms": 750,
        "trust_score": 0.88,
    }
    
    changes = compare_versions(v1_metrics, v2_metrics)
    
    # Output
    typer.echo(f"\nComparing {version1} vs {version2}\n")
    typer.echo(f"{'Metric':<20} | {version1:<12} | {version2:<12} | Change")
    typer.echo("-" * 65)
    
    for metric_name, change_data in changes.items():
        indicator = "✅" if change_data['improved'] else "❌"
        typer.echo(f"{metric_name:<20} | {change_data['old']:<12.2f} | {change_data['new']:<12.2f} | {indicator} {change_data['change']}")
    
    typer.echo()


if __name__ == "__main__":
    app()
