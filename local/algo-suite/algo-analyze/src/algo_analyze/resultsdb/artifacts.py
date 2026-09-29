"""Reading one run directory's artifacts for the results database.

Every reader fails fast naming the file and the directory: the database must never hold
a run whose numbers came from a guessed or half-read artifact. Required in every
finished run: `run.json`, `metrics.json`, `trades.json`, `equity.csv` (written by
`algo-backtest statement --run`), `main.json` (LEAN's result JSON, for the orders) and
`decisions.parquet`. `log.txt` (the engine log with the `<TAG>_PLAN|`, `_TRAIL|`,
`_OCO_CANCEL|`, `_STOP_RESIZE|` and `_MODEL_SHA256=` lines) is required as soon as the
ledger has a trade — exit kinds and trail moves are classified from it. Optional:
`trade-plans.json`, `strategy-config.yaml`, `strategy-provenance.json`, and `statement.md`,
read for the positions still open at the end of the run and the account summary (balance,
floating P/L, equity) that reconciles the realized ledger with the mark-to-market curve.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml

from algo_analyze.resultsdb.statement import StatementFacts, read_statement

RUN_FILE = "run.json"
METRICS_FILE = "metrics.json"
TRADES_FILE = "trades.json"
PLANS_FILE = "trade-plans.json"
EQUITY_FILE = "equity.csv"
CONFIG_FILE = "strategy-config.yaml"
PROVENANCE_FILE = "strategy-provenance.json"
DECISIONS_FILE = "decisions.parquet"
LOG_FILE = "log.txt"
STATEMENT_FILE = "statement.md"
REPORT_FILE = "report.html"
EQUITY_PNG_FILE = "equity.png"
EQUITY_COLUMNS = ("time", "equity", "drawdown_pct")
_METRIC_KEYS = ("total_return", "sharpe", "max_drawdown", "hit_rate")
_LOG_TAGS = ("PLAN", "TRAIL", "OCO_CANCEL", "STOP_RESIZE")
_LOG_LINE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) [A-Z0-9]+_(" + "|".join(_LOG_TAGS) + r")\|(.*)$"
)
_MODEL_LINE = re.compile(r"[A-Z0-9]+_MODEL_SHA256=([0-9a-f]{64})")


@dataclass(frozen=True)
class LogRecord:
    """One tagged engine-log line: its algorithm time, tag and `key=value` fields."""

    time: datetime
    tag: str
    fields: Mapping[str, str]


@dataclass(frozen=True)
class RunArtifacts:
    """Everything the builder reads from one run directory (optional ones are `None`)."""

    run_dir: Path
    run: Mapping[str, Any]
    metrics: Mapping[str, float | None]
    trades: list[Mapping[str, Any]]
    plans: list[Mapping[str, Any]] | None
    equity: list[tuple[str, float, float]]
    config: Mapping[str, Any] | None
    provenance: Mapping[str, str] | None
    orders: Mapping[str, Mapping[str, Any]]
    decisions: list[Mapping[str, Any]]
    log: list[LogRecord]
    model_sha256: str | None
    statement: StatementFacts


def missing_message(name: str, run_dir: Path, remedy: str) -> str:
    """The one wording every absent-artifact failure uses (tests assert it verbatim)."""
    return f"{name} is missing from {run_dir}; {remedy}"


def _require(path: Path, remedy: str) -> Path:
    """`path` when it is a file, else fail naming it."""
    if not path.is_file():
        raise FileNotFoundError(missing_message(path.name, path.parent, remedy))
    return path


def read_json(path: Path, kind: type, remedy: str) -> Any:
    """Parse a required JSON artifact, failing fast on absence, syntax or top-level shape."""
    _require(path, remedy)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path.name} in {path.parent} is not valid JSON ({exc})") from exc
    if not isinstance(document, kind):
        raise ValueError(
            f"{path.name} in {path.parent} must be a JSON {kind.__name__}, got "
            f"{type(document).__name__}"
        )
    return document


def field(document: Mapping[str, Any], key: str, path: Path) -> Any:
    """A required key of an artifact, failing fast with the file and key names."""
    if key not in document:
        raise ValueError(f"{path.name} in {path.parent} lacks key {key!r}")
    return document[key]


def _optional_json(path: Path, kind: type) -> Any | None:
    """An optional artifact: `None` when absent, fail fast when present but broken."""
    return read_json(path, kind, "") if path.is_file() else None


def _metrics(run_dir: Path) -> dict[str, float | None]:
    """`metrics.json`'s four headline figures (`None` only where the file says null)."""
    path = run_dir / METRICS_FILE
    document = read_json(path, dict, "the run has no metrics — re-run `algo-backtest run`")
    out: dict[str, float | None] = {}
    for key in _METRIC_KEYS:
        value = field(document, key, path)
        out[key] = None if value is None else float(value)
    return out


