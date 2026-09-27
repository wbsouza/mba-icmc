"""Strict UTC calendar-day portfolio returns from LEAN's marked-to-market equity."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from algo_analyze.deflated import InferenceUnavailable


@dataclass(frozen=True)
class PortfolioReturns:
    """A common calendar grid plus auditable source and return-convention metadata."""

    timestamps: tuple[int, ...]
    returns: tuple[float, ...]
    metadata: dict[str, Any]


def read_json(path: Path) -> Any:
    """Read a JSON artifact and translate malformed JSON to a diagnostic."""
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def read_object(path: Path) -> dict[str, Any]:
    """Read a JSON artifact that must be an object."""
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def source_hash(path: Path) -> str:
    """Hash exact source bytes for reproducible analysis provenance."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contract(run_dir: Path) -> dict[str, Any]:
    """Require explicit experiment conventions rather than infer costs or missing sessions."""
    path = run_dir / "inference-inputs.json"
    if not path.exists():
        raise InferenceUnavailable(f"missing {path.name}; declare equity coverage and conventions")
    data = read_object(path)
    fixed = {
        "frequency": "calendar-day",
        "timezone": "UTC",
        "annualization": 365,
        "risk_free_daily": 0,
        "source": "main.json",
    }
    if any(data.get(key) != value for key, value in fixed.items()):
        raise ValueError("require main.json, calendar-day UTC, annualization365, risk_free_daily0")
    for key in ("costs", "symbol", "start", "end"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"inference-inputs requires nonempty {key}")
    _match_manifest(run_dir, data)
    return data


def _match_manifest(run_dir: Path, data: dict[str, Any]) -> None:
    """Verify declared coverage against the successful engine run manifest."""
    manifest = read_object(run_dir / "run.json")
    if manifest.get("success") is not True:
        raise ValueError("portfolio inference requires a successful run manifest")
    if not all(isinstance(manifest.get(key), str) for key in ("start", "end", "symbol")):
        raise ValueError("run manifest requires string start, end, symbol")
    expected_end = (date.fromisoformat(manifest["end"]) + timedelta(days=1)).isoformat()
    if (data["symbol"], data["start"], data["end"]) != (
        manifest["symbol"],
        manifest["start"],
        expected_end,
    ):
        raise ValueError("inference coverage must match run symbol and full inclusive run dates")


def _point(row: Any) -> tuple[int, float]:
    """Read LEAN line [epoch,value] or candle [epoch,open,high,low,close] points.

    LEAN's ``SampleEquity(time)`` documents ``time`` as the candlestick END time and
    builds the bar from every equity update since the previous sample, so the close
    is the portfolio mark at the timestamp. A scheduled "Daily Sampling" event fires
    at midnight, which is why every backtest carries an exact midnight close.
    """
    if not isinstance(row, list) or len(row) not in (2, 5):
        raise ValueError("equity points require [epoch,value] or [epoch,open,high,low,close]")
    timestamp, value = row[0], row[-1]
    if type(timestamp) is not int:
        raise ValueError("equity timestamp must be integer Unix seconds")
    if type(value) not in (int, float):
        raise ValueError("equity values must be numeric")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("equity values must be finite and positive")
    return timestamp, float(value)


def _equity(path: Path) -> tuple[dict[int, float], dict[int, float]]:
    """Read engine equity and, when exported, LEAN's own daily Return series (percent)."""
    if not path.exists():
        raise InferenceUnavailable("missing main.json engine portfolio equity; rerun simulation")
    data = read_object(path)
    try:
        series = data["charts"]["Strategy Equity"]["series"]
        values = series["Equity"]["values"]
    except (KeyError, TypeError) as exc:
        raise InferenceUnavailable("main.json lacks Strategy Equity/Equity values") from exc
    if not isinstance(values, list):
        raise ValueError("engine equity values must be a list")
    points = [_point(row) for row in values]
    timestamps = [point[0] for point in points]
    if timestamps != sorted(set(timestamps)):
        raise ValueError("engine equity timestamps must be ordered and unique")
    return dict(points), _daily_performance(series)


