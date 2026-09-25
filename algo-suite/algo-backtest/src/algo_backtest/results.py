"""Parse a LEAN backtest's /Results directory into the minimal artifact Slice C needs.

LEAN writes several files to its results folder; the algorithm result JSON (e.g.
`main.json`, plus a `*-summary.json` and `*-order-events.json`) carries
`totalPerformance.closedTrades` — the list of completed round-trip trades. For now we
extract only what proves the run path worked: whether it succeeded and how many trades
closed. Richer metrics (Sharpe, drawdown, equity) are deliberately deferred to Slice E.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunResult:
    """The minimal outcome of one LEAN backtest run."""

    success: bool
    closed_trades: int
    raw_results_path: Path
    error: str | None = None


def parse_results(results_dir: Path, *, success: bool) -> RunResult:
    """Parse the LEAN result JSON in `results_dir` into a RunResult.

    `success` is the run-level outcome (the engine's exit status), supplied by the
    runner. The closed-trade count comes from `totalPerformance.closedTrades`. `error`
    surfaces LEAN's own `state.RuntimeError` (e.g. an algorithm-initialization failure
    such as an unknown brokerage adapter) so a CLI caller sees *why* a run failed
    without opening the raw result JSON themselves — previously only `success=False`
    was visible at the CLI, with the reason buried in `raw_results_path`.

    Raises:
        FileNotFoundError: if no result JSON exposing `totalPerformance.closedTrades`
            is present — the backtest produced nothing parseable (fail fast).
    """
    result_json = find_result_json(results_dir)
    data = json.loads(result_json.read_text())
    closed_trades = len(data["totalPerformance"]["closedTrades"])
    error = data.get("state", {}).get("RuntimeError") or None
    return RunResult(
        success=success, closed_trades=closed_trades, raw_results_path=result_json, error=error
    )


def _has_closed_trades(path: Path) -> bool:
    """Whether a JSON file exposes `totalPerformance.closedTrades` (the result file)."""
    try:
        data: Any = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return (
        isinstance(data, dict)
        and isinstance(data.get("totalPerformance"), dict)
        and "closedTrades" in data["totalPerformance"]
    )


def find_result_json(results_dir: Path) -> Path:
    """Locate the algorithm result JSON: the full file, not its derived siblings.

    LEAN writes the full result as `<algo>.json` plus `<algo>-summary.json` and
    `<algo>-order-events.json`; only the first two expose `totalPerformance.closedTrades`.
    Select the full file by excluding the `-summary`/`-order-events` siblings (a content
    distinction, not a name-length heuristic), and fail fast if the result is absent or
    ambiguous.
    """
    candidates = [p for p in results_dir.glob("*.json") if _has_closed_trades(p)]
    if not candidates:
        raise FileNotFoundError(
            f"no LEAN result JSON with totalPerformance.closedTrades in {results_dir}; "
            f"the backtest did not produce a parseable result (check the run logs)"
        )
    primary = [p for p in candidates if not _is_derived_sibling(p)]
    if len(primary) > 1:
        raise ValueError(
            f"ambiguous LEAN result: multiple primary result JSONs in {results_dir}: "
            f"{sorted(p.name for p in primary)}"
        )
    return primary[0] if primary else candidates[0]


def _is_derived_sibling(path: Path) -> bool:
    """Whether `path` is a derived result sibling (`*-summary`, `*-order-events`)."""
    return path.stem.endswith("-summary") or path.stem.endswith("-order-events")
