"""Discover run directories under each `--runs-root`, ingest each into the database.

A run directory is `<runs-root>/<strategy>/<stamp>/` holding `run.json` (the engine
writes it last, so a directory without one is a run still in progress: it is skipped
and counted, never half-read). Ingesting a run is an upsert keyed by the directory name:
its previous rows are deleted and the fresh ones inserted in one transaction, so
re-running the build on the same roots is idempotent.

The job label of a root is given as `LABEL=DIR`; without a label it is the name of the
nearest ancestor of DIR that is not called `runs` or `data` (so
`.../2026-09-28-broad-window-h4/data/runs` is the job `2026-09-28-broad-window-h4`).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from algo_backtest.chain.price_features import PriceFeatureConfig
from algo_backtest.statement import _leaf_paths
from algo_core.instrument import build_instrument

from algo_analyze.resultsdb import schema
from algo_analyze.resultsdb.artifacts import (
    EQUITY_PNG_FILE,
    REPORT_FILE,
    RUN_FILE,
    STATEMENT_FILE,
    RunArtifacts,
    field,
    load_run_artifacts,
)
from algo_analyze.resultsdb.bars import BarStore
from algo_analyze.resultsdb.decisions import DecisionRow, decision_rows, summarize
from algo_analyze.resultsdb.trades import (
    PlanRow,
    TradeRow,
    TrailMove,
    lot_notional_units,
    plan_row,
    plans_by_entry,
    trade_row,
    trail_moves,
)

_GENERIC_DIRS = frozenset({"runs", "data"})
DECISION_MODES: tuple[str, ...] = ("full", "entries")


@dataclass(frozen=True)
class RunsRoot:
    """One `--runs-root` argument: the job label and the directory of `<strategy>/<stamp>/`."""

    job: str
    path: Path

    @classmethod
    def parse(cls, text: str) -> RunsRoot:
        """`LABEL=DIR` or `DIR` (label = nearest ancestor not named runs/data)."""
        label, sep, raw = text.partition("=")
        path = Path(raw if sep else text).expanduser().resolve()
        if sep and not label:
            raise ValueError(f"--runs-root {text!r}: the label before '=' is empty")
        return cls(job=label if sep else job_label(path), path=path)


def job_label(path: Path) -> str:
    """The nearest ancestor-or-self name of `path` that is not a generic `runs`/`data`."""
    for part in reversed(path.parts):
        if part not in _GENERIC_DIRS and part != path.anchor:
            return part
    raise ValueError(f"--runs-root {path}: cannot derive a job label; pass LABEL={path}")


@dataclass(frozen=True)
class BuildRequest:
    """What one `results-db build` does."""

    roots: Sequence[RunsRoot]
    out: Path
    bars_root: Path | None = None
    bars_before: int = 30
    bars_after: int = 30
    decisions: str = "full"

    def __post_init__(self) -> None:
        """Fail fast on an unknown --decisions mode."""
        if self.decisions not in DECISION_MODES:
            raise ValueError(
                f"--decisions must be one of {list(DECISION_MODES)}, got {self.decisions!r}"
            )


@dataclass(frozen=True)
class BuildReport:
    """What the build did: the ingested run ids and the unfinished directories skipped."""

    ingested: tuple[str, ...]
    skipped: tuple[Path, ...]
    out: Path


def discover(root: RunsRoot) -> tuple[list[Path], list[Path]]:
    """(finished run directories, unfinished ones) under `root`, both sorted.

    Raises:
        FileNotFoundError: the root does not exist or holds no `<strategy>/<stamp>/` dirs.
    """
    if not root.path.is_dir():
        raise FileNotFoundError(f"--runs-root {root.path} is not a directory")
    candidates = sorted(p for p in root.path.glob("*/*") if p.is_dir())
    if not candidates:
        raise FileNotFoundError(
            f"--runs-root {root.path} holds no <strategy>/<stamp>/ run directories"
        )
    finished = [p for p in candidates if (p / RUN_FILE).is_file()]
    return finished, [p for p in candidates if p not in finished]


# --- row derivation ----------------------------------------------------------------------


def bar_minutes_of(config: Mapping[str, Any] | None) -> int:
    """`price_features.bar_minutes` of the resolved config, else the engine's default."""
    default = PriceFeatureConfig().bar_minutes
    if config is None:
        return default
    section = config.get("price_features")
    if not isinstance(section, Mapping) or "bar_minutes" not in section:
        return default
    return int(section["bar_minutes"])


