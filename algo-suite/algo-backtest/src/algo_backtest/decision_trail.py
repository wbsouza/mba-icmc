"""Per-trade decision trails: how the filter chain reached each closed trade, LEAN-free.

`report.html`'s Trade History lets every closed trade expand into the chain's reasoning
at the moment of entry, the plan the executor placed around it and the order that
closed it. This module builds that trail purely from the run directory's artifacts (no
LEAN import, no engine re-run), so `algo-backtest statement --run` regenerates it for
any finished chain run on disk:

  trades.json          the closed trade: `orderIds` (entry first, exits in fill order),
                       `entryTime`, `exitTime`, `entryPrice`, `exitPrice`, `profitLoss`
  trade-plans.json     the plan placed at the entry, joined by
                       `trades.json.orderIds[0] == entry_order_id`
  decisions.parquet    the chain's row at the entry bar: the first row whose `trade_id`
                       equals the trade's id (`orderIds[0]`, the flat-to-flat policy of
                       `chain/decision_recorder.py`), or, failing that, the row timestamped
                       at the entry; neither -> fail fast naming the trade, never invent
  strategy-config.json the F7 thresholds (`meta_learner.theta_high` / `theta_low` /
                       `regime_gate`) the recorded `p_hat` was judged against
  <algo>.json          LEAN's `orders` map, which classifies the exit: the trade's last
                       order is a stop-market (`type` 2), a limit target (`type` 1) or a
                       market order (`type` 0; `tag` "Liquidated" when the algorithm
                       liquidated the position on a reversal or a veto)
  log.txt              OPTIONAL: the executor's `<TAG>_TRAIL|entry=..|from=..|to=..` stop
                       moves inside the trade's window and the `<TAG>_OCO_CANCEL|reason=`
                       line at the exit (the reason behind a market liquidation)

Pip distances use the instrument's pip (`algo_core.instrument.build_instrument`), the same
value the executor sized the plan with; nothing here is a per-pair constant.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from algo_core.instrument import build_instrument
from algo_core.repository.parquet import ParquetRepository

from algo_backtest.chain.audit import DecisionRow
from algo_backtest.statement import (
    TRADE_PLANS_FILE,
    RunArtifacts,
    direction_label,
    load_run_artifacts,
    parse_time,
)

DECISIONS_FILE = "decisions.parquet"
LOG_FILE = "log.txt"
# How the last order of a trade closed it (LEAN `OrderType`: 0 market, 1 limit, 2 stop-market).
EXIT_STOP = "stop-market"
EXIT_TARGET = "limit target"
EXIT_MARKET = "market"
EXIT_LIQUIDATION = "market liquidation"
_ORDER_TYPES: Mapping[int, str] = {0: EXIT_MARKET, 1: EXIT_TARGET, 2: EXIT_STOP}
_LIQUIDATED_TAG = "Liquidated"
# The executor's log lines (`engine/chain_algorithm.py`), prefixed by LEAN's algorithm time.
_LOG_TIME = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \w+"
_TRAIL_LINE = re.compile(_LOG_TIME + r"_TRAIL\|entry=([^|\s]+)\|from=([^|\s]+)\|to=([^|\s]+)")
_CANCEL_LINE = re.compile(_LOG_TIME + r"_OCO_CANCEL\|reason=(\w+)\|")
_LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_FLAT = "flat"
_P_HAT = "p_hat"
_META_LEARNER = "meta_learner"


@dataclass(frozen=True)
class FilterVerdict:
    """One filter's contribution at the entry bar, in chain order."""

    filter_name: str
    recommendation: str
    veto: bool
    reason: str


@dataclass(frozen=True)
class EntryVerdict:
    """The chain's outcome at the entry bar and the F7 thresholds it was judged against.

    `p_hat` is F7's recorded probability (`None` when no filter enriched one); the thetas
    and the regime gate come from `strategy-config.json` and are `None` when the run
    recorded no config.
    """

    timestamp: datetime
    final_decision: str
    vetoed_by: str | None
    p_hat: float | None
    theta_high: float | None
    theta_low: float | None
    regime_gate: bool | None
    filters: tuple[FilterVerdict, ...]


