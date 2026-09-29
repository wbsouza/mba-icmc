"""Steps for run_baseline.feature — baseline-ma CLI validation + a real run."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from algo_backtest.cli import app
from algo_backtest.materialize import materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/run_baseline.feature")

_EURUSD = build_instrument("EURUSD")


@pytest.fixture
def bctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root (zero-config => UTC). No Docker (guard steps)."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {"data_root": data_root}


def _swing_bars(first: datetime, count: int = 60) -> list[QuoteBar]:
    """Triangular price swing (up then down) so a fast/slow SMA crosses both ways."""
    bars = []
    for i in range(count):
        offset = min(i, count - 1 - i)  # rises to the midpoint, then falls
        mid = 1.3800 + 0.0003 * offset
        bid = round(mid, 5)
        ask = round(mid + 0.0001, 5)
        bars.append(
            QuoteBar(
                timestamp=first + timedelta(minutes=i),
                bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
                ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
                tick_count=1,
            )
        )
    return bars


@given("no materialized EUR/USD lean-data")
def _no_data(bctx: dict[str, Any]) -> None:
    pass  # the fixture's data root is empty


def _flat_bars(first: datetime, count: int = 60) -> list[QuoteBar]:
    """A flat price — fast and slow SMA never cross, so the strategy never trades."""
    bid, ask = 1.38000, 1.38010
    return [
        QuoteBar(
            timestamp=first + timedelta(minutes=i),
            bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
            ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
            tick_count=1,
        )
        for i in range(count)
    ]


def _materialize(bctx: dict[str, Any], bars: list[QuoteBar]) -> None:
    """Write bars to canonical Parquet for 2014-05 and materialize them to lean-data."""
    ParquetRepository(
        QuoteBar, price_path_for(bctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 5)
    ).put(bars)
    materialize_month(bctx["data_root"], _EURUSD, 2014, 5, ZoneInfo("UTC"))


@given("materialized EUR/USD minute data with a price swing in 2014-05")
def _materialize_swing(bctx: dict[str, Any]) -> None:
    _materialize(bctx, _swing_bars(datetime(2014, 5, 7, 13, 0, tzinfo=UTC)))


@given("materialized EUR/USD minute data with a flat price in 2014-05")
def _materialize_flat(bctx: dict[str, Any]) -> None:
    _materialize(bctx, _flat_bars(datetime(2014, 5, 7, 13, 0, tzinfo=UTC)))


@when(parsers.parse('I run "{command}"'))
def _run_cli(bctx: dict[str, Any], command: str) -> None:
    bctx["cli"] = CliRunner().invoke(app, command.split()[1:])


@when("I run baseline-ma over 2014-05-07 to 2014-05-09 with fast 3 and slow 8")
def _run_baseline(bctx: dict[str, Any], require_docker: None) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        ["run", "--strategy", "baseline-ma", "--symbol", "EURUSD",
         "--from", "2014-05-07", "--to", "2014-05-09",
         "--param", "fast=3", "--param", "slow=8", "--param", "size=0.5"],
    )


@then(parsers.parse("the run command exits with code {code:d}"))
def _exit_code(bctx: dict[str, Any], code: int) -> None:
    assert bctx["cli"].exit_code == code, bctx["cli"].output


@then("the strategy run exits successfully")
def _exit_ok(bctx: dict[str, Any]) -> None:
    assert bctx["cli"].exit_code == 0, bctx["cli"].output


@then("the error names the unknown strategy")
def _unknown(bctx: dict[str, Any]) -> None:
    assert "unknown strategy" in bctx["cli"].output and "bogus" in bctx["cli"].output


@then("the error says fast must be below slow")
def _fast_slow(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "fast" in out and "slow" in out and "below" in out


@then("the error says from must not be after to")
def _from_to(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "from date" in out and "after" in out


@then("the error says size must be in range")
def _size_range(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "size" in out and "(0, 1]" in out


@then("the error says the fast period must be positive")
def _fast_positive(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "fast period" in out and "positive" in out


@then("the error tells me to run materialize first")
def _materialize_hint(bctx: dict[str, Any]) -> None:
    assert "materialize" in bctx["cli"].output


def _closed_trades(output: str) -> int:
    """The closed-trade count parsed from the run command's summary line."""
    match = re.search(r"closed_trades=(\d+)", output)
    assert match, output
    return int(match.group(1))


@then("the parsed result has at least one closed trade")
def _closed_trade(bctx: dict[str, Any]) -> None:
    assert _closed_trades(bctx["cli"].output) >= 1, bctx["cli"].output


@then("the parsed result has zero closed trades")
def _zero_closed_trades(bctx: dict[str, Any]) -> None:
    assert _closed_trades(bctx["cli"].output) == 0, bctx["cli"].output


@then("a metrics summary is reported")
def _metrics_reported(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "metrics:" in out and "total_return=" in out, out


@then("the reported metrics show zero total return and zero max drawdown")
def _flat_metrics_zero(bctx: dict[str, Any]) -> None:
    # A no-trade run never opens a position: a real LEAN run must report exactly zero
    # net profit and zero drawdown. Reading the persisted metrics.json anchors the
    # portfolioStatistics -> Metrics mapping against a real engine result (not just a
    # synthetic fixture) and proves the artifact itself, free of print formatting.
    metrics_files = list((bctx["data_root"] / "runs" / "baseline-ma").glob("*/metrics.json"))
    assert len(metrics_files) == 1, metrics_files
    doc = json.loads(metrics_files[0].read_text())
    assert doc["total_return"] == 0.0, doc
    assert doc["max_drawdown"] == 0.0, doc


@then("the run artifacts are written under the data root")
def _artifacts_written(bctx: dict[str, Any]) -> None:
    runs = bctx["data_root"] / "runs" / "baseline-ma"
    assert list(runs.glob("*/run.json")), f"no run.json under {runs}"
    assert list(runs.glob("*/trades.json")), f"no trades.json under {runs}"
    assert list(runs.glob("*/metrics.json")), f"no metrics.json under {runs}"
