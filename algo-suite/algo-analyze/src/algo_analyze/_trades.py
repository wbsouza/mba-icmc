"""Shared reader for a run's fractional per-trade returns (`trades.json`).

Promoted out of `figures.py` because `cli.py`'s `metrics`/`significance` commands need the
same per-trade return series that `figures.py` already reads for the equity/drawdown
curves — one reader, reused, instead of two copies drifting apart.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_RETURN_FIELD = "return"


def trade_returns(run_dir: Path) -> list[float]:
    """Read fractional trade returns from ``run_dir / 'trades.json'``."""
    path = run_dir / "trades.json"
    if not path.is_file():
        raise FileNotFoundError(f"run {run_dir.name!r} has no trades artifact: {path}")
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON") from exc
    if not isinstance(document, list):
        raise ValueError(f"{path} must contain a list of closed trades")
    if not document:
        return []
    return [_trade_return(path, index, trade) for index, trade in enumerate(document)]


def _trade_return(path: Path, index: int, trade: Any) -> float:
    """Extract one finite fractional return from a closed-trade mapping."""
    if not isinstance(trade, Mapping):
        raise ValueError(f"{path} trade {index} is not an object")
    if _RETURN_FIELD not in trade:
        known = ", ".join(str(key) for key in trade)
        raise ValueError(
            f"{path} trade {index} has no fractional return field; known fields: {known}"
        )
    value = trade[_RETURN_FIELD]
    if value is None:
        raise ValueError(f"{path} trade {index} return {_RETURN_FIELD!r} is null")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{path} trade {index} return {_RETURN_FIELD!r} is not a number: {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise ValueError(f"{path} trade {index} return {_RETURN_FIELD!r} is not finite")
    if number < -1.0:
        raise ValueError(
            f"{path} trade {index} return {_RETURN_FIELD!r} is below -100% ({number}), "
            "which is not a valid trade return"
        )
    return number
