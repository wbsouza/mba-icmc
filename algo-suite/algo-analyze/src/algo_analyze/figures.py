"""Render vector PDF figures from algo-analyze run artifacts."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from algo_analyze._style import ACCENT, DANGER, FIGURE_SIZE, PRIMARY, plt, thesis_style

_RETURN_COLUMNS = ("return", "returns", "trade_return", "realized_return")
_PNL_COLUMNS = ("realized_pnl", "pnl", "profit_loss", "net_profit")


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


def ablation_bars_figure(rows: Iterable[Any], out: Path) -> Path:
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
    fig.savefig(out, format="pdf")
    plt.close(fig)


def _trade_returns(run_dir: Path) -> list[float]:
    """Read trade returns from ``run_dir / 'trades.parquet'``."""
    path = run_dir / "trades.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"run {run_dir.name!r} has no trades artifact: {path}")
    table = pq.read_table(path)  # type: ignore[no-untyped-call]
    if table.num_rows == 0:
        return []
    columns = table.to_pydict()
    for name in _RETURN_COLUMNS:
        if name in columns:
            return _finite_values(name, columns[name])
    for name in _PNL_COLUMNS:
        if name in columns:
            return _finite_values(name, columns[name])
    known = ", ".join(table.column_names)
    raise ValueError(f"{path} has no return or PnL column; known columns: {known}")


def _finite_values(name: str, values: Sequence[Any]) -> list[float]:
    """Return finite float values from a Parquet column, rejecting nulls and NaNs."""
    result: list[float] = []
    for value in values:
        if value is None:
            raise ValueError(f"trade column {name!r} contains null values")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"trade column {name!r} contains non-finite values")
        result.append(number)
    return result


def _equity_curve(returns: Sequence[float]) -> list[float]:
    """Convert per-trade returns into an equity multiple curve starting at 1.0."""
    equity = [1.0]
    current = 1.0
    for value in returns:
        current *= 1.0 + value
        equity.append(current)
    return equity


def _drawdown_curve(equity: Sequence[float]) -> list[float]:
    """Convert an equity curve into fractional drawdown from the running peak."""
    peak = equity[0] if equity else 1.0
    drawdown: list[float] = []
    for value in equity:
        peak = max(peak, value)
        drawdown.append((value / peak) - 1.0 if peak else 0.0)
    return drawdown


def _ablation_values(rows: Iterable[Any]) -> tuple[list[str], list[float]]:
    """Extract labels and total-return deltas from row objects or mappings."""
    labels: list[str] = []
    deltas: list[float] = []
    for row in rows:
        labels.append(str(_field(row, "run_id")))
        delta = float(_field(row, "delta_total_return"))
        if not math.isfinite(delta):
            raise ValueError("ablation delta_total_return values must be finite")
        deltas.append(delta)
    if not labels:
        raise ValueError("at least one ablation row is required")
    return labels, deltas


def _field(row: Any, name: str) -> Any:
    """Read ``name`` from a dataclass-like row or mapping."""
    if isinstance(row, Mapping):
        return row[name]
    return getattr(row, name)
