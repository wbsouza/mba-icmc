"""Persist stable raw artifacts from a backtest run (Slices E1 + E2).

After a run, the LEAN result JSON already sits in the results dir; alongside it we
persist three small, stable files so a result is self-describing and re-analyzable later
without re-running the engine:

  run.json     — the run manifest (strategy, symbol, window, params, success, trades)
  trades.json  — the closed-trade ledger (LEAN's totalPerformance.closedTrades), each
                 trade augmented with a normalized fractional `return` field (Spec 05f)
  metrics.json — the four Chapter-4 metrics (see metrics.py)

This layer is pure persistence: the caller parses LEAN's (large) result JSON once and
passes the derived ledger + metrics in, so a backtest sweep never re-reads it here.

Deliberately minimal local JSON — not the final trades.parquet schema (that, and richer
analytics, are later work). The point is a durable, parseable record of one run.

Normalized return contract (Spec 05f): consumers such as `algo_analyze.figures` need a
finite fractional per-trade return, not LEAN's raw dollar `profitLoss`. When a closed
trade carries `entryPrice`, `quantity` and `profitLoss`, this module adds a `return`
field computed as `profitLoss / abs(entryPrice * quantity)` — the trade's profit or loss
against its own cost basis. The raw LEAN fields are preserved unchanged alongside it.
When a trade lacks enough data (or the computed value is not finite), no `return` field
is added rather than guessing — the trade is left exactly as LEAN reported it, and
downstream consumers fail fast on the missing field instead of silently trusting an
absolute PnL value as if it were a return.

Completeness convention: `metrics.json` is written last, so its presence marks a finished
run whose metrics are citable. Each file is written atomically (`write_text_atomic`), so no
individual artifact is ever half-written; a killed run leaves an obviously-incomplete dir
rather than a corrupt one.
"""

from __future__ import annotations

import json
import math
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
    is written last as the run's completeness marker (see module docstring). Each trade is
    augmented with a normalized fractional `return` field where the raw payload supports
    computing one (see `_normalize_trade`).
    """
    run_path = results_dir / "run.json"
    write_text_atomic(run_path, json.dumps(asdict(manifest), indent=2))

    normalized_trades = [_normalize_trade(trade) for trade in closed_trades]
    trades_path = results_dir / "trades.json"
    write_text_atomic(trades_path, json.dumps(normalized_trades, indent=2))

    metrics_path = results_dir / "metrics.json"
    write_text_atomic(metrics_path, json.dumps(metrics.as_dict(), indent=2))

    return Artifacts(run_json=run_path, trades_json=trades_path, metrics_json=metrics_path)


def _normalize_trade(trade: dict[str, Any]) -> dict[str, Any]:
    """Add a normalized fractional `return` field to one raw LEAN closed-trade dict.

    Computes `profitLoss / abs(entryPrice * quantity)` when `entryPrice`, `quantity`
    and `profitLoss` are all present and numeric, the cost basis is non-zero, and the
    result is finite — always from those raw fields, even when the trade already
    carries a `return` key, since `return` is this module's own normalized output and
    must never be trusted as pre-computed input. Otherwise the trade is returned
    unchanged: we never guess a return from an absolute PnL value alone, so a trade
    shape we can't normalize is left exactly as LEAN reported it and downstream
    consumers fail fast on the missing field instead of trusting a fabricated one.
    """
    try:
        entry_price = float(trade["entryPrice"])
        quantity = float(trade["quantity"])
        profit_loss = float(trade["profitLoss"])
    except (KeyError, TypeError, ValueError):
        return dict(trade)
    cost_basis = abs(entry_price * quantity)
    if cost_basis == 0.0:
        return dict(trade)
    fractional_return = profit_loss / cost_basis
    if not math.isfinite(fractional_return):
        return dict(trade)
    return {**trade, "return": fractional_return}
