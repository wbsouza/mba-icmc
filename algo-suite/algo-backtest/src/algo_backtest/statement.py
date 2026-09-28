"""End-of-run broker statement (`statement.md`), equity chart (`equity.png`) and the
chart's series as `equity.csv`.

Every simulation ends with a retail-FX account statement laid out like a MetaTrader /
MIG Bank daily or monthly confirmation (the run window is the period): a header line,
"Closed Transactions:", "Open Trades:", "Working Orders:" and the two-column "A/C
Summary:" block, followed by two extra sections (Performance, Parameters) and an
equity/drawdown chart. `equity.csv` holds exactly the series the chart draws — one row
per LEAN equity sample: `time` (ISO-8601 UTC), `equity`, `drawdown_pct` (percent below
the running peak) — so `algo-analyze equity-curves` can overlay several runs without
re-reading LEAN's result JSON. All three files are built **purely from the run
directory's artifacts** — no LEAN import, no engine re-run — so `algo-backtest statement
--run` can regenerate them for any finished run on disk:

  run.json                  strategy, symbol, window, params, broker_adapter
  trades.json               LEAN's closed-trade ledger (`totalPerformance.closedTrades`)
  <algo>.json               LEAN's result JSON (`statistics`, `runtimeStatistics`,
                            `charts['Strategy Equity']`, `charts['Portfolio Margin']`,
                            `orders`, `totalPerformance`, `algorithmConfiguration`)
  <algo>-order-events.json  every order event (LEAN omits the file when no order was
                            placed; it is required as soon as trades.json is non-empty)
  strategy-config.json      resolved strategy config (chain strategies only)
  strategy-provenance.json  dotted parameter path -> the config.yaml that set it
  trade-plans.json          OPTIONAL, written by the plan-driven executor (story 12 item
                            D): a list of {"entry_order_id": int, "entry_time": ISO,
                            "direction": "buy"|"sell", "lots": float, "quantity": float,
                            "stop_loss": float, "take_profits": [{"price": float,
                            "close_fraction": float}], "trail_stops": [...]}, joined to
                            trades.json by `orderIds[0]`. Absent -> the S / L and T / P
                            columns show "—" and the statement says so explicitly.

Direction contract (verified against a real run's fills, 2026-09-27): trades.json
`direction` is LEAN's `TradeDirection` — 0 = Long (entry fill `direction: "buy"`,
positive `fillQuantity`), 1 = Short (entry fill `direction: "sell"`, negative
`fillQuantity`). The builder cross-checks each trade's label against its entry fill and
fails fast on a contradiction rather than printing a wrong side.

Formats: times `YYYY.MM.DD HH:MM` UTC; prices at the instrument's quote precision — one
decimal more than its pip (the pipette, LEAN's minimum price variation: 5 for EURUSD's
0.0001 pip, 3 for USDJPY's 0.01), the pip taken from the instrument registry
(`algo_core.instrument`), never a per-pair constant here; for a symbol the registry does
not know, the most decimals any recorded price carries. The plan's stop and target prices
are derived floats (`entry - pips × pip`), so rendering at the float's own repr would
print binary noise such as `1.1207350000000003` — the quote precision is what a broker
confirmation shows. Lots and money to two decimals, money with thousands separators.
Nothing is fabricated: every figure comes from the artifacts; the only constants are
presentation (file names, chart size/dpi, labels).
"""

from __future__ import annotations

import csv
import io
import json
import statistics as pystats
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
from algo_core.atomicio import write_text_atomic  # noqa: E402
from algo_core.instrument import UnknownSymbolError, build_instrument  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from algo_backtest.results import find_result_json  # noqa: E402

