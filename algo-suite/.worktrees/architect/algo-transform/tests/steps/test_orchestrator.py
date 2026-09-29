"""Step definitions for orchestrator.feature (completeness-gated idempotency)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import TickFile, price_path_for
from algo_core.repository.parquet import ParquetRepository
from algo_transform.orchestrator import transform_month
from algo_transform.readers.dukascopy import expected_hours
from algo_transform.result import TransformStatus
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import bi5_payload, write_raw

scenarios("../features/orchestrator.feature")

_INSTRUMENT = build_instrument("EURUSD")


def _bar() -> QuoteBar:
    """A single canonical QuoteBar used to seed a prior partition."""
    return QuoteBar(
        timestamp=datetime(2020, 1, 2, 14, 0, tzinfo=UTC),
        bid_open=1.1, bid_high=1.2, bid_low=1.0, bid_close=1.15,
        ask_open=1.1, ask_high=1.2, ask_low=1.0, ask_close=1.15, tick_count=1,
    )


@given("a writable data root")
def _writable(data_root: Path) -> None:
    assert data_root.is_dir()


@given("a prior complete m1 partition exists for EURUSD 2020-01")
def _prior_partition(data_root: Path) -> None:
    path = price_path_for(data_root, _INSTRUMENT, "m1", 2020, 1)
    ParquetRepository(QuoteBar, path).put([_bar()])  # a prior (complete) write


@given("the EURUSD 2020-01 month is filled with no-data markers")
def _fill_markers(data_root: Path) -> None:
    for tick in expected_hours("EURUSD", 2020, 1):
        write_raw(data_root, tick, b"")


@given(parsers.parse(
    "a data hour at EURUSD 2020-01-{day:d} {hour:d}h with one EUR/USD tick"
))
def _data_hour(data_root: Path, day: int, hour: int) -> None:
    write_raw(
        data_root,
        TickFile(symbol="EURUSD", year=2020, month=1, day=day, hour=hour),
        bi5_payload([(86, 111966, 111963, 4.39, 0.75)]),
    )


@given(parsers.parse("a corrupt hour at EURUSD 2020-01-{day:d} {hour:d}h"))
def _corrupt_hour(data_root: Path, day: int, hour: int) -> None:
    write_raw(
        data_root,
        TickFile(symbol="EURUSD", year=2020, month=1, day=day, hour=hour),
        b"not-lzma",
    )


@when("I transform_month EURUSD 2020-01")
def _transform(context: dict[str, object], data_root: Path) -> None:
    context["report"] = transform_month(data_root, _INSTRUMENT, 2020, 1)


@when(parsers.parse("I transform_month EURUSD 2020-01 at timeframe H4"))
def _transform_h4(context: dict[str, object], data_root: Path) -> None:
    context["report"] = transform_month(
        data_root, _INSTRUMENT, 2020, 1, timeframe=Timeframe.H4
    )


def _report(context: dict[str, object]):  # type: ignore[no-untyped-def]
    return context["report"]


@then(parsers.parse("the report status is {status}"))
def _status(context: dict[str, object], status: str) -> None:
    assert _report(context).status is TransformStatus[status]


@then("the report exit code is 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _report(context).exit_code == 0


@then("the report exit code is non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert _report(context).exit_code != 0


@then(parsers.parse("the report quarantined count is {count:d}"))
def _quarantined(context: dict[str, object], count: int) -> None:
    assert _report(context).quarantined == count


@then(parsers.parse("an {tf} partition exists for EURUSD 2020-01"))
def _partition_exists(data_root: Path, tf: str) -> None:
    assert price_path_for(data_root, _INSTRUMENT, tf, 2020, 1).is_file()


@then(parsers.parse("no {tf} partition exists for EURUSD 2020-01"))
def _partition_absent(data_root: Path, tf: str) -> None:
    assert not price_path_for(data_root, _INSTRUMENT, tf, 2020, 1).exists()
