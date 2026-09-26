"""Steps for feature_parity.feature — training vs live (LEAN) price features."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from algo_backtest.leandata import write_lean_minute
from algo_backtest.training import (
    HORIZON_MINUTES,
    build_training_rows,
    lean_bar_stream,
    load_event_intensity,
)
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/feature_parity.feature")

_ALGOS = Path(__file__).parent.parent / "algos"
_LEAN_SUBPATH = "forex/oanda/minute/eurusd"
_DAY = datetime(2014, 5, 7, tzinfo=UTC)


def _sine_day() -> list[QuoteBar]:
    """Every minute of 2014-05-07 on a 30-pip, four-hour sine cycle (1-pip spread)."""
    bars = []
    for i in range(24 * 60):
        mid = 1.3800 + 0.0030 * math.sin(2 * math.pi * i / 240)
        bid, ask = round(mid, 5), round(mid + 0.0001, 5)
        bars.append(
            QuoteBar(
                timestamp=_DAY + timedelta(minutes=i),
                bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
                ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
                tick_count=1,
            )
        )
    return bars


_GAPS = {
    "with every minute present": set(),
    "with minutes 06:00-06:04 and 12:30 missing": {
        *(_DAY + timedelta(hours=6, minutes=m) for m in range(5)),
        _DAY + timedelta(hours=12, minutes=30),
    },
}


@given(
    parsers.parse(
        "a one-day EUR/USD minute sine cycle on 2014-05-07 {with_gaps} materialized to lean-data"
    )
)
def _materialize(ctx: dict[str, Any], tmp_path: Path, with_gaps: str) -> None:
    missing = _GAPS[with_gaps]
    ctx["bars"] = [bar for bar in _sine_day() if bar.timestamp not in missing]
    write_lean_minute(tmp_path, build_instrument("EURUSD"), ctx["bars"], data_tz=ZoneInfo("UTC"))
    ctx["symbol_dir"] = tmp_path / "lean-data" / "forex" / "oanda" / "minute" / "eurusd"


@when(parsers.parse('the feature-parity probe replays "{day}" in the LEAN container'))
def _run_probe(ctx: dict[str, Any], lean_backtest: Any, tmp_path: Path, day: str) -> None:
    results = tmp_path / "results"
    results.mkdir(exist_ok=True)
    ctx["run"] = lean_backtest(
        algo_dir=_ALGOS / "feature_parity",
        results_dir=results,
        data_mounts={_LEAN_SUBPATH: ctx["symbol_dir"]},
        parameters={"day": day},
    )


def _live(ctx: dict[str, Any]) -> dict[datetime, dict[str, float]]:
    """Live features keyed by *bar start* (decision time minus one minute)."""
    live: dict[datetime, dict[str, float]] = {}
    for line in ctx["run"].logs.splitlines():
        if "PARITY|" not in line:
            continue
        when, payload = line.split("PARITY|", 1)[1].split("|", 1)
        decided = datetime.fromisoformat(when.strip()).replace(tzinfo=UTC)
        live[decided - timedelta(minutes=1)] = json.loads(payload)
    assert live, ctx["run"].logs[-3000:]
    return live


@then("the live algorithm's first decision bar is the first training row's bar")
def _same_warmup(ctx: dict[str, Any]) -> None:
    rows = build_training_rows(ctx["bars"])
    assert min(_live(ctx)) == rows[0].timestamp


@then(
    parsers.parse(
        "every live decision bar's price features match its training row within {tol:g}"
    )
)
def _parity(ctx: dict[str, Any], tol: float) -> None:
    """Same decision bars on both sides (bar for bar), then the same feature values.

    The only live bars without a training row are the final `HORIZON_MINUTES` delivered
    bars (no label yet) — any other missing or extra timestamp is a failure.
    """
    rows = {row.timestamp: row.features for row in build_training_rows(ctx["bars"])}
    live = _live(ctx)
    unlabeled = {bar.timestamp for bar in lean_bar_stream(ctx["bars"])[-HORIZON_MINUTES:]}
    assert set(live) - unlabeled == set(rows), (
        sorted(set(live) - unlabeled - set(rows))[:5],
        sorted(set(rows) - set(live))[:5],
    )
    assert unlabeled <= set(live)
    worst: dict[str, float] = {}
    for bar_start, features in rows.items():
        for key, value in live[bar_start].items():
            gap = abs(float(features[key]) - float(value))  # type: ignore[arg-type]
            worst[key] = max(worst.get(key, 0.0), gap)
    assert all(gap <= tol for gap in worst.values()), worst


def _minute_intensity(i: int) -> float:
    """A value unique to minute `i`, so a one-minute keying shift changes every lookup."""
    return round(math.sin(i / 7.3) * 5.0 + i * 1e-4, 9)


@given(
    "GDELT event features whose intensity differs every minute from 2014-05-07 through "
    "2014-05-08T00:00"
)
def _varying_news(ctx: dict[str, Any], tmp_path: Path) -> None:
    root = tmp_path / "news-root"
    rows = [
        GdeltFeature(timestamp=_DAY + timedelta(minutes=i), event_intensity=_minute_intensity(i))
        for i in range(24 * 60 + 1)
    ]
    ParquetRepository(GdeltFeature, event_feature_path(root, "gdelt", 2014, 5)).put(rows)
    ctx["news_root"] = root


@when(parsers.parse('the news-parity probe replays "{day}" in the LEAN container'))
def _run_news_probe(ctx: dict[str, Any], lean_backtest: Any, tmp_path: Path, day: str) -> None:
    from algo_backtest.container_paths import NEWS_DATA_ROOT
    from algo_backtest.run import _news_mounts

    results = tmp_path / "results"
    results.mkdir(exist_ok=True)
    ctx["run"] = lean_backtest(
        algo_dir=_ALGOS / "news_parity",
        results_dir=results,
        data_mounts={_LEAN_SUBPATH: ctx["symbol_dir"], **_news_mounts(ctx["news_root"])},
        parameters={"day": day, "news_data_root": str(NEWS_DATA_ROOT)},
    )


@then("for every live decision bar F4 looked up exactly the training row's news_event_intensity")
def _news_parity(ctx: dict[str, Any]) -> None:
    """Same bars, and bar for bar the same value — a one-minute keying drift fails here."""
    live: dict[datetime, float] = {}
    for line in ctx["run"].logs.splitlines():
        if "NEWS|" in line:
            when, value = line.split("NEWS|", 1)[1].split("|", 1)
            decided = datetime.fromisoformat(when.strip()).replace(tzinfo=UTC)
            live[decided - timedelta(minutes=1)] = float(value)
    assert live, ctx["run"].logs[-3000:]
    intensity = load_event_intensity(ctx["news_root"], _DAY.date(), _DAY.date())
    rows = {r.timestamp: r.features for r in build_training_rows(ctx["bars"], intensity)}
    unlabeled = {bar.timestamp for bar in lean_bar_stream(ctx["bars"])[-HORIZON_MINUTES:]}
    assert set(live) - unlabeled == set(rows)
    mismatched = [
        (bar, live[bar], features["news_event_intensity"])
        for bar, features in rows.items()
        if live[bar] != features["news_event_intensity"]
    ]
    assert not mismatched, mismatched[:5]
