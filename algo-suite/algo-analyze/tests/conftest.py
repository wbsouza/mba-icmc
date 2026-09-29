"""Test path setup and shared engine-artifact factories for algo-analyze."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from math import sin
from pathlib import Path

import pytest


def pytest_configure() -> None:
    """Make the package's src layout importable when pytest runs from this tool dir."""
    src = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src))


def write_portfolio(path: Path, offset: float = 0.0) -> None:
    """Write an engine-shaped run: 121 midnight equity points, contract, manifest, ledger.

    The trade ledger is deliberately unrelated to the equity path so a test that mixes
    per-trade returns into portfolio inference fails loudly.
    """
    path.mkdir(parents=True, exist_ok=True)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    values, equity = [], 100000.0
    for i in range(121):
        values.append([int((start + timedelta(days=i)).timestamp()), equity])
        equity *= 1 + 0.005 * sin(i * 0.71 + offset) + 0.001 + offset * 0.0001
    artifacts = {
        "main.json": {"charts": {"Strategy Equity": {"series": {"Equity": {"values": values}}}}},
        "run.json": {
            "success": True,
            "symbol": "EURUSD",
            "start": "2020-01-01",
            "end": "2020-04-29",
        },
        "metrics.json": {
            "sharpe": 99.0,
            "total_return": 0.1,
            "max_drawdown": -0.1,
            "hit_rate": 0.5,
        },
        "trades.json": [{"return": 100}] * (2 if offset else 7),
        "inference-inputs.json": {
            "source": "main.json",
            "frequency": "calendar-day",
            "timezone": "UTC",
            "annualization": 365,
            "risk_free_daily": 0,
            "costs": "brokerage:fixture",
            "symbol": "EURUSD",
            "start": "2020-01-01",
            "end": "2020-04-30",
        },
    }
    for name, value in artifacts.items():
        (path / name).write_text(json.dumps(value))


@pytest.fixture
def portfolio_factory() -> Callable[..., None]:
    """Expose the engine-artifact writer to step modules without cross-test imports."""
    return write_portfolio
