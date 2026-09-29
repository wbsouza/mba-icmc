"""Steps for features/leandata.feature — the materializer's pure encoding + fail-fast.

Pins LEAN's minute-CSV encoding contract (ms = bar START in the configured data tz,
file-day = START date) and the fail-fast guards, without spinning a container. The
encoding was confirmed empirically against the real engine in the timezone feature.
"""

from __future__ import annotations

import multiprocessing
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from algo_backtest.leandata import lean_minute_rows, write_lean_minute
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/leandata.feature")

_EURUSD = build_instrument("EURUSD")


def _bar(utc_start: str, price: float = 1.10000) -> QuoteBar:
    """A QuoteBar starting at an ISO `utc_start` (naive → UTC), flat bid/ask at `price`."""
    start = datetime.fromisoformat(utc_start).replace(tzinfo=UTC)
    return QuoteBar(
        timestamp=start,
        bid_open=price,
        bid_high=price,
        bid_low=price,
        bid_close=price,
        ask_open=price + 0.00010,
        ask_high=price + 0.00010,
        ask_low=price + 0.00010,
        ask_close=price + 0.00010,
        tick_count=1,
    )


@given(parsers.parse('a QuoteBar starting at "{utc_start}" UTC'))
def _one_bar(ctx: dict[str, Any], utc_start: str) -> None:
    """Stage a single bar."""
    ctx["bars"] = [_bar(utc_start)]


@given("QuoteBars starting at:")
def _many_bars(ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """Stage several bars from a one-column (utc_start) table (first row is the header)."""
    ctx["bars"] = [_bar(row[0]) for row in datatable[1:]]


@when(parsers.parse('I compute the lean-data rows in timezone "{data_tz}"'))
def _compute_rows(ctx: dict[str, Any], data_tz: str) -> None:
    """Compute rows, capturing a ValueError so fail-fast scenarios can assert on it."""
    ctx["rows"] = ctx["error"] = None
    try:
        ctx["rows"] = lean_minute_rows(ctx["bars"], data_tz=ZoneInfo(data_tz), digits=5)
    except ValueError as exc:
        ctx["error"] = str(exc)


@when(parsers.parse('I write lean-data minute files in timezone "{data_tz}"'))
def _write_files(ctx: dict[str, Any], data_tz: str, tmp_path: Path) -> None:
    """Write day-zips under a tmp lean-data root."""
    ctx["written"] = write_lean_minute(tmp_path, _EURUSD, ctx["bars"], data_tz=ZoneInfo(data_tz))


def _write_worker(
    data_root: Path,
    bars: list[QuoteBar],
    data_tz: str,
    result_queue: multiprocessing.Queue[tuple[str, list[str] | str]],
) -> None:
    """Subprocess entry point: call `write_lean_minute` and report outcome via `result_queue`.

    Runs in a real OS process (distinct PID) so a regression of the tmp-filename
    collision this scenario guards against would reproduce the original
    `FileNotFoundError` race, not just be masked by same-process/same-PID reuse.
    """
    try:
        written = write_lean_minute(data_root, _EURUSD, bars, data_tz=ZoneInfo(data_tz))
        result_queue.put(("ok", [str(p) for p in written]))
    except Exception as exc:  # noqa: BLE001 - must surface any subprocess failure, not swallow it
        result_queue.put(("error", repr(exc)))


@when(
    parsers.parse(
        'two processes concurrently write lean-data minute files in timezone "{data_tz}"'
    )
)
def _write_files_concurrently(ctx: dict[str, Any], data_tz: str, tmp_path: Path) -> None:
    """Race two real processes writing the same day to the same lean-data root."""
    result_queue: multiprocessing.Queue[tuple[str, list[str] | str]] = multiprocessing.Queue()
    procs = [
        multiprocessing.Process(
            target=_write_worker, args=(tmp_path, ctx["bars"], data_tz, result_queue)
        )
        for _ in range(2)
    ]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(timeout=30)
    results = [result_queue.get(timeout=5) for _ in procs]
    ctx["concurrent_results"] = results
    ok_paths = next(paths for status, paths in results if status == "ok")
    ctx["written"] = [Path(p) for p in ok_paths]


@then("both writers succeed")
def _both_writers_succeed(ctx: dict[str, Any]) -> None:
    results = ctx["concurrent_results"]
    assert all(status == "ok" for status, _ in results), results


def _only_day_lines(ctx: dict[str, Any]) -> list[str]:
    """The CSV rows for the single file-day produced by a compute step."""
    return next(iter(ctx["rows"].values()))


@then(parsers.parse('the file day is "{file_day}"'))
def _file_day(ctx: dict[str, Any], file_day: str) -> None:
    assert next(iter(ctx["rows"])).isoformat() == file_day


@then(parsers.parse("the first row ms is {ms:d}"))
def _first_ms(ctx: dict[str, Any], ms: int) -> None:
    assert _only_day_lines(ctx)[0].split(",")[0] == str(ms)


@then(parsers.parse("the row has {n:d} columns"))
def _n_cols(ctx: dict[str, Any], n: int) -> None:
    assert len(_only_day_lines(ctx)[0].split(",")) == n


@then(parsers.parse('both volume columns are "{v}"'))
def _volumes(ctx: dict[str, Any], v: str) -> None:
    cols = _only_day_lines(ctx)[0].split(",")
    assert cols[5] == v and cols[10] == v


@then(parsers.parse('the bid-open column is "{val}"'))
def _bid_open(ctx: dict[str, Any], val: str) -> None:
    assert _only_day_lines(ctx)[0].split(",")[1] == val


@then(parsers.parse('the ask-open column is "{val}"'))
def _ask_open(ctx: dict[str, Any], val: str) -> None:
    assert _only_day_lines(ctx)[0].split(",")[6] == val


@then(parsers.parse('the row ms values are "{csv}"'))
def _row_ms_values(ctx: dict[str, Any], csv: str) -> None:
    assert [line.split(",")[0] for line in _only_day_lines(ctx)] == csv.split(",")


@then(parsers.parse('one file "{name}" is written'))
def _one_file(ctx: dict[str, Any], name: str) -> None:
    assert len(ctx["written"]) == 1 and ctx["written"][0].name == name


@then(parsers.parse('it contains the CSV "{name}"'))
def _contains_csv(ctx: dict[str, Any], name: str) -> None:
    with zipfile.ZipFile(ctx["written"][0]) as zf:
        ctx["csv_body"] = zf.read(name).decode()


@then(parsers.parse('the CSV row ms values are "{csv}"'))
def _csv_ms_values(ctx: dict[str, Any], csv: str) -> None:
    lines = ctx["csv_body"].splitlines()
    assert [line.split(",")[0] for line in lines] == csv.split(",")


@then(parsers.parse('the written files are "{csv}"'))
def _written_files(ctx: dict[str, Any], csv: str) -> None:
    assert {p.name for p in ctx["written"]} == set(csv.split(","))


@then(parsers.parse('it fails with "{needle}"'))
def _fails_with(ctx: dict[str, Any], needle: str) -> None:
    assert ctx["error"] is not None and needle in ctx["error"]