def _equity(run_dir: Path) -> list[tuple[str, float, float]]:
    """`equity.csv` rows as (ISO time, equity, drawdown %), checking the header."""
    path = _require(
        run_dir / EQUITY_FILE,
        f"regenerate it with `algo-backtest statement --run {run_dir}`",
    )
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or tuple(rows[0]) != EQUITY_COLUMNS:
        raise ValueError(
            f"{EQUITY_FILE} in {run_dir} must start with the header "
            f"{','.join(EQUITY_COLUMNS)}; regenerate it with `algo-backtest statement --run`"
        )
    try:
        samples = [(row[0], float(row[1]), float(row[2])) for row in rows[1:]]
    except (IndexError, ValueError) as exc:
        raise ValueError(f"{EQUITY_FILE} in {run_dir} has a malformed row ({exc})") from exc
    if not samples:
        raise ValueError(f"{EQUITY_FILE} in {run_dir} has no equity samples")
    return samples


def _config(run_dir: Path) -> Mapping[str, Any] | None:
    """The resolved strategy config (`strategy-config.yaml`), `None` for code strategies."""
    path = run_dir / CONFIG_FILE
    if not path.is_file():
        return None
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{CONFIG_FILE} in {run_dir} is not valid YAML ({exc})") from exc
    if not isinstance(document, Mapping):
        raise ValueError(f"{CONFIG_FILE} in {run_dir} must be a YAML mapping")
    return document


def _orders(run_dir: Path) -> Mapping[str, Mapping[str, Any]]:
    """LEAN's `orders` map (order id -> order) from `main.json`."""
    path = run_dir / "main.json"
    result = read_json(path, dict, "LEAN's result JSON is required for the orders")
    orders = field(result, "orders", path)
    if not isinstance(orders, Mapping):
        raise ValueError(f"main.json in {run_dir} key 'orders' must be a JSON object")
    return orders


def _decisions(run_dir: Path) -> list[Mapping[str, Any]]:
    """Every `decisions.parquet` row as a dict (filter_results nested as lists of dicts)."""
    path = _require(
        run_dir / DECISIONS_FILE,
        "the chain writes the audit trail at the end of a run — re-run it",
    )
    try:
        table = pq.read_table(path)  # type: ignore[no-untyped-call]  # pyarrow is untyped
    except Exception as exc:  # pyarrow raises ArrowInvalid/OSError; both mean "broken file"
        raise ValueError(f"{DECISIONS_FILE} in {run_dir} is not readable Parquet ({exc})") from exc
    rows: list[Mapping[str, Any]] = table.to_pylist()
    return rows


def parse_log_line(line: str) -> LogRecord | None:
    """A tagged engine-log line -> `LogRecord`; `None` for any other line."""
    match = _LOG_LINE.search(line.rstrip("\n"))
    if match is None:
        return None
    fields: dict[str, str] = {}
    for part in match.group(3).split("|"):
        key, sep, value = part.partition("=")
        if sep:
            fields[key] = value
    moment = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return LogRecord(time=moment, tag=match.group(2), fields=fields)


def _log(run_dir: Path, trades: int) -> tuple[list[LogRecord], str | None]:
    """The tagged records and the model hash of `log.txt` (required once trades exist)."""
    path = run_dir / LOG_FILE
    if not path.is_file():
        if trades:
            raise FileNotFoundError(
                missing_message(
                    LOG_FILE, run_dir,
                    f"trades.json lists {trades} closed trade(s) and exit kinds are "
                    "classified from the engine log",
                )
            )
        return [], None
    records: list[LogRecord] = []
    model: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        record = parse_log_line(line)
        if record is not None:
            records.append(record)
        hashed = _MODEL_LINE.search(line)
        if hashed is not None:
            model = hashed.group(1)
    return records, model


def load_run_artifacts(run_dir: Path) -> RunArtifacts:
    """Read every artifact of `run_dir` (see the module docstring for what is required).

    Raises:
        FileNotFoundError: a required artifact is absent (message names it).
        ValueError: an artifact is malformed (message names it and why).
    """
    run_path = run_dir / RUN_FILE
    run = read_json(run_path, dict, "not a finished run — `run.json` is written at the end")
    trades: list[Mapping[str, Any]] = read_json(
        run_dir / TRADES_FILE, list, "LEAN's closed-trade ledger is required"
    )
    log, model = _log(run_dir, len(trades))
    return RunArtifacts(
        statement=read_statement(run_dir, STATEMENT_FILE),
        run_dir=run_dir, run=run, metrics=_metrics(run_dir), trades=trades,
        plans=_optional_json(run_dir / PLANS_FILE, list), equity=_equity(run_dir),
        config=_config(run_dir), provenance=_optional_json(run_dir / PROVENANCE_FILE, dict),
        orders=_orders(run_dir), decisions=_decisions(run_dir), log=log, model_sha256=model,
    )
