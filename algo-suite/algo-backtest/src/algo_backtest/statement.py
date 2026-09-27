"""End-of-run broker statement (`statement.md`) and equity chart (`equity.png`).

Every simulation ends with a retail-FX-style account statement, modelled on a broker's
daily confirmation (closed transactions, open trades, working orders, A/C summary),
plus an equity/drawdown chart. Both are built **purely from the run directory's
artifacts** — no LEAN import, no engine re-run — so `algo-backtest statement --run` can
regenerate them for any finished run on disk:

  run.json                  strategy, symbol, window, params, broker_adapter
  trades.json               LEAN's closed-trade ledger (`totalPerformance.closedTrades`)
  <algo>.json               LEAN's result JSON (`statistics`, `runtimeStatistics`,
                            `charts['Strategy Equity']`, `charts['Portfolio Margin']`,
                            `orders`, `totalPerformance`)
  <algo>-order-events.json  every order event (LEAN omits the file when no order was
                            placed; it is required as soon as trades.json is non-empty)
  strategy-config.json      resolved strategy config (chain strategies only)
  strategy-provenance.json  dotted parameter path -> the config.yaml that set it
  trade-plans.json          OPTIONAL, written by the plan-driven executor (story 12 item
                            D): a list of {"entry_order_id": int, "entry_time": ISO,
                            "direction": "buy"|"sell", "lots": float, "quantity": float,
                            "stop_loss": float, "take_profits": [{"price": float,
                            "close_fraction": float}], "trail_stops": [...]}, joined to
                            trades.json by `orderIds[0]`. Absent -> the S/L and T/P
                            columns show "—" and the statement says so explicitly.

Direction contract (verified against a real run's fills, 2026-09-27): trades.json
`direction` is LEAN's `TradeDirection` — 0 = Long (entry fill `direction: "buy"`,
positive `fillQuantity`), 1 = Short (entry fill `direction: "sell"`, negative
`fillQuantity`). The builder cross-checks each trade's label against its entry fill and
fails fast on a contradiction rather than printing a wrong side.

Nothing here is fabricated: every money figure comes from the artifacts; the only
constants are presentation (file names, chart size/dpi, decimal places).
"""

from __future__ import annotations

import json
import statistics as pystats
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
from algo_core.atomicio import write_text_atomic  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from algo_backtest.results import find_result_json  # noqa: E402

STATEMENT_FILE = "statement.md"
CHART_FILE = "equity.png"
TRADE_PLANS_FILE = "trade-plans.json"
# Presentation only — no money math depends on these.
CHART_DPI = 150
CHART_SIZE = (10.0, 6.0)
PRICE_DECIMALS = 5
ABSENT = "—"
NO_TRANSACTIONS = "No transactions"
NO_PLANS_NOTE = "no trade plan recorded for this run"
NO_CONFIG_NOTE = "no strategy-config.json recorded for this run"
SWAP_NOTE = "Swap is 0.00 on every line: the LEAN forex model applies no overnight rollover."
_DIRECTION_LABELS: Mapping[int, str] = {0: "buy", 1: "sell"}
# LEAN OrderStatus values after which an order can never fill; anything else still on
# the book at the end of the run is a working order.
_TERMINAL_ORDER_STATUSES = frozenset({"filled", "canceled", "invalid"})
_FILL_STATUSES = frozenset({"filled", "partiallyFilled"})
# LEAN `statistics` keys quoted verbatim in the Performance section (label, key).
_PERFORMANCE_KEYS: Sequence[tuple[str, str]] = (
    ("Net profit", "Net Profit"),
    ("Max drawdown", "Drawdown"),
    ("Sharpe ratio", "Sharpe Ratio"),
    ("Win rate", "Win Rate"),
    ("Average win", "Average Win"),
    ("Average loss", "Average Loss"),
    ("Total orders", "Total Orders"),
)


@dataclass(frozen=True)
class RunArtifacts:
    """The parsed artifacts of one run directory (optional ones are `None` when absent)."""

    run_dir: Path
    run: dict[str, Any]
    trades: list[dict[str, Any]]
    result: dict[str, Any]
    result_name: str
    order_events: list[dict[str, Any]]
    order_events_name: str
    strategy_config: dict[str, Any] | None
    provenance: dict[str, str] | None
    trade_plans: list[dict[str, Any]] | None


