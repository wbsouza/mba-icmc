"""Pure trade-plan math for the executor (story 12, item D): the numbers an F7 signal turns
into orders, LEAN-free and typed so `tests/features/trade_plan.feature` proves them offline.

F6 (item B) enriches ``state.features["trade_plan"]`` with the plan in **pips** — one block
per direction, because the spread term makes long and short offsets differ — and this
module converts that plan, at the moment of the entry fill, into signed order quantities
and absolute prices (``order_quantity``, ``stop_price``, ``target_prices``,
``target_quantities``), then manages the open position bar by bar (``trail_update``,
``hold_elapsed``) and reconciles its working orders when one of them fills
(``orders_to_cancel``, ``stop_quantity_for``). ``TradePlanRecord`` is the per-trade audit
row the algorithm writes to ``trade-plans.json`` (``container_paths.TRADE_PLANS_FILE``),
the contract the run statement reads — its keys are frozen.

Conventions: ``Direction.BUY`` profits as price rises; a quantity's sign is its direction
(positive = long units), so an exit quantity has the opposite sign of the position. Prices
are raw floats (LEAN rounds order prices to the instrument's tick on submission); every
quantity is snapped toward zero to the instrument's ``lot_step`` so LEAN never rounds an
order silently.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from algo_backtest.rules.close_portion import build_close_ladder
from algo_backtest.rules.trail_stop import Direction

_FEATURE_KEY = "trade_plan"
_F6 = "f6_capital_mgmt"
# Float tolerance on "is a lot-step multiple" / "is tighter" comparisons.
_EPSILON = 1e-9


# --- The plan as F6 enriches it ---------------------------------------------------------


@dataclass(frozen=True)
class PlanTarget:
    """One take-profit level: its distance from entry in pips and the fraction it closes."""

    pips: float
    close_fraction: float


@dataclass(frozen=True)
class PlanTrailStep:
    """One trailing step: the favourable move (pips) that arms it and the signed pip offset
    from entry the stop moves to (negative = still on the losing side)."""

    at_pips: float
    to_pips: float


@dataclass(frozen=True)
class DirectionalPlan:
    """The plan for one trade direction, every distance in pips from the entry fill."""

    stop_pips: float
    targets: tuple[PlanTarget, ...]
    trail_stops: tuple[PlanTrailStep, ...]
    reward_risk: float | None


@dataclass(frozen=True)
class TradePlan:
    """F6's full enrichment: the lot size and the long/short plans."""

    lot_size: float
    spread_pips: float
    long: DirectionalPlan
    short: DirectionalPlan

    def for_direction(self, direction: Direction) -> DirectionalPlan:
        """The block for `direction` (long for BUY, short for SELL)."""
        return self.long if direction is Direction.BUY else self.short


def _plan_field(block: Mapping[str, Any], key: str, where: str) -> Any:
    """`block[key]`, failing fast with the F6 contract named when it is absent."""
    if key not in block:
        raise KeyError(
            f"trade_plan: {where} is missing {key!r} — {_F6} must enrich "
            f"state.features[{_FEATURE_KEY!r}] with it (see engine/trade_plan.py)"
        )
    return block[key]


def _float_field(block: Mapping[str, Any], key: str, where: str) -> float:
    """A required numeric field of the plan as a float (booleans are not numbers)."""
    value = _plan_field(block, key, where)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"trade_plan: {where}.{key} must be a number, got {value!r}")
    return float(value)


def _directional(block: Any, where: str) -> DirectionalPlan:
    """One direction's block, typed and validated."""
    if not isinstance(block, Mapping):
        raise ValueError(f"trade_plan: {where} must be a mapping, got {block!r}")
    targets = tuple(
        PlanTarget(
            pips=_float_field(t, "pips", f"{where}.targets[{i}]"),
            close_fraction=_float_field(t, "close_fraction", f"{where}.targets[{i}]"),
        )
        for i, t in enumerate(_plan_field(block, "targets", where))
    )
    trail = tuple(
        PlanTrailStep(
            at_pips=_float_field(s, "at_pips", f"{where}.trail_stops[{i}]"),
            to_pips=_float_field(s, "to_pips", f"{where}.trail_stops[{i}]"),
        )
        for i, s in enumerate(_plan_field(block, "trail_stops", where))
    )
    reward = _plan_field(block, "reward_risk", where)
    return DirectionalPlan(
        stop_pips=_float_field(block, "stop_pips", where),
        targets=targets,
        trail_stops=trail,
        reward_risk=None if reward is None else float(reward),
    )


