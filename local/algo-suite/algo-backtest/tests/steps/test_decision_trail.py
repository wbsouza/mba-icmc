"""Steps for decision_trail.feature — the per-trade decision drill-down of report.html.

Every input lives in the feature's tables: the chain rows written to a synthetic
`decisions.parquet` (through the package's own `write_decisions`), the ledger trades,
the executor's plans, LEAN's order book and the executor's log lines. The steps only
translate cells into the artifact shapes and read the resulting `DecisionTrail`s back.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.chain.audit import DecisionRow, FilterResultRow, write_decisions
from algo_backtest.cli import app
from algo_backtest.decision_trail import (
    DecisionTrail,
    build_decision_trails,
    format_duration,
)
from algo_backtest.report import render_report
from algo_backtest.statement import build_statement, load_run_artifacts
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/decision_trail.feature")

_NONE = "none"
_LOG_TAG = "HYBRID"
_LOG_PREFIX = "2026-09-28T02:16:48.1523100Z TRACE:: Debug: "


@pytest.fixture
def dt_ctx(tmp_path: Path) -> dict[str, Any]:
    """Accumulated fixture state for one scenario's run directory."""
    run_dir = tmp_path / "20260927T000000-deadbeef"
    run_dir.mkdir()
    return {
        "run_dir": run_dir, "run": {}, "config": {}, "decisions": [], "trades": [],
        "events": [], "orders": {}, "plans": None, "log": None,
    }


# --- fixture assembly ------------------------------------------------------------------


def _iso(text: str) -> datetime:
    """A feature timestamp (`...Z`) as an aware UTC datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    """A Gherkin table as one dict per row, keyed by the header."""
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _fill_events(order_id: int, side: str, units: float, price: float, when: datetime) -> list[
    dict[str, Any]
]:
    """A submitted + filled event pair the way LEAN's order-events file records them."""
    common = {
        "orderId": order_id, "symbolValue": "EURUSD", "direction": side, "quantity": units,
        "time": when.timestamp(), "fillPriceCurrency": "USD",
    }
    submitted = {"orderEventId": 1, "status": "submitted", "fillPrice": 0.0, "fillQuantity": 0.0}
    filled = {"orderEventId": 2, "status": "filled", "fillPrice": price, "fillQuantity": units}
    return [{**common, **submitted}, {**common, **filled}]


def _targets(text: str) -> list[dict[str, float]]:
    """`price:fraction,...` -> take_profits records."""
    out = []
    for item in filter(None, text.split(",")):
        price, fraction = item.split(":")
        out.append({"price": float(price), "close_fraction": float(fraction), "quantity": 0.0})
    return out


def _trail_stops(text: str) -> list[dict[str, float]]:
    """`at_price:at_ratio>to_price:to_ratio,...` -> trail_stops records."""
    out = []
    for item in filter(None, text.split(",")):
        at, to = item.split(">")
        at_price, at_ratio = at.split(":")
        to_price, to_ratio = to.split(":")
        out.append({
            "at_level_ratio": float(at_ratio), "to_level_ratio": float(to_ratio),
            "at_price": float(at_price), "to_price": float(to_price),
        })
    return out


def _main_json(dt_ctx: dict[str, Any]) -> dict[str, Any]:
    """LEAN's result JSON, minimal but shaped like the engine's."""
    start = _iso(f"{dt_ctx['run']['start']}T00:00:00Z").timestamp()
    return {
        "statistics": {
            "Net Profit": "0.100%", "Drawdown": "0.500%", "Sharpe Ratio": "1.2",
            "Win Rate": "50%", "Average Win": "0.01%", "Average Loss": "-0.01%",
            "Total Orders": str(len(dt_ctx["orders"])),
        },
        "runtimeStatistics": {
            "Equity": "$10,000.00", "Holdings": "$0.00", "Unrealized": "$0.00", "Fees": "-$0.00",
        },
        "charts": {
            "Strategy Equity": {"series": {"Equity": {"values": [[start] + [10000.0] * 4]}}}
        },
        "orders": dt_ctx["orders"],
        "algorithmConfiguration": {"accountCurrency": "USD"},
        "totalPerformance": {
            "closedTrades": dt_ctx["trades"],
            "portfolioStatistics": {"startEquity": "10000.0000", "endEquity": "10000.0000"},
            "tradeStatistics": {"totalNumberOfTrades": len(dt_ctx["trades"])},
        },
    }


