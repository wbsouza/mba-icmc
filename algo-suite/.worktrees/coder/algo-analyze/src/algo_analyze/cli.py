"""CLI for algo-analyze."""

from __future__ import annotations

from pathlib import Path

import structlog
import typer
from algo_core.logging import configure_logging, run_with_logging

app = typer.Typer(
    name="algo-analyze",
    help="Aggregate experiment results into the Chapter-4 summary; metrics + ablations (planned).",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Tool entry point; subcommands are listed below."""


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("algo-analyze"))


@app.command()
def summary(
    out: str = typer.Option(
        "", "--out", help="CSV output path (default: <data_root>/analysis/summary.csv)."
    ),
) -> None:
    """Aggregate every successful experiment into one deterministic Chapter-4 CSV."""
    from algo_analyze.config import load_analyze_config
    from algo_analyze.summary import (
        discover_experiment_manifests,
        load_summary_rows,
        write_summary_csv,
    )

    log = structlog.get_logger("analyze")
    config = load_analyze_config()
    for line in config.provenance:
        log.info("config", provenance=line)

    out_path = Path(out) if out else config.data_root / "analysis" / "summary.csv"
    try:
        manifests = discover_experiment_manifests(config.data_root)
        rows = load_summary_rows(manifests)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc

    write_summary_csv(rows, out_path)
    typer.echo(
        f"summary: {len(rows)} run(s) from {len(manifests)} experiment(s) -> {out_path}"
    )


def main() -> None:
    """Console-script entry point (see [project.scripts])."""
    configure_logging()
    run_with_logging(app, logger_name="analyze")


if __name__ == "__main__":
    main()