def parse_trade_plan(features: Mapping[str, object]) -> TradePlan:
    """The `trade_plan` F6 left in `state.features`, typed.

    Raises:
        KeyError: no `trade_plan` feature (F6 did not run, or ran without enriching it)
            or a block is missing a key — each naming the F6 contract to fix.
        ValueError: a value has the wrong type.
    """
    if _FEATURE_KEY not in features:
        raise KeyError(
            f"trade_plan: state.features has no {_FEATURE_KEY!r} — the executor sizes every "
            f"order from it, so {_F6} must be listed in the strategy's filters and must "
            "enrich the plan before F7 decides"
        )
    raw = features[_FEATURE_KEY]
    if not isinstance(raw, Mapping):
        raise ValueError(f"trade_plan: {_FEATURE_KEY!r} must be a mapping, got {raw!r}")
    return TradePlan(
        lot_size=_float_field(raw, "lot_size", _FEATURE_KEY),
        spread_pips=_float_field(raw, "spread_pips", _FEATURE_KEY),
        long=_directional(_plan_field(raw, "long", _FEATURE_KEY), f"{_FEATURE_KEY}.long"),
        short=_directional(_plan_field(raw, "short", _FEATURE_KEY), f"{_FEATURE_KEY}.short"),
    )


# --- Entry: quantity, stop and target prices --------------------------------------------


def _sign(direction: Direction) -> float:
    """+1 for BUY, -1 for SELL: the sign of a position and of a favourable price move."""
    return 1.0 if direction is Direction.BUY else -1.0


def _require_positive(name: str, value: float) -> None:
    """Fail fast on a scale that must be strictly positive."""
    if value <= 0:
        raise ValueError(f"trade_plan: {name} must be > 0, got {value!r}")


def order_quantity(lot_size: float, lot_notional_units: float, direction: Direction) -> float:
    """Signed entry quantity in units: `lot_size × lot_notional_units`, negative for SELL.

    Raises:
        ValueError: `lot_size` or `lot_notional_units` is not strictly positive (a zero
            lot is a sizing failure to surface, not an order to place).
    """
    _require_positive("lot_size", lot_size)
    _require_positive("lot_notional_units", lot_notional_units)
    return _sign(direction) * lot_size * lot_notional_units


def round_to_lot_step(quantity: float, lot_step: float) -> float:
    """`quantity` snapped toward zero to a multiple of the instrument's `lot_step`.

    Raises:
        ValueError: `lot_step` is not strictly positive.
    """
    _require_positive("lot_step", lot_step)
    steps = math.floor(abs(quantity) / lot_step + _EPSILON)
    return math.copysign(steps * lot_step, quantity) if steps else 0.0


def stop_price(entry: float, stop_pips: float, pip_size: float, direction: Direction) -> float:
    """The protective stop: `stop_pips` against the trade from `entry`.

    Raises:
        ValueError: `stop_pips` or `pip_size` is not strictly positive.
    """
    _require_positive("stop_pips", stop_pips)
    _require_positive("pip_size", pip_size)
    return entry - _sign(direction) * stop_pips * pip_size


def target_prices(
    entry: float, targets: Sequence[PlanTarget], pip_size: float, direction: Direction
) -> list[tuple[float, float]]:
    """`(price, close_fraction)` per target: `target.pips` in the trade's favour from `entry`.

    Raises:
        ValueError: `pip_size` or a target's `pips` is not strictly positive.
    """
    _require_positive("pip_size", pip_size)
    prices: list[tuple[float, float]] = []
    for index, target in enumerate(targets):
        _require_positive(f"targets[{index}].pips", target.pips)
        prices.append((entry + _sign(direction) * target.pips * pip_size, target.close_fraction))
    return prices


