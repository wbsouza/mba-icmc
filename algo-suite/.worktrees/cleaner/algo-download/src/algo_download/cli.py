"""CLI for algo-download."""

from __future__ import annotations

from typing import NoReturn

import typer
from algo_core.instrument import UnknownSymbolError, build_instrument
from algo_core.logging import configure_logging, run_with_logging

import algo_download.adapters  # noqa: F401  (import-for-side-effect: registers adapters)
from algo_download.orchestrator import run as run_download
from algo_download.registry import UnknownSourceError, build_data_source
from algo_download.request import DownloadRequest
from algo_download.result import RunReport, UnitStatus
from algo_download.source import DataSource, RequestShape

app = typer.Typer(
    name="algo-download",
    help="Bulk download per source (Dukascopy, GDELT, GDELT NGrams, GPR) into the raw store.",
    no_args_is_help=True,
    add_completion=False,
)

_USAGE_ERROR = 2


@app.callback()
def _root() -> None:
    """Tool entry point; subcommands are listed below."""


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("algo-download"))


@app.command()
def run(
    source: str = typer.Option(..., "--source", help="Registered source, e.g. dukascopy."),
    symbol: str | None = typer.Option(None, "--symbol", help="Instrument symbol, e.g. EURUSD."),
    month: str | None = typer.Option(None, "--month", help="Single month, YYYY-MM."),
    from_: str | None = typer.Option(None, "--from", help="Range start, YYYY-MM (with --to)."),
    to: str | None = typer.Option(None, "--to", help="Range end, YYYY-MM (with --from)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the plan; fetch nothing."),
) -> None:
    """Download one source's raw payloads for a symbol over a month or range."""
    adapter = _adapter(source)
    request = _request(adapter, symbol, month, from_, to)
    if dry_run:
        for unit in adapter.plan(request):
            typer.echo(unit.key)
        raise typer.Exit(0)
    report = run_download(adapter, request)
    typer.echo(_render(report))
    raise typer.Exit(report.exit_code)


def _request(
    source: DataSource, symbol: str | None, month: str | None, from_: str | None, to: str | None
) -> DownloadRequest:
    if source.request_shape is RequestShape.INSTRUMENT_MONTHS:
        return _instrument_request(symbol, month, from_, to)
    if source.request_shape is RequestShape.GLOBAL_MONTHS:
        return _global_month_request(symbol, month, from_, to, source=source.name)
    if source.request_shape is RequestShape.WHOLE_WINDOW:
        return _whole_window_request(symbol, month, from_, to, source=source.name)
    _fail(f"unknown request shape for source {source.name!r}: {source.request_shape!r}.")


def _instrument_request(
    symbol: str | None, month: str | None, from_: str | None, to: str | None
) -> DownloadRequest:
    if symbol is None:
        _fail("provide --symbol for source dukascopy.")
    try:
        build_instrument(symbol)  # validate early so a typo fails fast, not mid-fetch
    except UnknownSymbolError as exc:
        _fail(f"{exc}\nFix: use a symbol from the instrument catalog.")
    return DownloadRequest(symbol=symbol, months=_months(month, from_, to))


def _global_month_request(
    symbol: str | None,
    month: str | None,
    from_: str | None,
    to: str | None,
    source: str = "gdelt",
) -> DownloadRequest:
    if symbol is not None:
        _fail(f"source {source} has no symbol dimension; remove --symbol.")
    return DownloadRequest(months=_months(month, from_, to))


def _whole_window_request(
    symbol: str | None,
    month: str | None,
    from_: str | None,
    to: str | None,
    source: str = "gpr",
) -> DownloadRequest:
    if symbol is not None:
        _fail(f"source {source} has no symbol dimension; remove --symbol.")
    if month is not None:
        _fail(f"source {source} has no date partitioning; remove --month.")
    if from_ is not None or to is not None:
        _fail(f"source {source} has no date partitioning; remove --from and --to.")
    return DownloadRequest()


def _adapter(source: str) -> DataSource:
    """Build the source, failing fast (and explaining how to fix) on a bad name."""
    try:
        return build_data_source(source)
    except UnknownSourceError as exc:
        _fail(f"{exc}\nFix: pass --source with one of the listed names.")


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


def _render(report: RunReport) -> str:
    parts = [f"{status.value}={report.count(status)}" for status in UnitStatus]
    return "  ".join(parts)


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
