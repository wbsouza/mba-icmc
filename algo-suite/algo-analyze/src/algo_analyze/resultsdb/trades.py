"""Closed trades, their plans, exit kinds and trail moves.

Exit-kind rules (the `exit_kind` column, one of `schema.EXIT_KINDS`), decided from the
LEAN order that produced the trade's final fill (the last id in `trades.json`
`orderIds`, looked up in `main.json` `orders`) and the engine log:

- a **limit** order (LEAN type 1) closed it -> `target` (a take-profit level filled);
- a **stop** order (type 2) closed it -> `trail_stop` when a `<TAG>_TRAIL|` line moved
  this trade's stop between its entry and exit (the line's `entry=` price is the
  trade's entry price), else `stop` (the initial protective stop);
- a **market** order (type 0) closed it -> `reversal` when a `<TAG>_OCO_CANCEL|` line
  with `reason=reversal` was logged at the exit minute, `liquidation` when that line's
  reason is `veto` (the chain closed the position on a stand-aside), else `unknown`;
- any other order type -> `unknown`.

Nothing is guessed: a trade whose closing order cannot be found in `main.json` is a
malformed run directory and fails the build.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from algo_backtest.statement import direction_label, duration_minutes, parse_time

from algo_analyze.resultsdb.artifacts import PLANS_FILE, TRADES_FILE, LogRecord, field

_ORDER_TYPES: Mapping[int, str] = {0: "market", 1: "limit", 2: "stop"}
_MARKET_KINDS: Mapping[str, str] = {"reversal": "reversal", "veto": "liquidation"}


@dataclass(frozen=True)
class TradeRow:
    """One `trades` row (times ISO-8601 UTC; `lots` None when no plan or lot size)."""

    trade_id: str
    entry_order_id: int
    direction: str
    lots: float | None
    quantity: float
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    profit: float
    fees: float
    is_win: bool
    exit_kind: str
    exit_order_id: int
    exit_order_type: str
    holding_minutes: float


@dataclass(frozen=True)
class PlanRow:
    """One `trade_plans` row: the stop, its distance in pips, targets and trail steps."""

    trade_id: str
    stop_loss: float
    stop_pips: float | None
    targets_json: str
    trail_steps_json: str
    spread_pips: float | None


@dataclass(frozen=True)
class TrailMove:
    """One `trail_moves` row (`trade_id` None when no closed trade spans the move)."""

    trade_id: str | None
    time: datetime
    from_stop: float
    to_stop: float


def order_type(orders: Mapping[str, Mapping[str, Any]], order_id: int, run_dir: Path) -> str:
    """`market`/`limit`/`stop` of one LEAN order; fail fast when it is not recorded."""
    order = orders.get(str(order_id))
    if order is None:
        raise ValueError(
            f"main.json in {run_dir} has no order {order_id}, the closing order of a trade "
            "in trades.json; the run directory is inconsistent"
        )
    kind = field(order, "type", run_dir / "main.json")
    if kind not in _ORDER_TYPES:
        raise ValueError(f"main.json in {run_dir} order {order_id} has unknown type {kind!r}")
    return _ORDER_TYPES[int(kind)]


def _trailed(log: Sequence[LogRecord], entry: datetime, exit_: datetime, price: float) -> bool:
    """Whether a TRAIL line moved the stop of the trade opened at `price` in [entry, exit]."""
    return any(
        r.tag == "TRAIL" and entry <= r.time <= exit_ and float(r.fields["entry"]) == price
        for r in log
    )


def _market_exit_kind(log: Sequence[LogRecord], exit_: datetime) -> str:
    """`reversal`/`liquidation` from the OCO_CANCEL reason logged at the exit minute."""
    for record in log:
        if record.tag == "OCO_CANCEL" and record.time == exit_:
            kind = _MARKET_KINDS.get(record.fields.get("reason", ""))
            if kind is not None:
                return kind
    return "unknown"


def classify_exit(
    closing_type: str, log: Sequence[LogRecord], entry: datetime, exit_: datetime, price: float
) -> str:
    """The exit kind of a trade (rules in the module docstring); pure."""
    if closing_type == "limit":
        return "target"
    if closing_type == "stop":
        return "trail_stop" if _trailed(log, entry, exit_, price) else "stop"
    if closing_type == "market":
        return _market_exit_kind(log, exit_)
    return "unknown"


def _lots(plan: Mapping[str, Any] | None, quantity: float, lot_units: float | None) -> float | None:
    """Lots from the plan, else quantity / lot size, else None (never guessed)."""
    if plan is not None and plan.get("lots") is not None:
        return float(plan["lots"])
    if lot_units:
        return abs(quantity) / lot_units
    return None


def lot_notional_units(config: Mapping[str, Any] | None) -> float | None:
    """`capital_mgmt.lot_notional_units` of the resolved config, `None` when unrecorded."""
    if config is None:
        return None
    section = config.get("capital_mgmt")
    if not isinstance(section, Mapping) or section.get("lot_notional_units") is None:
        return None
    return float(section["lot_notional_units"])


def plans_by_entry(plans: Sequence[Mapping[str, Any]] | None, run_dir: Path) -> dict[int, Any]:
    """`trade-plans.json` indexed by entry order id (empty when the file is absent)."""
    if plans is None:
        return {}
    return {int(field(plan, "entry_order_id", run_dir / PLANS_FILE)): plan for plan in plans}


def trade_row(
    trade: Mapping[str, Any], orders: Mapping[str, Mapping[str, Any]], log: Sequence[LogRecord],
    plan: Mapping[str, Any] | None, lot_units: float | None, run_dir: Path,
) -> TradeRow:
    """One `trades.json` ledger entry -> one `trades` row, exit kind classified."""
    path = run_dir / TRADES_FILE
    order_ids = [int(i) for i in field(trade, "orderIds", path)]
    if not order_ids:
        raise ValueError(f"{TRADES_FILE} in {run_dir} has a closed trade with empty orderIds")
    entry = parse_time(str(field(trade, "entryTime", path)), "entryTime", TRADES_FILE)
    exit_ = parse_time(str(field(trade, "exitTime", path)), "exitTime", TRADES_FILE)
    entry_price = float(field(trade, "entryPrice", path))
    closing = order_type(orders, order_ids[-1], run_dir)
    quantity = float(field(trade, "quantity", path))
    return TradeRow(
        trade_id=str(order_ids[0]), entry_order_id=order_ids[0],
        direction=direction_label(field(trade, "direction", path)),
        lots=_lots(plan, quantity, lot_units), quantity=quantity, entry_time=entry,
        entry_price=entry_price, exit_time=exit_, exit_price=float(field(trade, "exitPrice", path)),
        profit=float(field(trade, "profitLoss", path)), fees=float(trade.get("totalFees", 0.0)),
        is_win=bool(trade.get("isWin", float(field(trade, "profitLoss", path)) > 0)),
        exit_kind=classify_exit(closing, log, entry, exit_, entry_price),
        exit_order_id=order_ids[-1], exit_order_type=closing,
        holding_minutes=duration_minutes(str(field(trade, "duration", path))),
    )


def _stop_pips(plan: Mapping[str, Any]) -> float | None:
    """The stop distance in pips when the plan records it (older plans do not)."""
    for key in ("stop_pips", "stop_loss_pips"):
        if plan.get(key) is not None:
            return float(plan[key])
    return None


def plan_row(trade_id: str, plan: Mapping[str, Any], run_dir: Path) -> PlanRow:
    """One `trade-plans.json` record -> one `trade_plans` row (targets/trail as JSON)."""
    path = run_dir / PLANS_FILE
    return PlanRow(
        trade_id=trade_id, stop_loss=float(field(plan, "stop_loss", path)),
        stop_pips=_stop_pips(plan),
        targets_json=json.dumps(field(plan, "take_profits", path)),
        trail_steps_json=json.dumps(plan.get("trail_stops", [])),
        spread_pips=None if plan.get("spread_pips") is None else float(plan["spread_pips"]),
    )


def trail_moves(log: Sequence[LogRecord], trades: Sequence[TradeRow]) -> list[TrailMove]:
    """Every TRAIL line, joined to the closed trade it moved (by time span and entry)."""
    moves: list[TrailMove] = []
    for record in log:
        if record.tag != "TRAIL":
            continue
        price = float(record.fields["entry"])
        owner = next(
            (t for t in trades
             if t.entry_time <= record.time <= t.exit_time and t.entry_price == price),
            None,
        )
        moves.append(TrailMove(
            trade_id=None if owner is None else owner.trade_id, time=record.time,
            from_stop=float(record.fields["from"]), to_stop=float(record.fields["to"]),
        ))
    return moves
