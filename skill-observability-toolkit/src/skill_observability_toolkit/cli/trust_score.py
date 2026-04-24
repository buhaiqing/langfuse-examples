"""CLI command for displaying Trust Score."""

import json

import typer

app = typer.Typer(help="Display Trust Score for a skill")


def calculate_trust_score(results: list) -> float:
    """Calculate trust score from results."""
    if not results:
        return 1.0

    passed_count = sum(1 for r in results if r.get('passed', False))
    return passed_count / len(results)


@app.command()
def show(
    skill: str = typer.Option(..., "--skill", "-s", help="Skill name"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
):
    """Show Trust Score for a skill."""
    # Load assertion results (simulated)
    results = [
        {"passed": True, "assertion": "test1"},
        {"passed": True, "assertion": "test2"},
        {"passed": False, "assertion": "test3"},
        {"passed": True, "assertion": "test4"},
        {"passed": True, "assertion": "test5"},
    ]

    score = calculate_trust_score(results)

    if format == "json":
        output = {
            "skill": skill,
            "trust_score": score,
            "period_days": days,
            "total_assertions": len(results),
            "passed_assertions": sum(1 for r in results if r['passed']),
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        # Text format with ASCII chart
        bar_length = 40
        filled = int(score * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        typer.echo(f"""
Trust Score for: {skill}
Period: Last {days} days

Score: [{bar}] {score:.2%}

Details:
  Total Assertions: {len(results)}
  Passed: {sum(1 for r in results if r['passed'])}
  Failed: {sum(1 for r in results if not r['passed'])}
""")


if __name__ == "__main__":
    app()
