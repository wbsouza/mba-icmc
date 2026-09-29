"""BDD for complete, causal UTC quote-bar aggregation."""

import json
from datetime import datetime, timedelta
from typing import Any

import pytest
from algo_backtest.perception.bar_clock import ClosedBarClock, aggregate_closed_bars
from algo_core.bars import QuoteBar
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/bar_clock.feature")


@pytest.fixture
def clock_state() -> dict[str, Any]:
    """Keep input quotes and clock observations isolated per scenario."""
    return {}


def _quote(timestamp: datetime, offset: int = 0) -> QuoteBar:
    """Build distinguishable, valid minute quotes with nonconstant activity."""
    return QuoteBar(
        timestamp=timestamp,
        bid_open=10 + offset,
        bid_high=12 + offset,
        bid_low=9 + offset,
        bid_close=11 + offset,
        ask_open=20 + offset,
        ask_high=22 + offset,
        ask_low=19 + offset,
        ask_close=21 + offset,
        tick_count=offset % 7,
    )


def _offsets(value: str) -> list[int]:
    """Parse an optional comma-separated list of minute offsets."""
    return [int(item) for item in value.split(",") if item.strip()]


@given(parsers.parse('a closed bar clock of {minutes:d} minutes starting at "{start}"'))
def clock(clock_state: dict[str, Any], minutes: int, start: str) -> None:
    """Construct a fresh incremental aggregator."""
    clock_state.update(minutes=minutes, start=datetime.fromisoformat(start))
    clock_state["clock"] = ClosedBarClock(minutes)


@given("the following minute quotes")
def table_quotes(clock_state: dict[str, Any], datatable: list[list[str]]) -> None:
    """Read explicit independent bid/ask extrema from the acceptance fixture."""
    quotes = []
    for row in datatable[1:]:
        values = dict(zip(datatable[0], row, strict=True))
        timestamp = clock_state["start"] + timedelta(minutes=int(values.pop("offset")))
        ticks = int(values.pop("tick_count"))
        quotes.append(
            QuoteBar(
                timestamp=timestamp,
                tick_count=ticks,
                **{field: float(value) for field, value in values.items()},
            )
        )
    clock_state["quotes"] = quotes


@given(parsers.re(r'minute quotes at offsets "(?P<offsets>[^"]*)"'))
def offset_quotes(clock_state: dict[str, Any], offsets: str) -> None:
    """Represent real gaps by absent inputs, without filling them."""
    clock_state["quotes"] = [
        _quote(clock_state["start"] + timedelta(minutes=offset), offset)
        for offset in _offsets(offsets)
    ]


@given("exactly one complete bucket of minute quotes")
def complete_bucket(clock_state: dict[str, Any]) -> None:
    """Supply every expected minute and stop at the bucket's final minute."""
    offset_quotes(clock_state, ",".join(str(i) for i in range(clock_state["minutes"])))


@when("the minute quotes are consumed by the clock")
def consume(clock_state: dict[str, Any]) -> None:
    """Record each return value at its precise input minute."""
    clock_state["originals"] = [quote.model_dump() for quote in clock_state["quotes"]]
    clock_state["outputs"] = [clock_state["clock"].update(q) for q in clock_state["quotes"]]


@then(
    parsers.re(
        r'bars are emitted only on input offsets "(?P<emissions>[^"]*)" '
        r'with bucket offsets "(?P<buckets>[^"]*)"'
    )
)
def emission_times(clock_state: dict[str, Any], emissions: str, buckets: str) -> None:
    """Check both publication time and the emitted bucket-start timestamp."""
    pairs = list(zip(clock_state["quotes"], clock_state["outputs"], strict=True))
    expected_inputs = [clock_state["start"] + timedelta(minutes=i) for i in _offsets(emissions)]
    expected_buckets = [clock_state["start"] + timedelta(minutes=i) for i in _offsets(buckets)]
    assert [q.timestamp for q, out in pairs if out is not None] == expected_inputs
    assert [out.timestamp for _, out in pairs if out is not None] == expected_buckets


