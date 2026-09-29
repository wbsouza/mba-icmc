"""Steps for trail_stop.feature — target / trail-stop-arm / trail-stop-destination levels."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from algo_backtest.rules.trail_stop import (
    Direction,
    target_level,
    trail_stop_at_level,
    trail_stop_to_level,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/trail_stop.feature")


@dataclass
class _TrailStopCtx:
    """Per-scenario entry/SL/spread plus the outcome of the most recent computation."""

    entry: float = 0.0
    stop_loss: float = 0.0
    spread: float = 0.0
    direction: Direction = Direction.BUY
    result: float | None = None
    error: Exception | None = None


@pytest.fixture
def ts_ctx() -> _TrailStopCtx:
    return _TrailStopCtx()


@given(parsers.parse("a BUY trade with entry {entry:g} and stop-loss {stop_loss:g}"))
def _buy(ts_ctx: _TrailStopCtx, entry: float, stop_loss: float) -> None:
    ts_ctx.entry = entry
    ts_ctx.stop_loss = stop_loss
    ts_ctx.direction = Direction.BUY


@given(parsers.parse("a SELL trade with entry {entry:g} and stop-loss {stop_loss:g}"))
def _sell(ts_ctx: _TrailStopCtx, entry: float, stop_loss: float) -> None:
    ts_ctx.entry = entry
    ts_ctx.stop_loss = stop_loss
    ts_ctx.direction = Direction.SELL


@given(parsers.parse("a spread of {spread:g}"))
def _spread(ts_ctx: _TrailStopCtx, spread: float) -> None:
    ts_ctx.spread = spread


@when(parsers.parse("I compute the target level for factor {factor:g}"))
def _compute_target(ts_ctx: _TrailStopCtx, factor: float) -> None:
    ts_ctx.result = ts_ctx.error = None
    try:
        ts_ctx.result = target_level(
            entry=ts_ctx.entry,
            stop_loss=ts_ctx.stop_loss,
            target_factor=factor,
            spread=ts_ctx.spread,
            direction=ts_ctx.direction,
        )
    except ValueError as exc:
        ts_ctx.error = exc


@when(parsers.parse("I compute the trail-stop arm level for factor {factor:g}"))
def _compute_arm(ts_ctx: _TrailStopCtx, factor: float) -> None:
    ts_ctx.result = ts_ctx.error = None
    try:
        ts_ctx.result = trail_stop_at_level(
            entry=ts_ctx.entry,
            stop_loss=ts_ctx.stop_loss,
            trail_stop_at_level_factor=factor,
            spread=ts_ctx.spread,
            direction=ts_ctx.direction,
        )
    except ValueError as exc:
        ts_ctx.error = exc


@when(parsers.parse("I compute the trail-stop destination level for factor {factor:g}"))
def _compute_destination(ts_ctx: _TrailStopCtx, factor: float) -> None:
    ts_ctx.result = ts_ctx.error = None
    try:
        ts_ctx.result = trail_stop_to_level(
            entry=ts_ctx.entry,
            stop_loss=ts_ctx.stop_loss,
            trail_stop_to_level_factor=factor,
            spread=ts_ctx.spread,
            direction=ts_ctx.direction,
        )
    except ValueError as exc:
        ts_ctx.error = exc


@then(parsers.parse("the target level is {expected:g}"))
@then(parsers.parse("the trail-stop arm level is {expected:g}"))
@then(parsers.parse("the trail-stop destination level is {expected:g}"))
def _assert_level(ts_ctx: _TrailStopCtx, expected: float) -> None:
    assert ts_ctx.error is None, f"unexpected error: {ts_ctx.error}"
    assert ts_ctx.result == pytest.approx(expected)


@then("computing the level fails with a zero-distance error")
def _assert_zero_distance(ts_ctx: _TrailStopCtx) -> None:
    assert isinstance(ts_ctx.error, ValueError)
    assert "distance" in str(ts_ctx.error)
