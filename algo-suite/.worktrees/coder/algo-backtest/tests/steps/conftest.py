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
