"""CLI entry point."""
import typer

from skill_observability_toolkit.cli.compare import app as compare_app
from skill_observability_toolkit.cli.init import app as init_app
from skill_observability_toolkit.cli.observe import app as observe_app
from skill_observability_toolkit.cli.report import app as report_app
from skill_observability_toolkit.cli.run import app as run_app
from skill_observability_toolkit.cli.trust_score import app as trust_score_app
from skill_observability_toolkit.cli.validate import app as validate_app

app = typer.Typer(
    name="stop",
    help="STOP Protocol CLI - Skill Transparency & Observability Protocol",
)
app.add_typer(init_app, name="init")
app.add_typer(validate_app, name="validate")
app.add_typer(run_app, name="run")
app.add_typer(report_app, name="report")
app.add_typer(compare_app, name="compare")
app.add_typer(trust_score_app, name="trust-score")
app.add_typer(observe_app, name="observe")


if __name__ == "__main__":
    app()