def target_quantities(
    quantity: float, targets: Sequence[PlanTarget], lot_step: float
) -> list[float]:
    """The signed exit quantity per target: each closes its fraction of the entry
    `quantity`, snapped to `lot_step`; when the fractions close the whole position the last
    target takes the exact remainder so the exits sum to the position
    (`rules/close_portion.build_close_ladder`).

    Raises:
        ValueError: `quantity` is zero or not a `lot_step` multiple, or the fractions are
            outside (0, 1] / sum past 1 (`build_close_ladder`'s own checks).
    """
    _require_positive("lot_step", lot_step)
    if quantity == 0:
        raise ValueError("trade_plan: target_quantities needs a non-zero position quantity")
    if abs(round_to_lot_step(quantity, lot_step) - quantity) > _EPSILON:
        raise ValueError(
            f"trade_plan: quantity {quantity!r} is not a multiple of lot_step {lot_step!r}; "
            "snap the entry quantity with round_to_lot_step first"
        )
    if not targets:
        return []
    ladder = build_close_ladder(abs(quantity), [t.close_fraction for t in targets])
    exits: list[float] = []
    closed = 0.0
    for rung in ladder.rungs:
        if rung.lot_remaining == 0.0:
            portion = abs(quantity) - closed  # the exact remainder, already a step multiple
        else:
            portion = round_to_lot_step(rung.lot_to_close, lot_step)
        closed += portion
        exits.append(-math.copysign(portion, quantity))
    return exits


# --- Management while open --------------------------------------------------------------


@dataclass(frozen=True)
class TrailMove:
    """The outcome of one trail check: the newly armed step indices (consumed for good)
    and the stop to move to, or `None` when no armed step tightens the current stop."""

    fired: tuple[int, ...]
    new_stop: float | None


def _tighter(candidate: float, current_stop: float, direction: Direction) -> bool:
    """Whether `candidate` protects more than `current_stop` (closer to the profit side)."""
    return _sign(direction) * (candidate - current_stop) > _EPSILON


def trail_update(
    entry: float,
    current: float,
    current_stop: float,
    trail_stops: Sequence[PlanTrailStep],
    pip_size: float,
    direction: Direction,
    *,
    fired: frozenset[int] = frozenset(),
) -> TrailMove | None:
    """Arm every not-yet-fired step whose `at_pips` the favourable move from `entry` to
    `current` has reached, and move the stop to the tightest armed destination
    (`entry + to_pips` on the profit axis) that is tighter than `current_stop`.

    A step fires once: the caller carries the returned `fired` indices (union with its own)
    into the next call. Returns `None` when nothing new armed this bar.

    Raises:
        ValueError: `pip_size` is not strictly positive.
    """
    _require_positive("pip_size", pip_size)
    favourable = _sign(direction) * (current - entry)
    armed = tuple(
        index
        for index, step in enumerate(trail_stops)
        if index not in fired and favourable + _EPSILON >= step.at_pips * pip_size
    )
    if not armed:
        return None
    best: float | None = None
    for index in armed:
        candidate = entry + _sign(direction) * trail_stops[index].to_pips * pip_size
        if _tighter(candidate, current_stop, direction) and (
            best is None or _tighter(candidate, best, direction)
        ):
            best = candidate
    return TrailMove(fired=armed, new_stop=best)


def hold_elapsed(entry_bar_index: int, now_index: int, min_hold_bars: int) -> bool:
    """Whether at least `min_hold_bars` bars have passed since the entry bar.

    Raises:
        ValueError: `now_index` precedes `entry_bar_index` or `min_hold_bars` is negative.
    """
    if min_hold_bars < 0:
        raise ValueError(f"trade_plan: min_hold_bars must be >= 0, got {min_hold_bars!r}")
    if now_index < entry_bar_index:
        raise ValueError(
            f"trade_plan: now_index {now_index!r} precedes entry_bar_index {entry_bar_index!r}"
        )
    return now_index - entry_bar_index >= min_hold_bars


# --- Working-order reconciliation (OCO emulation) ---------------------------------------


@dataclass(frozen=True)
class OpenOrder:
    """One working order of the plan, as LEAN's `Transactions.get_open_orders` reports it."""

    order_id: int
    quantity: float