STATEMENT_FILE = "statement.md"
CHART_FILE = "equity.png"
EQUITY_CSV_FILE = "equity.csv"
EQUITY_CSV_COLUMNS: tuple[str, ...] = ("time", "equity", "drawdown_pct")
TRADE_PLANS_FILE = "trade-plans.json"
# Presentation only — no money math depends on these.
CHART_DPI = 150
CHART_SIZE = (10.0, 6.0)
TIME_FORMAT = "%Y.%m.%d %H:%M"
ABSENT = "—"
NO_TRANSACTIONS = "No transactions"
NO_PLANS_NOTE = "no trade plan recorded for this run"
NO_CONFIG_NOTE = "no strategy-config.json recorded for this run"
SWAP_NOTE = "R/O Swap is 0.00 on every line: the LEAN forex model applies no rollover."
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
_TRADE_COLUMNS = ("Ticket", "Open Time", "Type", "Lots", "Item", "Price", "S / L", "T / P")
CLOSED_COLUMNS = (*_TRADE_COLUMNS, "Close Time", "Price", "Commission", "R/O Swap", "Trade P/L")


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
    """One row of Closed Transactions (commission is negative when a cost)."""

    ticket: int
    open_time: datetime
    type: str
    lots: float | None
    item: str
    open_price: float
    stop_loss: float | None
    take_profits: tuple[float, ...] | None
    close_time: datetime
    close_price: float
    commission: float
    swap: float
    profit: float


@dataclass(frozen=True)
class OpenTrade:
    """A position still open when the run ended (profit = the engine's unrealized P/L)."""

    ticket: int
    open_time: datetime
    type: str
    lots: float | None
    item: str
    open_price: float
    stop_loss: float | None
    take_profits: tuple[float, ...] | None
    current_price: float | None
    commission: float
    swap: float
    profit: float
    quantity: float
    holdings: float


@dataclass(frozen=True)
class WorkingOrder:
    """An order still on the book when the run ended (never filled, never cancelled)."""

    ticket: int
    open_time: datetime
    type: str
    lots: float | None
    item: str
    price: float | None
    stop_loss: float | None
    take_profits: tuple[float, ...] | None
    market_price: float | None
    status: str


@dataclass(frozen=True)
class AccountSummary:
    """The A/C Summary block: balance = deposit + closed P/L; equity = balance + floating."""

    previous_balance: float
    closed_pl: float
    deposit_withdrawal: float
    balance: float
    floating_pl: float
    total_credit_facility: float
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
    period_end: datetime
    run_id: str
    broker_adapter: str
    starting_deposit: float
    price_decimals: int
    transactions: tuple[ClosedTransaction, ...]
    open_trades: tuple[OpenTrade, ...]
    working_orders: tuple[WorkingOrder, ...]
    summary: AccountSummary
    performance: tuple[tuple[str, str], ...]
    parameters: tuple[Parameter, ...]
    plans_recorded: bool
    config_recorded: bool
    equity: tuple[tuple[datetime, float], ...]


@dataclass(frozen=True)
class EquityRow:
    """One `equity.csv` row: an ISO-8601 UTC time, the equity and its drawdown percent."""

    time: str
    equity: float
    drawdown_pct: float


@dataclass(frozen=True)
class StatementPaths:
    """Where the statement, its chart and the equity CSV were written."""

    statement: Path
    chart: Path
    equity_csv: Path
    report: Path


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


def parse_time(text: str, key: str, file: str) -> datetime:
    """An ISO-8601 timestamp of an artifact (LEAN's trailing 'Z') as an aware UTC datetime."""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{file} key {key!r} is not an ISO timestamp ({text!r})") from exc
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)


def unix_time(seconds: float) -> datetime:
    """Unix seconds (LEAN order-event `time`) -> aware UTC datetime."""
    return datetime.fromtimestamp(seconds, UTC)


def format_time(moment: datetime) -> str:
    """`YYYY.MM.DD HH:MM` in UTC, the broker confirmation's time format."""
    return moment.astimezone(UTC).strftime(TIME_FORMAT)


def _decimals_of(value: float) -> int:
    """How many decimals `repr(value)` carries (0 for an integer-valued float)."""
    exponent = Decimal(repr(float(value))).normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def price_precision(prices: Iterable[float]) -> int:
    """The fallback quote precision for a symbol outside the instrument registry: the most
    decimals any recorded price carries (5 for EURUSD quotes such as 1.08668, 3 for
    USDJPY's 120.123); 0 when none."""
    return max((_decimals_of(price) for price in prices), default=0)


def quote_decimals(pip_size: float) -> int:
    """The quote precision implied by a pip: one decimal finer than the pip (the pipette,
    LEAN's minimum price variation) — 0.0001 -> 5, 0.01 -> 3.

    Raises:
        ValueError: `pip_size` is not strictly positive.
    """
    if pip_size <= 0:
        raise ValueError(f"pip size must be positive to derive a quote precision, got {pip_size!r}")
    return _decimals_of(pip_size) + 1


