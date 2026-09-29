"""Steps for candle_context.feature: causal T-line, stochastic, level and trend evidence."""

from __future__ import annotations

import json
import math
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from algo_backtest.perception.candle_context import ContextEvaluator
from algo_backtest.perception.candle_contract import (
    CandleConfig,
    ClosedBar,
    ContextConfig,
    ContextEvidence,
    IndicatorValue,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/candle_context.feature")

_HOUR = timedelta(hours=1)
_T0 = datetime(2024, 1, 1, tzinfo=UTC)
_TOLERANCE = 1e-9


@pytest.fixture
def ctx_ctx() -> dict[str, Any]:
    """Per-scenario state: staged OHLC tuples, evidence and captured errors."""
    return {"bars": [], "config": CandleConfig()}


def _close_bar(close: float) -> tuple[float, float, float, float]:
    """The feature's single-close convention: (c, c + 0.5, c - 0.5, c)."""
    return (close, close + 0.5, close - 0.5, close)


def _floats(raw: str) -> list[float]:
    """A comma-separated list of numbers."""
    return [float(item) for item in raw.split(",")]


def _closed(
    bars: list[tuple[float, float, float, float]], end: datetime | None = None
) -> list[ClosedBar]:
    """Hourly UTC closed bars; from 01:00 unless an end time is given."""
    start = _T0 + _HOUR if end is None else end - _HOUR * (len(bars) - 1)
    return [ClosedBar(start + _HOUR * i, *bar) for i, bar in enumerate(bars)]


def _stream(config: CandleConfig, bars: list[ClosedBar]) -> list[ContextEvidence]:
    """Evidence per bar from a fresh evaluator."""
    evaluator = ContextEvaluator(config)
    return [evaluator.update(bar) for bar in bars]


def _maybe(raw: str) -> float | None:
    """``None`` or a number from a table cell."""
    return None if raw == "None" else float(raw)


def _assert_value(indicator: IndicatorValue, value: float | None, status: str) -> None:
    """Exact status and a value within 1e-9 (or None)."""
    assert indicator.status == status
    if value is None:
        assert indicator.value is None
    else:
        assert indicator.value is not None
        assert math.isclose(indicator.value, value, abs_tol=_TOLERANCE)


# --- staging --------------------------------------------------------------------------


@given(parsers.parse('closes {closes} as 60-minute bars ending at "{end}"'))
def closes_ending(ctx_ctx: dict[str, Any], closes: str, end: str) -> None:
    """Single-close bars ending at the given UTC time."""
    ctx_ctx["bars"] = [_close_bar(c) for c in _floats(closes)]
    ctx_ctx["end"] = datetime.fromisoformat(end)


@given(parsers.parse("closes {closes} as 60-minute bars"))
def closes(ctx_ctx: dict[str, Any], closes: str) -> None:
    """Single-close bars from 01:00 UTC."""
    ctx_ctx["bars"] = [_close_bar(c) for c in _floats(closes)]


@given(
    parsers.parse(
        "{count:d} bars with open {open:g}, high {high:g} and low {low:g} whose closes are {spec}"
    )
)
def fixed_range_closes(
    ctx_ctx: dict[str, Any], count: int, open: float, high: float, low: float, spec: str
) -> None:
    """Bars with fixed open/high/low; ``15 x12`` repeats a close."""
    closes: list[float] = []
    for item in spec.split(","):
        value, _, times = item.strip().partition(" x")
        closes.extend([float(value)] * (int(times) if times else 1))
    assert len(closes) == count
    ctx_ctx["bars"] = [(open, high, low, close) for close in closes]


@given(
    parsers.parse(
        "{count:d} bars with open {open:g}, high {high:g} and low {low:g} and every close {close:g}"
    )
)
def fixed_range_every(
    ctx_ctx: dict[str, Any], count: int, open: float, high: float, low: float, close: float
) -> None:
    """Bars with fixed open/high/low and one repeated close."""
    ctx_ctx["bars"] = [(open, high, low, close)] * count


@given(
    parsers.parse(
        "{count:d} flat bars ({fo:g}, {fh:g}, {fl:g}, {fc:g}) followed by {after:d} bars with open "
        "{open:g}, high {high:g}, low {low:g} and close {close:g}"
    )
)
def flat_then_ranged(
    ctx_ctx: dict[str, Any],
    count: int,
    fo: float,
    fh: float,
    fl: float,
    fc: float,
    after: int,
    open: float,
    high: float,
    low: float,
    close: float,
) -> None:
    """Flat bars, then ranged bars."""
    ctx_ctx["bars"] = [(fo, fh, fl, fc)] * count + [(open, high, low, close)] * after


@given(parsers.parse("{count:d} flat bars ({fo:g}, {fh:g}, {fl:g}, {fc:g})"))
def flat_bars(
    ctx_ctx: dict[str, Any], count: int, fo: float, fh: float, fl: float, fc: float
) -> None:
    """Repeated flat bars."""
    ctx_ctx["bars"] = [(fo, fh, fl, fc)] * count


@given(
    parsers.parse(
        "{first:d} bars closing at {c1:g} followed by {second:d} bars closing at {c2:g}, "
        "as 60-minute bars"
    )
)
def two_levels(ctx_ctx: dict[str, Any], first: int, c1: float, second: int, c2: float) -> None:
    """A two-level close series."""
    ctx_ctx["bars"] = [_close_bar(c1)] * first + [_close_bar(c2)] * second


@given(
    parsers.parse(
        "{first:d} bars closing at {c1:g} followed by {second:d} bars with open {open:g}, "
        "high {high:g}, low {low:g} and close {close:g}"
    )
)
def level_then_ranged(
    ctx_ctx: dict[str, Any],
    first: int,
    c1: float,
    second: int,
    open: float,
    high: float,
    low: float,
    close: float,
) -> None:
    """Single-close bars, then ranged bars."""
    ctx_ctx["bars"] = [_close_bar(c1)] * first + [(open, high, low, close)] * second


@given(parsers.parse("a context configuration with {field} set to {value}"))
def context_config(ctx_ctx: dict[str, Any], field: str, value: str) -> None:
    """Stage a ContextConfig builder with one raw field override."""
    ctx_ctx["build"] = lambda: ContextConfig(**{field: json.loads(value)})


@given(parsers.parse("fibonacci is enabled with a lookback of {lookback:d} bars"))
def fibonacci_config(ctx_ctx: dict[str, Any], lookback: int) -> None:
    """A configuration with Fibonacci confluence on, every other parameter default."""
    ctx_ctx["config"] = CandleConfig(
        context=ContextConfig(fibonacci_enabled=True, fibonacci_lookback_bars=lookback)
    )


@given(
    parsers.parse(
        "a minimal context configuration with fibonacci enabled and a lookback of {lookback:d} bars"
    )
)
def minimal_fibonacci_config(ctx_ctx: dict[str, Any], lookback: int) -> None:
    """A one-bar-ready EMA/stochastic/level configuration so only Fibonacci warms up."""
    ctx_ctx["config"] = CandleConfig(
        context=ContextConfig(
            ema_period=1,
            stochastic_k=1,
            stochastic_k_smooth=1,
            stochastic_d=1,
            sma_periods=(1,),
            fibonacci_enabled=True,
            fibonacci_lookback_bars=lookback,
        )
    )


@given("the following closed bars, 60-minute UTC from 01:00:")
def explicit_bars_table(ctx_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """An explicit OHLC table, one bar per row, oldest first."""
    ctx_ctx["bars"] = [tuple(float(value) for value in row) for row in datatable[1:]]


@given(
    parsers.parse('a candle configuration with max_history {history:d} and sma_periods "{smas}"')
)
def candle_config(ctx_ctx: dict[str, Any], history: int, smas: str) -> None:
    """Stage a CandleConfig builder with a short history and long SMA periods."""
    periods = tuple(int(item) for item in smas.split(","))
    ctx_ctx["build"] = lambda: CandleConfig(
        max_history=history, context=ContextConfig(sma_periods=periods)
    )


# --- actions --------------------------------------------------------------------------


def _validate(ctx_ctx: dict[str, Any]) -> None:
    """Run the staged builder, capturing a ValueError."""
    try:
        ctx_ctx["build"]()
        ctx_ctx["error"] = None
    except ValueError as error:
        ctx_ctx["error"] = error


@when("the context configuration is validated")
def validate_context_config(ctx_ctx: dict[str, Any]) -> None:
    """Construct the context configuration."""
    _validate(ctx_ctx)


@when("the candle configuration is validated")
def validate_candle_config(ctx_ctx: dict[str, Any]) -> None:
    """Construct the candle configuration."""
    _validate(ctx_ctx)


@when(parsers.parse("the context is evaluated after {count:d} bars"))
def evaluate_after(ctx_ctx: dict[str, Any], count: int) -> None:
    """Stream the first ``count`` staged bars."""
    ctx_ctx["evidences"] = _stream(ctx_ctx["config"], _closed(ctx_ctx["bars"][:count]))
    ctx_ctx["evidence"] = ctx_ctx["evidences"][-1]


@when("the context is evaluated after all bars")
def evaluate_all(ctx_ctx: dict[str, Any]) -> None:
    """Stream every staged bar."""
    ctx_ctx["evidences"] = _stream(ctx_ctx["config"], _closed(ctx_ctx["bars"], ctx_ctx.get("end")))
    ctx_ctx["evidence"] = ctx_ctx["evidences"][-1]


@when("the context is evaluated after all bars, keeping the evaluator")
def evaluate_all_keep_evaluator(ctx_ctx: dict[str, Any]) -> None:
    """Stream every staged bar through an evaluator kept for direct inspection."""
    evaluator = ContextEvaluator(ctx_ctx["config"])
    bars = _closed(ctx_ctx["bars"], ctx_ctx.get("end"))
    ctx_ctx["evidences"] = [evaluator.update(bar) for bar in bars]
    ctx_ctx["evidence"] = ctx_ctx["evidences"][-1]
    ctx_ctx["evaluator"] = evaluator


@then(parsers.parse("the context evaluator's history holds {count:d} bars"))
def assert_evaluator_history(ctx_ctx: dict[str, Any], count: int) -> None:
    """The evaluator exposes its bound history via the ``history`` accessor."""
    assert ctx_ctx["evaluator"].history.history_count == count


@when(parsers.parse("a bar with OHLC {prices} is offered to the context"))
def offer_invalid(ctx_ctx: dict[str, Any], prices: str) -> None:
    """Stream the staged bars, then offer an invalid bar and keep the error."""
    evaluator = ContextEvaluator(ctx_ctx["config"])
    bars = _closed(ctx_ctx["bars"])
    for bar in bars:
        evaluator.update(bar)
    ctx_ctx["evaluator"], ctx_ctx["next_time"] = evaluator, bars[-1].close_time + _HOUR
    try:
        evaluator.update(ClosedBar(ctx_ctx["next_time"], *json.loads(prices)))
        ctx_ctx["error"] = None
    except ValueError as error:
        ctx_ctx["error"] = error


@when("the same prefix is evaluated before a rising suffix and before a falling suffix")
def diverging_suffixes(ctx_ctx: dict[str, Any]) -> None:
    """Replay the identical prefix ahead of a rising and a falling future."""
    prefix = ctx_ctx["bars"]
    last = prefix[-1][3]
    runs = []
    for step in (1.0, -0.5):
        suffix = [_close_bar(last + step * i) for i in range(1, 11)]
        runs.append(_stream(ctx_ctx["config"], _closed(prefix + suffix))[: len(prefix)])
    ctx_ctx["prefix_runs"] = runs


# --- assertions -----------------------------------------------------------------------


@then(parsers.parse('context configuration validation rejects mentioning "{field}"'))
def assert_context_rejected(ctx_ctx: dict[str, Any], field: str) -> None:
    """A ValueError naming the field."""
    assert isinstance(ctx_ctx["error"], ValueError)
    assert field in str(ctx_ctx["error"])


@then(parsers.parse('candle configuration validation rejects mentioning "{mention}"'))
def assert_candle_rejected(ctx_ctx: dict[str, Any], mention: str) -> None:
    """A ValueError naming the offending lookback."""
    assert isinstance(ctx_ctx["error"], ValueError)
    assert mention in str(ctx_ctx["error"])


@then(parsers.parse('the ema status is "{status}" and its value is {value}'))
def assert_ema(ctx_ctx: dict[str, Any], status: str, value: str) -> None:
    """The T-line reading."""
    _assert_value(ctx_ctx["evidence"].ema, _maybe(value), status)


@then(parsers.parse('the t_line_position is "{position}"'))
def assert_position(ctx_ctx: dict[str, Any], position: str) -> None:
    """Close relative to the T-line."""
    assert ctx_ctx["evidence"].t_line_position == position


@then(parsers.parse('the trend is "{trend}"'))
def assert_trend(ctx_ctx: dict[str, Any], trend: str) -> None:
    """Trend evidence derived from the T-line."""
    assert ctx_ctx["evidence"].trend == trend


@then(parsers.parse('the raw stochastic K is {value} with status "{status}"'))
def assert_raw_k(ctx_ctx: dict[str, Any], value: str, status: str) -> None:
    """Raw %K reading."""
    _assert_value(ctx_ctx["evidence"].stochastic.raw_k, _maybe(value), status)


@then(parsers.parse('the slow stochastic K is {value} with status "{status}"'))
def assert_slow_k(ctx_ctx: dict[str, Any], value: str, status: str) -> None:
    """Slow %K reading."""
    _assert_value(ctx_ctx["evidence"].stochastic.slow_k, _maybe(value), status)


@then(parsers.parse('the stochastic D is {value} with status "{status}"'))
def assert_d(ctx_ctx: dict[str, Any], value: str, status: str) -> None:
    """%D reading."""
    _assert_value(ctx_ctx["evidence"].stochastic.d, _maybe(value), status)


@then(parsers.parse('the stochastic_zone is "{zone}"'))
def assert_zone(ctx_ctx: dict[str, Any], zone: str) -> None:
    """Zone derived from %D."""
    assert ctx_ctx["evidence"].stochastic.zone == zone


def _numbers(evidence: ContextEvidence) -> list[float]:
    """Every float carried by the evidence."""
    stochastic = evidence.stochastic
    values = [
        evidence.ema.value,
        stochastic.raw_k.value,
        stochastic.slow_k.value,
        stochastic.d.value,
    ]
    for level in evidence.levels:
        values += [level.sma.value, level.distance]
    return [value for value in values if value is not None]


@then("no context value is NaN or infinite")
def assert_finite(ctx_ctx: dict[str, Any]) -> None:
    """Every numeric field is finite."""
    assert all(math.isfinite(value) for value in _numbers(ctx_ctx["evidence"]))


@then(parsers.parse("the sma distances are: 20 -> {d20}, 50 -> {d50}, 200 -> {d200}"))
def assert_distances(ctx_ctx: dict[str, Any], d20: str, d50: str, d200: str) -> None:
    """Normalized distances per level, None while warming."""
    expected = {20: _maybe(d20), 50: _maybe(d50), 200: _maybe(d200)}
    actual = {level.period: level.distance for level in ctx_ctx["evidence"].levels}
    assert actual.keys() == expected.keys()
    for period, value in expected.items():
        if value is None:
            assert actual[period] is None
        else:
            assert actual[period] is not None
            assert math.isclose(actual[period], value, abs_tol=_TOLERANCE)


@then(parsers.parse('the level statuses are: 20 -> "{s20}", 50 -> "{s50}", 200 -> "{s200}"'))
def assert_level_statuses(ctx_ctx: dict[str, Any], s20: str, s50: str, s200: str) -> None:
    """Per-period readiness."""
    actual = {level.period: level.sma.status for level in ctx_ctx["evidence"].levels}
    assert actual == {20: s20, 50: s50, 200: s200}


@then(parsers.parse('the context status is "{status}"'))
def assert_status(ctx_ctx: dict[str, Any], status: str) -> None:
    """Overall readiness."""
    assert ctx_ctx["evidence"].status == status


@then(parsers.parse('the context rejects it mentioning "{fragment}" and a remedy'))
def assert_rejected(ctx_ctx: dict[str, Any], fragment: str) -> None:
    """A ValueError naming the problem and the corrective action."""
    assert isinstance(ctx_ctx["error"], ValueError)
    assert fragment in str(ctx_ctx["error"])
    assert "repair" in str(ctx_ctx["error"]).lower()


@then(
    parsers.parse(
        'the context after the next valid close {close:g} has ema {ema:g} and status "{status}" '
        "for the ema"
    )
)
def assert_recovers(ctx_ctx: dict[str, Any], close: float, ema: float, status: str) -> None:
    """The rejected bar consumed nothing: the next valid bar continues the series."""
    evidence = ctx_ctx["evaluator"].update(ClosedBar(ctx_ctx["next_time"], *_close_bar(close)))
    _assert_value(evidence.ema, ema, status)


@then(parsers.parse("the context history_count is {count:d}"))
def assert_history_count(ctx_ctx: dict[str, Any], count: int) -> None:
    """Bounded retained history."""
    assert ctx_ctx["evidence"].history_count == count


@then("the context evidence exposes distinct fields ema, stochastic, levels and trend")
def assert_fields(ctx_ctx: dict[str, Any]) -> None:
    """The evidence is separately typed."""
    names = {field.name for field in fields(ctx_ctx["evidence"])}
    assert {"ema", "stochastic", "levels", "trend"} <= names


@then("each field carries its own status")
def assert_own_status(ctx_ctx: dict[str, Any]) -> None:
    """Every indicator carries a readiness; the trend embeds WARMUP as its own."""
    evidence = ctx_ctx["evidence"]
    stochastic = evidence.stochastic
    assert evidence.ema.status == "READY"
    assert {stochastic.raw_k.status, stochastic.slow_k.status, stochastic.d.status} == {"READY"}
    assert [level.sma.status for level in evidence.levels] == ["READY", "READY", "READY"]
    assert evidence.trend in {"UP", "DOWN", "FLAT", "WARMUP"}


@then("the context evidence carries no pattern hit and no confirmation field")
def assert_no_hits(ctx_ctx: dict[str, Any]) -> None:
    """Geometry and confirmation stay outside the context evidence."""
    names = {field.name for field in fields(ctx_ctx["evidence"])}
    assert not names & {"hits", "confirmation", "pattern", "patterns"}


@then("the per-bar context evidence over the prefix is identical under both suffixes")
def assert_prefix_invariance(ctx_ctx: dict[str, Any]) -> None:
    """Future bars do not change already evaluated evidence."""
    first, second = ctx_ctx["prefix_runs"]
    assert first == second
    assert len(first) == len(ctx_ctx["bars"])


@then(parsers.parse("the final prefix ema is {ema:g}"))
def assert_prefix_ema(ctx_ctx: dict[str, Any], ema: float) -> None:
    """The prefix ends with the expected T-line."""
    _assert_value(ctx_ctx["prefix_runs"][0][-1].ema, ema, "READY")


@then(parsers.parse('the context evidence close_time is "{close_time}"'))
def assert_close_time(ctx_ctx: dict[str, Any], close_time: str) -> None:
    """The availability time is the evaluated bar's close."""
    assert ctx_ctx["evidence"].close_time == datetime.fromisoformat(close_time)


@then(parsers.parse('the fibonacci status is "{status}"'))
def assert_fibonacci_status(ctx_ctx: dict[str, Any], status: str) -> None:
    """The Fibonacci confluence field's own readiness."""
    assert ctx_ctx["evidence"].fibonacci.status == status


@then(parsers.parse("the fibonacci level is {level}"))
def assert_fibonacci_level(ctx_ctx: dict[str, Any], level: str) -> None:
    """The nearest retracement ratio the close is at, or None."""
    expected = _maybe(level)
    actual = ctx_ctx["evidence"].fibonacci.level
    if expected is None:
        assert actual is None
    else:
        assert actual is not None
        assert math.isclose(actual, expected, abs_tol=_TOLERANCE)


@then(parsers.parse("the fibonacci swing high is {high:g} and swing low is {low:g}"))
def assert_fibonacci_swing(ctx_ctx: dict[str, Any], high: float, low: float) -> None:
    """The causal swing high/low the retracement levels are anchored on."""
    fibonacci = ctx_ctx["evidence"].fibonacci
    assert fibonacci.swing_high.value is not None
    assert fibonacci.swing_low.value is not None
    assert math.isclose(fibonacci.swing_high.value, high, abs_tol=_TOLERANCE)
    assert math.isclose(fibonacci.swing_low.value, low, abs_tol=_TOLERANCE)


@then("the context evidence has no fibonacci field")
def assert_no_fibonacci(ctx_ctx: dict[str, Any]) -> None:
    """Fibonacci confluence is absent when not configured/enabled."""
    assert ctx_ctx["evidence"].fibonacci is None
