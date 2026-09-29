"""Persist stable raw artifacts from a backtest run (Slices E1 + E2).

After a run, the LEAN result JSON already sits in the results dir; alongside it we
persist three small, stable files so a result is self-describing and re-analyzable later
without re-running the engine:

  run.json     — the run manifest (strategy, symbol, window, params, success, trades)
  trades.json  — the closed-trade ledger (LEAN's totalPerformance.closedTrades)
  metrics.json — the four Chapter-4 metrics (see metrics.py)

This layer is pure persistence: the caller parses LEAN's (large) result JSON once and
passes the derived ledger + metrics in, so a backtest sweep never re-reads it here.

Deliberately minimal local JSON — not the final trades.parquet schema (that, and richer
analytics, are later work). The point is a durable, parseable record of one run.

Completeness convention: `metrics.json` is written last, so its presence marks a finished
run whose metrics are citable. Each file is written atomically (`write_text_atomic`), so no
individual artifact is ever half-written; a killed run leaves an obviously-incomplete dir
rather than a corrupt one.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from algo_core.atomicio import write_text_atomic

from algo_backtest.metrics import Metrics


@dataclass(frozen=True)
class RunManifest:
    """Identifying metadata for one backtest run (params are strategy-specific)."""

    strategy: str
    symbol: str
    start: str  # ISO date (YYYY-MM-DD)
    end: str
    params: dict[str, str]
    success: bool
    closed_trades: int


@dataclass(frozen=True)
class Artifacts:
    """Paths to the persisted raw artifacts."""

    run_json: Path
    trades_json: Path
    metrics_json: Path


def write_run_artifacts(
    results_dir: Path,
    manifest: RunManifest,
    closed_trades: list[dict[str, Any]],
    metrics: Metrics,
) -> Artifacts:
    """Write run.json (manifest), trades.json (ledger) and metrics.json into results_dir.

    Pure persistence: `closed_trades` (LEAN's `totalPerformance.closedTrades`) and
    `metrics` are derived by the caller from a single parse of the result JSON. metrics.json
    is written last as the run's completeness marker (see module docstring).
    """
    run_path = results_dir / "run.json"
    write_text_atomic(run_path, json.dumps(asdict(manifest), indent=2))

    trades_path = results_dir / "trades.json"
    write_text_atomic(trades_path, json.dumps(closed_trades, indent=2))

    metrics_path = results_dir / "metrics.json"
    write_text_atomic(metrics_path, json.dumps(metrics.as_dict(), indent=2))

    return Artifacts(run_json=run_path, trades_json=trades_path, metrics_json=metrics_path)
