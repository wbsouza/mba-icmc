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
_SINE_PERIOD_MINUTES = 240


def _sine_bars(first: datetime, days: int) -> list[QuoteBar]:
    """Every minute of `days` UTC days from `first` on a 30-pip four-hour sine cycle."""
    import math

    bars = []
    for i in range(days * 24 * 60):
        mid = 1.3800 + 0.0030 * math.sin(2 * math.pi * i / _SINE_PERIOD_MINUTES)
        bid, ask = round(mid, 5), round(mid + 0.0001, 5)
        bars.append(
            QuoteBar(
                timestamp=first + timedelta(minutes=i),
                bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
                ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
                tick_count=1,
            )
        )
    return bars


@given(
    parsers.parse(
        "materialized EUR/USD minute data with a four-hour sine cycle over {first} to {last}"
    )
)
def _materialize_sine(bctx: dict[str, Any], first: str, last: str) -> None:
    """Canonical m1 Parquet + LEAN minute zips for the sine fixture, per touched month."""
    from datetime import date

    from algo_backtest.materialize import materialize_month
    from algo_core.bars import Timeframe
    from algo_core.layout import price_path_for
    from algo_core.repository.parquet import ParquetRepository

    start, end = date.fromisoformat(first), date.fromisoformat(last)
    bars = _sine_bars(datetime.combine(start, datetime.min.time(), UTC), (end - start).days + 1)
    by_month: dict[tuple[int, int], list[QuoteBar]] = {}
    for bar in bars:
        by_month.setdefault((bar.timestamp.year, bar.timestamp.month), []).append(bar)
    for (year, month), rows in by_month.items():
        path = price_path_for(bctx["data_root"], _EURUSD, Timeframe.M1.value, year, month)
        ParquetRepository(QuoteBar, path).put(rows)
        materialize_month(bctx["data_root"], _EURUSD, year, month, ZoneInfo("UTC"))


