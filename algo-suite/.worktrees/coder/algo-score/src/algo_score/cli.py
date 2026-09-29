"""CLI for algo-score."""

from __future__ import annotations

from datetime import date
from typing import NoReturn

import typer
from algo_core import layout

from algo_score.events import build_event_features
from algo_score.scorers.lexicon import DEFAULT_MODEL_VERSION
from algo_score.scoring import run_lm_scoring

app = typer.Typer(
    name="algo-score",
    help="Score sentiment (FinBERT + Loughran-McDonald, per-currency) and events.",
    no_args_is_help=True,
    add_completion=False,
)

_USAGE_ERROR = 2


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    scorer: str | None = typer.Option(None, "--scorer", help="Sentiment scorer: lm."),
    source: str = typer.Option("gdelt", "--source", help="News source fixture."),
    month: str | None = typer.Option(None, "--month", help="Single month, YYYY-MM."),
    from_: str | None = typer.Option(None, "--from", help="Range start, YYYY-MM-DD."),
    to: str | None = typer.Option(None, "--to", help="Range end, YYYY-MM-DD."),
    model_version: str = typer.Option(
        DEFAULT_MODEL_VERSION, "--model-version", help="Scorer model/cache version."
    ),
) -> None:
    """Tool entry point; score sentiment when ``--scorer`` is provided."""
    if ctx.invoked_subcommand is not None:
        return
    if scorer is None:
        return
    if scorer != "lm":
        _fail(f"unknown scorer: {scorer!r}; known scorers: lm.")
    try:
        start, end = _date_window(month, from_, to)
        report = run_lm_scoring(layout.data_root(), source, start, end, model_version=model_version)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(
        f"articles={report.articles} computed={report.computed} "
        f"dropped={report.dropped} path={report.sentiment_path}"
    )
    raise typer.Exit(0)


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("algo-score"))


@app.command()
def events(
    kind: str = typer.Option(..., "--kind", help="Event feature kind: gdelt or gpr."),
    month: str | None = typer.Option(None, "--month", help="Single month, YYYY-MM."),
    from_: str | None = typer.Option(None, "--from", help="Range start, YYYY-MM-DD."),
    to: str | None = typer.Option(None, "--to", help="Range end, YYYY-MM-DD."),
) -> None:
    """Build event-derived minute features."""
    try:
        start, end = _date_window(month, from_, to)
        report = build_event_features(layout.data_root(), kind, start, end)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"written={report.rows} path={report.output_root}")
    raise typer.Exit(0)


def _date_window(month: str | None, from_: str | None, to: str | None) -> tuple[date, date]:
    """Resolve a CLI month/range into inclusive start and end dates."""
    if month is not None:
        if from_ is not None or to is not None:
            _fail("use --month or --from/--to, not both.")
        year, month_number = _year_month(month)
        next_year, next_month = (year + 1, 1) if month_number == 12 else (year, month_number + 1)
        return date(year, month_number, 1), date.fromordinal(
            date(next_year, next_month, 1).toordinal() - 1
        )
    if from_ is None or to is None:
        _fail("provide --month YYYY-MM, or both --from and --to as YYYY-MM-DD.")
    start, end = _iso_date(from_), _iso_date(to)
    if start > end:
        _fail(f"--from {start.isoformat()} is after --to {end.isoformat()}.")
    return start, end


def _year_month(spec: str) -> tuple[int, int]:
    """Parse ``YYYY-MM`` and fail fast on impossible months."""
    try:
        year_s, month_s = spec.split("-")
        year, month = int(year_s), int(month_s)
    except ValueError:
        _fail(f"bad month {spec!r}; expected YYYY-MM.")
    if not 1 <= month <= 12:
        _fail(f"bad month {spec!r}: month must be 01-12.")
    return year, month


def _iso_date(spec: str) -> date:
    """Parse an ISO date and print a friendly fix on failure."""
    try:
        return date.fromisoformat(spec)
    except ValueError:
        _fail(f"bad date {spec!r}; expected YYYY-MM-DD.")


def _fail(message: str) -> NoReturn:
    """Print a fail-fast explanation and exit."""
    typer.echo(message)
    raise typer.Exit(_USAGE_ERROR)


def main() -> None:
    """Console-script entry point (see [project.scripts])."""
    app()


if __name__ == "__main__":
    main()