def parameters(artifacts: RunArtifacts) -> list[tuple[str, str, str]]:
    """(key, JSON value, source) for every config leaf, then the run's `--param` values."""
    rows: list[tuple[str, str, str]] = []
    if artifacts.config is not None:
        provenance = artifacts.provenance or {}
        for path, value in sorted(_leaf_paths(artifacts.config)):
            rows.append((path, json.dumps(value), provenance.get(path, "unknown")))
    params = field(artifacts.run, "params", artifacts.run_dir / RUN_FILE)
    rows.extend((key, json.dumps(value), "--param") for key, value in sorted(params.items()))
    return rows


def monthly_returns(
    equity: Sequence[tuple[str, float, float]], exits: Sequence[datetime]
) -> list[tuple[str, float, float, float, int]]:
    """(month, start, end, return %, trades closed) per month of the equity series.

    Same rule as `report.monthly_returns`: a month starts at the previous month's last
    sample (the first sample for the first month) and ends at its own last sample.
    """
    last_by_month: dict[str, float] = {}
    for time, value, _ in equity:
        last_by_month[datetime.fromisoformat(time).astimezone(UTC).strftime("%Y-%m")] = value
    closes = [moment.astimezone(UTC).strftime("%Y-%m") for moment in exits]
    rows: list[tuple[str, float, float, float, int]] = []
    start = equity[0][1]
    for month, end in last_by_month.items():
        if start <= 0:
            raise ValueError(f"equity must be positive to define a monthly return, got {start}")
        rows.append((month, start, end, (end / start - 1.0) * 100.0, closes.count(month)))
        start = end
    return rows


def _window(run: Mapping[str, Any], path: Path) -> tuple[date, date]:
    """The run's inclusive (start, end) dates from run.json."""
    try:
        return date.fromisoformat(str(field(run, "start", path))), date.fromisoformat(
            str(field(run, "end", path))
        )
    except ValueError as exc:
        raise ValueError(
            f"{path.name} in {path.parent} start/end are not YYYY-MM-DD ({exc})"
        ) from exc


def _optional_path(run_dir: Path, name: str) -> str | None:
    """The absolute path of an optional statement artifact, `None` when absent."""
    path = run_dir / name
    return str(path) if path.is_file() else None


def _cash(run: Mapping[str, Any]) -> float | None:
    """The `--param cash` value of the run, `None` when the run recorded none."""
    params = run.get("params") or {}
    return None if params.get("cash") is None else float(params["cash"])


@dataclass(frozen=True)
class RunRows:
    """Every row of one run, derived before anything is written."""

    run_id: str
    header: tuple[Any, ...]
    parameters: list[tuple[str, str, str]]
    equity: list[tuple[str, float, float]]
    monthly: list[tuple[str, float, float, float, int]]
    trades: list[TradeRow]
    plans: list[PlanRow]
    decisions: list[DecisionRow]
    summary: list[tuple[str, str, int]]
    trail: list[TrailMove]
    bar_minutes: int
    symbol: str
    window: tuple[date, date]


