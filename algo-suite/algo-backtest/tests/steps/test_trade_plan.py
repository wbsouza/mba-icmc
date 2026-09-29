"""Steps for trade_plan.feature — the LEAN-free executor math of story 12, item D."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import pytest
import yaml
from algo_backtest.engine.trade_plan import (
    DirectionalPlan,
    OpenOrder,
    PlannedPosition,
    PlanTarget,
    PlanTrailStep,
    TradePlan,
    TradePlanRecord,
    TrailMove,
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
    position: PlannedPosition | None = None


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


@when(parsers.parse("rounding {quantity:g} units to a lot step of {lot_step:g} fails"))
def _round_fails(plan_ctx: _PlanCtx, quantity: float, lot_step: float) -> None:
    _fail(plan_ctx, lambda: round_to_lot_step(quantity, lot_step))


@then(parsers.parse("the rounded quantity is {rounded:g}"))
def _rounded_is(plan_ctx: _PlanCtx, rounded: float) -> None:
    assert plan_ctx.result == rounded


@then(parsers.parse('the rounded quantity is written as "{text}"'))
def _rounded_text(plan_ctx: _PlanCtx, text: str) -> None:
    """The sign matters in a log line or a JSON document: `-0.0` is not `0.0` there."""
    assert f"{plan_ctx.result}" == text


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


@when(
    parsers.parse(
        "computing the target prices for a {direction} at {entry:g} with targets {targets} "
        "and pip size {pip_size:g} fails"
    )
)
def _target_prices_fail(
    plan_ctx: _PlanCtx, direction: str, entry: float, targets: str, pip_size: float
) -> None:
    _fail(
        plan_ctx, lambda: target_prices(entry, _targets(targets), pip_size, Direction(direction))
    )


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


@when(
    parsers.parse(
        "checking the trail for a {direction} entered at {entry:g} now at {current:g} with "
        "stop {current_stop:g} fails"
    )
)
def _trail_check_fails(
    plan_ctx: _PlanCtx, direction: str, entry: float, current: float, current_stop: float
) -> None:
    _fail(
        plan_ctx,
        lambda: trail_update(
            entry, current, current_stop, plan_ctx.steps, plan_ctx.pip_size,
            Direction(direction), fired=plan_ctx.fired,
        ),
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


@given(
    parsers.parse(
        "a planned BUY position with stop {stop:g} whose fired steps are {fired}"
    )
)
def _position(plan_ctx: _PlanCtx, stop: float, fired: str) -> None:
    """The executor's record of one open long trade at 1.10000 (order ids are arbitrary)."""
    plan = DirectionalPlan(stop_pips=20.0, targets=(), trail_stops=(), reward_risk=None)
    plan_ctx.position = PlannedPosition(
        direction=Direction.BUY, plan=plan, entry_price=1.1, entry_bar_index=0,
        entry_order_id=1, stop_order_id=2, target_order_ids=(), current_stop=stop,
        fired=frozenset(yaml.safe_load(fired)),
    )


@when(parsers.parse("the trail move firing {fired} with new stop {new_stop} is applied to it"))
def _apply_move(plan_ctx: _PlanCtx, fired: str, new_stop: str) -> None:
    assert plan_ctx.position is not None
    stop = yaml.safe_load(new_stop)
    move = TrailMove(
        fired=tuple(yaml.safe_load(fired)), new_stop=None if stop is None else float(stop)
    )
    plan_ctx.position.apply(move)


@then(parsers.parse("the position's fired steps are {fired} and its stop is {stop:g}"))
def _position_is(plan_ctx: _PlanCtx, fired: str, stop: float) -> None:
    assert plan_ctx.position is not None
    assert plan_ctx.position.fired == frozenset(yaml.safe_load(fired))
    assert plan_ctx.position.current_stop == pytest.approx(stop, abs=1e-9)


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


def _walk(node: Any, path: str) -> tuple[Any, str | int]:
    """The container and final key/index a dotted `a.b[0].c` path names inside `node`."""
    parts = re.findall(r"\[(\d+)\]|([^.\[\]]+)", path)
    keys: list[str | int] = [int(index) if index else name for index, name in parts]
    for key in keys[:-1]:
        node = node[key]
    return node, keys[-1]


@given("the state features hold this trade_plan")
def _feature(plan_ctx: _PlanCtx, docstring: str) -> None:
    """The F6 enrichment as a YAML document (the Background of the parsing rule)."""
    plan_ctx.features = {"trade_plan": yaml.safe_load(docstring)}