@dataclass(frozen=True)
class ClosedTransaction:
    """One row of the Closed Transactions table (commission is negative when a cost)."""

    ticket: int
    open_time: str
    type: str
    lots: float | None
    item: str
    open_price: float
    stop_loss: float | None
    take_profits: tuple[float, ...] | None
    close_time: str
    close_price: float
    commission: float
    swap: float
    profit: float


@dataclass(frozen=True)
class OpenPosition:
    """A position still open when the run ended."""

    item: str
    type: str
    quantity: float
    lots: float | None
    holdings: float
    floating_pl: float


@dataclass(frozen=True)
class WorkingOrder:
    """An order still on the book when the run ended (never filled, never cancelled)."""

    ticket: int
    time: str
    type: str
    quantity: float
    item: str
    status: str
    price: float | None


@dataclass(frozen=True)
class AccountSummary:
    """The A/C Summary block: balance = deposit + closed P/L; equity = balance + floating."""

    previous_balance: float
    closed_pl: float
    deposit_withdrawal: float
    balance: float
    floating_pl: float
    equity: float
    engine_equity: float
    margin_requirement: float | None
    available_margin: float | None


@dataclass(frozen=True)
class Parameter:
    """One resolved strategy parameter and the source that set it."""

    key: str
    value: str
    source: str


@dataclass(frozen=True)
class Statement:
    """Everything the Markdown statement and the console summary render."""

    strategy: str
    symbol: str
    start: str
    end: str
    run_id: str
    broker_adapter: str
    starting_deposit: float
    transactions: tuple[ClosedTransaction, ...]
    open_positions: tuple[OpenPosition, ...]
    working_orders: tuple[WorkingOrder, ...]
    summary: AccountSummary
    performance: tuple[tuple[str, str], ...]
    parameters: tuple[Parameter, ...]
    plans_recorded: bool
    config_recorded: bool
    equity: tuple[tuple[datetime, float], ...]


@dataclass(frozen=True)
class StatementPaths:
    """Where the statement and its chart were written."""

    statement: Path
    chart: Path


# --- loading ---------------------------------------------------------------------------


def _read_json(path: Path, kind: type) -> Any:
    """Parse one artifact, failing fast with the file name on absence or malformed JSON."""
    if not path.is_file():
        raise FileNotFoundError(
            f"{path.name} is missing from {path.parent}; the run has no {path.name} artifact "
            "— finish the run (`algo-backtest run ...`) or point --run at a completed "
            "results directory"
        )
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name} in {path.parent} is not valid JSON ({exc}); re-run the backtest "
            "to regenerate it"
        ) from exc
    if not isinstance(doc, kind):
        raise ValueError(
            f"{path.name} in {path.parent} must be a JSON {kind.__name__}, got "
            f"{type(doc).__name__}; re-run the backtest to regenerate it"
        )
    return doc


def _optional_json(path: Path, kind: type) -> Any | None:
    """Parse an optional artifact: `None` when absent, fail fast when present but broken."""
    return _read_json(path, kind) if path.is_file() else None


def _field(doc: Mapping[str, Any], key: str, file: str) -> Any:
    """A required key of an artifact, failing fast with the file and key names."""
    if key not in doc:
        raise ValueError(
            f"{file} lacks key {key!r}; the run's artifacts are incomplete — re-run the "
            "backtest and confirm the engine exited successfully"
        )
    return doc[key]


def _locate_result(run_dir: Path) -> Path:
    """LEAN's full result JSON (main.json), naming it when it is missing."""
    try:
        return find_result_json(run_dir)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"main.json (LEAN's result JSON) is missing from {run_dir}: {exc}"
        ) from exc


