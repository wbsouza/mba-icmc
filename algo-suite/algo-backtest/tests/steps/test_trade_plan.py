"""Steps for trade_plan.feature — the LEAN-free executor math of story 12, item D."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest
import yaml
from algo_backtest.engine.trade_plan import (
    DirectionalPlan,
    OpenOrder,
    PlanTarget,
    PlanTrailStep,
    TradePlan,
    TradePlanRecord,
    build_record,
    hold_elapsed,
    order_quantity,
    orders_to_cancel,
    parse_trade_plan,
    plans_json,
    round_to_lot_step,
    stop_price,
    stop_quantity_for,
    target_prices,
    target_quantities,
    trail_update,
)
from algo_backtest.rules.trail_stop import Direction
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/trade_plan.feature")


@dataclass
class _PlanCtx:
    """Per-scenario inputs and the outcome of the computation under test."""

    result: Any = None
    error: Exception | None = None
    steps: list[PlanTrailStep] = field(default_factory=list)
    pip_size: float = 0.0
    fired: frozenset[int] = frozenset()
    features: dict[str, object] = field(default_factory=dict)
    record: TradePlanRecord | None = None
    serialised: dict[str, Any] = field(default_factory=dict)


@pytest.fixture
def plan_ctx() -> _PlanCtx:
    return _PlanCtx()


def _targets(cell: str) -> list[PlanTarget]:
    """A YAML list of `{pips, close_fraction}` cells as plan targets."""
    return [PlanTarget(**entry) for entry in yaml.safe_load(cell)]


def _trail(cell: str) -> list[PlanTrailStep]:
    """A YAML list of `{at_pips, to_pips}` cells as trailing steps."""
    return [PlanTrailStep(**entry) for entry in yaml.safe_load(cell)]


def _fail(plan_ctx: _PlanCtx, call: Any) -> None:
    """Run `call` expecting a ValueError/KeyError, keeping it for the Then steps."""
    with pytest.raises((ValueError, KeyError)) as exc_info:
        call()
    plan_ctx.error = exc_info.value


# --- quantity ---------------------------------------------------------------------------


@when(
    parsers.parse(
        "the order quantity is computed for {lots:g} lots of {units:g} units to {direction}"
    )
)
def _quantity(plan_ctx: _PlanCtx, lots: float, units: float, direction: str) -> None:
    plan_ctx.result = order_quantity(lots, units, Direction(direction))


@when(
    parsers.parse(
        "computing the order quantity for {lots:g} lots of {units:g} units to {direction} fails"
    )
)
def _quantity_fails(plan_ctx: _PlanCtx, lots: float, units: float, direction: str) -> None:
    _fail(plan_ctx, lambda: order_quantity(lots, units, Direction(direction)))


@then(parsers.parse("the quantity is {quantity:g}"))
def _quantity_is(plan_ctx: _PlanCtx, quantity: float) -> None:
    assert plan_ctx.result == quantity


@when(parsers.parse("{quantity:g} units are rounded to a lot step of {lot_step:g}"))
def _round(plan_ctx: _PlanCtx, quantity: float, lot_step: float) -> None:
    plan_ctx.result = round_to_lot_step(quantity, lot_step)


@then(parsers.parse("the rounded quantity is {rounded:g}"))
def _rounded_is(plan_ctx: _PlanCtx, rounded: float) -> None:
    assert plan_ctx.result == rounded


# --- stop and targets -------------------------------------------------------------------


@when(
    parsers.parse(
        "the stop price is computed for a {direction} at {entry:g} with stop {stop_pips:g} pips "
        "and pip size {pip_size:g}"
    )
)
def _stop(
    plan_ctx: _PlanCtx, direction: str, entry: float, stop_pips: float, pip_size: float
) -> None:
    plan_ctx.result = stop_price(entry, stop_pips, pip_size, Direction(direction))


@when(
    parsers.parse(
        "computing the stop price for a {direction} at {entry:g} with stop {stop_pips:g} pips "
        "and pip size {pip_size:g} fails"
    )
)
def _stop_fails(
    plan_ctx: _PlanCtx, direction: str, entry: float, stop_pips: float, pip_size: float
) -> None:
    _fail(plan_ctx, lambda: stop_price(entry, stop_pips, pip_size, Direction(direction)))


@then(parsers.parse("the stop price is {stop:g} within {tolerance:g}"))
def _stop_is(plan_ctx: _PlanCtx, stop: float, tolerance: float) -> None:
    assert plan_ctx.result == pytest.approx(stop, abs=tolerance)


@when(
    parsers.parse(
        "the target prices are computed for a {direction} at {entry:g} with targets {targets} "
        "and pip size {pip_size:g}"
    )
)
def _target_prices(
    plan_ctx: _PlanCtx, direction: str, entry: float, targets: str, pip_size: float
) -> None:
    plan_ctx.result = target_prices(entry, _targets(targets), pip_size, Direction(direction))


@then(parsers.parse("the target prices are {prices} within {tolerance:g}"))
def _target_prices_are(plan_ctx: _PlanCtx, prices: str, tolerance: float) -> None:
    expected = [tuple(pair) for pair in yaml.safe_load(prices)]
    assert len(plan_ctx.result) == len(expected)
    for (price, fraction), (want_price, want_fraction) in zip(
        plan_ctx.result, expected, strict=True
    ):
        assert price == pytest.approx(want_price, abs=tolerance)
        assert fraction == want_fraction


@when(
    parsers.parse(
        "the target quantities are computed for a position of {quantity:g} with fractions "
        "{fractions} and lot step {lot_step:g}"
    )
)
def _target_quantities(
    plan_ctx: _PlanCtx, quantity: float, fractions: str, lot_step: float
) -> None:
    targets = [PlanTarget(pips=1.0, close_fraction=f) for f in yaml.safe_load(fractions)]
    plan_ctx.result = target_quantities(quantity, targets, lot_step)


@when(
    parsers.parse(
        "computing the target quantities for a position of {quantity:g} with fractions "
        "{fractions} and lot step {lot_step:g} fails"
    )
)
def _target_quantities_fail(
    plan_ctx: _PlanCtx, quantity: float, fractions: str, lot_step: float
) -> None:
    targets = [PlanTarget(pips=1.0, close_fraction=f) for f in yaml.safe_load(fractions)]
    _fail(plan_ctx, lambda: target_quantities(quantity, targets, lot_step))


@then(parsers.parse("the target quantities are {exits}"))
def _target_quantities_are(plan_ctx: _PlanCtx, exits: str) -> None:
    assert plan_ctx.result == [float(q) for q in yaml.safe_load(exits)]


# --- trail ------------------------------------------------------------------------------


@given(parsers.parse("the trailing steps {steps} with pip size {pip_size:g}"))
def _trail_steps(plan_ctx: _PlanCtx, steps: str, pip_size: float) -> None:
    plan_ctx.steps = _trail(steps)
    plan_ctx.pip_size = pip_size


@given(parsers.parse("the steps already fired are {fired}"))
def _fired(plan_ctx: _PlanCtx, fired: str) -> None:
    plan_ctx.fired = frozenset(yaml.safe_load(fired))


@when(
    parsers.parse(
        "the trail is checked for a {direction} entered at {entry:g} now at {current:g} with "
        "stop {current_stop:g}"
    )
)
def _trail_check(
    plan_ctx: _PlanCtx, direction: str, entry: float, current: float, current_stop: float
) -> None:
    plan_ctx.result = trail_update(
        entry, current, current_stop, plan_ctx.steps, plan_ctx.pip_size, Direction(direction),
        fired=plan_ctx.fired,
    )


@then(
    parsers.parse(
        "the trail outcome is {outcome} with new stop {new_stop} and fired steps {newly_fired}"
    )
)
def _trail_outcome(plan_ctx: _PlanCtx, outcome: str, new_stop: str, newly_fired: str) -> None:
    move = plan_ctx.result
    if outcome == "none":
        assert move is None
        return
    assert move is not None
    assert move.fired == tuple(yaml.safe_load(newly_fired))
    expected = yaml.safe_load(new_stop)
    if outcome == "consume":
        assert move.new_stop is None and expected is None
    else:
        assert move.new_stop == pytest.approx(float(expected), abs=1e-9)


# --- hold -------------------------------------------------------------------------------


@when(
    parsers.parse(
        "the hold is checked for entry bar {entry_bar:d} at bar {now:d} with min hold {hold:d}"
    )
)
def _hold(plan_ctx: _PlanCtx, entry_bar: int, now: int, hold: int) -> None:
    plan_ctx.result = hold_elapsed(entry_bar, now, hold)


@when(
    parsers.parse(
        "checking the hold for entry bar {entry_bar:d} at bar {now:d} with min hold {hold:d} fails"
    )
)
def _hold_fails(plan_ctx: _PlanCtx, entry_bar: int, now: int, hold: int) -> None:
    _fail(plan_ctx, lambda: hold_elapsed(entry_bar, now, hold))


@then(parsers.parse("the hold elapsed is {elapsed}"))
def _hold_is(plan_ctx: _PlanCtx, elapsed: str) -> None:
    assert plan_ctx.result is (elapsed == "true")


# --- reconciliation ---------------------------------------------------------------------


@when(
    parsers.parse(
        "the orders to cancel are computed for a position of {position:g} with working "
        "orders {orders}"
    )
)
def _cancel(plan_ctx: _PlanCtx, position: float, orders: str) -> None:
    open_orders = [OpenOrder(order_id=i, quantity=q) for i, q in yaml.safe_load(orders)]
    plan_ctx.result = orders_to_cancel(position, open_orders)


@then(parsers.parse("the orders to cancel are {cancelled}"))
def _cancel_is(plan_ctx: _PlanCtx, cancelled: str) -> None:
    assert plan_ctx.result == tuple(yaml.safe_load(cancelled))


@when(parsers.parse("the stop quantity is computed for a remaining position of {position:g}"))
def _stop_quantity(plan_ctx: _PlanCtx, position: float) -> None:
    plan_ctx.result = stop_quantity_for(position)


@when(
    parsers.parse("computing the stop quantity for a remaining position of {position:g} fails")
)
def _stop_quantity_fails(plan_ctx: _PlanCtx, position: float) -> None:
    _fail(plan_ctx, lambda: stop_quantity_for(position))


@then(parsers.parse("the stop quantity is {quantity:g}"))
def _stop_quantity_is(plan_ctx: _PlanCtx, quantity: float) -> None:
    assert plan_ctx.result == quantity


# --- parsing ----------------------------------------------------------------------------


def _long_block(stop: float, targets: str, trail: str) -> dict[str, Any]:
    """A directional block of the F6 contract."""
    return {
        "stop_pips": stop,
        "targets": yaml.safe_load(targets),
        "trail_stops": yaml.safe_load(trail),
        "reward_risk": 2.0,
    }


@given(
    parsers.parse(
        "a trade_plan feature with lot_size {lots:g} and spread {spread:g} whose long stop is "
        "{stop:g} pips with targets {targets} and trail {trail}"
    )
)
def _feature(
    plan_ctx: _PlanCtx, lots: float, spread: float, stop: float, targets: str, trail: str
) -> None:
    plan_ctx.features = {
        "trade_plan": {
            "lot_size": lots,
            "spread_pips": spread,
            "long": _long_block(stop, targets, trail),
            "short": _long_block(stop, "[]", "[]"),
        }
    }


@given("features without a trade_plan")
def _no_feature(plan_ctx: _PlanCtx) -> None:
    plan_ctx.features = {"proposed_lot_size": 1.0}


@given(parsers.parse('a trade_plan feature whose long block lacks "{key}"'))
def _feature_lacking(plan_ctx: _PlanCtx, key: str) -> None:
    long = _long_block(16.0, "[]", "[]")
    del long[key]
    plan_ctx.features = {
        "trade_plan": {"lot_size": 1.0, "spread_pips": 1.0, "long": long,
                       "short": _long_block(16.0, "[]", "[]")}
    }


@given(parsers.parse("a trade_plan feature where {path} is set to {value}"))
def _feature_with_value(plan_ctx: _PlanCtx, path: str, value: str) -> None:
    """A complete plan with the dotted `path` (`trade_plan[.block[.key]]`) set to a YAML value."""
    plan_ctx.features = {
        "trade_plan": {"lot_size": 1.0, "spread_pips": 1.0, "long": _long_block(16.0, "[]", "[]"),
                       "short": _long_block(16.0, "[]", "[]")}
    }
    *parents, leaf = path.split(".")
    node: Any = plan_ctx.features
    for part in parents:
        node = node[part]
    node[leaf] = yaml.safe_load(value)


@when("the trade plan is parsed")
def _parse(plan_ctx: _PlanCtx) -> None:
    plan_ctx.result = parse_trade_plan(plan_ctx.features)


@when("parsing the trade plan fails")
def _parse_fails(plan_ctx: _PlanCtx) -> None:
    _fail(plan_ctx, lambda: parse_trade_plan(plan_ctx.features))


@then(
    parsers.parse(
        "the parsed plan has lot_size {lots:g}, spread {spread:g}, long stop {stop:g} pips, "
        "{n_targets:d} long target and {n_trail:d} long trail step"
    )
)
def _parsed(
    plan_ctx: _PlanCtx, lots: float, spread: float, stop: float, n_targets: int, n_trail: int
) -> None:
    plan: TradePlan = plan_ctx.result
    assert (plan.lot_size, plan.spread_pips, plan.long.stop_pips) == (lots, spread, stop)
    assert len(plan.long.targets) == n_targets and len(plan.long.trail_stops) == n_trail


@then("the parsed long block for BUY is the long plan")
def _for_direction(plan_ctx: _PlanCtx) -> None:
    plan: TradePlan = plan_ctx.result
    assert plan.for_direction(Direction.BUY) is plan.long
    assert plan.for_direction(Direction.SELL) is plan.short


@then(parsers.parse('the trade-plan failure names "{fragment}"'))
def _failure_names(plan_ctx: _PlanCtx, fragment: str) -> None:
    assert plan_ctx.error is not None
    assert fragment in str(plan_ctx.error), str(plan_ctx.error)


# --- record -----------------------------------------------------------------------------


@given(
    parsers.parse(
        "a {direction} plan record at {entry:g} for {lots:g} lots ({quantity:g} units), stop "
        "{stop:g}, targets {targets}, trail {trail} over a {stop_pips:g} pip stop, spread "
        "{spread:g}"
    )
)
def _record(
    plan_ctx: _PlanCtx, direction: str, entry: float, lots: float, quantity: float,
    stop: float, targets: str, trail: str, stop_pips: float, spread: float,
) -> None:
    plan = DirectionalPlan(
        stop_pips=stop_pips, targets=(), trail_stops=tuple(_trail(trail)), reward_risk=None
    )
    plan_ctx.record = build_record(
        entry_order_id=1, entry_time="2014-05-08T10:00:00+00:00", direction=Direction(direction),
        lots=lots, quantity=quantity, entry_price=entry, stop_loss=stop,
        targets=[tuple(t) for t in yaml.safe_load(targets)], plan=plan, pip_size=0.0001,
        spread_pips=spread,
    )


@when("the record is serialised")
def _serialise(plan_ctx: _PlanCtx) -> None:
    assert plan_ctx.record is not None
    plan_ctx.serialised = plan_ctx.record.to_mapping()


@then(parsers.parse("the serialised record has exactly the keys {keys}"))
def _keys(plan_ctx: _PlanCtx, keys: str) -> None:
    assert list(plan_ctx.serialised) == [k.strip() for k in keys.split(",")]


@then(parsers.parse('the serialised direction is "{direction}"'))
def _direction(plan_ctx: _PlanCtx, direction: str) -> None:
    assert plan_ctx.serialised["direction"] == direction


@then(parsers.parse("the serialised take_profits are {take_profits}"))
def _take_profits(plan_ctx: _PlanCtx, take_profits: str) -> None:
    assert plan_ctx.serialised["take_profits"] == yaml.safe_load(take_profits)


@then(parsers.parse("the serialised trail_stops are {trail} within {tolerance:g}"))
def _trail_records(plan_ctx: _PlanCtx, trail: str, tolerance: float) -> None:
    expected = yaml.safe_load(trail)
    actual = plan_ctx.serialised["trail_stops"]
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected, strict=True):
        assert set(got) == set(want)
        for key, value in want.items():
            assert got[key] == pytest.approx(value, abs=tolerance), key


@then("the trade-plans document is a JSON list of that one record")
def _document(plan_ctx: _PlanCtx) -> None:
    assert plan_ctx.record is not None
    assert json.loads(plans_json([plan_ctx.record])) == [plan_ctx.serialised]