def pip_size_for(symbol: str) -> float | None:
    """The instrument's pip from the registry, `None` for a symbol it does not know."""
    try:
        return float(build_instrument(symbol).unit_size)
    except UnknownSymbolError:
        return None


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
    return [(unix_time(row[0]), float(row[-1])) for row in rows]


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


def equity_rows(equity: Sequence[tuple[datetime, float]]) -> list[EquityRow]:
    """The `equity.csv` rows of an equity series: ISO-8601 UTC time, equity, drawdown %.

    Pure: the drawdown column is `drawdowns()` of the same closes the chart plots, so the
    CSV and `equity.png` never disagree.
    """
    values = [value for _, value in equity]
    return [
        EquityRow(time=moment.astimezone(UTC).isoformat(), equity=value, drawdown_pct=dd)
        for (moment, value), dd in zip(equity, drawdowns(values), strict=True)
    ]


def render_equity_csv(rows: Sequence[EquityRow]) -> str:
    """`equity.csv` text: the header then one row per equity sample (LF line endings)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EQUITY_CSV_COLUMNS)
    writer.writerows((row.time, row.equity, row.drawdown_pct) for row in rows)
    return buffer.getvalue()


def _leaf_paths(document: Mapping[str, Any], prefix: str = "") -> Iterator[tuple[str, Any]]:
    """(dotted path, value) for every leaf of a nested mapping; a list is one leaf."""
    for key, value in document.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            yield from _leaf_paths(value, f"{path}.")
        else:
            yield path, value


# --- building --------------------------------------------------------------------------


def _fills(events: Sequence[Mapping[str, Any]], file: str) -> list[dict[str, Any]]:
    """Every fill event in file order, each with an int `orderId` (fail fast if missing)."""
    fills = []
    for event in events:
        if event.get("status") in _FILL_STATUSES:
            fills.append({**event, "orderId": int(_field(event, "orderId", file))})
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


def _plan_levels(
    plans: Mapping[int, Mapping[str, Any]] | None, ticket: int
) -> tuple[float | None, tuple[float, ...] | None]:
    """(stop_loss, take-profit prices) of the plan for `ticket`; (None, None) when none."""
    plan = plans.get(ticket) if plans is not None else None
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


@dataclass(frozen=True)
class _Context:
    """Shared inputs of the row builders."""

    symbol: str
    lot_units: float | None
    fills_by_order: Mapping[int, Mapping[str, Any]]
    plans: Mapping[int, Mapping[str, Any]] | None
    events_file: str


def _closed_transaction(trade: Mapping[str, Any], ctx: _Context) -> ClosedTransaction:
    """One ledger trade -> one Closed Transactions row."""
    order_ids = _field(trade, "orderIds", "trades.json")
    if not order_ids:
        raise ValueError("trades.json has a closed trade with empty orderIds; cannot ticket it")
    ticket = int(order_ids[0])
    stop_loss, take_profits = _plan_levels(ctx.plans, ticket)
    return ClosedTransaction(
        ticket=ticket,
        open_time=parse_time(str(_field(trade, "entryTime", "trades.json")), "entryTime",
                             "trades.json"),
        type=_entry_side(trade, ticket, ctx.fills_by_order, ctx.events_file),
        lots=lots_from_quantity(float(_field(trade, "quantity", "trades.json")), ctx.lot_units),
        item=ctx.symbol,
        open_price=float(_field(trade, "entryPrice", "trades.json")),
        stop_loss=stop_loss,
        take_profits=take_profits,
        close_time=parse_time(str(_field(trade, "exitTime", "trades.json")), "exitTime",
                              "trades.json"),
        close_price=float(_field(trade, "exitPrice", "trades.json")),
        commission=-float(_field(trade, "totalFees", "trades.json")),
        swap=0.0,
        profit=float(_field(trade, "profitLoss", "trades.json")),
    )


def _opening_fill(fills: Sequence[Mapping[str, Any]]) -> tuple[float, Mapping[str, Any] | None]:
    """(net position, the fill that last took the account from flat) over all fills."""
    net = 0.0
    opening: Mapping[str, Any] | None = None
    for fill in fills:
        if net == 0:
            opening = fill
        net += float(fill.get("fillQuantity", 0.0))
    return net, opening if net != 0 else None


def _current_price(
    holdings: float, quantity: float, fill: Mapping[str, Any], account_currency: Any
) -> float | None:
    """Holdings / quantity when the fill's price currency is the account currency (then
    LEAN's holdings value is exactly quantity × price); `None` otherwise — never guessed."""
    if account_currency is None or fill.get("fillPriceCurrency") != account_currency:
        return None
    return abs(holdings) / abs(quantity)


