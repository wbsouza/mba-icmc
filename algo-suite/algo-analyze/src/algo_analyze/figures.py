"""Render vector PDF figures from algo-analyze run artifacts."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from algo_analyze._style import ACCENT, DANGER, FIGURE_SIZE, PRIMARY, plt, thesis_style
from algo_analyze.ablation import AblationRow

_RETURN_FIELD = "return"


def equity_curve_figure(run_dir: Path, out: Path) -> Path:
    """Render a vector PDF equity curve for one run directory."""
    returns = _trade_returns(run_dir)
    equity = _equity_curve(returns)
    points = list(range(len(equity)))

    with thesis_style():
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        ax.plot(points, equity, color=PRIMARY, linewidth=1.8)
        ax.axhline(1.0, color="#666666", linewidth=0.8)
        ax.set_title("Equity curve")
        ax.set_xlabel("Closed trade")
        ax.set_ylabel("Equity multiple")
        ax.set_xlim(0, max(1, len(equity) - 1))
        _save_pdf(fig, out)
    return out


def drawdown_curve_figure(run_dir: Path, out: Path) -> Path:
    """Render a vector PDF drawdown curve for one run directory."""
    equity = _equity_curve(_trade_returns(run_dir))
    drawdown = _drawdown_curve(equity)
    points = list(range(len(drawdown)))

    with thesis_style():
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        ax.fill_between(points, drawdown, 0.0, color=DANGER, alpha=0.28)
        ax.plot(points, drawdown, color=DANGER, linewidth=1.4)
        ax.axhline(0.0, color="#666666", linewidth=0.8)
        ax.set_title("Drawdown")
        ax.set_xlabel("Closed trade")
        ax.set_ylabel("Drawdown")
        ax.set_xlim(0, max(1, len(drawdown) - 1))
        _save_pdf(fig, out)
    return out


def ablation_bars_figure(rows: Sequence[AblationRow], out: Path) -> Path:
    """Render a vector PDF bar chart from ablation rows."""
    labels, deltas = _ablation_values(rows)

    with thesis_style():
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        colors = [ACCENT if value >= 0 else DANGER for value in deltas]
        ax.bar(labels, deltas, color=colors, width=0.62)
        ax.axhline(0.0, color="#666666", linewidth=0.8)
        ax.set_title("Ablation contribution")
        ax.set_xlabel("Run")
        ax.set_ylabel("Delta total return")
        ax.tick_params(axis="x", rotation=20)
        _save_pdf(fig, out)
    return out


def _save_pdf(fig: Any, out: Path) -> None:
    """Persist ``fig`` as a vector PDF and close it promptly."""
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.savefig(out, format="pdf")
    finally:
        plt.close(fig)


def _trade_returns(run_dir: Path) -> list[float]:
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
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path} trade {index} return {_RETURN_FIELD!r} is not finite")
    if number < -1.0:
        raise ValueError(
            f"{path} trade {index} return {_RETURN_FIELD!r} is below -100% ({number}), "
            "which is not a valid trade return"
        )
    return number


def _equity_curve(returns: Sequence[float]) -> list[float]:
    """Convert per-trade returns into an equity multiple curve starting at 1.0."""
    equity = [1.0]
    current = 1.0
    for value in returns:
        current *= 1.0 + value
        equity.append(current)
    return equity


def _drawdown_curve(equity: Sequence[float]) -> list[float]:
    """Convert an equity curve into fractional drawdown from the running peak.

    ``peak`` starts at ``equity[0]`` (1.0 for a non-empty curve, since
    ``_equity_curve`` always seeds it there) and only ever grows via ``max``, so it is
    never zero for a non-empty curve; the division below is always safe.
    """
    peak = equity[0] if equity else 1.0
    drawdown: list[float] = []
    for value in equity:
        peak = max(peak, value)
        drawdown.append((value / peak) - 1.0)
    return drawdown


def _ablation_values(rows: Sequence[AblationRow]) -> tuple[list[str], list[float]]:
    """Extract labels and total-return deltas from ablation rows."""
    labels: list[str] = []
    deltas: list[float] = []
    for row in rows:
        labels.append(row.run_id)
        if not math.isfinite(row.delta_total_return):
            raise ValueError("ablation delta_total_return values must be finite")
        deltas.append(row.delta_total_return)
    if not labels:
        raise ValueError("at least one ablation row is required")
    return labels, deltas