def _trades_and_plans(
    artifacts: RunArtifacts, symbol: str
) -> tuple[list[TradeRow], list[PlanRow]]:
    """The ledger's trades and, for those with a recorded plan, their plan rows."""
    plans = plans_by_entry(artifacts.plans, artifacts.run_dir)
    lot_units = lot_notional_units(artifacts.config)
    pip_size = build_instrument(symbol).unit_size
    trades: list[TradeRow] = []
    plan_rows: list[PlanRow] = []
    for trade in artifacts.trades:
        entry_id = int(field(trade, "orderIds", artifacts.run_dir / "trades.json")[0])
        plan = plans.get(entry_id)
        row = trade_row(trade, artifacts.orders, artifacts.log, plan, lot_units, artifacts.run_dir)
        trades.append(row)
        if plan is not None:
            plan_rows.append(plan_row(row.trade_id, plan, pip_size, artifacts.run_dir))
    return sorted(trades, key=lambda t: t.entry_time), plan_rows


def derive_rows(artifacts: RunArtifacts, job: str) -> RunRows:
    """Turn one run's artifacts into the rows of every table (pure; raises on inconsistency)."""
    run, run_dir = artifacts.run, artifacts.run_dir
    path = run_dir / RUN_FILE
    symbol = str(field(run, "symbol", path))
    trades, plans = _trades_and_plans(artifacts, symbol)
    metrics = artifacts.metrics
    decisions = decision_rows(artifacts.decisions, run_dir)
    header = (
        run_dir.name, job, str(run_dir), str(field(run, "strategy", path)),
        symbol, str(field(run, "start", path)),
        str(field(run, "end", path)), _cash(run), bar_minutes_of(artifacts.config),
        artifacts.model_sha256, run.get("code_revision"), int(bool(run.get("success", True))),
        int(field(run, "closed_trades", path)) if "closed_trades" in run else len(trades),
        metrics["total_return"], metrics["sharpe"], metrics["max_drawdown"], metrics["hit_rate"],
        _optional_path(run_dir, STATEMENT_FILE), _optional_path(run_dir, REPORT_FILE),
        _optional_path(run_dir, EQUITY_PNG_FILE), datetime.now(UTC).isoformat(),
    )
    return RunRows(
        run_id=run_dir.name, header=header, parameters=parameters(artifacts),
        equity=artifacts.equity,
        monthly=monthly_returns(artifacts.equity, [t.exit_time for t in trades]),
        trades=trades, plans=plans, decisions=decisions, summary=summarize(decisions),
        trail=trail_moves(artifacts.log, trades), bar_minutes=bar_minutes_of(artifacts.config),
        symbol=symbol, window=_window(run, path),
    )


# --- writing -----------------------------------------------------------------------------


def _iso(moment: datetime) -> str:
    """ISO-8601 UTC text for a time column."""
    return moment.astimezone(UTC).isoformat()


def _write_trades(connection: sqlite3.Connection, rows: RunRows) -> None:
    """Insert the trades, plans and trail moves of one run."""
    connection.executemany(
        "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (rows.run_id, t.trade_id, t.entry_order_id, t.direction, t.lots, t.quantity,
             _iso(t.entry_time), t.entry_price, _iso(t.exit_time), t.exit_price, t.profit,
             t.fees, int(t.is_win), t.exit_kind, t.exit_order_id, t.exit_order_type,
             t.holding_minutes)
            for t in rows.trades
        ],
    )
    connection.executemany(
        "INSERT INTO trade_plans VALUES (?,?,?,?,?,?,?)",
        [(rows.run_id, p.trade_id, p.stop_loss, p.stop_pips, p.targets_json, p.trail_steps_json,
          p.spread_pips) for p in rows.plans],
    )
    connection.executemany(
        "INSERT INTO trail_moves VALUES (?,?,?,?,?)",
        [(rows.run_id, m.trade_id, _iso(m.time), m.from_stop, m.to_stop) for m in rows.trail],
    )


