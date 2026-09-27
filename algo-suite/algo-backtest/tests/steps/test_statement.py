"""Steps for statement.feature — the end-of-run broker statement and equity chart.

The run directory is assembled in tmp_path from small hand-written JSON documents that
mirror the real artifact shapes (run.json, trades.json, main.json, main-order-events.json,
strategy-config.json, strategy-provenance.json, trade-plans.json). Every Given accumulates
state in `st_ctx`; the files are written when a When step runs.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.cli import app
from algo_backtest.statement import (
    Statement,
    build_statement,
    drawdowns,
    equity_series,
    format_time,
    header_line,
    load_run_artifacts,
    price_precision,
    render_markdown,
    summary_lines,
    unix_time,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/statement.feature")

_ENTRY_TIME = "2015-09-01T10:00:00Z"
_EXIT_TIME = "2015-09-01T10:10:00Z"
_EVENT_TIME = 1441101600.0


@pytest.fixture
def st_ctx(tmp_path: Path) -> dict[str, Any]:
    """Accumulated fixture state for one scenario's run directory."""
    run_dir = tmp_path / "20260927T000000-deadbeef"
    run_dir.mkdir()
    return {
        "run_dir": run_dir, "run": {}, "trades": [], "events": {}, "orders": {},
        "statistics": {}, "portfolio": {}, "runtime": {}, "equity_rows": [],
        "config": None, "provenance": None, "plans": None, "margin": "absent",
        "no_equity_chart": False, "no_order_events": False, "lacking": set(), "corrupt": set(),
        "account_currency": "USD",
    }


# --- fixture assembly ------------------------------------------------------------------


def _fill_events(order_id: int, side: str, units: float, price: float) -> list[dict[str, Any]]:
    """A submitted + filled event pair the way LEAN's order-events file records them."""
    common = {
        "orderId": order_id, "symbolValue": "EURUSD", "direction": side, "quantity": units,
        "time": _EVENT_TIME, "fillPriceCurrency": "USD",
    }
    submitted = {"orderEventId": 1, "status": "submitted", "fillPrice": 0.0, "fillQuantity": 0.0}
    filled = {"orderEventId": 2, "status": "filled", "fillPrice": price, "fillQuantity": units}
    return [{**common, **submitted}, {**common, **filled}]


def _trade(
    orders: str, direction: int, quantity: float, entry: float, exit_: float, profit: float,
    fees: float, duration: str = "00:10:00", entry_time: str = _ENTRY_TIME,
) -> dict[str, Any]:
    """One closed trade in LEAN's ledger shape."""
    return {
        "id": f"trade-{orders}", "entryTime": entry_time, "entryPrice": entry,
        "direction": direction, "quantity": quantity, "exitTime": _EXIT_TIME,
        "exitPrice": exit_, "profitLoss": profit, "totalFees": fees, "duration": duration,
        "isWin": profit > 0, "orderIds": [int(o) for o in orders.split(",")],
    }


def _add_trade_with_fills(st_ctx: dict[str, Any], trade: dict[str, Any]) -> None:
    """Append a trade and the entry/exit fills consistent with its direction."""
    st_ctx["trades"].append(trade)
    side = "buy" if trade["direction"] == 0 else "sell"
    sign = 1 if side == "buy" else -1
    entry_id, exit_id = trade["orderIds"][0], trade["orderIds"][-1]
    st_ctx["events"][entry_id] = _fill_events(
        entry_id, side, sign * trade["quantity"], trade["entryPrice"]
    )
    st_ctx["events"][exit_id] = _fill_events(
        exit_id, "sell" if side == "buy" else "buy", -sign * trade["quantity"], trade["exitPrice"]
    )


