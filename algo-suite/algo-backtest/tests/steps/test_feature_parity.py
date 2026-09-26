"""Steps for feature_parity.feature — training vs live (LEAN) price features."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from algo_backtest.leandata import write_lean_minute
from algo_backtest.training import build_training_rows
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
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
    rows = {row.timestamp: row.features for row in build_training_rows(ctx["bars"])}
    live = _live(ctx)
    compared = 0
    worst: dict[str, float] = {}
    for bar_start, features in live.items():
        if bar_start not in rows:  # last HORIZON bars have no training row
            continue
        compared += 1
        for key, value in features.items():
            gap = abs(float(rows[bar_start][key]) - float(value))  # type: ignore[arg-type]
            worst[key] = max(worst.get(key, 0.0), gap)
    assert compared > 1000, compared
    assert all(gap <= tol for gap in worst.values()), worst
