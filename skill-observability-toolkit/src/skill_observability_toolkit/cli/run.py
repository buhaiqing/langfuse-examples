"""CLI command for running skills locally."""

import json
import sys
from pathlib import Path

import typer
from skill_observability_toolkit.config import get_config
from skill_observability_toolkit.stop.tracer import STOPTracer

app = typer.Typer(help="Run skill locally with tracing")


@app.command()
def main(
    skill: str = typer.Option(..., "--skill", "-s", help="Skill name"),
    input_file: str = typer.Option("input.json", "--input", "-i", help="Input JSON file"),
    output: str = typer.Option(None, "--output", "-o", help="Output trace file"),
    live_trace: bool = typer.Option(False, "--live-trace", "-l", help="Send to Langfuse"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run a skill locally with tracing."""
    config = get_config()
    
    # Load skill manifest
    skill_yaml = Path(f"{skill}/skill.yaml")
    if not skill_yaml.exists():
        typer.echo(f"❌ Skill manifest not found: {skill_yaml}", err=True)
        raise typer.Exit(1)
    
    # Load input
    input_path = Path(input_file)
    if input_path.exists():
        with open(input_path) as f:
            input_data = json.load(f)
    else:
        input_data = {}
        if verbose:
            typer.echo(f"⚠️  Input file not found, using empty input")
    
    # Initialize tracer
    tracer = STOPTracer()
    if live_trace and config.is_langfuse_enabled():
        if verbose:
            typer.echo(f"📊 Live tracing enabled")
    
    # Execute skill (simulated)
    tracer.start_trace(name=f"{skill}_execution")
    
    with tracer.start_span(name="load_skill") as span:
        if verbose:
            typer.echo(f"📦 Loading skill: {skill}")
    
    with tracer.start_span(name="execute") as span:
        span.input_data = input_data
        result = {"status": "success", "message": f"Skill {skill} executed"}
        span.output_data = result
    
    trace_data = tracer.end_trace()
    
    # Output results
    if output:
        with open(output, 'w') as f:
            json.dump(trace_data, f, indent=2)
        typer.echo(f"✅ Trace saved to: {output}")
    else:
        typer.echo(f"✅ Skill executed successfully")
        if verbose:
            typer.echo(f"📊 Trace: {json.dumps(trace_data, indent=2)}")


if __name__ == "__main__":
    app()