def orders_to_cancel(position_quantity: float, open_orders: Sequence[OpenOrder]) -> tuple[int, ...]:
    """The working orders to cancel after a fill: all of them once the position is flat
    (the stop and the targets are one-cancels-the-others), none while it is still open."""
    if position_quantity != 0:
        return ()
    return tuple(order.order_id for order in open_orders)


def stop_quantity_for(position_quantity: float) -> float:
    """The stop order's quantity after a partial exit: exactly what closes the position.

    Raises:
        ValueError: the position is flat (a flat position has no stop to resize).
    """
    if position_quantity == 0:
        raise ValueError("trade_plan: stop_quantity_for needs an open position, got 0")
    return -position_quantity


@dataclass
class PlannedPosition:
    """The executor's memory of the one open planned trade: what was placed and how far the
    trailing logic has come. LEAN's portfolio stays the source of truth for the quantity."""

    direction: Direction
    plan: DirectionalPlan
    entry_price: float
    entry_bar_index: int
    entry_order_id: int
    stop_order_id: int
    target_order_ids: tuple[int, ...]
    current_stop: float
    fired: frozenset[int] = frozenset()

    def apply(self, move: TrailMove) -> None:
        """Consume the newly fired steps and adopt the tightened stop, if any."""
        self.fired = self.fired | frozenset(move.fired)
        if move.new_stop is not None:
            self.current_stop = move.new_stop


# --- The per-trade audit record (trade-plans.json contract) -----------------------------


@dataclass(frozen=True)
class TakeProfitRecord:
    """One take-profit order as placed."""

    price: float
    close_fraction: float
    quantity: float


@dataclass(frozen=True)
class TrailStopRecord:
    """One trailing step as planned: the ratios (pips over the stop distance) and prices."""

    at_level_ratio: float
    to_level_ratio: float
    at_price: float
    to_price: float


@dataclass(frozen=True)
class TradePlanRecord:
    """One entry and the plan placed around it — a row of `trade-plans.json`.

    Key names are the contract the run statement (story 12, item H) reads; do not rename.
    """

    entry_order_id: int
    entry_time: str  # ISO-8601 UTC
    direction: str  # "buy" | "sell"
    lots: float
    quantity: float
    entry_price: float
    stop_loss: float
    take_profits: tuple[TakeProfitRecord, ...]
    trail_stops: tuple[TrailStopRecord, ...]
    spread_pips: float

    def to_mapping(self) -> dict[str, Any]:
        """The record as the JSON object written to `trade-plans.json` (lists, not tuples)."""
        mapping = asdict(self)
        mapping["take_profits"] = [asdict(t) for t in self.take_profits]
        mapping["trail_stops"] = [asdict(t) for t in self.trail_stops]
        return mapping


def build_record(
    *,
    entry_order_id: int,
    entry_time: str,
    direction: Direction,
    lots: float,
    quantity: float,
    entry_price: float,
    stop_loss: float,
    targets: Sequence[tuple[float, float, float]],
    plan: DirectionalPlan,
    pip_size: float,
    spread_pips: float,
) -> TradePlanRecord:
    """Assemble the audit record from the orders placed and the directional plan.

    `targets` are `(price, close_fraction, quantity)` triples as placed; the trailing
    steps' ratios are their pip offsets over the plan's stop distance.
    """
    sign = _sign(direction)
    return TradePlanRecord(
        entry_order_id=entry_order_id,
        entry_time=entry_time,
        direction=direction.value.lower(),
        lots=lots,
        quantity=quantity,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profits=tuple(
            TakeProfitRecord(price=price, close_fraction=fraction, quantity=qty)
            for price, fraction, qty in targets
        ),
        trail_stops=tuple(
            TrailStopRecord(
                at_level_ratio=step.at_pips / plan.stop_pips,
                to_level_ratio=step.to_pips / plan.stop_pips,
                at_price=entry_price + sign * step.at_pips * pip_size,
                to_price=entry_price + sign * step.to_pips * pip_size,
            )
            for step in plan.trail_stops
        ),
        spread_pips=spread_pips,
    )


def plans_json(records: Sequence[TradePlanRecord]) -> str:
    """The `trade-plans.json` document: a JSON list of records, one per entry, in order."""
    return json.dumps([record.to_mapping() for record in records], indent=2) + "\n"
