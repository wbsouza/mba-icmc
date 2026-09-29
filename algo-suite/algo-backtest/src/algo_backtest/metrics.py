"""Extract the first Chapter-4 metrics from a LEAN run result (Slice E2).

LEAN already computes the headline statistics; we extract the four the thesis cites
from `totalPerformance.portfolioStatistics` (typed floats — no string parsing), so the
first Chapter-4 number is read deterministically from a run's raw artifacts rather than
re-implemented. Richer analytics (CPCV, deflated Sharpe, equity curves) are later work.

Schema coupling: the field names below are the pinned engine's contract
(`quantconnect/lean:17748`, `totalPerformance.portfolioStatistics`); a different image
may rename them. `total_return` is a **fraction** (LEAN's `totalNetProfit`, e.g. 0.002 =
0.2% over the window); `hit_rate` is `winRate` in [0, 1]; `max_drawdown` is a fraction.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Metrics:
    """The first Chapter-4 metric set for one run."""

    total_return: float
    sharpe: float
    max_drawdown: float
    hit_rate: float

    def as_dict(self) -> dict[str, float]:
        """The metrics as a plain dict (for JSON / display)."""
        return asdict(self)


def extract_metrics(result_json: Path) -> Metrics:
    """Read the four headline metrics from a LEAN result JSON file (one-off / CLI path)."""
    return metrics_from_results(json.loads(result_json.read_text()), source=result_json)


def metrics_from_results(results: dict[str, Any], *, source: Path | None = None) -> Metrics:
    """Extract the four metrics from an already-parsed LEAN result document.

    Separating the file read (`extract_metrics`) from extraction lets the run path parse
    LEAN's large result JSON once and derive both the trade ledger and these metrics from
    the same in-memory document — the backtest sweep is performance-critical, so the hot
    path must not re-read it.

    Args:
        source: the originating file, used only to make the failure message actionable.

    Raises:
        ValueError: if the result lacks complete portfolio statistics — fail fast with a
            remediation hint, since a citable metric must come from a finished backtest
            (a partial/aborted run has no statistics block).
    """
    try:
        stats = results["totalPerformance"]["portfolioStatistics"]
        return Metrics(
            total_return=float(stats["totalNetProfit"]),
            sharpe=float(stats["sharpeRatio"]),
            max_drawdown=float(stats["drawdown"]),
            hit_rate=float(stats["winRate"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        where = str(source) if source is not None else "the LEAN result"
        raise ValueError(
            f"{where} has no complete portfolioStatistics ({exc}); the backtest may not "
            "have finished — re-run it and confirm the engine exited successfully"
        ) from exc


def metrics_from_artifact(metrics_json: Path) -> Metrics:
    """Load the persisted metrics.json artifact, failing fast on a malformed file.

    The `metrics --run` path reads this artifact directly, so a truncated/invalid file or
    a wrong shape must surface as an actionable error — not a raw traceback — exactly like
    extraction from the LEAN result does.

    Raises:
        ValueError: if the file is not valid JSON or lacks the four numeric metric fields.
    """
    try:
        data = json.loads(metrics_json.read_text())
        return Metrics(
            total_return=float(data["total_return"]),
            sharpe=float(data["sharpe"]),
            max_drawdown=float(data["max_drawdown"]),
            hit_rate=float(data["hit_rate"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"{metrics_json} is not a valid metrics artifact ({exc}); re-run the backtest "
            "to regenerate it"
        ) from exc
