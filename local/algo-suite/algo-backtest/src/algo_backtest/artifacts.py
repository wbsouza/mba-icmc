"""Persist stable raw artifacts from a backtest run (Slices E1 + E2).

After a run, the LEAN result JSON already sits in the results dir; alongside it we
persist three small, stable files so a result is self-describing and re-analyzable later
without re-running the engine:

  run.json     — the run manifest (strategy, symbol, window, params, success, trades)
  trades.json  — the closed-trade ledger (LEAN's totalPerformance.closedTrades), each
                 trade augmented with a normalized fractional `return` field (Spec 05f)
  metrics.json — the four Chapter-4 metrics (see metrics.py)

Chain-driven runs additionally snapshot the resolved strategy configuration at
initialization (`write_strategy_config`): `strategy-config.json` and, since story 12,
`strategy-config.yaml` — the same mapping in the form a strategy `config.yaml` takes.

This layer is pure persistence: the caller parses LEAN's (large) result JSON once and
passes the derived ledger + metrics in, so a backtest sweep never re-reads it here.

Deliberately minimal local JSON — not the final trades.parquet schema (that, and richer
analytics, are later work). The point is a durable, parseable record of one run.

Normalized return contract (Spec 05f): consumers such as `algo_analyze.figures` need a
finite fractional per-trade return, not LEAN's raw dollar `profitLoss`. When a closed
trade carries `entryPrice`, `quantity` and `profitLoss`, this module adds a `return`
field computed as `profitLoss / abs(entryPrice * quantity)` — the trade's profit or loss
against its own cost basis. The other raw LEAN fields are preserved unchanged alongside
it. If a trade lacks enough data (or the computed value is not finite), the reserved
`return` field is omitted rather than guessed, even when the raw payload carried a
stray `return`; downstream consumers fail fast on the missing field instead of silently
trusting an absolute PnL value or an unverified raw value as if it were normalized here.

This per-trade `return` is deliberately a different figure from `metrics.json`'s
`total_return` (LEAN's portfolio-level `totalNetProfit`, see `metrics.py`): `return` is
each trade's profit/loss against its own cost basis, while `total_return` reflects the
run's actual account-level compounding and position sizing. The two are not expected to
reconcile numerically — `total_return` is the citable headline metric; `return` exists
for trade-sequence visualization (see `algo_analyze.figures`), not as an alternative
computation of it.

Completeness convention: `metrics.json` is written last, so its presence marks a finished
run whose metrics are citable. Each file is written atomically (`write_text_atomic`), so no
individual artifact is ever half-written; a killed run leaves an obviously-incomplete dir
rather than a corrupt one.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from algo_core.atomicio import write_text_atomic

from algo_backtest.metrics import Metrics
from algo_backtest.strategies import StrategyChainConfig, resolved_yaml


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
    # Config-selected fill/fee/spread model; recorded into inference-inputs.json as the
    # cost convention so a paired comparison can prove both arms shared it. Required:
    # an unknown cost model must never be silently labeled.
    broker_adapter: str


@dataclass(frozen=True)
class Artifacts:
    """Paths to the persisted raw artifacts."""

    run_json: Path
    trades_json: Path
    metrics_json: Path
    inference_inputs_json: Path


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

    inference_path = results_dir / "inference-inputs.json"
    inference = {
        "source": "main.json",
        "frequency": "calendar-day",
        "timezone": "UTC",
        "annualization": 365,
        "risk_free_daily": 0,
        "costs": f"brokerage:{manifest.broker_adapter}",
        "symbol": manifest.symbol,
        "start": manifest.start,
        "end": (date.fromisoformat(manifest.end) + timedelta(days=1)).isoformat(),
    }
    write_text_atomic(inference_path, json.dumps(inference, indent=2))
    manifest_doc = asdict(manifest)
    manifest_doc["inference_inputs_sha256"] = hashlib.sha256(
        inference_path.read_bytes()
    ).hexdigest()
    write_text_atomic(run_path, json.dumps(manifest_doc, indent=2))

    metrics_path = results_dir / "metrics.json"
    write_text_atomic(metrics_path, json.dumps(metrics.as_dict(), indent=2))

    return Artifacts(
        run_json=run_path, trades_json=trades_path, metrics_json=metrics_path,
        inference_inputs_json=inference_path,
    )


def _normalize_trade(trade: dict[str, Any]) -> dict[str, Any]:
    """Add a normalized fractional `return` field to one raw LEAN closed-trade dict.

    Computes `profitLoss / abs(entryPrice * quantity)` when `entryPrice`, `quantity`
    and `profitLoss` are all present and numeric, the cost basis is non-zero, and the
    result is finite — always from those raw fields, even when the trade already
    carries a `return` key, since `return` is this module's own normalized output and
    must never be trusted as pre-computed input. Otherwise the trade is returned with
    any pre-existing `return` key stripped rather than guessed: we never fabricate a
    return from an absolute PnL value alone, so a trade shape we can't normalize is
    left as LEAN reported it (minus a stray `return` we can't vouch for) and
    downstream consumers fail fast on the missing field instead of trusting one that
    was never actually computed here.
    """
    without_return = {key: value for key, value in trade.items() if key != "return"}
    try:
        entry_price = float(trade["entryPrice"])
        quantity = float(trade["quantity"])
        profit_loss = float(trade["profitLoss"])
    except (KeyError, TypeError, ValueError):
        return without_return
    cost_basis = abs(entry_price * quantity)
    if cost_basis == 0.0:
        return without_return
    fractional_return = profit_loss / cost_basis
    if not math.isfinite(fractional_return):
        return without_return
    return {**without_return, "return": fractional_return}


def write_strategy_config(results_dir: Path, config: StrategyChainConfig) -> None:
    """Atomically snapshot resolved config.raw before a chain run starts, twice from the
    same mapping: `strategy-config.json` (read by the QA and provenance tooling) and
    `strategy-config.yaml` (story 12; the form a `strategies/<name>/config.yaml` takes, so
    a run's exact parameters can seed a new variant). The JSON check runs first, so a value
    JSON rejects never reaches either file.

    Raises:
        ValueError: configuration includes unsupported or non-finite JSON values.
        OSError: the filesystem cannot atomically publish an artifact.
    """
    try:
        text = json.dumps(dict(config.raw), indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"strategy {config.name!r} cannot be recorded as JSON; use JSON-safe finite "
            "values in its config.yaml"
        ) from exc
    write_text_atomic(results_dir / "strategy-config.json", text)
    write_text_atomic(results_dir / "strategy-config.yaml", resolved_yaml(config))