def _write_decisions(connection: sqlite3.Connection, rows: RunRows, mode: str) -> None:
    """Insert the funnel summary, then every decision (or only the entries) with its
    filter rows (ids assigned by SQLite)."""
    connection.executemany(
        "INSERT INTO decision_summary VALUES (?,?,?,?)",
        [(rows.run_id, *row) for row in rows.summary],
    )
    kept = rows.decisions if mode == "full" else [d for d in rows.decisions if d.is_entry]
    for decision in kept:
        cursor = connection.execute(
            "INSERT INTO decisions (run_id, trade_id, timestamp, final_decision, vetoed_by, "
            "p_hat, is_entry) VALUES (?,?,?,?,?,?,?)",
            (rows.run_id, decision.trade_id, _iso(decision.timestamp), decision.final_decision,
             decision.vetoed_by, decision.p_hat, int(decision.is_entry)),
        )
        decision_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO decision_filters VALUES (?,?,?,?,?,?,?)",
            [(decision_id, f.position, f.filter_name, f.recommendation, int(f.veto), f.reason,
              f.pattern_name) for f in decision.filters],
        )


def _write_bars(connection: sqlite3.Connection, rows: RunRows, store: BarStore) -> None:
    """Insert the entry-window bars of every trade of one run."""
    for trade in rows.trades:
        connection.executemany(
            "INSERT INTO entry_bars VALUES (?,?,?,?,?,?,?,?)",
            [
                (rows.run_id, trade.trade_id, e.offset, _iso(e.bar.time), e.bar.open, e.bar.high,
                 e.bar.low, e.bar.close)
                for e in store.around(
                    rows.symbol, rows.bar_minutes, trade.entry_time, *rows.window
                )
            ],
        )


def write_run(
    connection: sqlite3.Connection, rows: RunRows, store: BarStore | None, mode: str = "full"
) -> None:
    """Upsert one run: delete its old rows, insert the new ones, in one transaction."""
    with connection:
        schema.delete_run(connection, rows.run_id)
        connection.execute("INSERT INTO runs VALUES (" + ",".join("?" * 21) + ")", rows.header)
        connection.executemany(
            "INSERT INTO run_parameters VALUES (?,?,?,?)",
            [(rows.run_id, *row) for row in rows.parameters],
        )
        connection.executemany(
            "INSERT INTO equity_samples VALUES (?,?,?,?)",
            [(rows.run_id, *row) for row in rows.equity],
        )
        connection.executemany(
            "INSERT INTO monthly_returns VALUES (?,?,?,?,?,?)",
            [(rows.run_id, *row) for row in rows.monthly],
        )
        _write_trades(connection, rows)
        _write_decisions(connection, rows, mode)
        if store is not None:
            _write_bars(connection, rows, store)


def _runs(request: BuildRequest) -> Iterator[tuple[RunsRoot, Path]]:
    """Every finished run directory of every root, with its root."""
    for root in request.roots:
        finished, _ = discover(root)
        for run_dir in finished:
            yield root, run_dir


def build_database(request: BuildRequest) -> BuildReport:
    """Ingest every finished run of every root into `request.out` (upsert per run).

    Raises what `discover`, `load_run_artifacts`, `derive_rows` and `BarStore` raise; the
    run being ingested is named in a prefixed message so the failing directory is clear.
    """
    if not request.roots:
        raise ValueError("at least one --runs-root is required")
    store = None
    if request.bars_root is not None:
        store = BarStore(request.bars_root, request.bars_before, request.bars_after)
    skipped: list[Path] = []
    for root in request.roots:
        skipped.extend(discover(root)[1])
    connection = schema.connect(request.out)
    ingested: list[str] = []
    try:
        for root, run_dir in _runs(request):
            rows = derive_rows(load_run_artifacts(run_dir), root.job)
            write_run(connection, rows, store, request.decisions)
            ingested.append(run_dir.name)
    finally:
        connection.close()
    return BuildReport(ingested=tuple(ingested), skipped=tuple(skipped), out=request.out)