@then(
    parsers.parse('the closed quote has bid OHLC "{bid}" and ask OHLC "{ask}" and {ticks:d} ticks')
)
def aggregated_prices(clock_state: dict[str, Any], bid: str, ask: str, ticks: int) -> None:
    """Verify opens, independent extrema, final closes, and summed tick counts."""
    output = clock_state["outputs"][-1]
    assert isinstance(output, QuoteBar)
    for side, expected in (("bid", bid), ("ask", ask)):
        assert [
            getattr(output, f"{side}_{field}") for field in ("open", "high", "low", "close")
        ] == [float(value) for value in expected.split(",")]
    assert output.tick_count == ticks


@then("exactly one bucket is emitted on its last minute")
def complete_emission(clock_state: dict[str, Any]) -> None:
    """No next-bar lookahead is needed, even for an entire UTC day."""
    assert clock_state["outputs"][:-1] == [None] * (clock_state["minutes"] - 1)
    first, last = clock_state["quotes"][0], clock_state["quotes"][-1]
    output = clock_state["outputs"][-1]
    assert output == QuoteBar(
        timestamp=first.timestamp,
        bid_open=first.bid_open,
        bid_high=last.bid_high,
        bid_low=first.bid_low,
        bid_close=last.bid_close,
        ask_open=first.ask_open,
        ask_high=last.ask_high,
        ask_low=first.ask_low,
        ask_close=last.ask_close,
        tick_count=sum(q.tick_count for q in clock_state["quotes"]),
    )


@then("batch results match the streaming results")
def batch_parity(clock_state: dict[str, Any]) -> None:
    """The batch helper also accepts a one-pass minute stream."""
    assert aggregate_closed_bars(iter(clock_state["quotes"]), clock_state["minutes"]) == [
        out for out in clock_state["outputs"] if out is not None
    ]


@then("batch results match streaming results for every input prefix")
def prefix_parity(clock_state: dict[str, Any]) -> None:
    """Truncation never leaks future quotes or flushes a partial final candle."""
    for length in range(len(clock_state["quotes"]) + 1):
        assert aggregate_closed_bars(clock_state["quotes"][:length], clock_state["minutes"]) == [
            out for out in clock_state["outputs"][:length] if out is not None
        ]


@then("the input quotes are unchanged")
def immutable_inputs(clock_state: dict[str, Any]) -> None:
    """Aggregation must not alter minute prices or timestamps in shared inputs."""
    assert [q.model_dump() for q in clock_state["quotes"]] == clock_state["originals"]


@when(parsers.parse("a closed bar clock and an empty batch are requested with minutes {value}"))
def invalid_minutes(clock_state: dict[str, Any], value: str) -> None:
    """Exercise the same period validation at both public entry points."""
    minutes = json.loads(value)
    with pytest.raises(ValueError) as live_error:
        ClosedBarClock(minutes)
    with pytest.raises(ValueError) as batch_error:
        aggregate_closed_bars([], minutes)
    clock_state["errors"] = [str(live_error.value), str(batch_error.value)]


@then("both requests fail with a minutes validation error")
def period_errors(clock_state: dict[str, Any]) -> None:
    """Errors identify the invalid parameter and its supported domain."""
    assert all("minutes" in error and "1440" in error for error in clock_state["errors"])


@when(parsers.parse('a minute quote at "{timestamp}" is submitted'))
def invalid_timestamp(clock_state: dict[str, Any], timestamp: str) -> None:
    """Both APIs reject invalid minute ordering or subminute timestamps."""
    quote = _quote(datetime.fromisoformat(timestamp))
    with pytest.raises(ValueError) as live_error:
        clock_state["clock"].update(quote)
    with pytest.raises(ValueError) as batch_error:
        aggregate_closed_bars([*clock_state["quotes"], quote], clock_state["minutes"])
    clock_state["errors"] = [str(live_error.value), str(batch_error.value)]


@then(parsers.parse('the quote fails with a timestamp validation error containing "{reason}"'))
def timestamp_error(clock_state: dict[str, Any], reason: str) -> None:
    """Explain how the caller must repair its minute stream."""
    assert all("timestamp" in error and reason in error for error in clock_state["errors"])


@then("a subsequent valid minute can still close")
def recover_after_rejection(clock_state: dict[str, Any]) -> None:
    """Rejected updates leave the previously accepted clock state intact."""
    quote = _quote(clock_state["start"] + timedelta(minutes=2))
    assert clock_state["clock"].update(quote) == quote
