"""Steps for results_db.feature — run directories into the SQLite results database.

Synthetic run directories are assembled in tmp_path with the real artifact shapes:
run.json / metrics.json / trades.json / trade-plans.json / equity.csv /
strategy-config.yaml / strategy-provenance.json / main.json (orders) / log.txt (tagged
engine lines) and a real decisions.parquet written by `algo_backtest.chain.audit`. M1
partitions for the entry bars are written with `algo_core`'s ParquetRepository.
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_analyze.cli import app
from algo_analyze.resultsdb import BuildRequest, RunsRoot, build_database
from algo_analyze.resultsdb.decisions import extract_pattern
from algo_backtest.chain.audit import DecisionRow, FilterResultRow, write_decisions
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/results_db.feature")

_ORDER_TYPES = {"market": 0, "limit": 1, "stop": 2}
_DIRECTIONS = {"buy": 0, "sell": 1}
_LOG_PREFIX = "2026-09-28T02:28:11.1797446Z TRACE:: Debug: "


def _utc(text: str) -> datetime:
    """ISO text (with `Z` or an offset) -> aware UTC datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def _duration(entry: datetime, exit_: datetime) -> str:
    """LEAN TimeSpan text `[d.]hh:mm:ss` of a trade's holding time."""
    total = int((exit_ - entry).total_seconds())
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    prefix = f"{days}." if days else ""
    return f"{prefix}{hours:02d}:{minutes:02d}:{seconds:02d}"


