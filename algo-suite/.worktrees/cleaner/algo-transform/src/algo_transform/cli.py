"""CLI for algo-transform."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer
from algo_core import layout
from algo_core.bars import Timeframe
from algo_core.instrument import Instrument, UnknownSymbolError, build_instrument
from algo_core.logging import configure_logging, run_with_logging

from algo_transform.coverage import compute_matrix, select_training_window
from algo_transform.coverage_artifacts import (
    scan_gdelt_coverage,
    write_coverage_artifacts,
)
from algo_transform.orchestrator import transform_gdelt_month, transform_gpr, transform_month

app = typer.Typer(
    name="algo-transform",
    help="Transform raw payloads into canonical Parquet; coverage + currency-strength.",
    no_args_is_help=True,
    add_completion=False,
)

_USAGE_ERROR = 2
_DUKASCOPY = "dukascopy"
_GDELT = "gdelt"
_GPR = "gpr"
_SOURCES = (_DUKASCOPY, _GDELT, _GPR)
# Module-level so the non-literal enum default is not a call in an argument default (ruff B008).
_TIMEFRAME_OPTION = typer.Option(
    Timeframe.M1, "--timeframe", help="Bar timeframe: m1, m5, m15, m30, h1, h4 or d1."
)


@app.callback()
def _root() -> None:
    """Tool entry point; subcommands are listed below."""


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("algo-transform"))


@app.command()
def run(
    source: str = typer.Option(..., "--source", help="Source to transform."),
    symbol: str | None = typer.Option(None, "--symbol", help="Instrument symbol, e.g. EURUSD."),
    month: str | None = typer.Option(None, "--month", help="Single month, YYYY-MM."),
    from_: str | None = typer.Option(None, "--from", help="Range start, YYYY-MM (with --to)."),
    to: str | None = typer.Option(None, "--to", help="Range end, YYYY-MM (with --from)."),
    timeframe: Timeframe = _TIMEFRAME_OPTION,
    rebuild: bool = typer.Option(False, "--rebuild", help="Rewrite even if the partition exists."),
) -> None:
    """Decode raw ticks and write the canonical QuoteBar Parquet for a month/range."""
    if source not in _SOURCES:
        _fail(f"unsupported --source {source!r}; known sources: {', '.join(_SOURCES)}.")
    data_root = layout.data_root()
    if source == _GPR:
        raise typer.Exit(_run_gpr(data_root, symbol, month, from_, to, rebuild))
    if source == _GDELT:
        raise typer.Exit(_run_gdelt(data_root, symbol, month, from_, to, rebuild))
    raise typer.Exit(_run_dukascopy(data_root, symbol, month, from_, to, timeframe, rebuild))


def _run_gpr(
    data_root: Path,
    symbol: str | None,
    month: str | None,
    from_: str | None,
    to: str | None,
    rebuild: bool,
) -> int:
    """Run the whole-window GPR transform after source-specific flag checks."""
    if symbol is not None:
        _fail("gpr is a whole-window source; do not pass --symbol.")
    if month is not None:
        _fail("gpr is a whole-window source; do not pass --month.")
    if from_ is not None or to is not None:
        _fail("gpr is a whole-window source; do not pass --from/--to.")
    report = transform_gpr(data_root, rebuild=rebuild)
    typer.echo(report.render())
    return report.exit_code


def _run_gdelt(
    data_root: Path,
    symbol: str | None,
    month: str | None,
    from_: str | None,
    to: str | None,
    rebuild: bool,
) -> int:
    """Run GDELT month transforms after source-specific flag checks."""
    if symbol is not None:
        _fail("gdelt is global; do not pass --symbol.")
    exit_code = 0
    for year, month_num in _months(month, from_, to):
        report = transform_gdelt_month(data_root, year, month_num, rebuild=rebuild)
        typer.echo(report.render())
        exit_code = max(exit_code, report.exit_code)
    return exit_code


def _run_dukascopy(
    data_root: Path,
    symbol: str | None,
    month: str | None,
    from_: str | None,
    to: str | None,
    timeframe: Timeframe,
    rebuild: bool,
) -> int:
    """Run Dukascopy month transforms after source-specific flag checks."""
    if symbol is None:
        _fail("dukascopy requires --symbol.")
    instrument = _instrument(symbol)
    exit_code = 0
    for year, month_num in _months(month, from_, to):
        report = transform_month(
            data_root, instrument, year, month_num, timeframe=timeframe, rebuild=rebuild
        )
        typer.echo(report.render())
        exit_code = max(exit_code, report.exit_code)
    return exit_code


@app.command()
def coverage() -> None:
    """Compute the coverage matrix and print the selected training window."""
    data_root = layout.data_root()
    rows = compute_matrix(scan_gdelt_coverage(data_root))
    artifacts = write_coverage_artifacts(data_root, rows)
    window = select_training_window(rows)
    if window is None:
        typer.echo("selected window: none")
    else:
        typer.echo(f"selected window: {window.render()}")
    typer.echo(f"coverage matrix: {artifacts.matrix_path}")
    typer.echo(f"coverage figure: {artifacts.figure_path}")


def _instrument(symbol: str) -> Instrument:
    try:
        return build_instrument(symbol)
    except UnknownSymbolError as exc:
        _fail(f"{exc}\nFix: use a symbol from the instrument catalog.")


def _months(month: str | None, from_: str | None, to: str | None) -> tuple[tuple[int, int], ...]:
    if month is not None:
        return (_year_month(month),)
    if from_ is not None and to is not None:
        return _month_range(_year_month(from_), _year_month(to))
    _fail("provide --month YYYY-MM, or both --from and --to.")


def _year_month(spec: str) -> tuple[int, int]:
    try:
        year_str, month_str = spec.split("-")
        year, month = int(year_str), int(month_str)
    except ValueError:
        _fail(f"bad month {spec!r}; expected YYYY-MM (e.g. 2020-01).")
    if not 1 <= month <= 12:
        _fail(f"bad month {spec!r}: month must be 01-12, got {month:02d}.")
    return year, month


def _month_range(start: tuple[int, int], end: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    if start > end:
        _fail(f"--from {start} is after --to {end}.")
    months: list[tuple[int, int]] = []
    year, month = start
    while (year, month) <= end:
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return tuple(months)


def _fail(message: str) -> NoReturn:
    """Print a fail-fast explanation (what went wrong + how to fix) and exit."""
    typer.echo(message)
    raise typer.Exit(_USAGE_ERROR)


def main() -> None:
    """Console-script entry point (see [project.scripts])."""
    configure_logging()
    run_with_logging(app)


if __name__ == "__main__":  # pragma: no cover
    main()