def _open_trades(
    fills: Sequence[Mapping[str, Any]], result: Mapping[str, Any], ctx: _Context, file: str
) -> tuple[OpenTrade, ...]:
    """The position left open by the fills, reconciled with the engine's Holdings."""
    runtime = _field(result, "runtimeStatistics", file)
    holdings = parse_money(_field(runtime, "Holdings", file), "Holdings", file)
    floating = parse_money(_field(runtime, "Unrealized", file), "Unrealized", file)
    net, opening = _opening_fill(fills)
    if opening is None:
        if holdings != 0:
            raise ValueError(
                f"{file} runtimeStatistics Holdings is {holdings} but the order fills net "
                "to zero; the run's artifacts are inconsistent — re-run the backtest"
            )
        return ()
    ticket = int(opening["orderId"])
    stop_loss, take_profits = _plan_levels(ctx.plans, ticket)
    account_currency = (result.get("algorithmConfiguration") or {}).get("accountCurrency")
    return (
        OpenTrade(
            ticket=ticket, open_time=unix_time(float(_field(opening, "time", file))),
            type="buy" if net > 0 else "sell", lots=lots_from_quantity(net, ctx.lot_units),
            item=ctx.symbol, open_price=float(_field(opening, "fillPrice", file)),
            stop_loss=stop_loss, take_profits=take_profits,
            current_price=_current_price(holdings, net, opening, account_currency),
            commission=-float(opening.get("orderFeeAmount", 0.0)), swap=0.0, profit=floating,
            quantity=abs(net), holdings=holdings,
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
    events: Sequence[Mapping[str, Any]], result: Mapping[str, Any], ctx: _Context,
    market_price: float | None, file: str,
) -> tuple[WorkingOrder, ...]:
    """Orders whose last event is not terminal — still pending when the run ended."""
    orders = result.get("orders") or {}
    last: dict[int, Mapping[str, Any]] = {}
    for event in events:
        last[int(_field(event, "orderId", file))] = event
    working = []
    for ticket, event in sorted(last.items()):
        if event.get("status") in _TERMINAL_ORDER_STATUSES:
            continue
        stop_loss, take_profits = _plan_levels(ctx.plans, ticket)
        working.append(
            WorkingOrder(
                ticket=ticket, open_time=unix_time(float(_field(event, "time", file))),
                type=str(_field(event, "direction", file)),
                lots=lots_from_quantity(float(_field(event, "quantity", file)), ctx.lot_units),
                item=str(event.get("symbolValue", ctx.symbol)),
                price=_order_price(orders, ticket), stop_loss=stop_loss,
                take_profits=take_profits, market_price=market_price,
                status=str(_field(event, "status", file)),
            )
        )
    return tuple(working)


def _margin_requirement(
    result: Mapping[str, Any], equity: float, open_trades: Sequence[OpenTrade],
    last_fill_time: float,
) -> float | None:
    """End-of-run margin in account currency, never guessed.

    A flat account needs no margin (0.0). With a position open, LEAN's `Portfolio Margin`
    chart (per-symbol margin used as % of portfolio value, sampled daily) is used only
    when its last sample is not older than the last fill — an older snapshot describes
    an earlier position — and is `None` (rendered "n/a") otherwise.
    """
    if not open_trades:
        return 0.0
    chart = _margin_chart(result)
    if chart is None:
        return None
    percent = _current_margin_percent(_latest_margin_samples(chart), last_fill_time)
    return None if percent is None else equity * percent / 100.0


def _margin_chart(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """LEAN's `Portfolio Margin` chart, `None` when the result records none."""
    chart = (result.get("charts") or {}).get("Portfolio Margin")
    return chart if isinstance(chart, Mapping) else None


def _latest_margin_samples(chart: Mapping[str, Any]) -> list[Any]:
    """The last `[time, ..., percent]` sample of every non-empty series of the chart."""
    return [s["values"][-1] for s in (chart.get("series") or {}).values() if s.get("values")]


def _current_margin_percent(samples: Sequence[Any], last_fill_time: float) -> float | None:
    """The summed per-symbol margin percentage when every sample is at least as recent as
    the last fill; `None` (never guessed) when there are no samples or one is older."""
    if not samples or min(float(row[0]) for row in samples) < last_fill_time:
        return None
    return float(sum(row[-1] for row in samples))


def _account_summary(
    transactions: Sequence[ClosedTransaction], open_trades: Sequence[OpenTrade],
    result: Mapping[str, Any], file: str, last_fill_time: float,
) -> AccountSummary:
    """Balance = deposit + Σ(P/L + commission + swap); equity = balance + floating P/L."""
    portfolio = _field(_field(result, "totalPerformance", file), "portfolioStatistics", file)
    start = float(_field(portfolio, "startEquity", file))
    closed_pl = sum(t.profit + t.commission + t.swap for t in transactions)
    floating = sum(t.profit for t in open_trades)
    balance = start + closed_pl
    equity = balance + floating
    runtime = _field(result, "runtimeStatistics", file)
    margin = _margin_requirement(result, equity, open_trades, last_fill_time)
    return AccountSummary(
        previous_balance=start, closed_pl=closed_pl, deposit_withdrawal=0.0, balance=balance,
        floating_pl=floating, total_credit_facility=0.0, equity=equity,
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


def _recorded_prices(
    transactions: Sequence[ClosedTransaction], open_trades: Sequence[OpenTrade],
    working: Sequence[WorkingOrder],
) -> Iterator[float]:
    """Every price the artifacts recorded (never a derived one), for the quote precision."""
    for t in transactions:
        yield from (t.open_price, t.close_price)
    for o in open_trades:
        yield o.open_price
    for w in working:
        if w.price is not None:
            yield w.price
    rows: list[ClosedTransaction | OpenTrade | WorkingOrder] = [*transactions, *open_trades]
    rows.extend(working)
    for row in rows:
        if row.stop_loss is not None:
            yield row.stop_loss
        yield from row.take_profits or ()


def _price_decimals(symbol: str, recorded: Iterable[float]) -> int:
    """The quote precision: from the instrument's pip when the registry knows the symbol,
    else the most decimals the recorded prices carry."""
    pip = pip_size_for(symbol)
    return quote_decimals(pip) if pip is not None else price_precision(recorded)


def _period_end(equity: Sequence[tuple[datetime, float]], file: str) -> datetime:
    """The statement's as-of time: the engine's last equity sample."""
    if not equity:
        raise ValueError(
            f"{file} charts['Strategy Equity'] has no samples; the backtest may not have "
            "run — re-run it"
        )
    return equity[-1][0]


def build_statement(artifacts: RunArtifacts) -> Statement:
    """Assemble the statement from parsed artifacts (pure; raises on inconsistency).

    Raises:
        ValueError: a required key is missing, a direction contradicts its fill, or the
            fills and the engine's Holdings disagree about the end-of-run position.
    """
    run, result, file = artifacts.run, artifacts.result, artifacts.result_name
    fills = _fills(artifacts.order_events, artifacts.order_events_name)
    by_order: dict[int, Mapping[str, Any]] = {}
    for fill in fills:
        by_order.setdefault(fill["orderId"], fill)
    ctx = _Context(
        symbol=str(_field(run, "symbol", "run.json")),
        lot_units=_lot_notional_units(artifacts.strategy_config), fills_by_order=by_order,
        plans=_plans_by_entry(artifacts.trade_plans), events_file=artifacts.order_events_name,
    )
    transactions = tuple(
        sorted((_closed_transaction(t, ctx) for t in artifacts.trades), key=lambda t: t.open_time)
    )
    open_trades = _open_trades(fills, result, ctx, file)
    market_price = open_trades[0].current_price if open_trades else None
    working = _working_orders(artifacts.order_events, result, ctx, market_price, file)
    last_fill_time = max((float(f.get("time", 0.0)) for f in fills), default=0.0)
    summary = _account_summary(transactions, open_trades, result, file, last_fill_time)
    equity = tuple(equity_series(result, file))
    return Statement(
        strategy=str(_field(run, "strategy", "run.json")), symbol=ctx.symbol,
        start=str(_field(run, "start", "run.json")), end=str(_field(run, "end", "run.json")),
        period_end=_period_end(equity, file), run_id=artifacts.run_dir.name,
        broker_adapter=str(run.get("broker_adapter", "not recorded in run.json")),
        starting_deposit=summary.previous_balance,
        price_decimals=_price_decimals(
            ctx.symbol, _recorded_prices(transactions, open_trades, working)
        ),
        transactions=transactions, open_trades=open_trades, working_orders=working,
        summary=summary, performance=_performance(result, artifacts.trades, file),
        parameters=_parameters(artifacts), plans_recorded=ctx.plans is not None,
        config_recorded=artifacts.strategy_config is not None, equity=equity,
    )


# --- rendering -------------------------------------------------------------------------


def money(value: float) -> str:
    """Two decimals with thousands separators; never '-0.00'."""
    return f"{round(value, 2) + 0.0:,.2f}"


def _price(value: float | None, decimals: int) -> str:
    """A price at the instrument's quote precision, or the explicit absence marker."""
    return ABSENT if value is None else f"{value:.{decimals}f}"


def _targets(prices: tuple[float, ...] | None, decimals: int) -> str:
    """Take-profit levels joined with ' / ', or the absence marker when no plan exists."""
    return ABSENT if prices is None else " / ".join(_price(p, decimals) for p in prices)


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


def _leading_cells(row: ClosedTransaction | OpenTrade | WorkingOrder, decimals: int) -> list[str]:
    """The cells every trade-like table shares: Ticket .. T / P."""
    price = row.open_price if not isinstance(row, WorkingOrder) else row.price
    return [
        str(row.ticket), format_time(row.open_time), row.type, _lots(row.lots), row.item,
        _price(price, decimals), _price(row.stop_loss, decimals),
        _targets(row.take_profits, decimals),
    ]


def _totals_row(rows: Sequence[ClosedTransaction | OpenTrade], width: int) -> list[str]:
    """A totals row: Commission, R/O Swap and Trade P/L sums under the last three columns."""
    return ["**Total**"] + [""] * (width - 4) + [
        money(sum(r.commission for r in rows)), money(sum(r.swap for r in rows)),
        money(sum(r.profit for r in rows)),
    ]


def transaction_cells(t: ClosedTransaction, decimals: int) -> list[str]:
    """The thirteen Closed Transactions cells of one trade (shared with report.html)."""
    return [
        *_leading_cells(t, decimals), format_time(t.close_time), _price(t.close_price, decimals),
        money(t.commission), money(t.swap), money(t.profit),
    ]


def _closed_section(statement: Statement) -> list[str]:
    """Closed Transactions: the ledger rows, a totals row and the closed P/L line."""
    headers = list(CLOSED_COLUMNS)
    rows = [transaction_cells(t, statement.price_decimals) for t in statement.transactions]
    if not rows:
        rows = [[NO_TRANSACTIONS] + [""] * (len(headers) - 1)]
    rows.append(_totals_row(statement.transactions, len(headers)))
    s = statement.summary
    lines = ["## Closed Transactions:", "", *_table(headers, rows), ""]
    lines.append(
        f"Deposit/Withdrawal: {money(s.deposit_withdrawal)}    "
        f"Credit Facility: {money(s.total_credit_facility)}    "
        f"Closed Trade P/L: {money(s.closed_pl)}"
    )
    lines.extend(("", f"_{SWAP_NOTE}_"))
    if not statement.plans_recorded:
        lines.append(
            f"_S / L and T / P are {ABSENT}: {NO_PLANS_NOTE} ({TRADE_PLANS_FILE} absent)._"
        )
    return lines


def _open_section(statement: Statement) -> list[str]:
    """Open Trades at the end of the run, with a totals row and the floating P/L line."""
    d = statement.price_decimals
    lines = ["## Open Trades:", ""]
    if not statement.open_trades:
        return [*lines, NO_TRANSACTIONS]
    headers = [*_TRADE_COLUMNS, "Price", "Commission", "R/O Swap", "Trade P/L"]
    rows = [
        [*_leading_cells(t, d), _price(t.current_price, d), money(t.commission), money(t.swap),
         money(t.profit)]
        for t in statement.open_trades
    ]
    rows.append(_totals_row(statement.open_trades, len(headers)))
    floating = f"Floating P/L: {money(statement.summary.floating_pl)}"
    return [*lines, *_table(headers, rows), "", floating]


def _working_section(statement: Statement) -> list[str]:
    """Working Orders (pending stop/limit orders) at the end of the run."""
    d = statement.price_decimals
    lines = ["## Working Orders:", ""]
    if not statement.working_orders:
        return [*lines, NO_TRANSACTIONS]
    rows = [[*_leading_cells(o, d), _price(o.market_price, d)] for o in statement.working_orders]
    return [*lines, *_table([*_TRADE_COLUMNS, "Market Price"], rows)]


def summary_lines(statement: Statement) -> list[str]:
    """The A/C Summary as `label: amount` lines (also printed on the console)."""
    s = statement.summary
    return [
        f"Previous Ledger Balance: {money(s.previous_balance)}",
        f"Closed Trade P/L: {money(s.closed_pl)}",
        f"Deposit/Withdrawal: {money(s.deposit_withdrawal)}",
        f"Balance: {money(s.balance)}",
        f"Floating P/L: {money(s.floating_pl)}",
        f"Total Credit Facility: {money(s.total_credit_facility)}",
        f"Equity: {money(s.equity)}",
        f"Margin Requirement: {_optional_money(s.margin_requirement)}",
        f"Available Margin: {_optional_money(s.available_margin)}",
        f"Equity (engine-reported): {money(s.engine_equity)}",
    ]


def _summary_section(statement: Statement) -> list[str]:
    """The A/C Summary as the broker's two-column block (balance side | equity side)."""
    cells = [line.split(": ", 1) for line in summary_lines(statement)]
    left, right, engine = cells[:4], cells[4:9], cells[9]
    rows = [
        [*(left[i] if i < len(left) else ["", ""]), *right[i]] for i in range(len(right))
    ]
    return [
        "## A/C Summary:", "", *_table(["", "", "", ""], rows), "",
        f"_{engine[0]}: {engine[1]} (LEAN's runtimeStatistics Equity, for reconciliation)._",
    ]


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


def header_line(statement: Statement) -> str:
    """`A/C No: <run id>   Name: <strategy> / <symbol>   <period end>` — the confirmation's
    header (the run window is the period; its end is the engine's last equity sample)."""
    return (
        f"A/C No: {statement.run_id}   Name: {statement.strategy} / {statement.symbol}   "
        f"{format_time(statement.period_end)}"
    )


def render_markdown(statement: Statement) -> str:
    """The whole statement as GitHub-flavoured Markdown."""
    header = [
        "# Account Statement", "", f"**{header_line(statement)}**", "",
        f"Period: {statement.start} .. {statement.end} UTC · Broker adapter: "
        f"{statement.broker_adapter} · Starting deposit: {money(statement.starting_deposit)} · "
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ]
    sections = [
        header, _closed_section(statement), _open_section(statement),
        _working_section(statement), _summary_section(statement),
        _performance_section(statement), _parameters_section(statement),
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
    """Write `statement.md`, `equity.png`, `equity.csv` and `report.html` for a built
    statement into `target`.

    The Markdown, the CSV and the HTML are written atomically; the chart is rendered to a
    temp file and renamed into place, so no artifact is ever half-written.
    """
    # Local import: report.py builds on this module's Statement (no import cycle).
    from algo_backtest.report import REPORT_FILE, render_report

    target.mkdir(parents=True, exist_ok=True)
    chart = render_equity_chart(statement, target / CHART_FILE)
    statement_path = target / STATEMENT_FILE
    write_text_atomic(statement_path, render_markdown(statement))
    equity_csv = target / EQUITY_CSV_FILE
    write_text_atomic(equity_csv, render_equity_csv(equity_rows(statement.equity)))
    report_path = target / REPORT_FILE
    write_text_atomic(report_path, render_report(statement))
    return StatementPaths(
        statement=statement_path, chart=chart, equity_csv=equity_csv, report=report_path
    )


def write_statement(run_dir: Path, out_dir: Path | None = None) -> StatementPaths:
    """Build and write `statement.md`, `equity.png`, `equity.csv` and `report.html` for a
    finished run.

    All four land in `out_dir` (default: the run directory itself). Raises what
    `load_run_artifacts`/`build_statement` raise on a missing or inconsistent artifact.
    """
    statement = build_statement(load_run_artifacts(run_dir))
    return write_statement_files(statement, out_dir if out_dir is not None else run_dir)