def _main_json(st_ctx: dict[str, Any]) -> dict[str, Any]:
    """LEAN's result JSON, minimal but shaped like the engine's."""
    charts: dict[str, Any] = {}
    if not st_ctx["no_equity_chart"]:
        charts["Strategy Equity"] = {"series": {"Equity": {"values": st_ctx["equity_rows"]}}}
    if st_ctx["margin"] == "empty":
        charts["Portfolio Margin"] = {"series": {}}
    elif st_ctx["margin"] != "absent":
        pct, sample_time = st_ctx["margin"]
        charts["Portfolio Margin"] = {
            "series": {"EURUSD": {"unit": "%", "values": [[sample_time, pct]]}}
        }
    orders = [event for events in st_ctx["events"].values() for event in events]
    statistics = {
        "Net Profit": "0.100%", "Drawdown": "0.500%", "Sharpe Ratio": "1.2", "Win Rate": "50%",
        "Average Win": "0.01%", "Average Loss": "-0.01%",
        "Total Orders": str(len(st_ctx["events"])), **st_ctx["statistics"],
    }
    runtime = {"Equity": "$10,000.00", "Holdings": "$0.00", "Unrealized": "$0.00",
               "Fees": "-$0.00", **st_ctx["runtime"]}
    return {
        "statistics": statistics, "runtimeStatistics": runtime, "charts": charts,
        "orders": st_ctx["orders"],
        "algorithmConfiguration": {"accountCurrency": st_ctx["account_currency"]},
        "totalPerformance": {
            "closedTrades": st_ctx["trades"],
            "portfolioStatistics": {
                "totalNetProfit": "0.001", "sharpeRatio": "1.2", "drawdown": "0.005",
                "winRate": "0.5", **st_ctx["portfolio"],
            },
            "tradeStatistics": {
                "totalNumberOfTrades": len(st_ctx["trades"]),
                "numberOfWinningTrades": sum(1 for t in st_ctx["trades"] if t["isWin"]),
            },
        },
        "state": {"OrderCount": str(len(orders))},
    }


def _materialize(st_ctx: dict[str, Any]) -> Path:
    """Write every artifact the accumulated state describes into the run directory."""
    run_dir: Path = st_ctx["run_dir"]
    docs: dict[str, Any] = {
        "run.json": st_ctx["run"], "trades.json": st_ctx["trades"],
        "main.json": _main_json(st_ctx),
    }
    if st_ctx["events"] and not st_ctx["no_order_events"]:
        docs["main-order-events.json"] = [
            event for events in st_ctx["events"].values() for event in events
        ]
    optional = {
        "strategy-config.json": "config", "strategy-provenance.json": "provenance",
        "trade-plans.json": "plans",
    }
    for name, key in optional.items():
        if st_ctx[key] is not None:
            docs[name] = st_ctx[key]
    for name, doc in docs.items():
        (run_dir / name).write_text(json.dumps(doc, indent=1))
    for name in st_ctx["lacking"]:
        (run_dir / name).unlink()
    for name in st_ctx["corrupt"]:
        (run_dir / name).write_text("{ not valid json")
    return run_dir


# --- Given -----------------------------------------------------------------------------


@given(
    parsers.parse(
        'a run directory for strategy "{strategy}" on "{symbol}" from "{start}" to "{end}"'
    )
)
def _run_manifest(st_ctx: dict[str, Any], strategy: str, symbol: str, start: str, end: str) -> None:
    st_ctx["run"] = {
        "strategy": strategy, "symbol": symbol, "start": start, "end": end, "params": {},
        "success": True, "closed_trades": 0, "broker_adapter": "oanda",
    }


@given(parsers.parse("the engine reports start equity {start:g} and end equity {end:g}"))
def _start_end_equity(st_ctx: dict[str, Any], start: float, end: float) -> None:
    st_ctx["statistics"].update({"Start Equity": f"{start:.2f}", "End Equity": f"{end:.2f}"})
    st_ctx["portfolio"].update({"startEquity": f"{start:.4f}", "endEquity": f"{end:.4f}"})
    st_ctx["runtime"]["Equity"] = f"${end:,.2f}"