@dataclass(frozen=True)
class TargetLevel:
    """One take-profit order of the plan."""

    price: float
    close_fraction: float


@dataclass(frozen=True)
class TrailStep:
    """One planned trailing step: reaching `at_price` moves the stop to `to_price`."""

    at_price: float
    to_price: float
    at_level_ratio: float
    to_level_ratio: float


@dataclass(frozen=True)
class PlanSummary:
    """The orders the executor placed at the entry, from `trade-plans.json`."""

    lots: float
    quantity: float
    entry_price: float
    stop_loss: float
    stop_pips: float
    targets: tuple[TargetLevel, ...]
    trail_steps: tuple[TrailStep, ...]
    spread_pips: float


@dataclass(frozen=True)
class TrailMove:
    """A stop move the executor logged while the trade was open."""

    time: datetime
    from_price: float
    to_price: float


@dataclass(frozen=True)
class TradeExit:
    """How and when the trade closed.

    `kind` is one of the `EXIT_*` constants; `reason` is the executor's `_OCO_CANCEL`
    reason at the exit when it was not the plain `flat` reconciliation (a reversal or a
    veto), `None` otherwise. `log_recorded` says whether `log.txt` existed at all — an
    empty `trail_moves` means "none logged" only when it did.
    """

    time: datetime
    price: float
    order_id: int
    kind: str
    reason: str | None
    trail_moves: tuple[TrailMove, ...]
    log_recorded: bool

    @property
    def label(self) -> str:
        """`kind`, with the executor's reason in parentheses when one was logged."""
        return f"{self.kind} ({self.reason})" if self.reason else self.kind


@dataclass(frozen=True)
class DecisionTrail:
    """Everything the drill-down of one closed trade shows."""

    ticket: int
    entry_time: datetime
    direction: str
    verdict: EntryVerdict
    plan: PlanSummary
    exit: TradeExit
    profit: float

    @property
    def holding(self) -> timedelta:
        """Exit time minus entry time."""
        return self.exit.time - self.entry_time


# --- pure helpers ----------------------------------------------------------------------


def _field(doc: Mapping[str, Any], key: str, where: str) -> Any:
    """A required key of an artifact record, failing fast with the record named."""
    if key not in doc:
        raise ValueError(
            f"{where} lacks key {key!r}; the run's artifacts are incomplete — re-run the "
            "backtest and confirm the engine exited successfully"
        )
    return doc[key]