class SyntheticRun:
    """One run directory under construction; `write()` materialises every artifact."""

    def __init__(self, run_dir: Path, strategy: str, symbol: str, start: str, end: str,
                 cash: str) -> None:
        self.run_dir = run_dir
        self.run: dict[str, Any] = {
            "strategy": strategy, "symbol": symbol, "start": start, "end": end,
            "params": {"cash": cash}, "success": True, "broker_adapter": "oanda",
        }
        self.metrics: dict[str, float] = {
            "total_return": 0.01, "sharpe": 0.5, "max_drawdown": 0.02, "hit_rate": 0.5,
        }
        self.equity: list[tuple[str, float]] = [
            (f"{start}T00:00:00+00:00", 10000.0), (f"{end}T00:00:00+00:00", 10100.0),
        ]
        self.trades: list[dict[str, Any]] = []
        self.orders: dict[str, dict[str, Any]] = {}
        self.plans: list[dict[str, Any]] | None = None
        self.config: dict[str, Any] | None = None
        self.provenance: dict[str, str] = {}
        self.decisions: list[DecisionRow] = []
        self.log_lines: list[str] = []
        self.model_sha256: str | None = None
        self.damage: list[tuple[str, str]] = []

    def add_trade(self, row: dict[str, str]) -> None:
        """One ledger trade plus its entry (market) and closing orders in main.json."""
        entry_id = int(row["order"])
        entry, exit_ = _utc(row["entry_time"]), _utc(row["exit_time"])
        profit = float(row["profit"])
        stamp = "%Y-%m-%dT%H:%M:%SZ"
        self.trades.append({
            "entryTime": entry.strftime(stamp), "entryPrice": float(row["entry_price"]),
            "direction": _DIRECTIONS[row["direction"]], "quantity": float(row["quantity"]),
            "exitTime": exit_.strftime(stamp), "exitPrice": float(row["exit_price"]),
            "profitLoss": profit, "totalFees": 0.0, "duration": _duration(entry, exit_),
            "isWin": profit > 0, "orderIds": [entry_id, entry_id + 1],
        })
        self.orders[str(entry_id)] = {"id": entry_id, "type": 0}
        self.orders[str(entry_id + 1)] = {
            "id": entry_id + 1, "type": _ORDER_TYPES[row["closing_order"]],
        }

    def set_config(self, key: str, value: str, source: str) -> None:
        """Set one dotted key of the resolved config and its provenance."""
        if self.config is None:
            self.config = {}
        node = self.config
        *parents, leaf = key.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = yaml.safe_load(value)
        self.provenance[key] = source

    def _write_log(self) -> None:
        """log.txt with the model hash line and every recorded tagged line."""
        lines = []
        if self.model_sha256:
            digest = f"HYBRID_MODEL_SHA256={self.model_sha256}"
            lines.append(f"{_LOG_PREFIX}2016-03-01 00:00:00 {digest}")
        lines.extend(self.log_lines)
        (self.run_dir / "log.txt").write_text("\n".join(lines) + "\n")

    def _write_equity(self) -> None:
        """equity.csv with the drawdown column derived from the running peak."""
        peak = float("-inf")
        with (self.run_dir / "equity.csv").open("w", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("time", "equity", "drawdown_pct"))
            for time, value in self.equity:
                peak = max(peak, value)
                writer.writerow((time, value, (peak - value) / peak * 100.0))

    def write(self) -> Path:
        """Materialise every artifact, then apply the requested damage."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        run = {**self.run, "closed_trades": len(self.trades)}
        (self.run_dir / "run.json").write_text(json.dumps(run))
        (self.run_dir / "metrics.json").write_text(json.dumps(self.metrics))
        (self.run_dir / "trades.json").write_text(json.dumps(self.trades))
        (self.run_dir / "main.json").write_text(json.dumps({"orders": self.orders}))
        (self.run_dir / "statement.md").write_text("# Account Statement\n")
        (self.run_dir / "report.html").write_text("<html></html>\n")
        if self.plans is not None:
            (self.run_dir / "trade-plans.json").write_text(json.dumps(self.plans))
        if self.config is not None:
            (self.run_dir / "strategy-config.yaml").write_text(yaml.safe_dump(self.config))
            (self.run_dir / "strategy-provenance.json").write_text(json.dumps(self.provenance))
        self._write_equity()
        self._write_log()
        write_decisions(self.decisions, self.run_dir / "decisions.parquet")
        for name, damage in self.damage:
            _apply_damage(self.run_dir / name, damage)
        return self.run_dir


def _apply_damage(path: Path, damage: str) -> None:
    """Break one artifact the way the outline names."""
    if damage == "missing":
        path.unlink()
    elif damage == "not valid JSON":
        path.write_text("not json")
    elif damage.startswith("lacking key "):
        document = json.loads(path.read_text())
        del document[damage.removeprefix("lacking key ")]
        path.write_text(json.dumps(document))
    elif damage == "headed wrongly":
        path.write_text("t,e,d\n2016-03-01T00:00:00+00:00,1,0\n")
    elif damage.startswith("lacking order "):
        document = json.loads(path.read_text())
        del document["orders"][damage.removeprefix("lacking order ")]
        path.write_text(json.dumps(document))
    else:
        raise ValueError(f"unknown damage {damage!r}")


@pytest.fixture
def rctx(tmp_path: Path) -> dict[str, Any]:
    """Accumulated state: the runs root, the run under construction, the database."""
    return {"tmp": tmp_path, "runs": [], "out": tmp_path / "results.sqlite"}


def _current(rctx: dict[str, Any]) -> SyntheticRun:
    """The run the last `Given a finished run` step created."""
    run: SyntheticRun = rctx["runs"][-1]
    return run


def _query(rctx: dict[str, Any], sql: str, *params: Any) -> list[tuple[Any, ...]]:
    """Rows of one query against the built database."""
    connection = sqlite3.connect(rctx["out"])
    try:
        return list(connection.execute(sql, params))
    finally:
        connection.close()


def _close(actual: Any, expected: str) -> bool:
    """Compare a cell: numbers approximately, everything else as text (`none` = NULL)."""
    if expected == "" or expected == "none":
        return actual is None or actual == ""
    try:
        return math.isclose(float(actual), float(expected), rel_tol=1e-6, abs_tol=1e-9)
    except (TypeError, ValueError):
        return str(actual) == expected


# --- Given -----------------------------------------------------------------------------


@given(parsers.parse('a runs root labelled "{label}" under a job directory "{job_dir}"'))
def _runs_root(rctx: dict[str, Any], label: str, job_dir: str) -> None:
    rctx["root"] = RunsRoot(job=label, path=rctx["tmp"] / job_dir)
    rctx["root"].path.mkdir(parents=True)


@given("an empty runs root")
def _empty_root(rctx: dict[str, Any]) -> None:
    rctx["root"] = RunsRoot(job="empty", path=rctx["tmp"] / "empty" / "runs")
    rctx["root"].path.mkdir(parents=True)


@given(parsers.parse(
    'a finished run "{run_id}" of strategy "{strategy}" on {symbol} from {start} to {end} '
    "with cash {cash}"
))
def _finished_run(rctx: dict[str, Any], run_id: str, strategy: str, symbol: str, start: str,
                  end: str, cash: str) -> None:
    run_dir = rctx["root"].path / strategy / run_id
    rctx["runs"].append(SyntheticRun(run_dir, strategy, symbol, start, end, cash))
    rctx["run_dir"] = run_dir


@given(parsers.parse(
    "its metrics are total_return {ret}, sharpe {sharpe}, max_drawdown {dd}, hit_rate {hit}"
))
def _metrics(rctx: dict[str, Any], ret: str, sharpe: str, dd: str, hit: str) -> None:
    _current(rctx).metrics = {
        "total_return": float(ret), "sharpe": float(sharpe), "max_drawdown": float(dd),
        "hit_rate": float(hit),
    }


@given("its config sets:")
def _config(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    header, *rows = datatable
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        _current(rctx).set_config(cells["key"], cells["value"], cells["source"])


@given("it has no strategy config")
def _no_config(rctx: dict[str, Any]) -> None:
    assert _current(rctx).config is None


@given(parsers.parse('its engine log names model sha256 "{digest}"'))
def _model(rctx: dict[str, Any], digest: str) -> None:
    _current(rctx).model_sha256 = digest


@given("its equity samples are:")
def _equity(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _current(rctx).equity = [(time, float(value)) for time, value in datatable[1:]]


@given("its closed trades are:")
def _trades(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    header, *rows = datatable
    for row in rows:
        _current(rctx).add_trade(dict(zip(header, row, strict=True)))


def _levels(text: str, keys: tuple[str, str]) -> list[dict[str, float]]:
    """`a:b,c:d` -> [{k1: a, k2: b}, ...] (targets or trail steps of a plan)."""
    out = []
    for pair in text.split(","):
        first, second = pair.split(":")
        out.append({keys[0]: float(first), keys[1]: float(second)})
    return out


@given("its trade plans are:")
def _plans(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    header, *rows = datatable
    plans = []
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        plans.append({
            "entry_order_id": int(cells["order"]), "lots": float(cells["lots"]),
            "stop_loss": float(cells["stop_loss"]), "stop_pips": float(cells["stop_pips"]),
            "take_profits": _levels(cells["targets"], ("price", "close_fraction")),
            "trail_stops": _levels(cells["trail_steps"], ("at_pips", "to_pips")),
            "spread_pips": float(cells["spread_pips"]),
        })
    _current(rctx).plans = plans


@given("its decisions are:")
def _decisions(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    header, *rows = datatable
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        _current(rctx).decisions.append(DecisionRow(
            trade_id=cells["trade_id"] or None, timestamp=_utc(cells["timestamp"]),
            pair="EURUSD", features_hash="0" * 64, filter_results=[],
            final_decision=cells["final_decision"], vetoed_by=cells["vetoed_by"] or None,
        ))


@given(parsers.parse("the decision at {timestamp} ran the filters:"))
def _filters(rctx: dict[str, Any], timestamp: str, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    decision = next(d for d in _current(rctx).decisions if d.timestamp == _utc(timestamp))
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        enrichment = {"p_hat": float(cells["p_hat"])} if cells["p_hat"] else None
        decision.filter_results.append(FilterResultRow(
            filter_name=cells["filter"], recommendation=cells["recommendation"],
            reason=cells["reason"], confidence=None, veto=cells["veto"] == "yes",
            enrichment=enrichment, metadata=None,
        ))


@given(parsers.parse('its engine log records "{line}" at {time}'))
def _log_line(rctx: dict[str, Any], line: str, time: str) -> None:
    if line == "-":
        return
    moment = _utc(time).strftime("%Y-%m-%d %H:%M:%S")
    _current(rctx).log_lines.append(f"{_LOG_PREFIX}{moment} {line}")


@given(parsers.parse('its file "{name}" is {damage}'))
def _damage(rctx: dict[str, Any], name: str, damage: str) -> None:
    _current(rctx).damage.append((name, damage))


@given(parsers.parse(
    'an unfinished run directory "{run_id}" of strategy "{strategy}" holding only main.json'
))
def _unfinished(rctx: dict[str, Any], run_id: str, strategy: str) -> None:
    run_dir = rctx["root"].path / strategy / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "main.json").write_text("{}")


@given(parsers.parse("the output file already holds schema version {version:d}"))
def _old_schema(rctx: dict[str, Any], version: int) -> None:
    connection = sqlite3.connect(rctx["out"])
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_version VALUES (?)", (version,))
    connection.commit()
    connection.close()


@given(parsers.parse(
    "M1 bars for {symbol} on {day} from {first} to {last} with bid {bid} rising {step} per "
    "minute and a {spread} spread"
))
def _m1_bars(rctx: dict[str, Any], symbol: str, day: str, first: str, last: str, bid: str,
             step: str, spread: str) -> None:
    start = _utc(f"{day}T{first}:00Z")
    minutes = int((_utc(f"{day}T{last}:00Z") - start).total_seconds() // 60)
    bars = []
    for i in range(minutes):
        b = float(bid) + float(step) * i
        a = b + float(spread)
        bars.append(QuoteBar(
            timestamp=start + timedelta(minutes=i), bid_open=b, bid_high=b, bid_low=b,
            bid_close=b, ask_open=a, ask_high=a, ask_low=a, ask_close=a, tick_count=1,
        ))
    root = rctx["tmp"] / "bars"
    path = price_path_for(root, build_instrument(symbol), "m1", start.year, start.month)
    path.parent.mkdir(parents=True)
    ParquetRepository(QuoteBar, path).put(bars)
    rctx["bars_root"] = root


# --- When ------------------------------------------------------------------------------


def _request(
    rctx: dict[str, Any], before: int | None = None, after: int | None = None
) -> BuildRequest:
    """The build request for the current root (with bars when the scenario asked)."""
    for run in rctx["runs"]:
        run.write()
    with_bars = before is not None
    return BuildRequest(
        roots=[rctx["root"]], out=rctx["out"],
        bars_root=rctx.get("bars_root", rctx["tmp"] / "bars") if with_bars else None,
        bars_before=before or 0, bars_after=after or 0,
    )


def _build(rctx: dict[str, Any], expect_failure: bool, before: int | None = None,
           after: int | None = None) -> None:
    """Run the build, recording the report or the failure message."""
    try:
        rctx["report"] = build_database(_request(rctx, before, after))
    except (FileNotFoundError, ValueError) as exc:
        assert expect_failure, f"unexpected failure: {exc}"
        rctx["error"] = str(exc)
        return
    assert not expect_failure, "the build was expected to fail"


@when("I build the results database")
@when("I build the results database again")
def _when_build(rctx: dict[str, Any]) -> None:
    _build(rctx, expect_failure=False)


@when("I build the results database expecting failure")
def _when_build_failing(rctx: dict[str, Any]) -> None:
    _build(rctx, expect_failure=True)


@when(parsers.parse(
    "I build the results database with {before:d} bars before and {after:d} after each entry"
))
def _when_build_bars(rctx: dict[str, Any], before: int, after: int) -> None:
    _build(rctx, expect_failure=False, before=before, after=after)


@when(parsers.parse(
    "I build the results database with {before:d} bars before and {after:d} after each entry "
    "expecting failure"
))
def _when_build_bars_failing(rctx: dict[str, Any], before: int, after: int) -> None:
    _build(rctx, expect_failure=True, before=before, after=after)


@when(parsers.parse(
    "its metrics change to total_return {ret}, sharpe {sharpe}, max_drawdown {dd}, hit_rate {hit}"
))
def _metrics_change(rctx: dict[str, Any], ret: str, sharpe: str, dd: str, hit: str) -> None:
    _metrics(rctx, ret, sharpe, dd, hit)


@when("I build the results database through the CLI")
def _when_cli(rctx: dict[str, Any]) -> None:
    for run in rctx["runs"]:
        run.write()
    root = rctx["root"]
    result = CliRunner().invoke(app, [
        "results-db", "build", "--runs-root", f"{root.job}={root.path}", "--out", str(rctx["out"]),
    ])
    assert result.exit_code == 0, result.output
    rctx["cli_output"] = result.output


@when(parsers.parse('I parse the runs root argument "{argument}"'))
def _when_parse_root(rctx: dict[str, Any], argument: str) -> None:
    rctx["parsed_root"] = RunsRoot.parse(argument)


# --- Then ------------------------------------------------------------------------------


@then(parsers.parse('table "{table}" has {count:d} row'))
@then(parsers.parse('table "{table}" has {count:d} rows'))
def _table_count(rctx: dict[str, Any], table: str, count: int) -> None:
    assert _query(rctx, f"SELECT COUNT(*) FROM {table}")[0][0] == count  # noqa: S608


@then(parsers.parse('the run "{run_id}" has:'))
def _run_has(rctx: dict[str, Any], run_id: str, datatable: list[list[str]]) -> None:
    for column, expected in datatable[1:]:
        (actual,) = _query(rctx, f"SELECT {column} FROM runs WHERE run_id = ?", run_id)[0]  # noqa: S608
        assert _close(actual, expected), f"{column}: {actual!r} != {expected!r}"


@then("the run's run_dir, statement_path and report_path point into its directory")
def _run_paths(rctx: dict[str, Any]) -> None:
    run_dir = str(_current(rctx).run_dir)
    (dir_, statement, report) = _query(
        rctx, "SELECT run_dir, statement_path, report_path FROM runs"
    )[0]
    assert dir_ == run_dir
    assert statement == f"{run_dir}/statement.md" and report == f"{run_dir}/report.html"


@then(parsers.parse('the parameter "{key}" of the run is "{value}" from "{source}"'))
def _parameter(rctx: dict[str, Any], key: str, value: str, source: str) -> None:
    rows = _query(rctx, "SELECT value, source FROM run_parameters WHERE key = ?", key)
    assert rows == [(value.replace('\\"', '"'), source)], rows


def _assert_rows(actual: list[tuple[Any, ...]], datatable: list[list[str]]) -> None:
    """Every expected row matches the actual row at the same index, cell by cell."""
    header, *expected = datatable
    assert len(actual) == len(expected), f"{len(actual)} rows, expected {len(expected)}"
    for got, want in zip(actual, expected, strict=True):
        for column, a, e in zip(header, got, want, strict=True):
            assert _close(a, e), f"{column}: {a!r} != {e!r}"


@then("the monthly returns of the run are:")
def _monthly(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    columns = ", ".join(datatable[0])
    _assert_rows(_query(rctx, f"SELECT {columns} FROM monthly_returns ORDER BY month"), datatable)  # noqa: S608


@then("the trades of the run are:")
def _trades_are(rctx: dict[str, Any], datatable: list[list[str]]) -> None:
    columns = ", ".join(datatable[0])
    _assert_rows(_query(rctx, f"SELECT {columns} FROM trades ORDER BY entry_time"), datatable)  # noqa: S608


@then(parsers.parse(
    'the trade plan of trade "{trade_id}" has stop_loss {stop}, stop_pips {pips}, '
    "{targets:d} targets and {steps:d} trail step"
))
def _plan(
    rctx: dict[str, Any], trade_id: str, stop: str, pips: str, targets: int, steps: int
) -> None:
    (stop_loss, stop_pips, targets_json, trail_json) = _query(
        rctx, "SELECT stop_loss, stop_pips, targets_json, trail_steps_json FROM trade_plans "
        "WHERE trade_id = ?", trade_id,
    )[0]
    assert _close(stop_loss, stop) and _close(stop_pips, pips)
    assert len(json.loads(targets_json)) == targets and len(json.loads(trail_json)) == steps


@then(parsers.parse(
    'the entry decision of trade "{trade_id}" is at {timestamp} with p_hat {p_hat}'
))
def _entry_decision(rctx: dict[str, Any], trade_id: str, timestamp: str, p_hat: str) -> None:
    rows = _query(
        rctx, "SELECT timestamp, p_hat FROM decisions WHERE trade_id = ? AND is_entry = 1", trade_id
    )
    assert len(rows) == 1 and rows[0][0] == timestamp and _close(rows[0][1], p_hat), rows


@then(parsers.parse(
    'the decision at {timestamp} is not an entry and was vetoed by "{filter_name}"'
))
def _vetoed_decision(rctx: dict[str, Any], timestamp: str, filter_name: str) -> None:
    rows = _query(
        rctx, "SELECT is_entry, vetoed_by, trade_id FROM decisions WHERE timestamp = ?", timestamp
    )
    assert rows == [(0, filter_name, None)], rows


@then(parsers.parse('the filters of the entry decision of trade "{trade_id}" are, in order:'))
def _entry_filters(rctx: dict[str, Any], trade_id: str, datatable: list[list[str]]) -> None:
    columns = ", ".join(datatable[0])
    rows = _query(
        rctx, f"SELECT {columns} FROM decision_filters WHERE decision_id = "  # noqa: S608
        "(SELECT id FROM decisions WHERE trade_id = ? AND is_entry = 1) ORDER BY position",
        trade_id,
    )
    _assert_rows(rows, datatable)


@then(parsers.parse('the pattern extracted from "{reason}" is {pattern}'))
def _pattern(reason: str, pattern: str) -> None:
    assert extract_pattern(reason) == (None if pattern == "none" else pattern)


@then(parsers.parse('the exit kind of trade "{trade_id}" is "{kind}"'))
def _exit_kind(rctx: dict[str, Any], trade_id: str, kind: str) -> None:
    rows = _query(rctx, "SELECT exit_kind FROM trades WHERE trade_id = ?", trade_id)
    assert rows == [(kind,)], rows


@then(parsers.parse('the trail moves of trade "{trade_id}" are:'))
def _trail(rctx: dict[str, Any], trade_id: str, datatable: list[list[str]]) -> None:
    columns = ", ".join(datatable[0])
    sql = f"SELECT {columns} FROM trail_moves WHERE trade_id = ? ORDER BY time"  # noqa: S608
    _assert_rows(_query(rctx, sql, trade_id), datatable)


@then(parsers.parse('the failure message is "{message}"'))
def _failure_is(rctx: dict[str, Any], message: str) -> None:
    expected = message.replace("{run_dir}", str(rctx["run_dir"]))
    assert rctx["error"] == expected, f"\n{rctx['error']}\n!=\n{expected}"


@then(parsers.parse('the failure message contains "{fragment}"'))
def _failure_contains(rctx: dict[str, Any], fragment: str) -> None:
    assert fragment in rctx["error"], rctx["error"]


@then(parsers.parse('the CLI reports "{line}"'))
def _cli_reports(rctx: dict[str, Any], line: str) -> None:
    assert line in rctx["cli_output"], rctx["cli_output"]


@then(parsers.parse('its job label is "{job}" and its path ends with "{tail}"'))
def _job_label(rctx: dict[str, Any], job: str, tail: str) -> None:
    root: RunsRoot = rctx["parsed_root"]
    assert root.job == job and root.path.name == tail, root


@then(parsers.parse('the entry bars of trade "{trade_id}" are:'))
def _entry_bars(rctx: dict[str, Any], trade_id: str, datatable: list[list[str]]) -> None:
    columns = ", ".join(datatable[0])
    sql = f"SELECT {columns} FROM entry_bars WHERE trade_id = ? ORDER BY offset"  # noqa: S608
    _assert_rows(_query(rctx, sql, trade_id), datatable)


_ = Callable  # keep the typing import meaningful for step helpers that take callables