def _daily_performance(series: Any) -> dict[int, float]:
    """Read LEAN's ``Return`` series (daily performance, percent) when the export has one."""
    values = series.get("Return", {}).get("values", []) if isinstance(series, dict) else []
    return dict(_performance_point(row) for row in values)


def _performance_point(row: Any) -> tuple[int, float]:
    """Read one ``[epoch, percent]`` daily-performance point."""
    if not isinstance(row, list) or len(row) != 2 or type(row[0]) is not int:
        raise ValueError("engine Return points require [epoch,percent]")
    if type(row[1]) not in (int, float) or not math.isfinite(row[1]):
        raise ValueError("engine Return points require [epoch,percent]")
    return row[0], float(row[1])


def load_portfolio_returns(run_dir: Path) -> PortfolioReturns:
    """Select exact UTC midnight endpoints; missing days are never imputed or dropped."""
    metadata = _contract(run_dir)
    grid = _daily_grid(metadata)
    equity, performance = _equity(run_dir / "main.json")
    returns = _daily_returns(grid, equity)
    _check_engine_performance(grid[1:], returns, performance)
    metadata = {
        **metadata,
        "source_sha256": source_hash(run_dir / "main.json"),
        "contract_sha256": source_hash(run_dir / "inference-inputs.json"),
        "manifest_sha256": source_hash(run_dir / "run.json"),
        "n_observations": len(returns),
        "equity_basis": "engine portfolio mark-to-market",
    }
    return PortfolioReturns(grid[1:], returns, metadata)


def _daily_grid(metadata: dict[str, Any]) -> tuple[int, ...]:
    """Build the full declared UTC endpoint grid, including flat weekend periods."""
    start, end = date.fromisoformat(metadata["start"]), date.fromisoformat(metadata["end"])
    if end <= start:
        raise ValueError("inference coverage end must be after start")
    grid = tuple(
        int(datetime.combine(start + timedelta(days=i), datetime.min.time(), UTC).timestamp())
        for i in range((end - start).days + 1)
    )
    return grid


def _daily_returns(grid: tuple[int, ...], equity: dict[int, float]) -> tuple[float, ...]:
    """Reject gaps or nonrepresentable returns; never impute missing observations."""
    missing = [timestamp for timestamp in grid if timestamp not in equity]
    if missing:
        first = datetime.fromtimestamp(missing[0], UTC).isoformat()
        raise InferenceUnavailable(
            f"missing exact UTC daily equity endpoint {first}; no gap filling"
        )
    returns = tuple(
        equity[right] / equity[left] - 1 for left, right in zip(grid, grid[1:], strict=False)
    )
    if not all(math.isfinite(value) for value in returns):
        raise ValueError("derived portfolio returns must be finite")
    return returns


ENGINE_RETURN_TOLERANCE = 1e-8


def _check_engine_performance(
    timestamps: tuple[int, ...], returns: tuple[float, ...], performance: dict[int, float]
) -> None:
    """Require derived returns to agree with the engine's daily Return series where exported.

    LEAN samples ``Return`` once per day from the same midnight equity, rounded to a few
    significant digits, so a mismatch beyond ``ENGINE_RETURN_TOLERANCE`` means the wrong
    mark (or the wrong day) was selected; it is never silently accepted.
    """
    for timestamp, derived in zip(timestamps, returns, strict=True):
        if timestamp not in performance:
            continue
        if abs(derived - performance[timestamp] / 100) > ENGINE_RETURN_TOLERANCE:
            day = datetime.fromtimestamp(timestamp, UTC).date().isoformat()
            raise ValueError(
                f"derived return on {day} disagrees with the engine daily Return series"
            )


def align_portfolios(a: PortfolioReturns, b: PortfolioReturns) -> None:
    """Require identical pair, window, calendar grid, costs, and risk-free convention."""
    keys = ("symbol", "start", "end", "frequency", "timezone", "risk_free_daily", "costs")
    if a.timestamps != b.timestamps or any(a.metadata[k] != b.metadata[k] for k in keys):
        raise ValueError("incompatible portfolio pair, windows, grid, or return conventions")