def _write_raw_gdelt(data_root: Path, first: str, last: str, goldstein: float) -> None:
    """One canonical GDELT event per day in [first, last] at `goldstein`, per month partition."""
    from datetime import date

    import pyarrow as pa
    import pyarrow.parquet as pq

    start, end = date.fromisoformat(first), date.fromisoformat(last)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    by_month: dict[tuple[int, int], list[date]] = {}
    for day in days:
        by_month.setdefault((day.year, day.month), []).append(day)
    for (year, month), month_days in by_month.items():
        path = (
            data_root / "parquet" / "events" / "gdelt" / f"year={year:04d}" / f"month={month:02d}"
            / "data.parquet"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        n = len(month_days)
        pq.write_table(
            pa.table(
                {
                    "global_event_id": list(range(1, n + 1)),
                    "event_date": month_days,
                    "event_code": ["042"] * n,
                    "goldstein_scale": [goldstein] * n,
                    "avg_tone": [0.0] * n,
                    "actor1_code": ["USA"] * n,
                    "actor2_code": ["EUR"] * n,
                    "num_mentions": [1] * n,
                    "num_sources": [1] * n,
                    "num_articles": [1] * n,
                    "source_url": ["https://example.test"] * n,
                }
            ),
            path,
        )


def _algo_score(bctx: dict[str, Any], command: str) -> None:
    """Run an `algo-score ...` command line through the real algo-score CLI."""
    from algo_score.cli import app as score_app
    from typer.testing import CliRunner

    result = CliRunner().invoke(score_app, command.split()[1:])
    assert result.exit_code == 0, result.output


@given(
    parsers.parse(
        "raw GDELT events at goldstein {goldstein:g} for every day from {first} to {last}, "
        "built into features by the remediation command for a {start} to {end} run"
    )
)
def _raw_gdelt_remediated(
    bctx: dict[str, Any], goldstein: float, first: str, last: str, start: str, end: str
) -> None:
    """Build features exactly as the run CLI tells the user to (production builder)."""
    from datetime import date

    from algo_backtest.chain.filters.f4_news_context import news_build_command

    _write_raw_gdelt(bctx["data_root"], first, last, goldstein)
    _algo_score(bctx, news_build_command(date.fromisoformat(start), date.fromisoformat(end)))


@given(
    parsers.parse(
        "raw GDELT events at goldstein {goldstein:g} for every day from {first} to {last}, "
        "built into features only from {start} through {end}"
    )
)
def _raw_gdelt_through(
    bctx: dict[str, Any], goldstein: float, first: str, last: str, start: str, end: str
) -> None:
    """Build features through the run's last day only (the pre-fix habit)."""
    _write_raw_gdelt(bctx["data_root"], first, last, goldstein)
    _algo_score(bctx, f"algo-score events --kind gdelt --from {start} --to {end}")


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


def _lean_instant(raw: str) -> datetime:
    """A LEAN result timestamp (ISO, `Z` or offset or naive-UTC) as an aware UTC datetime."""
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


@then("every decisions.parquet row's trade_id names the LEAN trade open at that row's instant")
def _decisions_identify_open_trade(bctx: dict[str, Any]) -> None:
    """Identity, not membership: each row's trade_id is the ledger trade open *then*.

    A ledger trade (LEAN's `closedTrades`, flat-to-flat) is open at `t` when
    `entryTime <= t < exitTime`; a row is recorded after that bar's fill, so an entry
    row carries its new trade and a flattening row carries none. A trade still open at
    the end has no ledger entry — the algorithm logs its id, open from its first row on.
    NO_TRADE rows are always null (SPEC.md §6.2) and are skipped.
    """
    import json

    from algo_backtest.chain.audit import DecisionRow
    from algo_core.repository.parquet import ParquetRepository

    (run_dir,) = list(bctx["data_root"].glob("runs/*/*/"))
    rows = ParquetRepository(DecisionRow, run_dir / "decisions.parquet").read_all()
    trades = json.loads((run_dir / "trades.json").read_text())
    episodes = [
        (str(t["orderIds"][0]), _lean_instant(t["entryTime"]), _lean_instant(t["exitTime"]))
        for t in trades
    ]
    open_at_end = next(
        (
            line.split("_OPEN_TRADE_AT_END=", 1)[1].strip()
            for line in (run_dir / "log.txt").read_text().splitlines()
            if "_OPEN_TRADE_AT_END=" in line
        ),
        "None",
    )
    if open_at_end != "None":
        first = min(r.timestamp for r in rows if r.trade_id == open_at_end)
        episodes.append((open_at_end, first, datetime.max.replace(tzinfo=UTC)))
    for row in rows:
        if row.final_decision == "NO_TRADE":
            assert row.trade_id is None, row
            continue
        open_now = [tid for tid, entry, exit_ in episodes if entry <= row.timestamp < exit_]
        assert len(open_now) <= 1, (row.timestamp, open_now)
        expected = open_now[0] if open_now else None
        assert row.trade_id == expected, (row.timestamp, row.final_decision, row.trade_id, expected)


@given(parsers.parse("the remediation command printed for a {start} to {end} run has been run"))
def _remediation_run(bctx: dict[str, Any], start: str, end: str) -> None:
    """Execute exactly the `algo-score events ...` line the run CLI prints."""
    from datetime import date

    from algo_backtest.chain.filters.f4_news_context import news_build_command

    command = news_build_command(date.fromisoformat(start), date.fromisoformat(end))
    bctx["remediation"] = command
    _algo_score(bctx, command)


@given(parsers.parse("GDELT features are also built from {start} through {end}"))
def _also_built(bctx: dict[str, Any], start: str, end: str) -> None:
    """A second, separate feature build (partial builds merge into existing partitions)."""
    _algo_score(bctx, f"algo-score events --kind gdelt --from {start} --to {end}")