def _materialize(dt_ctx: dict[str, Any]) -> Path:
    """Write every artifact the accumulated state describes into the run directory."""
    run_dir: Path = dt_ctx["run_dir"]
    docs: dict[str, Any] = {
        "run.json": dt_ctx["run"], "trades.json": dt_ctx["trades"], "main.json": _main_json(dt_ctx),
        "strategy-config.json": dt_ctx["config"],
    }
    if dt_ctx["events"]:
        docs["main-order-events.json"] = dt_ctx["events"]
    if dt_ctx["plans"] is not None:
        docs["trade-plans.json"] = dt_ctx["plans"]
    for name, doc in docs.items():
        (run_dir / name).write_text(json.dumps(doc, indent=1))
    if dt_ctx["decisions"]:
        write_decisions(dt_ctx["decisions"], run_dir / "decisions.parquet")
    if dt_ctx["log"] is not None:
        (run_dir / "log.txt").write_text("\n".join(dt_ctx["log"]) + "\n")
    return run_dir


# --- Given -----------------------------------------------------------------------------


@given(
    parsers.parse(
        'a chain run directory for strategy "{strategy}" on "{symbol}" from "{start}" to "{end}"'
    )
)
def _run_manifest(dt_ctx: dict[str, Any], strategy: str, symbol: str, start: str, end: str) -> None:
    dt_ctx["run"] = {
        "strategy": strategy, "symbol": symbol, "start": start, "end": end, "params": {},
        "success": True, "closed_trades": 0, "broker_adapter": "oanda",
    }


@given(
    parsers.parse(
        "the strategy config sets meta_learner theta_high {high:g}, theta_low {low:g} and "
        "regime_gate {gate}"
    )
)
def _meta_learner(dt_ctx: dict[str, Any], high: float, low: float, gate: str) -> None:
    dt_ctx["config"]["meta_learner"] = {
        "theta_high": high, "theta_low": low, "regime_gate": json.loads(gate),
    }


@given(parsers.parse("the strategy config sets {path} to {value}"))
def _config_sets(dt_ctx: dict[str, Any], path: str, value: str) -> None:
    *sections, leaf = path.split(".")
    node = dt_ctx["config"]
    for section in sections:
        node = node.setdefault(section, {})
    node[leaf] = json.loads(value)


@given(
    parsers.parse(
        'the chain decided "{decision}" at "{when}" for trade "{trade_id}" with the filter results'
    )
)
def _decision_row(
    dt_ctx: dict[str, Any], decision: str, when: str, trade_id: str, datatable: list[list[str]]
) -> None:
    """One decisions.parquet row; a `p_hat` cell becomes that filter's enrichment."""
    results = [
        FilterResultRow(
            filter_name=c["filter"], recommendation=c["recommendation"], reason=c["reason"],
            confidence=None, veto=c["veto"] == "yes",
            enrichment={"p_hat": float(c["p_hat"])} if c["p_hat"] else None, metadata=None,
        )
        for c in _cells(datatable)
    ]
    dt_ctx["decisions"].append(
        DecisionRow(
            trade_id=None if trade_id == _NONE else trade_id, timestamp=_iso(when),
            pair=dt_ctx["run"]["symbol"], features_hash="0" * 64, filter_results=results,
            final_decision=decision,
            vetoed_by=next((r.filter_name for r in results if r.veto), None),
        )
    )


