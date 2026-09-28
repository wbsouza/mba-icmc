"""The results database schema (version 1) and its connection helper.

Every table carries `run_id` (the run directory's name, e.g. `20260928T022009-934c0d9e00bf`)
so a re-ingest can replace one run atomically: `delete_run()` removes its rows from every
table, then the builder inserts the fresh ones in the same transaction.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

EXIT_KINDS: tuple[str, ...] = (
    "stop", "target", "trail_stop", "liquidation", "reversal", "unknown",
)

# Tables that hold per-run rows, in the order a run is deleted (children first).
RUN_TABLES: tuple[str, ...] = (
    "decision_filters", "decisions", "decision_summary", "entry_bars", "trail_moves",
    "trade_plans", "trades", "monthly_returns", "equity_samples", "run_parameters", "runs",
)

_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    job TEXT NOT NULL,
    run_dir TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    cash REAL,
    bar_minutes INTEGER NOT NULL,
    model_sha256 TEXT,
    code_revision TEXT,
    success INTEGER NOT NULL,
    closed_trades INTEGER NOT NULL,
    total_return REAL NOT NULL,
    sharpe REAL,
    max_drawdown REAL NOT NULL,
    hit_rate REAL,
    statement_path TEXT,
    report_path TEXT,
    equity_png_path TEXT,
    ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS run_parameters (
    run_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (run_id, key)
);
CREATE TABLE IF NOT EXISTS equity_samples (
    run_id TEXT NOT NULL,
    time TEXT NOT NULL,
    equity REAL NOT NULL,
    drawdown_pct REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS equity_samples_run ON equity_samples (run_id);
CREATE TABLE IF NOT EXISTS monthly_returns (
    run_id TEXT NOT NULL,
    month TEXT NOT NULL,
    start_equity REAL NOT NULL,
    end_equity REAL NOT NULL,
    return_pct REAL NOT NULL,
    trades INTEGER NOT NULL,
    PRIMARY KEY (run_id, month)
);
CREATE TABLE IF NOT EXISTS trades (
    run_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    entry_order_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    lots REAL,
    quantity REAL NOT NULL,
    entry_time TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_time TEXT NOT NULL,
    exit_price REAL NOT NULL,
    profit REAL NOT NULL,
    fees REAL NOT NULL,
    is_win INTEGER NOT NULL,
    exit_kind TEXT NOT NULL,
    exit_order_id INTEGER,
    exit_order_type TEXT,
    holding_minutes REAL NOT NULL,
    PRIMARY KEY (run_id, trade_id)
);
CREATE TABLE IF NOT EXISTS trade_plans (
    run_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    stop_loss REAL NOT NULL,
    stop_pips REAL,
    targets_json TEXT NOT NULL,
    trail_steps_json TEXT NOT NULL,
    spread_pips REAL,
    PRIMARY KEY (run_id, trade_id)
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trade_id TEXT,
    timestamp TEXT NOT NULL,
    final_decision TEXT NOT NULL,
    vetoed_by TEXT,
    p_hat REAL,
    is_entry INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS decisions_run ON decisions (run_id);
CREATE INDEX IF NOT EXISTS decisions_trade ON decisions (run_id, trade_id);
CREATE TABLE IF NOT EXISTS decision_filters (
    decision_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    filter_name TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    veto INTEGER NOT NULL,
    reason TEXT NOT NULL,
    pattern_name TEXT,
    PRIMARY KEY (decision_id, position)
);
CREATE TABLE IF NOT EXISTS decision_summary (
    run_id TEXT NOT NULL,
    final_decision TEXT NOT NULL,
    vetoed_by TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (run_id, final_decision, vetoed_by)
);
CREATE TABLE IF NOT EXISTS trail_moves (
    run_id TEXT NOT NULL,
    trade_id TEXT,
    time TEXT NOT NULL,
    from_stop REAL NOT NULL,
    to_stop REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS trail_moves_trade ON trail_moves (run_id, trade_id);
CREATE TABLE IF NOT EXISTS entry_bars (
    run_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    offset INTEGER NOT NULL,
    time TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    PRIMARY KEY (run_id, trade_id, offset)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the results database and make sure its schema is current.

    Raises:
        ValueError: the file already holds a different schema version — rebuild it into
            a new file rather than mixing versions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(_DDL)
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_version")]
    if not versions:
        connection.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        connection.commit()
    elif versions != [SCHEMA_VERSION]:
        connection.close()
        raise ValueError(
            f"{path} holds results-db schema version {versions}, this build writes version "
            f"{SCHEMA_VERSION}; point --out at a new file (or delete the old one) to rebuild"
        )
    return connection


def delete_run(connection: sqlite3.Connection, run_id: str) -> None:
    """Remove every row of one run from every table (the upsert's first half)."""
    connection.execute(
        "DELETE FROM decision_filters WHERE decision_id IN "
        "(SELECT id FROM decisions WHERE run_id = ?)",
        (run_id,),
    )
    for table in RUN_TABLES[1:]:
        connection.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))  # noqa: S608