@given("the state features hold no trade_plan at all")
def _no_feature(plan_ctx: _PlanCtx) -> None:
    plan_ctx.features = {}


@given(parsers.parse("the state features hold the trade_plan value {value}"))
def _feature_scalar(plan_ctx: _PlanCtx, value: str) -> None:
    plan_ctx.features = {"trade_plan": yaml.safe_load(value)}


@given(parsers.parse("the trade_plan path {path} is removed"))
def _feature_lacking(plan_ctx: _PlanCtx, path: str) -> None:
    """Delete one key (`long.targets[0].pips`-style path) from the Background's plan."""
    node, key = _walk(plan_ctx.features["trade_plan"], path)
    del node[key]


@given(parsers.parse("the trade_plan path {path} is set to {value}"))
def _feature_with_value(plan_ctx: _PlanCtx, path: str, value: str) -> None:
    """Overwrite one key of the Background's plan with a YAML value."""
    node, key = _walk(plan_ctx.features["trade_plan"], path)
    node[key] = yaml.safe_load(value)


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


@then(
    parsers.parse(
        "the parsed long target {index:d} is {pips:g} pips closing {fraction:g} of the position"
    )
)
def _parsed_target(plan_ctx: _PlanCtx, index: int, pips: float, fraction: float) -> None:
    plan: TradePlan = plan_ctx.result
    assert plan.long.targets[index - 1] == PlanTarget(pips=pips, close_fraction=fraction)


@then(
    parsers.parse(
        "the parsed long trail step {index:d} arms at {at_pips:g} pips and moves the stop to "
        "{to_pips:g} pips"
    )
)
def _parsed_trail(plan_ctx: _PlanCtx, index: int, at_pips: float, to_pips: float) -> None:
    plan: TradePlan = plan_ctx.result
    assert plan.long.trail_stops[index - 1] == PlanTrailStep(at_pips=at_pips, to_pips=to_pips)


@then(parsers.parse("the parsed long plan has reward_risk {ratio}"))
def _parsed_reward(plan_ctx: _PlanCtx, ratio: str) -> None:
    plan: TradePlan = plan_ctx.result
    assert plan.long.reward_risk == yaml.safe_load(ratio)


@then(parsers.parse("the parsed short plan has stop_pips {stop:g} and reward_risk {ratio}"))
def _parsed_short(plan_ctx: _PlanCtx, stop: float, ratio: str) -> None:
    plan: TradePlan = plan_ctx.result
    assert (plan.short.stop_pips, plan.short.reward_risk) == (stop, yaml.safe_load(ratio))


@then("the parsed long block for BUY is the long plan")
def _for_direction(plan_ctx: _PlanCtx) -> None:
    plan: TradePlan = plan_ctx.result
    assert plan.for_direction(Direction.BUY) is plan.long
    assert plan.for_direction(Direction.SELL) is plan.short


@then(parsers.parse('the trade-plan failure names "{fragment}"'))
def _failure_names(plan_ctx: _PlanCtx, fragment: str) -> None:
    assert plan_ctx.error is not None
    assert fragment in str(plan_ctx.error), str(plan_ctx.error)


@then(parsers.parse('the trade-plan failure is exactly "{message}"'))
def _failure_exactly(plan_ctx: _PlanCtx, message: str) -> None:
    """The whole message (`args[0]`, since `str(KeyError)` re-quotes it)."""
    assert plan_ctx.error is not None
    assert plan_ctx.error.args[0] == message


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


@then("the serialised scalar fields are")
def _scalar_fields(plan_ctx: _PlanCtx, datatable: list[list[str]]) -> None:
    """Each `field | value` row, compared as text (ints, floats and ISO strings alike)."""
    _header, *rows = datatable
    for field_name, value in rows:
        assert f"{plan_ctx.serialised[field_name]}" == value, field_name


@then("the trade-plans document is a JSON list of that one record")
def _document(plan_ctx: _PlanCtx) -> None:
    assert plan_ctx.record is not None
    assert json.loads(plans_json([plan_ctx.record])) == [plan_ctx.serialised]


@then("the trade-plans document is exactly")
def _document_exactly(plan_ctx: _PlanCtx, docstring: str) -> None:
    """Byte-for-byte: two-space indentation and one trailing newline."""
    assert plan_ctx.record is not None
    assert plans_json([plan_ctx.record]) == docstring + "\n"
