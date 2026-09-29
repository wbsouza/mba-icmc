"""BDD proving native LEAN and offline training share signal timing and values."""

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from algo_backtest.chain.filters.f3_pattern import PatternConfig
from algo_backtest.chain.filters.volume_strength import VolumeConfig
from algo_backtest.chain.price_features import PriceFeatureConfig
from algo_backtest.leandata import write_lean_minute
from algo_backtest.training import build_training_rows
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.layout import price_path
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/closed_signal_parity.feature")


@given("five days of canonical quotes with a missing minute and varying tick activity")
def canonical(ctx, tmp_path):
    """Real Parquet and LEAN zip fixtures carry the same OHLC, with separate activity."""
    start = datetime(2014, 5, 5, tzinfo=UTC)
    bars = []
    for i in range(5 * 1440):
        if i == 370:
            continue
        open_ = round(1.38 + 0.003 * math.sin(i / 35), 5)
        close = round(1.38 + 0.003 * math.sin((i + 1) / 35), 5)
        low, high = min(open_, close) - 0.00002, max(open_, close) + 0.00002
        bars.append(QuoteBar(
            timestamp=start + timedelta(minutes=i), bid_open=open_, bid_high=round(high, 5),
            bid_low=round(low, 5), bid_close=close, ask_open=round(open_ + 0.0001, 5),
            ask_high=round(high + 0.0001, 5), ask_low=round(low + 0.0001, 5),
            ask_close=round(close + 0.0001, 5), tick_count=10 + i % 17))
    ctx["bars"] = bars
    path = price_path(tmp_path, "forex", "EURUSD", "m1", 2014, 5)
    ParquetRepository(QuoteBar, path).put(bars)
    write_lean_minute(tmp_path, build_instrument("EURUSD"), bars, ZoneInfo("UTC"))


@when(parsers.parse("the native closed-signal probe runs with {minutes:d} minute candles"))
def native(ctx, tmp_path, lean_backtest, minutes):
    """Run the production code in the pinned LEAN image, with canonical activity read-only."""
    ctx["minutes"] = minutes
    results = tmp_path / "results"
    results.mkdir()
    result = lean_backtest(
        algo_dir=Path(__file__).parents[1] / "algos" / "closed_signal_parity",
        results_dir=results,
        data_mounts={
            "forex/oanda/minute/eurusd": tmp_path / "lean-data/forex/oanda/minute/eurusd",
            "activity/parquet/forex": tmp_path / "parquet/forex",
        }, parameters={"minutes": str(minutes), "activity_data_root": "/Lean/Data/activity"})
    assert result.exit_code == 0, result.logs[-12000:]
    assert (results / "signal-observations.json").is_file(), result.logs[-12000:]
    ctx["native"] = json.loads((results / "signal-observations.json").read_text())


@then("every labeled native candle matches offline training signals and indicators")
def parity(ctx):
    """Compare every key with independent native indicators; categorical signals are exact."""
    minutes = ctx["minutes"]
    periods = PriceFeatureConfig(
        ema_fast=2, ema_slow=3, ema_higher_tf=4, rsi_period=3,
        macd_fast=2, macd_slow=4, macd_signal=2, atr_period=3,
        swing_lookback_bars=4, bar_minutes=minutes)
    rows = build_training_rows(
        ctx["bars"], instrument=build_instrument("EURUSD"), price_features_config=periods,
        horizon_minutes=minutes, pattern_config=PatternConfig(detector="talib"),
        volume_config=VolumeConfig(lookback=3))
    actual = {datetime.fromisoformat(row["end"]) - timedelta(minutes=minutes): row["features"]
              for row in ctx["native"]}
    assert rows and actual
    assert min(actual) == rows[0].timestamp
    assert len(actual) == len(rows) + 1
    for row in rows:
        for key, expected in row.features.items():
            value = actual[row.timestamp][key]
            if expected is None or isinstance(expected, str):
                assert value == expected, (row.timestamp, key, value, expected)
            else:
                assert value == pytest.approx(expected, abs=1e-9, rel=0), (
                    row.timestamp, key, value, expected)
