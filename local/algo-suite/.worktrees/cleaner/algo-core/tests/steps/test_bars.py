"""Step definitions for bars.feature (pytest-bdd).

Tests in this suite are written as Gherkin scenarios; this module binds the
steps to the algo-core market-data value objects.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from algo_core.bars import QuoteBar, Tick, Timeframe
from pydantic import ValidationError
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/bars.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Carries the timestamp, value object or raised error between steps."""
    return {}


def _make_tick() -> Tick:
    """Build the canonical tick fixture used by the assertions."""
    return Tick(
        timestamp=datetime(2020, 1, 2, 14, 0, 0, 86_000, tzinfo=UTC),
        bid=1.11963,
        ask=1.11966,
        bid_volume=0.75,
        ask_volume=4.39,
    )


def _make_bar() -> QuoteBar:
    """Build the canonical quotebar fixture used by the assertions."""
    return QuoteBar(
        timestamp=datetime(2020, 1, 2, 14, 0, tzinfo=UTC),
        bid_open=1.10,
        bid_high=1.20,
        bid_low=1.00,
        bid_close=1.15,
        ask_open=1.1002,
        ask_high=1.2002,
        ask_low=1.0002,
        ask_close=1.1502,
        tick_count=42,
    )


# --- Timeframe -------------------------------------------------------------


@given("the timestamp 2020-01-02 14:37:45.123 UTC")
def _given_timestamp(context: dict[str, object]) -> None:
    context["ts"] = datetime(2020, 1, 2, 14, 37, 45, 123_000, tzinfo=UTC)


@when(parsers.parse('I floor it with timeframe "{timeframe}"'))
def _floor(context: dict[str, object], timeframe: str) -> None:
    ts = context["ts"]
    assert isinstance(ts, datetime)
    context["floored"] = Timeframe[timeframe].floor(ts)


@then(
    parsers.parse(
        "the floored timestamp is {hour:d}:{minute:d} UTC on 2020-01-02"
    )
)
def _floored_is(context: dict[str, object], hour: int, minute: int) -> None:
    assert context["floored"] == datetime(2020, 1, 2, hour, minute, tzinfo=UTC)


@then(parsers.parse('timeframe "{timeframe}" has {minutes:d} minutes'))
def _minutes(timeframe: str, minutes: int) -> None:
    assert Timeframe[timeframe].minutes == minutes


# --- Tick ------------------------------------------------------------------


@given("a tick")
def _given_tick(context: dict[str, object]) -> None:
    context["tick"] = _make_tick()


@then(parsers.parse("its bid is {value:g}"))
def _tick_bid(context: dict[str, object], value: float) -> None:
    tick = context["tick"]
    assert isinstance(tick, Tick)
    assert tick.bid == value


@then(parsers.parse("its ask is {value:g}"))
def _tick_ask(context: dict[str, object], value: float) -> None:
    tick = context["tick"]
    assert isinstance(tick, Tick)
    assert tick.ask == value


@then(parsers.parse("its bid_volume is {value:g}"))
def _tick_bid_volume(context: dict[str, object], value: float) -> None:
    tick = context["tick"]
    assert isinstance(tick, Tick)
    assert tick.bid_volume == value


@then(parsers.parse("its ask_volume is {value:g}"))
def _tick_ask_volume(context: dict[str, object], value: float) -> None:
    tick = context["tick"]
    assert isinstance(tick, Tick)
    assert tick.ask_volume == value


@when("I assign 9.9 to the tick bid")
def _assign_tick_bid(context: dict[str, object]) -> None:
    tick = context["tick"]
    assert isinstance(tick, Tick)
    try:
        tick.bid = 9.9  # type: ignore[misc]
    except ValidationError as exc:
        context["error"] = exc


@when("I build a tick with a naive timestamp")
def _tick_naive(context: dict[str, object]) -> None:
    try:
        Tick(
            timestamp=datetime(2020, 1, 2, 14, 0),  # naive, no tzinfo
            bid=1.1,
            ask=1.2,
            bid_volume=1.0,
            ask_volume=1.0,
        )
    except ValidationError as exc:
        context["error"] = exc


@when("I build a tick with a negative bid_volume")
def _tick_negative_volume(context: dict[str, object]) -> None:
    try:
        Tick(
            timestamp=datetime(2020, 1, 2, 14, 0, tzinfo=UTC),
            bid=1.1,
            ask=1.2,
            bid_volume=-1.0,
            ask_volume=1.0,
        )
    except ValidationError as exc:
        context["error"] = exc


# --- QuoteBar --------------------------------------------------------------


@given("a quotebar")
def _given_bar(context: dict[str, object]) -> None:
    context["bar"] = _make_bar()


@then(parsers.parse("its bid_close is {value:g}"))
def _bar_bid_close(context: dict[str, object], value: float) -> None:
    bar = context["bar"]
    assert isinstance(bar, QuoteBar)
    assert bar.bid_close == value


@then(parsers.parse("its ask_high is {value:g}"))
def _bar_ask_high(context: dict[str, object], value: float) -> None:
    bar = context["bar"]
    assert isinstance(bar, QuoteBar)
    assert bar.ask_high == value


@then(parsers.parse("its tick_count is {value:d}"))
def _bar_tick_count(context: dict[str, object], value: int) -> None:
    bar = context["bar"]
    assert isinstance(bar, QuoteBar)
    assert bar.tick_count == value


@when("I assign 9.9 to the quotebar bid_close")
def _assign_bar_bid_close(context: dict[str, object]) -> None:
    bar = context["bar"]
    assert isinstance(bar, QuoteBar)
    try:
        bar.bid_close = 9.9  # type: ignore[misc]
    except ValidationError as exc:
        context["error"] = exc


@when("I build a quotebar with a naive timestamp")
def _bar_naive(context: dict[str, object]) -> None:
    try:
        QuoteBar(
            timestamp=datetime(2020, 1, 2, 14, 0),  # naive
            bid_open=1.1,
            bid_high=1.2,
            bid_low=1.0,
            bid_close=1.15,
            ask_open=1.1,
            ask_high=1.2,
            ask_low=1.0,
            ask_close=1.15,
            tick_count=1,
        )
    except ValidationError as exc:
        context["error"] = exc


@when("I build a quotebar with a negative tick_count")
def _bar_negative_count(context: dict[str, object]) -> None:
    try:
        QuoteBar(
            timestamp=datetime(2020, 1, 2, 14, 0, tzinfo=UTC),
            bid_open=1.1,
            bid_high=1.2,
            bid_low=1.0,
            bid_close=1.15,
            ask_open=1.1,
            ask_high=1.2,
            ask_low=1.0,
            ask_close=1.15,
            tick_count=-1,
        )
    except ValidationError as exc:
        context["error"] = exc


# --- Shared -----------------------------------------------------------------


@then("a validation error is raised")
def _validation_error(context: dict[str, object]) -> None:
    assert isinstance(context.get("error"), ValidationError)
