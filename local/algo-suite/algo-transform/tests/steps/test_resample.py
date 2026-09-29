"""Step definitions for resample.feature (pure tick -> QuoteBar aggregation)."""

from __future__ import annotations

from datetime import UTC, datetime

from algo_core.bars import Tick, Timeframe
from algo_transform.resample import resample
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import make_tick

scenarios("../features/resample.feature")

_TIMESTAMPS = {
    "2020-01-02 14:00 UTC": datetime(2020, 1, 2, 14, 0, tzinfo=UTC),
    "2020-01-02 14:05 UTC": datetime(2020, 1, 2, 14, 5, tzinfo=UTC),
    "2020-01-02 12:00 UTC": datetime(2020, 1, 2, 12, 0, tzinfo=UTC),
    "2020-01-02 16:00 UTC": datetime(2020, 1, 2, 16, 0, tzinfo=UTC),
    "2020-01-02 00:00 UTC": datetime(2020, 1, 2, 0, 0, tzinfo=UTC),
    "2020-01-03 00:00 UTC": datetime(2020, 1, 3, 0, 0, tzinfo=UTC),
}


@given("the ticks", target_fixture="ticks")
def _ticks_from_table(datatable: list[list[str]]) -> list[Tick]:
    """Build ticks from the data table (header row skipped)."""
    return [
        make_tick(int(r[0]), int(r[1]), int(r[2]), int(r[3]), float(r[4]), float(r[5]))
        for r in datatable[1:]
    ]


@given("no ticks", target_fixture="ticks")
def _no_ticks() -> list[Tick]:
    return []


@when(parsers.parse('I resample at timeframe "{name}"'))
def _resample(context: dict[str, object], ticks: list[Tick], name: str) -> None:
    context["bars"] = resample(ticks, Timeframe[name])


def _bars(context: dict[str, object]) -> list:  # type: ignore[type-arg]
    bars = context["bars"]
    assert isinstance(bars, list)
    return bars


@then(parsers.parse("it yields {count:d} bars"))
def _yields(context: dict[str, object], count: int) -> None:
    assert len(_bars(context)) == count


@then(parsers.parse("bar {idx:d} has timestamp 2020-01-02 14:00 UTC"))
def _bar_timestamp(context: dict[str, object], idx: int) -> None:
    assert _bars(context)[idx].timestamp == datetime(2020, 1, 2, 14, 0, tzinfo=UTC)


@then(parsers.parse("bar {idx:d} has bid OHLC {b_open:g} {b_high:g} {b_low:g} {b_close:g}"))
def _bid_ohlc(
    context: dict[str, object],
    idx: int,
    b_open: float,
    b_high: float,
    b_low: float,
    b_close: float,
) -> None:
    bar = _bars(context)[idx]
    assert (bar.bid_open, bar.bid_high, bar.bid_low, bar.bid_close) == (
        b_open,
        b_high,
        b_low,
        b_close,
    )


@then(parsers.parse("bar {idx:d} has tick_count {count:d}"))
def _tick_count(context: dict[str, object], idx: int, count: int) -> None:
    assert _bars(context)[idx].tick_count == count


@then("the bar timestamps are")
def _timestamps(context: dict[str, object], datatable: list[list[str]]) -> None:
    expected = [_TIMESTAMPS[r[0].strip()] for r in datatable[1:]]
    assert [b.timestamp for b in _bars(context)] == expected


@then(parsers.parse("bar {idx:d} has bid_open {b_open:g} and bid_close {b_close:g} "
                    "and tick_count {count:d}"))
def _open_close_count(
    context: dict[str, object], idx: int, b_open: float, b_close: float, count: int
) -> None:
    bar = _bars(context)[idx]
    assert bar.bid_open == b_open and bar.bid_close == b_close and bar.tick_count == count


@then(parsers.parse("bar {idx:d} has bid_high {b_high:g} and tick_count {count:d}"))
def _high_count(context: dict[str, object], idx: int, b_high: float, count: int) -> None:
    bar = _bars(context)[idx]
    assert bar.bid_high == b_high and bar.tick_count == count


@then(parsers.parse("the bar hours are {first:d} and {second:d}"))
def _bar_hours(context: dict[str, object], first: int, second: int) -> None:
    assert [b.timestamp.hour for b in _bars(context)] == [first, second]