def format_duration(duration: timedelta) -> str:
    """`[<d>d ]<h>h <m>m`: whole minutes, days shown only when at least one elapsed."""
    minutes = int(duration.total_seconds() // 60)
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    return f"{days}d {hours}h {mins}m" if days else f"{hours}h {mins}m"


def entry_row(rows: Sequence[DecisionRow], ticket: int, entry_time: datetime) -> DecisionRow:
    """The chain row at the entry bar: the first carrying the trade's id, else the row
    timestamped at the entry.

    Raises:
        ValueError: neither exists — the audit trail and the ledger disagree.
    """
    trade_id = str(ticket)
    for row in rows:
        if row.trade_id == trade_id:
            return row
    for row in rows:
        if row.timestamp == entry_time:
            return row
    raise ValueError(
        f"{DECISIONS_FILE} has no row for trade {ticket} entered at {entry_time.isoformat()}: "
        f"no row carries trade_id {trade_id!r} and none is timestamped at the entry; the audit "
        "trail and trades.json disagree — re-run the backtest"
    )


def p_hat_of(row: DecisionRow) -> float | None:
    """F7's recorded probability: the first non-null `enrichment.p_hat` in chain order."""
    for result in row.filter_results:
        value = (result.enrichment or {}).get(_P_HAT)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def thresholds(config: Mapping[str, Any] | None) -> tuple[float | None, float | None, bool | None]:
    """`(theta_high, theta_low, regime_gate)` from the resolved config's `meta_learner`
    section; `None`s when the run recorded no config or no such section."""
    section = (config or {}).get(_META_LEARNER)
    if not isinstance(section, Mapping):
        return None, None, None
    high, low, gate = (section.get(k) for k in ("theta_high", "theta_low", "regime_gate"))
    return (
        None if high is None else float(high),
        None if low is None else float(low),
        None if gate is None else bool(gate),
    )


def entry_verdict(row: DecisionRow, config: Mapping[str, Any] | None) -> EntryVerdict:
    """The chain's outcome at the entry bar with F7's thresholds alongside."""
    high, low, gate = thresholds(config)
    return EntryVerdict(
        timestamp=row.timestamp, final_decision=row.final_decision, vetoed_by=row.vetoed_by,
        p_hat=p_hat_of(row), theta_high=high, theta_low=low, regime_gate=gate,
        filters=tuple(
            FilterVerdict(r.filter_name, r.recommendation, r.veto, r.reason)
            for r in row.filter_results
        ),
    )


def plan_summary(plan: Mapping[str, Any], pip_size: float) -> PlanSummary:
    """A `trade-plans.json` record typed, with the stop distance in pips."""
    where = f"{TRADE_PLANS_FILE} entry_order_id {plan.get('entry_order_id')!r}"
    entry = float(_field(plan, "entry_price", where))
    stop = float(_field(plan, "stop_loss", where))
    return PlanSummary(
        lots=float(_field(plan, "lots", where)),
        quantity=float(_field(plan, "quantity", where)),
        entry_price=entry,
        stop_loss=stop,
        stop_pips=abs(entry - stop) / pip_size,
        targets=tuple(
            TargetLevel(float(_field(t, "price", where)), float(_field(t, "close_fraction", where)))
            for t in _field(plan, "take_profits", where)
        ),
        trail_steps=tuple(
            TrailStep(
                at_price=float(_field(s, "at_price", where)),
                to_price=float(_field(s, "to_price", where)),
                at_level_ratio=float(_field(s, "at_level_ratio", where)),
                to_level_ratio=float(_field(s, "to_level_ratio", where)),
            )
            for s in _field(plan, "trail_stops", where)
        ),
        spread_pips=float(_field(plan, "spread_pips", where)),
    )


def classify_exit(
    order: Mapping[str, Any], order_id: int, reason: str | None
) -> tuple[str, str | None]:
    """`(kind, reason)` of the order that closed a trade, from LEAN's order record.

    A market order tagged "Liquidated" is the algorithm closing the position itself
    (`EXIT_LIQUIDATION`); the executor's logged cancel reason (`reversal`, `veto`) is kept
    for that case only — a stop or target fill's `flat` reconciliation says nothing new.

    Raises:
        ValueError: the order's `type` is not market, limit or stop-market.
    """
    order_type = _field(order, "type", f"main.json orders[{order_id}]")
    if order_type not in _ORDER_TYPES:
        raise ValueError(
            f"main.json orders[{order_id}] has type {order_type!r}, not a market (0), limit (1) "
            "or stop-market (2) order; the exit of this trade cannot be classified"
        )
    kind = _ORDER_TYPES[int(order_type)]
    if kind != EXIT_MARKET:
        return kind, None
    if _LIQUIDATED_TAG in str(order.get("tag", "")):
        kind = EXIT_LIQUIDATION
    return kind, None if reason in (None, _FLAT) else reason


@dataclass(frozen=True)
class ExecutorLog:
    """The executor's stop moves and cancel reasons parsed from `log.txt`."""

    recorded: bool
    moves: tuple[tuple[datetime, float, float, float], ...]  # (time, entry, from, to)
    cancel_reasons: Mapping[datetime, str]


def _log_time(text: str) -> datetime:
    """LEAN's algorithm-time prefix (`YYYY-MM-DD HH:MM:SS`, the algorithm runs in UTC)."""
    return datetime.strptime(text, _LOG_TIME_FORMAT).replace(tzinfo=UTC)


def parse_executor_log(lines: Iterable[str] | None) -> ExecutorLog:
    """Every `_TRAIL` move and `_OCO_CANCEL` reason in the log; `None` means no log file."""
    if lines is None:
        return ExecutorLog(recorded=False, moves=(), cancel_reasons={})
    moves: list[tuple[datetime, float, float, float]] = []
    reasons: dict[datetime, str] = {}
    for line in lines:
        if trail := _TRAIL_LINE.search(line):
            when, entry, from_price, to_price = trail.groups()
            moves.append((_log_time(when), float(entry), float(from_price), float(to_price)))
        elif cancel := _CANCEL_LINE.search(line):
            reasons[_log_time(cancel.group(1))] = cancel.group(2)
    return ExecutorLog(recorded=True, moves=tuple(moves), cancel_reasons=reasons)


def trail_moves(
    log: ExecutorLog, entry_price: float, entry_time: datetime, exit_time: datetime
) -> tuple[TrailMove, ...]:
    """The logged stop moves inside the trade's window whose `entry=` is the trade's entry."""
    return tuple(
        TrailMove(when, from_price, to_price)
        for when, entry, from_price, to_price in log.moves
        if entry_time <= when <= exit_time and entry == entry_price
    )


# --- building --------------------------------------------------------------------------


def _pip_size(symbol: str) -> float:
    """The instrument's pip, the unit the executor sized the plan in."""
    return float(build_instrument(symbol).unit_size)


def _plan_for(
    plans: Mapping[int, Mapping[str, Any]], ticket: int, entry_time: datetime
) -> Mapping[str, Any]:
    """The plan whose `entry_order_id` is the trade's ticket, or fail fast naming the trade."""
    if ticket not in plans:
        raise ValueError(
            f"{TRADE_PLANS_FILE} has no plan with entry_order_id {ticket} for the closed trade "
            f"entered at {entry_time.isoformat()}; the executor records one per planned entry, "
            "so the run's artifacts are inconsistent — re-run the backtest"
        )
    return plans[ticket]


def _last_order(orders: Mapping[str, Any], order_ids: Sequence[Any], ticket: int) -> tuple[
    int, Mapping[str, Any]
]:
    """The trade's last order (LEAN lists a flat-to-flat trade's orders in fill order)."""
    last = int(order_ids[-1])
    order = orders.get(str(last))
    if not isinstance(order, Mapping):
        raise ValueError(
            f"main.json orders has no order {last}, the last order of closed trade {ticket} in "
            "trades.json; the run directory is inconsistent — re-run the backtest"
        )
    return last, order


def _trade_exit(
    trade: Mapping[str, Any], ticket: int, orders: Mapping[str, Any], log: ExecutorLog,
    plan: PlanSummary, entry_time: datetime,
) -> TradeExit:
    """The exit of one ledger trade: its last order classified, plus the logged stop moves."""
    exit_time = parse_time(str(_field(trade, "exitTime", "trades.json")), "exitTime", "trades.json")
    last_id, order = _last_order(orders, _field(trade, "orderIds", "trades.json"), ticket)
    kind, reason = classify_exit(order, last_id, log.cancel_reasons.get(exit_time))
    return TradeExit(
        time=exit_time, price=float(_field(trade, "exitPrice", "trades.json")), order_id=last_id,
        kind=kind, reason=reason,
        trail_moves=trail_moves(log, plan.entry_price, entry_time, exit_time),
        log_recorded=log.recorded,
    )


def _trail(
    trade: Mapping[str, Any], artifacts: RunArtifacts, plans: Mapping[int, Mapping[str, Any]],
    decisions: Sequence[DecisionRow], log: ExecutorLog, pip_size: float,
) -> DecisionTrail:
    """One closed trade -> its trail (raises on a missing plan, row or order)."""
    order_ids = _field(trade, "orderIds", "trades.json")
    if not order_ids:
        raise ValueError("trades.json has a closed trade with empty orderIds; cannot ticket it")
    ticket = int(order_ids[0])
    entry_time = parse_time(
        str(_field(trade, "entryTime", "trades.json")), "entryTime", "trades.json"
    )
    raw_plan = _plan_for(plans, ticket, entry_time)
    direction = str(_field(raw_plan, "direction", f"{TRADE_PLANS_FILE} entry_order_id {ticket}"))
    ledger_side = direction_label(_field(trade, "direction", "trades.json"))
    if direction != ledger_side:
        raise ValueError(
            f"{TRADE_PLANS_FILE} plan {ticket} is a {direction} but trades.json records the trade "
            f"as {ledger_side}; the artifacts contradict each other — re-run the backtest"
        )
    plan = plan_summary(raw_plan, pip_size)
    orders = artifacts.result.get("orders") or {}
    return DecisionTrail(
        ticket=ticket, entry_time=entry_time, direction=direction,
        verdict=entry_verdict(entry_row(decisions, ticket, entry_time), artifacts.strategy_config),
        plan=plan, exit=_trade_exit(trade, ticket, orders, log, plan, entry_time),
        profit=float(_field(trade, "profitLoss", "trades.json")),
    )


def assemble_trails(
    artifacts: RunArtifacts, decisions: Sequence[DecisionRow], log_lines: Iterable[str] | None
) -> list[DecisionTrail]:
    """Every closed trade's trail, in ledger order (pure: no file access).

    Raises:
        ValueError: `trade-plans.json` is absent or lacks a trade's plan, `decisions.parquet`
            has no row for a trade, an order is missing from LEAN's `orders`, or the plan and
            the ledger disagree about a trade's direction.
    """
    if artifacts.trade_plans is None:
        raise ValueError(
            f"{TRADE_PLANS_FILE} is missing from {artifacts.run_dir}; the decision trail needs the "
            "plan the executor placed at every entry (a run predating story 12 has none)"
        )
    plans = {int(_field(p, "entry_order_id", TRADE_PLANS_FILE)): p for p in artifacts.trade_plans}
    log = parse_executor_log(log_lines)
    pip_size = _pip_size(str(_field(artifacts.run, "symbol", "run.json")))
    return [_trail(t, artifacts, plans, decisions, log, pip_size) for t in artifacts.trades]


def read_decisions(run_dir: Path) -> list[DecisionRow]:
    """Every `decisions.parquet` row of the run, validated into `DecisionRow`.

    Raises:
        FileNotFoundError: the run has no `decisions.parquet` (not a chain strategy, or the
            algorithm never reached `on_end_of_algorithm`).
    """
    path = run_dir / DECISIONS_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"{DECISIONS_FILE} is missing from {run_dir}; only a chain strategy records the "
            "audit trail the decision drill-down is built from"
        )
    return ParquetRepository(DecisionRow, path).read_all()


def has_trail_artifacts(run_dir: Path) -> bool:
    """Whether the run recorded both `decisions.parquet` and `trade-plans.json`."""
    return (run_dir / DECISIONS_FILE).is_file() and (run_dir / TRADE_PLANS_FILE).is_file()


def build_decision_trails(run_dir: Path) -> list[DecisionTrail]:
    """One `DecisionTrail` per closed trade of the run in `run_dir`.

    Reads the statement's artifacts, `decisions.parquet` and, when present, `log.txt`.
    Raises what `load_run_artifacts`, `read_decisions` and `assemble_trails` raise.
    """
    artifacts = load_run_artifacts(run_dir)
    log_path = run_dir / LOG_FILE
    lines = log_path.read_text().splitlines() if log_path.is_file() else None
    return assemble_trails(artifacts, read_decisions(run_dir), lines)