@given("the engine equity chart rows")
def _equity_rows(st_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    st_ctx["equity_rows"] = [[int(t)] + [float(c)] * 4 for t, c in rows]


@given(parsers.parse("the strategy config sets {path} to {value}"))
def _config_sets(st_ctx: dict[str, Any], path: str, value: str) -> None:
    """Set one dotted parameter in strategy-config.json; `absent` records no config at all."""
    if value == "absent":
        return
    config = st_ctx["config"] if st_ctx["config"] is not None else {}
    *sections, leaf = path.split(".")
    node = config
    for section in sections:
        node = node.setdefault(section, {})
    node[leaf] = json.loads(value)
    st_ctx["config"] = config


@given(parsers.parse('the strategy provenance maps "{path}" to "{source}"'))
def _provenance_maps(st_ctx: dict[str, Any], path: str, source: str) -> None:
    provenance = st_ctx["provenance"] if st_ctx["provenance"] is not None else {}
    provenance[path] = source
    st_ctx["provenance"] = provenance


@given(parsers.parse('the run params include "{key}" = "{value}"'))
def _run_param(st_ctx: dict[str, Any], key: str, value: str) -> None:
    st_ctx["run"]["params"][key] = value


@given(
    parsers.parse(
        "a closed trade with orders {orders} direction {direction:d} quantity {quantity:g} "
        "entry {entry:g} exit {exit_:g} profit {profit:g} fees {fees:g}"
    )
)
def _one_trade(
    st_ctx: dict[str, Any], orders: str, direction: int, quantity: float, entry: float,
    exit_: float, profit: float, fees: float,
) -> None:
    """A single ledger trade; its fills are declared separately (they are an input)."""
    st_ctx["trades"].append(_trade(orders, direction, quantity, entry, exit_, profit, fees))


@given("the closed trades")
def _trades_table(st_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """Several ledger trades with entry/exit fills consistent with each direction."""
    header, *rows = datatable
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        _add_trade_with_fills(
            st_ctx,
            _trade(
                cells["orders"], int(cells["direction"]), float(cells["quantity"]),
                float(cells["entry"]), float(cells["exit"]), float(cells["profit"]),
                float(cells["fees"]), entry_time=cells.get("open_time", _ENTRY_TIME),
            ),
        )


@given("the closed trades with durations")
def _trades_durations(st_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    for orders, duration in rows:
        _add_trade_with_fills(st_ctx, _trade(orders, 0, 1000, 1.1, 1.2, 1.0, 0.0, duration))


@given(parsers.parse('order {order_id:d} filled as "{side}" for {units:g} units'))
def _order_filled(st_ctx: dict[str, Any], order_id: int, side: str, units: float) -> None:
    st_ctx["events"][order_id] = _fill_events(order_id, side, units, 1.1)


@given(parsers.parse('order {order_id:d} filled as "{side}" for {units:g} units at {price:g}'))
def _order_filled_at(
    st_ctx: dict[str, Any], order_id: int, side: str, units: float, price: float
) -> None:
    st_ctx["events"][order_id] = _fill_events(order_id, side, units, price)


@given(parsers.parse('the engine account currency is "{currency}"'))
def _account_currency(st_ctx: dict[str, Any], currency: str) -> None:
    st_ctx["account_currency"] = currency


@given(
    parsers.parse(
        'order {order_id:d} was submitted as "{side}" for {units:g} units and never filled'
    )
)
def _order_pending(st_ctx: dict[str, Any], order_id: int, side: str, units: float) -> None:
    st_ctx["events"][order_id] = _fill_events(order_id, side, units, 0.0)[:1]


@given(
    parsers.parse(
        'order {order_id:d} was submitted as "{side}" for {units:g} units and then marked '
        '"{status}"'
    )
)
def _order_terminal(
    st_ctx: dict[str, Any], order_id: int, side: str, units: float, status: str
) -> None:
    submitted, filled = _fill_events(order_id, side, units, 0.0)
    st_ctx["events"][order_id] = [submitted, {**filled, "status": status, "fillQuantity": 0.0}]


@given(parsers.parse("the engine order book prices order {order_id:d} at stop {price:g}"))
def _order_stop_price(st_ctx: dict[str, Any], order_id: int, price: float) -> None:
    st_ctx["orders"][str(order_id)] = {"id": order_id, "type": 2, "stopPrice": price}


@given(
    parsers.parse(
        'the engine runtime statistics report holdings "{holdings}" and unrealized "{unrealized}"'
    )
)
def _runtime_holdings(st_ctx: dict[str, Any], holdings: str, unrealized: str) -> None:
    st_ctx["runtime"].update({"Holdings": holdings, "Unrealized": unrealized})


@given(parsers.parse('the engine runtime statistics report equity "{equity}"'))
def _runtime_equity(st_ctx: dict[str, Any], equity: str) -> None:
    st_ctx["runtime"]["Equity"] = equity


@given(parsers.parse("the portfolio margin chart is {spec}"))
def _margin_chart(st_ctx: dict[str, Any], spec: str) -> None:
    """`absent`, `empty`, or `at <pct> percent sampled before|after the last fill`."""
    if spec in ("absent", "empty"):
        st_ctx["margin"] = spec
        return
    pct, _, when = spec.removeprefix("at ").partition(" percent sampled ")
    offset = -86400.0 if when == "before the last fill" else 0.0
    st_ctx["margin"] = (float(pct), _EVENT_TIME + offset)


@given("no order ever filled")
def _no_fills(st_ctx: dict[str, Any]) -> None:
    """The account stays flat: no order events at all."""
    st_ctx["events"].clear()


@given("the trade plans")
def _trade_plans(st_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    st_ctx["plans"] = [
        {
            "entry_order_id": int(entry_id), "entry_time": _ENTRY_TIME, "direction": direction,
            "lots": 0.1, "quantity": 10000.0, "stop_loss": float(stop),
            "take_profits": [
                {"price": float(price), "close_fraction": 0.5} for price in targets.split(",")
            ],
            "trail_stops": [],
        }
        for entry_id, direction, stop, targets in rows
    ]


@given("the engine result has no equity chart")
def _no_equity_chart(st_ctx: dict[str, Any]) -> None:
    st_ctx["no_equity_chart"] = True


@given("the order-events file is missing")
def _no_order_events(st_ctx: dict[str, Any]) -> None:
    st_ctx["no_order_events"] = True


@given(parsers.parse('the run directory lacks "{artifact}"'))
def _lacks(st_ctx: dict[str, Any], artifact: str) -> None:
    st_ctx["lacking"].add(artifact)


@given(parsers.parse('the run directory\'s "{artifact}" is corrupt'))
def _corrupt(st_ctx: dict[str, Any], artifact: str) -> None:
    st_ctx["corrupt"].add(artifact)


# --- When ------------------------------------------------------------------------------


@when("I build the statement")
def _build(st_ctx: dict[str, Any]) -> None:
    statement = build_statement(load_run_artifacts(_materialize(st_ctx)))
    st_ctx["statement"] = statement
    st_ctx["markdown"] = render_markdown(statement)


@when("I build the statement expecting failure")
def _build_failing(st_ctx: dict[str, Any]) -> None:
    run_dir = _materialize(st_ctx)
    with pytest.raises((ValueError, FileNotFoundError)) as exc_info:
        build_statement(load_run_artifacts(run_dir))
    st_ctx["error"] = str(exc_info.value)


@when("I read the equity series")
def _read_equity(st_ctx: dict[str, Any]) -> None:
    run_dir = _materialize(st_ctx)
    st_ctx["series"] = equity_series(json.loads((run_dir / "main.json").read_text()))


@when(parsers.parse("I compute drawdowns for the equity values {values}"))
def _compute_drawdowns(st_ctx: dict[str, Any], values: str) -> None:
    st_ctx["drawdowns"] = drawdowns([float(v) for v in values.split(",")])


@when(parsers.parse("I derive the price precision of {prices}"))
def _derive_precision(st_ctx: dict[str, Any], prices: str) -> None:
    st_ctx["precision"] = price_precision(float(p) for p in prices.split(","))


@when("I run the statement command on that run directory")
def _run_cli(st_ctx: dict[str, Any]) -> None:
    run_dir = _materialize(st_ctx)
    st_ctx["cli"] = CliRunner().invoke(app, ["statement", "--run", str(run_dir)])


@when("I run the statement command on that run directory with an --out directory")
def _run_cli_out(st_ctx: dict[str, Any], tmp_path: Path) -> None:
    run_dir = _materialize(st_ctx)
    out = tmp_path / "statements" / "nested"
    st_ctx["out"] = out
    st_ctx["cli"] = CliRunner().invoke(
        app, ["statement", "--run", str(run_dir), "--out", str(out)]
    )


# --- Then ------------------------------------------------------------------------------


def _section(markdown: str, title: str) -> str:
    """The body of one `## title` section of the rendered statement."""
    marker = f"## {title}\n"
    start = markdown.index(marker) + len(marker)
    end = markdown.find("\n## ", start)
    return markdown[start:] if end == -1 else markdown[start:end]


def _table_rows(section: str) -> list[list[str]]:
    """Data rows (header and separator dropped) of the first table in a section."""
    lines = [line for line in section.splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[2:]]


def _closed_rows(st_ctx: dict[str, Any]) -> list[list[str]]:
    """Closed Transactions data rows without the totals row."""
    rows = _table_rows(_section(st_ctx["markdown"], "Closed Transactions:"))
    return [row for row in rows if row[0] != "**Total**"]


def _totals_row(st_ctx: dict[str, Any]) -> list[str]:
    rows = _table_rows(_section(st_ctx["markdown"], "Closed Transactions:"))
    return next(row for row in rows if row[0] == "**Total**")


def _header_cells(section: str) -> list[str]:
    """The header cells of the first table in a section."""
    line = next(line for line in section.splitlines() if line.startswith("|"))
    return [cell.strip() for cell in line.strip("|").split("|")]


def _summary(st_ctx: dict[str, Any]) -> dict[str, str]:
    statement: Statement = st_ctx["statement"]
    return dict(line.split(": ", 1) for line in summary_lines(statement))


@then(
    parsers.parse(
        'closed transaction {index:d} shows ticket {ticket:d}, type "{side}", lots "{lots}", '
        'item "{item}"'
    )
)
def _row_identity(
    st_ctx: dict[str, Any], index: int, ticket: int, side: str, lots: str, item: str
) -> None:
    row = _closed_rows(st_ctx)[index - 1]
    assert row[:5] == [str(ticket), "2015.09.01 10:00", side, lots, item], row


@then(
    parsers.parse(
        'closed transaction {index:d} shows open time "{opened}" and close time "{closed}"'
    )
)
def _row_times(st_ctx: dict[str, Any], index: int, opened: str, closed: str) -> None:
    row = _closed_rows(st_ctx)[index - 1]
    assert row[1] == opened and row[8] == closed, row


@then(parsers.parse("the closed transaction tickets are {tickets}"))
def _row_order(st_ctx: dict[str, Any], tickets: str) -> None:
    expected = [t.strip() for t in tickets.split(",")]
    assert [row[0] for row in _closed_rows(st_ctx)] == expected


@then(parsers.parse('the closed transactions section states "{text}"'))
def _closed_states(st_ctx: dict[str, Any], text: str) -> None:
    assert text in _section(st_ctx["markdown"], "Closed Transactions:")


@then(parsers.parse('the header line is "{text}"'))
def _header(st_ctx: dict[str, Any], text: str) -> None:
    assert header_line(st_ctx["statement"]) == text
    assert text in st_ctx["markdown"]


@then(parsers.parse('the closed transactions table has the columns "{columns}"'))
def _closed_columns(st_ctx: dict[str, Any], columns: str) -> None:
    expected = [c.strip() for c in columns.split("|")]
    assert _header_cells(_section(st_ctx["markdown"], "Closed Transactions:")) == expected


@then(parsers.parse("the price precision is {decimals:d}"))
def _precision_is(st_ctx: dict[str, Any], decimals: int) -> None:
    assert st_ctx["precision"] == decimals


@then("the A/C summary block rows are")
def _summary_block(st_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    rows = _table_rows(_section(st_ctx["markdown"], "A/C Summary:"))
    assert rows == [[cell.strip() for cell in row] for row in datatable], rows


@then(
    parsers.parse(
        "closed transaction {index:d} shows open price {entry:g}, close price {exit_:g}, "
        'commission "{commission}", swap "{swap}", P/L "{pl}"'
    )
)
def _row_money(
    st_ctx: dict[str, Any], index: int, entry: float, exit_: float, commission: str, swap: str,
    pl: str,
) -> None:
    row = _closed_rows(st_ctx)[index - 1]
    assert row[5] == f"{entry:.5f}" and row[9] == f"{exit_:.5f}", row
    assert row[10:13] == [commission, swap, pl], row


@then(parsers.parse('closed transaction {index:d} shows S/L "{stop}" and T/P "{target}"'))
def _row_levels(st_ctx: dict[str, Any], index: int, stop: str, target: str) -> None:
    row = _closed_rows(st_ctx)[index - 1]
    assert row[6] == stop and row[7] == target, row


@then(parsers.parse("the statement lists {count:d} closed transactions"))
def _row_count(st_ctx: dict[str, Any], count: int) -> None:
    assert len(_closed_rows(st_ctx)) == count
    assert len(st_ctx["statement"].transactions) == count


@then(parsers.parse('the totals row shows commission "{commission}", swap "{swap}" and P/L "{pl}"'))
def _totals(st_ctx: dict[str, Any], commission: str, swap: str, pl: str) -> None:
    assert _totals_row(st_ctx)[10:13] == [commission, swap, pl], _totals_row(st_ctx)


@then(parsers.parse('the failure names both "{first}" and "{second}"'))
def _failure_names_two(st_ctx: dict[str, Any], first: str, second: str) -> None:
    assert first in st_ctx["error"] and second in st_ctx["error"], st_ctx["error"]


@then(parsers.parse('the failure names "{name}"'))
def _failure_names(st_ctx: dict[str, Any], name: str) -> None:
    assert name in st_ctx["error"], st_ctx["error"]


@then(
    parsers.parse(
        'the A/C summary shows previous ledger balance "{start}", closed trade P/L "{closed}", '
        'balance "{balance}", floating P/L "{floating}" and equity "{equity}"'
    )
)
def _summary_arithmetic(
    st_ctx: dict[str, Any], start: str, closed: str, balance: str, floating: str, equity: str
) -> None:
    summary = _summary(st_ctx)
    assert summary["Previous Ledger Balance"] == start, summary
    assert summary["Closed Trade P/L"] == closed, summary
    assert summary["Balance"] == balance, summary
    assert summary["Floating P/L"] == floating, summary
    assert summary["Equity"] == equity, summary
    assert _section(st_ctx["markdown"], "A/C Summary:").count(balance) >= 1


@then(
    parsers.parse(
        'the A/C summary shows deposit/withdrawal "{value}" and total credit facility "{credit}"'
    )
)
def _summary_deposit(st_ctx: dict[str, Any], value: str, credit: str) -> None:
    assert _summary(st_ctx)["Deposit/Withdrawal"] == value
    assert _summary(st_ctx)["Total Credit Facility"] == credit


@then(parsers.parse('the A/C summary shows engine-reported equity "{value}"'))
def _summary_engine_equity(st_ctx: dict[str, Any], value: str) -> None:
    assert _summary(st_ctx)["Equity (engine-reported)"] == value


@then(
    parsers.parse(
        'the A/C summary shows margin requirement "{requirement}" and available margin '
        '"{available}"'
    )
)
def _summary_margin(st_ctx: dict[str, Any], requirement: str, available: str) -> None:
    summary = _summary(st_ctx)
    assert summary["Margin Requirement"] == requirement, summary
    assert summary["Available Margin"] == available, summary


@then(parsers.parse('the statement says "{text}"'))
def _says(st_ctx: dict[str, Any], text: str) -> None:
    assert text in st_ctx["markdown"], st_ctx["markdown"]


@then(parsers.parse('the statement does not say "{text}"'))
def _does_not_say(st_ctx: dict[str, Any], text: str) -> None:
    assert text not in st_ctx["markdown"], st_ctx["markdown"]


@then(parsers.parse('the open trades section says "{text}"'))
def _open_says(st_ctx: dict[str, Any], text: str) -> None:
    assert _section(st_ctx["markdown"], "Open Trades:").strip() == text


@then(parsers.parse('the working orders section says "{text}"'))
def _working_says(st_ctx: dict[str, Any], text: str) -> None:
    assert _section(st_ctx["markdown"], "Working Orders:").strip() == text


@then(parsers.parse('the open trades section states "{text}"'))
def _open_states(st_ctx: dict[str, Any], text: str) -> None:
    assert text in _section(st_ctx["markdown"], "Open Trades:")


@then(
    parsers.parse(
        'the open trades section lists ticket {ticket:d} opened "{opened}" of type "{side}", '
        'lots "{lots}", price "{price}", current price "{current}", P/L "{pl}"'
    )
)
def _open_trade(
    st_ctx: dict[str, Any], ticket: int, opened: str, side: str, lots: str, price: str,
    current: str, pl: str,
) -> None:
    rows = _table_rows(_section(st_ctx["markdown"], "Open Trades:"))
    assert rows[0] == [str(ticket), opened, side, lots, "EURUSD", price, "—", "—", current,
                       "0.00", "0.00", pl], rows
    assert rows[1][0] == "**Total**" and rows[1][-1] == pl, rows
    assert format_time(unix_time(_EVENT_TIME)) == opened


@then(
    parsers.parse(
        'the working orders section lists ticket {ticket:d} opened "{opened}" of type "{side}", '
        'lots "{lots}", price "{price}", market price "{market}"'
    )
)
def _working_order(
    st_ctx: dict[str, Any], ticket: int, opened: str, side: str, lots: str, price: str,
    market: str,
) -> None:
    rows = _table_rows(_section(st_ctx["markdown"], "Working Orders:"))
    assert rows == [[str(ticket), opened, side, lots, "EURUSD", price, "—", "—", market]], rows


@then("the equity series is")
def _equity_series_is(st_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    expected = [(datetime.fromisoformat(t), float(e)) for t, e in rows]
    assert st_ctx["series"] == expected


@then(parsers.parse("the drawdowns are {values}"))
def _drawdowns_are(st_ctx: dict[str, Any], values: str) -> None:
    assert st_ctx["drawdowns"] == pytest.approx([float(v) for v in values.split(",")])


@then(
    parsers.parse(
        'the performance section shows median holding "{median}" minutes and trades "{trades}"'
    )
)
def _performance(st_ctx: dict[str, Any], median: str, trades: str) -> None:
    rows = dict(map(tuple, _table_rows(_section(st_ctx["markdown"], "Performance"))))
    assert rows["Median holding (minutes)"] == median, rows
    assert rows["Trades"] == trades, rows


@then(parsers.parse('the parameters table has row "{key}" = "{value}" from "{source}"'))
def _parameter_row(st_ctx: dict[str, Any], key: str, value: str, source: str) -> None:
    rows = _table_rows(_section(st_ctx["markdown"], "Parameters"))
    assert [key, f"`{value}`", source] in rows, rows


@then(parsers.parse("the statement command exits with code {code:d}"))
def _cli_exit(st_ctx: dict[str, Any], code: int) -> None:
    assert st_ctx["cli"].exit_code == code, st_ctx["cli"].output


@then(parsers.parse('the run directory contains "{first}" and "{second}"'))
def _run_dir_contains(st_ctx: dict[str, Any], first: str, second: str) -> None:
    run_dir: Path = st_ctx["run_dir"]
    assert (run_dir / first).stat().st_size > 0 and (run_dir / second).stat().st_size > 0


@then(parsers.parse('the --out directory contains "{first}" and "{second}"'))
def _out_dir_contains(st_ctx: dict[str, Any], first: str, second: str) -> None:
    out: Path = st_ctx["out"]
    assert (out / first).stat().st_size > 0 and (out / second).stat().st_size > 0
    assert not (st_ctx["run_dir"] / first).exists()


@then(parsers.parse('the output prints the A/C summary balance "{balance}" and both file paths'))
def _cli_output(st_ctx: dict[str, Any], balance: str) -> None:
    out = st_ctx["cli"].output
    assert f"statement: Balance: {balance}" in out, out
    assert str(st_ctx["run_dir"] / "statement.md") in out and "equity.png" in out, out


@then(parsers.parse('the output names "{artifact}"'))
def _cli_names(st_ctx: dict[str, Any], artifact: str) -> None:
    assert artifact in st_ctx["cli"].output, st_ctx["cli"].output
