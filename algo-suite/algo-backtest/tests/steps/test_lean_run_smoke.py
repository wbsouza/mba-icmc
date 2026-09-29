"""Steps for lean_run_smoke.feature — the full run path via the lean-smoke CLI."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import algo_backtest
import pytest
from algo_backtest.cli import app
from algo_backtest.lean_runner import run_lean
from algo_backtest.materialize import materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import lean_data_dir_for, price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/lean_run_smoke.feature")

_EURUSD = build_instrument("EURUSD")
_SMOKE_ALGO = Path(algo_backtest.__file__).parent / "algos" / "smoke_trade"


def _materialize_day(data_root: Path, first: datetime, count: int = 30) -> None:
    """Materialize `count` consecutive minute bars from `first` (UTC) for EUR/USD."""
    bars = [
        QuoteBar(
            timestamp=first + timedelta(minutes=i),
            bid_open=1.39 + i * 1e-4, bid_high=1.39 + i * 1e-4,
            bid_low=1.39 + i * 1e-4, bid_close=1.39 + i * 1e-4,
            ask_open=1.3901 + i * 1e-4, ask_high=1.3901 + i * 1e-4,
            ask_low=1.3901 + i * 1e-4, ask_close=1.3901 + i * 1e-4,
            tick_count=1,
        )
        for i in range(count)
    ]
    repo: ParquetRepository[QuoteBar] = ParquetRepository(
        QuoteBar, price_path_for(data_root, _EURUSD, Timeframe.M1.value, first.year, first.month)
    )
    repo.put(bars)
    materialize_month(data_root, _EURUSD, first.year, first.month, ZoneInfo("UTC"))


@pytest.fixture
def smoke_ctx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, require_docker: None
) -> dict[str, Any]:
    """Tmp data root + clean ALGO_ env (zero-config => UTC); skips if Docker is absent."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {"data_root": data_root}


@given("materialized EUR/USD minute data for 2014-05")
def _materialize(smoke_ctx: dict[str, Any]) -> None:
    # the smoke-trade algorithm trades on 2014-05-07
    _materialize_day(smoke_ctx["data_root"], datetime(2014, 5, 7, 12, 0, tzinfo=UTC))


@given("materialized EUR/USD minute data outside the smoke-trade window")
def _materialize_outside(smoke_ctx: dict[str, Any]) -> None:
    # 2014-05-09 is after the algorithm's 2014-05-07..08 window: no bars will arrive
    _materialize_day(smoke_ctx["data_root"], datetime(2014, 5, 9, 12, 0, tzinfo=UTC))


@when("I run the lean-smoke CLI command")
def _run_smoke(smoke_ctx: dict[str, Any]) -> None:
    smoke_ctx["cli"] = CliRunner().invoke(app, ["lean-smoke"])


@when("I run the smoke-trade algorithm directly")
def _run_algo_directly(smoke_ctx: dict[str, Any]) -> None:
    symbol_dir = lean_data_dir_for(smoke_ctx["data_root"], _EURUSD, "minute")
    results = smoke_ctx["data_root"] / "runs" / "direct"
    results.mkdir(parents=True, exist_ok=True)
    smoke_ctx["run"] = run_lean(
        _SMOKE_ALGO, results, data_mounts={"forex/oanda/minute/eurusd": symbol_dir}
    )


@then("the algorithm reports it never entered")
def _never_entered(smoke_ctx: dict[str, Any]) -> None:
    assert smoke_ctx["run"].grep("ONESHOT_ERROR=never_entered"), smoke_ctx["run"].logs[-2000:]


@then("it reports zero closed trades")
def _zero_closed(smoke_ctx: dict[str, Any]) -> None:
    assert smoke_ctx["run"].grep("ONESHOT_CLOSED_TRADES=0"), smoke_ctx["run"].logs[-2000:]


@then("the command exits successfully")
def _exits_ok(smoke_ctx: dict[str, Any]) -> None:
    assert smoke_ctx["cli"].exit_code == 0, smoke_ctx["cli"].output


@then("it reports exactly one closed trade")
def _one_closed_trade(smoke_ctx: dict[str, Any]) -> None:
    assert "closed_trades=1" in smoke_ctx["cli"].output, smoke_ctx["cli"].output