@given("the closed trades")
def _trades(dt_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """Ledger trades with the entry/exit fills consistent with each direction."""
    for c in _cells(datatable):
        order_ids = [int(o) for o in c["orders"].split(",")]
        side = "buy" if c["direction"] == "0" else "sell"
        sign = 1 if side == "buy" else -1
        quantity = float(c["quantity"])
        entry, exit_ = _iso(c["entry_time"]), _iso(c["exit_time"])
        dt_ctx["trades"].append({
            "id": f"trade-{c['orders']}", "entryTime": c["entry_time"],
            "entryPrice": float(c["entry"]), "direction": int(c["direction"]),
            "quantity": quantity, "exitTime": c["exit_time"], "exitPrice": float(c["exit"]),
            "profitLoss": float(c["profit"]), "totalFees": 0.0,
            "duration": str(exit_ - entry), "isWin": float(c["profit"]) > 0, "orderIds": order_ids,
        })
        dt_ctx["events"] += _fill_events(
            order_ids[0], side, sign * quantity, float(c["entry"]), entry
        )
        dt_ctx["events"] += _fill_events(
            order_ids[-1], "sell" if side == "buy" else "buy", -sign * quantity,
            float(c["exit"]), exit_,
        )


@given("the trade plans")
def _plans(dt_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    dt_ctx["plans"] = [
        {
            "entry_order_id": int(c["entry_order_id"]),
            "entry_time": "2016-03-22T14:00:00+00:00", "direction": c["direction"],
            "lots": float(c["lots"]), "quantity": float(c["quantity"]),
            "entry_price": float(c["entry_price"]), "stop_loss": float(c["stop_loss"]),
            "take_profits": _targets(c["take_profits"]),
            "trail_stops": _trail_stops(c["trail_stops"]),
            "spread_pips": float(c["spread_pips"]),
        }
        for c in _cells(datatable)
    ]


@given("the engine order book")
def _order_book(dt_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    for c in _cells(datatable):
        dt_ctx["orders"][c["id"]] = {
            "id": int(c["id"]), "type": int(c["type"]), "status": int(c["status"]), "tag": c["tag"],
        }


@given("the executor log records")
def _log(dt_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """The executor's `<TAG>_TRAIL` / `<TAG>_OCO_CANCEL` lines as LEAN's log prints them."""
    lines = []
    for c in _cells(datatable):
        if c["event"] == "TRAIL":
            body = f"entry={c['entry']}|from={c['from']}|to={c['to']}|steps=[0]"
        else:
            body = f"reason={c['reason']}|orders=[3, 4]"
        lines.append(f"{_LOG_PREFIX}{c['time']} {_LOG_TAG}_{c['event']}|{body}")
    dt_ctx["log"] = lines


# --- When ------------------------------------------------------------------------------


@when("I build the decision trails")
def _build(dt_ctx: dict[str, Any]) -> None:
    dt_ctx["trails"] = build_decision_trails(_materialize(dt_ctx))


@when("building the decision trails fails")
def _build_fails(dt_ctx: dict[str, Any]) -> None:
    run_dir = _materialize(dt_ctx)
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        build_decision_trails(run_dir)
    dt_ctx["error"] = str(exc_info.value)


@when(parsers.parse('I format the holding time from "{entry}" to "{exit_}"'))
def _format_holding(dt_ctx: dict[str, Any], entry: str, exit_: str) -> None:
    dt_ctx["holding"] = format_duration(_iso(exit_) - _iso(entry))


@when("I build the report with the decision trails")
def _build_report(dt_ctx: dict[str, Any]) -> None:
    run_dir = _materialize(dt_ctx)
    statement = build_statement(load_run_artifacts(run_dir))
    dt_ctx["report"] = render_report(statement, trails=build_decision_trails(run_dir))


@when("I run the statement command on the run directory")
def _run_cli(dt_ctx: dict[str, Any]) -> None:
    run_dir = _materialize(dt_ctx)
    dt_ctx["cli"] = CliRunner().invoke(app, ["statement", "--run", str(run_dir)])
    report = run_dir / "report.html"
    dt_ctx["report"] = report.read_text() if report.is_file() else ""


# --- Then ------------------------------------------------------------------------------


def _trail(dt_ctx: dict[str, Any], ticket: int) -> DecisionTrail:
    return next(t for t in dt_ctx["trails"] if t.ticket == ticket)


def _details(report: str, ticket: int) -> str:
    """The `<details>` element of one ticket's trail."""
    match = re.search(
        rf"<details><summary>Decision trail · ticket {ticket} ·.*?</details>", report, re.DOTALL
    )
    assert match, f"no details element for ticket {ticket}"
    return match.group(0)


@then(parsers.parse("there is one trail per closed trade, for the tickets {tickets}"))
def _tickets(dt_ctx: dict[str, Any], tickets: str) -> None:
    assert [t.ticket for t in dt_ctx["trails"]] == [int(t) for t in tickets.split(",")]


@then(
    parsers.parse(
        'the trail for ticket {ticket:d} has direction "{direction}", decision "{decision}", '
        'vetoed by "{vetoed}" and p_hat {p_hat:g} against theta_high {high:g}, theta_low '
        "{low:g}, regime_gate {gate}"
    )
)
def _verdict(
    dt_ctx: dict[str, Any], ticket: int, direction: str, decision: str, vetoed: str,
    p_hat: float, high: float, low: float, gate: str,
) -> None:
    trail = _trail(dt_ctx, ticket)
    v = trail.verdict
    assert trail.direction == direction
    assert (v.final_decision, v.vetoed_by) == (decision, None if vetoed == _NONE else vetoed)
    assert (v.p_hat, v.theta_high, v.theta_low, v.regime_gate) == (
        p_hat, high, low, json.loads(gate)
    )


@then(parsers.parse("the trail for ticket {ticket:d} lists the filters"))
def _filters(dt_ctx: dict[str, Any], ticket: int, datatable: list[list[str]]) -> None:
    expected = [
        (c["filter"], c["recommendation"], c["veto"] == "yes", c["reason"])
        for c in _cells(datatable)
    ]
    actual = [
        (f.filter_name, f.recommendation, f.veto, f.reason)
        for f in _trail(dt_ctx, ticket).verdict.filters
    ]
    assert actual == expected


@then(
    parsers.parse(
        "the trail for ticket {ticket:d} plans lots {lots:g}, quantity {quantity:g}, entry "
        "{entry:g}, stop {stop:g} at {pips:g} pips, spread {spread:g} pips"
    )
)
def _plan(
    dt_ctx: dict[str, Any], ticket: int, lots: float, quantity: float, entry: float,
    stop: float, pips: float, spread: float,
) -> None:
    p = _trail(dt_ctx, ticket).plan
    assert (p.lots, p.quantity, p.entry_price, p.stop_loss, p.spread_pips) == (
        lots, quantity, entry, stop, spread
    )
    assert p.stop_pips == pytest.approx(pips)


@then(
    parsers.parse(
        'the trail for ticket {ticket:d} plans the targets "{targets}" and the trail steps '
        '"{steps}"'
    )
)
def _plan_levels(dt_ctx: dict[str, Any], ticket: int, targets: str, steps: str) -> None:
    p = _trail(dt_ctx, ticket).plan
    assert [(t.price, t.close_fraction) for t in p.targets] == [
        (t["price"], t["close_fraction"]) for t in _targets(targets)
    ]
    assert [
        (s.at_price, s.at_level_ratio, s.to_price, s.to_level_ratio) for s in p.trail_steps
    ] == [
        (s["at_price"], s["at_level_ratio"], s["to_price"], s["to_level_ratio"])
        for s in _trail_stops(steps)
    ]


@then(
    parsers.parse(
        'the trail for ticket {ticket:d} exits at "{when}" price {price:g} by "{label}" via '
        'order {order_id:d} with profit {profit:g} after "{holding}"'
    )
)
def _exit(
    dt_ctx: dict[str, Any], ticket: int, when: str, price: float, label: str, order_id: int,
    profit: float, holding: str,
) -> None:
    trail = _trail(dt_ctx, ticket)
    e = trail.exit
    assert (e.time, e.price, e.label, e.order_id) == (_iso(when), price, label, order_id)
    assert (trail.profit, format_duration(trail.holding)) == (profit, holding)


@then(
    parsers.parse(
        'the trail for ticket {ticket:d} was closed by "{label}" via order {order_id:d}'
    )
)
def _closed_by(dt_ctx: dict[str, Any], ticket: int, label: str, order_id: int) -> None:
    e = _trail(dt_ctx, ticket).exit
    assert (e.label, e.order_id) == (label, order_id)


@then(parsers.parse('the trail for ticket {ticket:d} records the trail moves "{moves}"'))
def _moves(dt_ctx: dict[str, Any], ticket: int, moves: str) -> None:
    expected = []
    for item in moves.split(","):
        when, prices = item.rsplit(":", 1)
        from_price, to_price = prices.split(">")
        expected.append((_iso(when), float(from_price), float(to_price)))
    e = _trail(dt_ctx, ticket).exit
    assert e.log_recorded
    assert [(m.time, m.from_price, m.to_price) for m in e.trail_moves] == expected


@then(parsers.parse("the trail for ticket {ticket:d} has no executor log"))
def _no_log(dt_ctx: dict[str, Any], ticket: int) -> None:
    e = _trail(dt_ctx, ticket).exit
    assert (e.log_recorded, e.trail_moves) == (False, ())


@then(parsers.parse('the holding time reads "{text}"'))
def _holding_reads(dt_ctx: dict[str, Any], text: str) -> None:
    assert dt_ctx["holding"] == text


@then(parsers.parse('the failure reads "{message}"'))
def _failure(dt_ctx: dict[str, Any], message: str) -> None:
    assert dt_ctx["error"] == message


@then(parsers.parse("the report has {count:d} details elements and no script element"))
def _details_count(dt_ctx: dict[str, Any], count: int) -> None:
    report: str = dt_ctx["report"]
    assert (report.count("<details"), report.count("<script")) == (count, 0)


@then(parsers.parse("the written report has {count:d} details elements and no script element"))
def _written_details_count(dt_ctx: dict[str, Any], count: int) -> None:
    _details_count(dt_ctx, count)


@then(parsers.parse('the report legend names the sections "{a}", "{b}" and "{c}"'))
def _legend(dt_ctx: dict[str, Any], a: str, b: str, c: str) -> None:
    legend = re.search(r'<p class="legend">(.*?)</p>', dt_ctx["report"])
    assert legend and all(name in legend.group(1) for name in (a, b, c)), legend


@then(
    parsers.parse(
        'the report trail for ticket {ticket:d} names the filters "{filters}" and the exit '
        '"{label}"'
    )
)
def _report_trail(dt_ctx: dict[str, Any], ticket: int, filters: str, label: str) -> None:
    details = _details(dt_ctx["report"], ticket)
    names = re.findall(r"<tr><td>([^<]+)</td><td>[A-Z_]+</td><td>(?:yes|no)</td>", details)
    assert names == [f.strip() for f in filters.split(",")], names
    assert f"<th>Closed by</th><td>{label} (order" in details, details


@then(parsers.parse('the report trail for ticket {ticket:d} shows "{text}"'))
def _report_trail_shows(dt_ctx: dict[str, Any], ticket: int, text: str) -> None:
    assert text in _details(dt_ctx["report"], ticket)


@then(parsers.parse("the report still has the tab labels {labels}"))
def _tab_labels(dt_ctx: dict[str, Any], labels: str) -> None:
    for label in re.findall(r'"([^"]+)"', labels):
        assert f">{label}</label>" in dt_ctx["report"], label


@then(parsers.parse("the statement command exits with code {code:d}"))
def _exit_code(dt_ctx: dict[str, Any], code: int) -> None:
    result = dt_ctx["cli"]
    assert result.exit_code == code, result.output


@then(parsers.parse('the written report states "{text}"'))
def _report_states(dt_ctx: dict[str, Any], text: str) -> None:
    assert text in dt_ctx["report"]
