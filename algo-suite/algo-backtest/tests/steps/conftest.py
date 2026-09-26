"""Shared BDD steps for the `@integration` features (LEAN-in-container round-trips).

These steps are reused by timezone_roundtrip and parquet_roundtrip; smoke uses only
the "exits successfully" / "logs contain" ones. Scenario state flows through the `ctx`
fixture; the LEAN runner and probe-log parser come from the `tests/conftest.py` harness.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from algo_backtest.leandata import write_lean_minute
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from pytest_bdd import given, parsers, then, when

_EURUSD = build_instrument("EURUSD")
_ALGOS = Path(__file__).parent.parent / "algos"
_LEAN_SUBPATH = "forex/oanda/minute/eurusd"


def _minute_bars(first_start_utc: datetime, count: int) -> list[QuoteBar]:
    """`count` 1-minute QuoteBars with distinct, bid != ask prices (payload-distinguishing)."""
    bars = []
    for i in range(count):
        bid = round(1.10000 + i * 0.00010, 5)
        ask = round(1.20000 + i * 0.00010, 5)
        bars.append(
            QuoteBar(
                timestamp=first_start_utc + timedelta(minutes=i),
                bid_open=bid,
                bid_high=bid,
                bid_low=bid,
                bid_close=bid,
                ask_open=ask,
                ask_high=ask,
                ask_low=ask,
                ask_close=ask,
                tick_count=1,
            )
        )
    return bars


@given(parsers.parse('{count:d} one-minute QuoteBars starting at "{first_start}" UTC'))
def _stage_bars(ctx: dict[str, Any], count: int, first_start: str) -> None:
    """Stage `count` consecutive minute bars; keep the originals for an equality check."""
    start = datetime.fromisoformat(first_start).replace(tzinfo=UTC)
    bars = _minute_bars(start, count)
    ctx["originals"] = bars
    ctx["bars"] = bars


@given(parsers.parse('they are materialized to lean-data in timezone "{data_tz}"'))
def _materialise(ctx: dict[str, Any], data_tz: str, tmp_path: Path) -> None:
    """Write the staged bars to a tmp lean-data tree; record the symbol dir to mount."""
    write_lean_minute(tmp_path, _EURUSD, ctx["bars"], data_tz=ZoneInfo(data_tz))
    ctx["symbol_dir"] = tmp_path / "lean-data" / "forex" / "oanda" / "minute" / "eurusd"


@when(parsers.parse('the probe replays "{day}" to "{next_day}" in the LEAN container'))
def _run_probe(
    ctx: dict[str, Any], lean_backtest: Any, tmp_path: Path, day: str, next_day: str
) -> None:
    """Run the timezone-probe algorithm over the materialized day."""
    results = tmp_path / "results"
    results.mkdir(exist_ok=True)
    ctx["run"] = lean_backtest(
        algo_dir=_ALGOS / "probe",
        results_dir=results,
        data_mounts={_LEAN_SUBPATH: ctx["symbol_dir"]},
        parameters={"start": day, "end": next_day},
    )


@then("the backtest exits successfully")
def _exit_ok(ctx: dict[str, Any]) -> None:
    assert ctx["run"].exit_code == 0, ctx["run"].logs[-3000:]


@then("the algorithm timezone is UTC")
def _algo_tz_utc(ctx: dict[str, Any]) -> None:
    assert "PROBE_TZ|UTC" in ctx["run"].logs, ctx["run"].logs[-3000:]


@then("each bar returns at its original UTC end with bid and ask intact")
def _bars_round_trip(ctx: dict[str, Any], probe_log: Any) -> None:
    expected = [
        ((b.timestamp + timedelta(minutes=1)).isoformat(), b.bid_close, b.ask_close)
        for b in ctx["bars"]
    ]
    assert probe_log.bars(ctx["run"].logs) == expected, ctx["run"].logs[-3000:]


@then(parsers.parse("the probe reports {n:d} bars"))
def _probe_count(ctx: dict[str, Any], probe_log: Any, n: int) -> None:
    assert probe_log.done_count(ctx["run"].logs) == n, ctx["run"].logs[-3000:]


# --- Chain-strategy (baseline/hybrid) trading fixture ---------------------------------
# A deterministic four-hour sine cycle over five days: long enough for every indicator
# (HTF EMA 60, MACD 26+9) to warm up and for trends to form, turn, and conflict with the
# higher timeframe, so a model trained on it through the real `algo_backtest.training`
# pipeline makes the chain open, reverse and close real trades inside LEAN.
_SINE_FIRST = datetime(2014, 5, 5, tzinfo=UTC)
_SINE_MINUTES = 5 * 24 * 60
_SINE_PERIOD_MINUTES = 240


def _sine_bars() -> list[QuoteBar]:
    """Every minute of 2014-05-05..09 on a 30-pip-amplitude four-hour sine cycle."""
    import math

    bars = []
    for i in range(_SINE_MINUTES):
        mid = 1.3800 + 0.0030 * math.sin(2 * math.pi * i / _SINE_PERIOD_MINUTES)
        bid, ask = round(mid, 5), round(mid + 0.0001, 5)
        bars.append(
            QuoteBar(
                timestamp=_SINE_FIRST + timedelta(minutes=i),
                bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
                ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
                tick_count=1,
            )
        )
    return bars


@given("materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09")
def _materialize_sine(bctx: dict[str, Any]) -> None:
    """Canonical m1 Parquet + LEAN minute zips for the sine fixture."""
    from algo_backtest.materialize import materialize_month
    from algo_core.bars import Timeframe
    from algo_core.layout import price_path_for
    from algo_core.repository.parquet import ParquetRepository

    path = price_path_for(bctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 5)
    ParquetRepository(QuoteBar, path).put(_sine_bars())
    materialize_month(bctx["data_root"], _EURUSD, 2014, 5, ZoneInfo("UTC"))


@given(
    parsers.parse(
        "a {strategy} F7 model trained on it: train through 2014-05-06, validate on "
        "2014-05-07, test 2014-05-08 to 2014-05-09"
    )
)
def _train_fixture_model(bctx: dict[str, Any], strategy: str, tmp_path: Path) -> None:
    """Train through the same `algo_backtest.training` path the real scripts use."""
    from datetime import date

    from algo_backtest.chain.filters.f7_meta_learner import (
        FeatureFamily,
        train_meta_learner,
        walk_forward_split,
    )
    from algo_backtest.training import (
        build_training_rows,
        load_event_intensity,
        load_m1_bars,
        save_model,
    )

    start, test_end = date(2014, 5, 5), date(2014, 5, 9)
    bars = load_m1_bars(bctx["data_root"], _EURUSD, start, test_end)
    news = strategy == "hybrid"
    intensity = load_event_intensity(bctx["data_root"], start, test_end) if news else None
    rows = build_training_rows(bars, intensity)
    split = walk_forward_split(
        rows, train_end=date(2014, 5, 6), validation_end=date(2014, 5, 7), test_end=test_end
    )
    families = (FeatureFamily.TREND, FeatureFamily.INDICATOR, FeatureFamily.PATTERN)
    if news:
        families += (FeatureFamily.NEWS,)
    model_path = tmp_path / f"{strategy}-fixture.json"
    save_model(
        train_meta_learner(families=families, split=split),
        model_path,
        {"strategy": strategy, "fixture": "sine"},
        data_root=bctx["data_root"],
        inputs=[],
    )
    bctx["model"] = model_path


@then("the container log shows the algorithm loaded the fixture model")
def _fixture_model_logged(bctx: dict[str, Any]) -> None:
    """The run is traceable to the exact model: its SHA-256 is in the container log."""
    import hashlib

    digest = hashlib.sha256(bctx["model"].read_bytes()).hexdigest()
    logs = list(bctx["data_root"].glob("runs/*/*/log.txt"))
    assert any(f"_MODEL_SHA256={digest}" in log.read_text() for log in logs), logs