def _order_events(result_path: Path, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The order-events sibling; LEAN writes none for a run without orders, so its
    absence is accepted only when the trade ledger is empty (otherwise fail fast)."""
    path = result_path.with_name(f"{result_path.stem}-order-events.json")
    if path.is_file():
        events: list[dict[str, Any]] = _read_json(path, list)
        return events
    if trades:
        raise FileNotFoundError(
            f"{path.name} is missing from {path.parent} although trades.json lists "
            f"{len(trades)} closed trade(s); the run directory is incomplete — re-run the "
            "backtest"
        )
    return []


def load_run_artifacts(run_dir: Path) -> RunArtifacts:
    """Read every artifact the statement needs from `run_dir`.

    Raises:
        FileNotFoundError: a required artifact (run.json, trades.json, LEAN's result JSON,
            or the order-events file for a run with trades) is absent.
        ValueError: an artifact is not valid JSON or has the wrong top-level shape.
    """
    if not run_dir.is_dir():
        raise FileNotFoundError(
            f"run directory {run_dir} does not exist; pass --run <results-dir> of a "
            "finished `algo-backtest run`"
        )
    run: dict[str, Any] = _read_json(run_dir / "run.json", dict)
    trades: list[dict[str, Any]] = _read_json(run_dir / "trades.json", list)
    result_path = _locate_result(run_dir)
    result: dict[str, Any] = _read_json(result_path, dict)
    return RunArtifacts(
        run_dir=run_dir, run=run, trades=trades, result=result, result_name=result_path.name,
        order_events=_order_events(result_path, trades),
        order_events_name=f"{result_path.stem}-order-events.json",
        strategy_config=_optional_json(run_dir / "strategy-config.json", dict),
        provenance=_optional_json(run_dir / "strategy-provenance.json", dict),
        trade_plans=_optional_json(run_dir / TRADE_PLANS_FILE, list),
    )


# --- pure helpers ----------------------------------------------------------------------


def direction_label(direction: Any, file: str = "trades.json") -> str:
    """Map LEAN's TradeDirection (0 = Long -> "buy", 1 = Short -> "sell"); fail on else."""
    if isinstance(direction, bool) or direction not in _DIRECTION_LABELS:
        raise ValueError(
            f"{file} has an unknown trade direction {direction!r} (expected 0 = long/buy or "
            "1 = short/sell, LEAN's TradeDirection); the ledger schema may have changed"
        )
    return _DIRECTION_LABELS[direction]


def lots_from_quantity(quantity: float, lot_notional_units: float | None) -> float | None:
    """Units -> lots (quantity / lot size); `None` when the strategy records no lot size."""
    if lot_notional_units is None:
        return None
    if lot_notional_units <= 0:
        raise ValueError(
            f"strategy-config.json capital_mgmt.lot_notional_units must be > 0, got "
            f"{lot_notional_units!r}"
        )
    return abs(quantity) / lot_notional_units


def parse_money(text: Any, key: str, file: str) -> float:
    """Parse LEAN's display money ('$9,995.38', '-$1,094.81', '$-12.50') into a float."""
    try:
        return float(str(text).replace("$", "").replace(",", "").strip())
    except ValueError as exc:
        raise ValueError(
            f"{file} key {key!r} is not a money amount ({text!r}); the engine's statistics "
            "format may have changed"
        ) from exc


def duration_minutes(duration: str) -> float:
    """LEAN TimeSpan text ('[d.]hh:mm:ss[.fraction]') -> minutes."""
    parts = duration.split(":")
    try:
        if len(parts) != 3:
            raise ValueError("expected hh:mm:ss")
        days_text, _, hours = parts[0].rpartition(".")
        days = int(days_text) if days_text else 0
        return days * 1440 + int(hours) * 60 + int(parts[1]) + float(parts[2]) / 60
    except ValueError as exc:
        raise ValueError(
            f"trades.json duration {duration!r} is not a LEAN TimeSpan ('[d.]hh:mm:ss')"
        ) from exc


def equity_series(main_json: Mapping[str, Any], file: str = "main.json") -> list[
    tuple[datetime, float]
]:
    """(UTC time, close) per equity candle from `charts['Strategy Equity'].series.Equity`.

    Rows are `[unix_seconds, open, high, low, close]` (a two-element `[time, value]` row
    is accepted too — the last element is the close either way).
    """
    try:
        rows = main_json["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"{file} lacks charts['Strategy Equity'].series.Equity.values ({exc!r}); the "
            "backtest may not have finished — re-run it"
        ) from exc
    return [(datetime.fromtimestamp(row[0], UTC), float(row[-1])) for row in rows]


def drawdowns(equity: Sequence[float]) -> list[float]:
    """Percent below the running peak for each equity point (0.0 at every new high)."""
    out: list[float] = []
    peak = float("-inf")
    for value in equity:
        peak = max(peak, value)
        if peak <= 0:
            raise ValueError(f"equity must be positive to define a drawdown, got {value}")
        out.append((peak - value) / peak * 100.0)
    return out


def _leaf_paths(document: Mapping[str, Any], prefix: str = "") -> Iterator[tuple[str, Any]]:
    """(dotted path, value) for every leaf of a nested mapping; a list is one leaf."""
    for key, value in document.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            yield from _leaf_paths(value, f"{path}.")
        else:
            yield path, value


# --- building --------------------------------------------------------------------------


def _fills_by_order(events: Sequence[Mapping[str, Any]], file: str) -> dict[int, dict[str, Any]]:
    """First fill event per orderId (the side and sign a trade's direction is checked on)."""
    fills: dict[int, dict[str, Any]] = {}
    for event in events:
        if event.get("status") in _FILL_STATUSES:
            fills.setdefault(int(_field(event, "orderId", file)), dict(event))
    return fills


def _lot_notional_units(config: Mapping[str, Any] | None) -> float | None:
    """`capital_mgmt.lot_notional_units` from the resolved config, `None` when unrecorded."""
    if config is None:
        return None
    capital = config.get("capital_mgmt")
    if not isinstance(capital, Mapping) or "lot_notional_units" not in capital:
        return None
    return float(capital["lot_notional_units"])


def _plans_by_entry(plans: Sequence[Mapping[str, Any]] | None) -> dict[int, dict[str, Any]] | None:
    """trade-plans.json indexed by entry order id; `None` when the file is absent."""
    if plans is None:
        return None
    return {
        int(_field(plan, "entry_order_id", TRADE_PLANS_FILE)): dict(plan) for plan in plans
    }


def _plan_levels(plan: Mapping[str, Any] | None) -> tuple[float | None, tuple[float, ...] | None]:
    """(stop_loss, take-profit prices) of a plan; (None, None) when no plan was recorded."""
    if plan is None:
        return None, None
    targets = _field(plan, "take_profits", TRADE_PLANS_FILE)
    prices = tuple(float(_field(target, "price", TRADE_PLANS_FILE)) for target in targets)
    return float(_field(plan, "stop_loss", TRADE_PLANS_FILE)), prices


def _entry_side(trade: Mapping[str, Any], ticket: int, fills: Mapping[int, Mapping[str, Any]],
                file: str) -> str:
    """The trade's side label, cross-checked against its entry fill (fail on mismatch)."""
    label = direction_label(_field(trade, "direction", "trades.json"))
    if ticket not in fills:
        raise ValueError(
            f"{file} has no fill event for order {ticket}, the entry order of a closed "
            "trade in trades.json; the run directory is inconsistent — re-run the backtest"
        )
    fill = fills[ticket]
    if fill.get("direction") != label:
        raise ValueError(
            f"trades.json direction {trade['direction']!r} (= {label}) contradicts the entry "
            f"fill of order {ticket} in {file} ({fill.get('direction')!r}, fillQuantity "
            f"{fill.get('fillQuantity')!r}); the ledger direction encoding may have changed"
        )
    return label


def _closed_transaction(
    trade: Mapping[str, Any], symbol: str, lot_units: float | None,
    fills: Mapping[int, Mapping[str, Any]], plans: Mapping[int, Mapping[str, Any]] | None,
    events_file: str,
) -> ClosedTransaction:
    """One ledger trade -> one Closed Transactions row."""
    order_ids = _field(trade, "orderIds", "trades.json")
    if not order_ids:
        raise ValueError("trades.json has a closed trade with empty orderIds; cannot ticket it")
    ticket = int(order_ids[0])
    stop_loss, take_profits = _plan_levels(plans.get(ticket) if plans is not None else None)
    return ClosedTransaction(
        ticket=ticket,
        open_time=str(_field(trade, "entryTime", "trades.json")),
        type=_entry_side(trade, ticket, fills, events_file),
        lots=lots_from_quantity(float(_field(trade, "quantity", "trades.json")), lot_units),
        item=symbol,
        open_price=float(_field(trade, "entryPrice", "trades.json")),
        stop_loss=stop_loss,
        take_profits=take_profits,
        close_time=str(_field(trade, "exitTime", "trades.json")),
        close_price=float(_field(trade, "exitPrice", "trades.json")),
        commission=-float(_field(trade, "totalFees", "trades.json")),
        swap=0.0,
        profit=float(_field(trade, "profitLoss", "trades.json")),
    )


def _open_positions(
    events: Sequence[Mapping[str, Any]], runtime: Mapping[str, Any], symbol: str,
    lot_units: float | None, file: str,
) -> tuple[OpenPosition, ...]:
    """The net position left by every fill, reconciled with the engine's Holdings."""
    net = sum(
        float(event.get("fillQuantity", 0.0))
        for event in events if event.get("status") in _FILL_STATUSES
    )
    holdings = parse_money(_field(runtime, "Holdings", file), "Holdings", file)
    floating = parse_money(_field(runtime, "Unrealized", file), "Unrealized", file)
    if net == 0:
        if holdings != 0:
            raise ValueError(
                f"{file} runtimeStatistics Holdings is {holdings} but the order fills net "
                "to zero; the run's artifacts are inconsistent — re-run the backtest"
            )
        return ()
    return (
        OpenPosition(
            item=symbol, type="buy" if net > 0 else "sell", quantity=abs(net),
            lots=lots_from_quantity(net, lot_units), holdings=holdings, floating_pl=floating,
        ),
    )


def _order_price(orders: Mapping[str, Any], ticket: int) -> float | None:
    """The stop or limit price LEAN recorded for an order, `None` for a market order."""
    order = orders.get(str(ticket))
    if not isinstance(order, Mapping):
        return None
    for key in ("stopPrice", "limitPrice"):
        if order.get(key) is not None:
            return float(order[key])
    return None


def _working_orders(
    events: Sequence[Mapping[str, Any]], orders: Mapping[str, Any], file: str
) -> tuple[WorkingOrder, ...]:
    """Orders whose last event is not terminal — still pending when the run ended."""
    last: dict[int, Mapping[str, Any]] = {}
    for event in events:
        last[int(_field(event, "orderId", file))] = event
    working = []
    for ticket, event in sorted(last.items()):
        if event.get("status") in _TERMINAL_ORDER_STATUSES:
            continue
        working.append(
            WorkingOrder(
                ticket=ticket,
                time=datetime.fromtimestamp(float(_field(event, "time", file)), UTC).isoformat(),
                type=str(_field(event, "direction", file)),
                quantity=abs(float(_field(event, "quantity", file))),
                item=str(event.get("symbolValue", event.get("symbol", ""))),
                status=str(_field(event, "status", file)),
                price=_order_price(orders, ticket),
            )
        )
    return tuple(working)


def _last_fill_time(events: Sequence[Mapping[str, Any]]) -> float:
    """Unix time of the last fill event (0.0 when nothing ever filled)."""
    return max(
        (float(e.get("time", 0.0)) for e in events if e.get("status") in _FILL_STATUSES),
        default=0.0,
    )


def _margin_requirement(
    result: Mapping[str, Any], equity: float, positions: Sequence[OpenPosition],
    last_fill_time: float,
) -> float | None:
    """End-of-run margin in account currency, never guessed.

    A flat account needs no margin (0.0). With a position open, LEAN's `Portfolio Margin`
    chart (per-symbol margin used as % of portfolio value, sampled daily) is used only
    when its last sample is not older than the last fill — an older snapshot describes
    an earlier position — and is `None` (rendered "n/a") otherwise.
    """
    if not positions:
        return 0.0
    chart = (result.get("charts") or {}).get("Portfolio Margin")
    if not isinstance(chart, Mapping):
        return None
    samples = [s["values"][-1] for s in (chart.get("series") or {}).values() if s.get("values")]
    if not samples or min(float(row[0]) for row in samples) < last_fill_time:
        return None
    return equity * float(sum(row[-1] for row in samples)) / 100.0


def _account_summary(
    transactions: Sequence[ClosedTransaction], positions: Sequence[OpenPosition],
    result: Mapping[str, Any], file: str, last_fill_time: float,
) -> AccountSummary:
    """Balance = deposit + Σ(P/L + commission + swap); equity = balance + floating P/L."""
    portfolio = _field(_field(result, "totalPerformance", file), "portfolioStatistics", file)
    start = float(_field(portfolio, "startEquity", file))
    closed_pl = sum(t.profit + t.commission + t.swap for t in transactions)
    floating = sum(p.floating_pl for p in positions)
    balance = start + closed_pl
    equity = balance + floating
    runtime = _field(result, "runtimeStatistics", file)
    margin = _margin_requirement(result, equity, positions, last_fill_time)
    return AccountSummary(
        previous_balance=start, closed_pl=closed_pl, deposit_withdrawal=0.0, balance=balance,
        floating_pl=floating, equity=equity,
        engine_equity=parse_money(_field(runtime, "Equity", file), "Equity", file),
        margin_requirement=margin,
        available_margin=None if margin is None else equity - margin,
    )


def _performance(
    result: Mapping[str, Any], trades: Sequence[Mapping[str, Any]], file: str
) -> tuple[tuple[str, str], ...]:
    """Headline figures quoted from LEAN's `statistics`, plus trade count and median hold."""
    stats = _field(result, "statistics", file)
    rows = [
        (label, str(_field(stats, key, f"{file} statistics"))) for label, key in _PERFORMANCE_KEYS
    ]
    trade_stats = _field(_field(result, "totalPerformance", file), "tradeStatistics", file)
    rows.append(("Trades", str(_field(trade_stats, "totalNumberOfTrades", file))))
    minutes = [duration_minutes(str(_field(t, "duration", "trades.json"))) for t in trades]
    median = f"{pystats.median(minutes):.1f}" if minutes else ABSENT
    rows.append(("Median holding (minutes)", median))
    return tuple(rows)


def _parameters(artifacts: RunArtifacts) -> tuple[Parameter, ...]:
    """Every resolved strategy parameter with its source, then the run's --param values."""
    rows: list[Parameter] = []
    if artifacts.strategy_config is not None:
        provenance = artifacts.provenance or {}
        for path, value in sorted(_leaf_paths(artifacts.strategy_config)):
            rows.append(Parameter(path, json.dumps(value), provenance.get(path, "unknown")))
    params = _field(artifacts.run, "params", "run.json")
    rows.extend(Parameter(key, str(value), "--param") for key, value in sorted(params.items()))
    return tuple(rows)


def build_statement(artifacts: RunArtifacts) -> Statement:
    """Assemble the statement from parsed artifacts (pure; raises on inconsistency).

    Raises:
        ValueError: a required key is missing, a direction contradicts its fill, or the
            fills and the engine's Holdings disagree about the end-of-run position.
    """
    run, result, file = artifacts.run, artifacts.result, artifacts.result_name
    symbol = str(_field(run, "symbol", "run.json"))
    lot_units = _lot_notional_units(artifacts.strategy_config)
    fills = _fills_by_order(artifacts.order_events, artifacts.order_events_name)
    plans = _plans_by_entry(artifacts.trade_plans)
    transactions = tuple(
        _closed_transaction(t, symbol, lot_units, fills, plans, artifacts.order_events_name)
        for t in artifacts.trades
    )
    positions = _open_positions(
        artifacts.order_events, _field(result, "runtimeStatistics", file), symbol, lot_units, file
    )
    summary = _account_summary(
        transactions, positions, result, file, _last_fill_time(artifacts.order_events)
    )
    return Statement(
        strategy=str(_field(run, "strategy", "run.json")), symbol=symbol,
        start=str(_field(run, "start", "run.json")), end=str(_field(run, "end", "run.json")),
        run_id=artifacts.run_dir.name,
        broker_adapter=str(run.get("broker_adapter", "not recorded in run.json")),
        starting_deposit=summary.previous_balance,
        transactions=transactions, open_positions=positions,
        working_orders=_working_orders(artifacts.order_events, result.get("orders") or {}, file),
        summary=summary, performance=_performance(result, artifacts.trades, file),
        parameters=_parameters(artifacts), plans_recorded=plans is not None,
        config_recorded=artifacts.strategy_config is not None,
        equity=tuple(equity_series(result, file)),
    )


# --- rendering -------------------------------------------------------------------------


def money(value: float) -> str:
    """Two decimals with thousands separators; never '-0.00'."""
    return f"{round(value, 2) + 0.0:,.2f}"


def _price(value: float | None) -> str:
    """A price at FX precision, or the explicit absence marker."""
    return ABSENT if value is None else f"{value:.{PRICE_DECIMALS}f}"


def _lots(value: float | None) -> str:
    """Lots to two decimals, or the absence marker when no lot size is recorded."""
    return ABSENT if value is None else f"{value:.2f}"


def _optional_money(value: float | None) -> str:
    """Money, or 'n/a' when the artifacts carry no figure."""
    return "n/a" if value is None else money(value)


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """A GitHub-flavoured Markdown table."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _transaction_row(t: ClosedTransaction) -> list[str]:
    """Cells of one Closed Transactions row."""
    take_profit = (
        ABSENT if t.take_profits is None else " / ".join(_price(p) for p in t.take_profits)
    )
    return [
        str(t.ticket), t.open_time, t.type, _lots(t.lots), t.item, _price(t.open_price),
        _price(t.stop_loss), take_profit, t.close_time, _price(t.close_price),
        money(t.commission), money(t.swap), money(t.profit),
    ]


def _closed_section(statement: Statement) -> list[str]:
    """The Closed Transactions table with its totals row and footnotes."""
    headers = [
        "Ticket", "Open Time", "Type", "Lots", "Item", "Price", "S/L", "T/P", "Close Time",
        "Price", "Commission", "Swap", "Trade P/L",
    ]
    rows = [_transaction_row(t) for t in statement.transactions]
    if not rows:
        rows = [[NO_TRANSACTIONS] + [""] * (len(headers) - 1)]
    totals = statement.summary
    rows.append(
        ["**Total**", "", "", "", "", "", "", "", "", "",
         money(sum(t.commission for t in statement.transactions)),
         money(sum(t.swap for t in statement.transactions)),
         money(sum(t.profit for t in statement.transactions))]
    )
    notes = [SWAP_NOTE]
    if not statement.plans_recorded:
        notes.append(f"S/L and T/P are {ABSENT}: {NO_PLANS_NOTE} ({TRADE_PLANS_FILE} absent).")
    lines = ["## Closed Transactions", "", *_table(headers, rows), ""]
    lines.extend(f"_{note}_" for note in notes)
    lines.append(f"Closed trade P/L after commission and swap: {money(totals.closed_pl)}")
    return lines


def _open_section(statement: Statement) -> list[str]:
    """Open Trades at the end of the run."""
    lines = ["## Open Trades", ""]
    if not statement.open_positions:
        return [*lines, NO_TRANSACTIONS]
    rows = [
        [
            p.item, p.type, f"{p.quantity:,.0f}", _lots(p.lots), money(p.holdings),
            money(p.floating_pl),
        ]
        for p in statement.open_positions
    ]
    return [*lines, *_table(["Item", "Type", "Quantity", "Lots", "Holdings", "Floating P/L"], rows)]


def _working_section(statement: Statement) -> list[str]:
    """Working Orders (pending stop/limit orders) at the end of the run."""
    lines = ["## Working Orders", ""]
    if not statement.working_orders:
        return [*lines, NO_TRANSACTIONS]
    rows = [
        [str(o.ticket), o.time, o.type, f"{o.quantity:,.0f}", o.item, o.status, _price(o.price)]
        for o in statement.working_orders
    ]
    headers = ["Ticket", "Time", "Type", "Quantity", "Item", "Status", "Price"]
    return [*lines, *_table(headers, rows)]


def summary_lines(statement: Statement) -> list[str]:
    """The A/C Summary as `label: amount` lines (also printed on the console)."""
    s = statement.summary
    return [
        f"Previous Ledger Balance: {money(s.previous_balance)}",
        f"Closed Trade P/L: {money(s.closed_pl)}",
        f"Deposit/Withdrawal: {money(s.deposit_withdrawal)}",
        f"Balance: {money(s.balance)}",
        f"Floating P/L: {money(s.floating_pl)}",
        f"Equity: {money(s.equity)}",
        f"Equity (engine-reported): {money(s.engine_equity)}",
        f"Margin Requirement: {_optional_money(s.margin_requirement)}",
        f"Available Margin: {_optional_money(s.available_margin)}",
    ]


def _summary_section(statement: Statement) -> list[str]:
    """The A/C Summary block as a two-column table."""
    rows = [line.split(": ", 1) for line in summary_lines(statement)]
    return ["## A/C Summary", "", *_table(["", "Amount"], rows)]


def _performance_section(statement: Statement) -> list[str]:
    """Headline performance figures."""
    rows = [[label, value] for label, value in statement.performance]
    return ["## Performance", "", *_table(["Metric", "Value"], rows)]


def _parameters_section(statement: Statement) -> list[str]:
    """Every strategy parameter with its provenance (or the explicit absence note)."""
    lines = ["## Parameters", ""]
    if not statement.config_recorded:
        lines.append(
            f"_{NO_CONFIG_NOTE} (code-registered strategy, or a run predating the artifact); "
            "run parameters only._"
        )
        lines.append("")
    rows = [[p.key, f"`{p.value}`", p.source] for p in statement.parameters]
    return [*lines, *_table(["Parameter", "Value", "Source"], rows)]


def render_markdown(statement: Statement) -> str:
    """The whole statement as GitHub-flavoured Markdown."""
    header = _table(
        ["", ""],
        [
            ["Account", statement.strategy], ["Item", statement.symbol],
            ["Window", f"{statement.start} .. {statement.end}"], ["Run id", statement.run_id],
            ["Broker adapter", statement.broker_adapter],
            ["Starting deposit", money(statement.starting_deposit)],
            ["Generated", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")],
        ],
    )
    sections = [
        [f"# Account Statement — {statement.strategy} / {statement.symbol}", "", *header],
        _closed_section(statement), _open_section(statement), _working_section(statement),
        _summary_section(statement), _performance_section(statement),
        _parameters_section(statement),
        [f"![Equity and drawdown]({CHART_FILE})"],
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"


def render_equity_chart(statement: Statement, out: Path) -> Path:
    """Equity close (top, with the starting deposit as reference) and drawdown % (bottom)."""
    times = [t for t, _ in statement.equity]
    values = [v for _, v in statement.equity]
    fig, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=CHART_SIZE, height_ratios=[3, 1])
    top.plot(times, values, color="#1f77b4", linewidth=1.2, label="Equity")
    top.axhline(statement.starting_deposit, color="#666666", linewidth=0.8, linestyle="--",
                label=f"Starting deposit {money(statement.starting_deposit)}")
    top.set_ylabel("Equity (account currency)")
    top.legend(loc="best", fontsize=8)
    top.grid(True, color="#d9d9d9", linewidth=0.6)
    bottom.fill_between(times, [-d for d in drawdowns(values)], 0, color="#d62728", alpha=0.6)
    bottom.set_ylabel("Drawdown %")
    bottom.grid(True, color="#d9d9d9", linewidth=0.6)
    fig.suptitle(
        f"{statement.strategy} / {statement.symbol} / {statement.start} .. {statement.end}"
    )
    fig.autofmt_xdate()
    tmp = out.with_name(f".{out.name}.tmp")
    fig.savefig(tmp, dpi=CHART_DPI, format="png", bbox_inches="tight")
    plt.close(fig)
    tmp.replace(out)
    return out


def write_statement_files(statement: Statement, target: Path) -> StatementPaths:
    """Write `statement.md` + `equity.png` for an already-built statement into `target`.

    The Markdown is written atomically; the chart is rendered to a temp file and renamed
    into place, so neither artifact is ever half-written.
    """
    target.mkdir(parents=True, exist_ok=True)
    chart = render_equity_chart(statement, target / CHART_FILE)
    statement_path = target / STATEMENT_FILE
    write_text_atomic(statement_path, render_markdown(statement))
    return StatementPaths(statement=statement_path, chart=chart)


def write_statement(run_dir: Path, out_dir: Path | None = None) -> StatementPaths:
    """Build and write `statement.md` + `equity.png` for a finished run.

    Both land in `out_dir` (default: the run directory itself). Raises what
    `load_run_artifacts`/`build_statement` raise on a missing or inconsistent artifact.
    """
    statement = build_statement(load_run_artifacts(run_dir))
    return write_statement_files(statement, out_dir if out_dir is not None else run_dir)
