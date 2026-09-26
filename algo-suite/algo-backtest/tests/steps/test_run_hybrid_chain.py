"""Steps for run_hybrid_chain.feature — the F1-F7 "hybrid" chain (with F4/news) wiring
smoke test.

Self-contained (own swing/materialization helpers), same rationale as
test_run_baseline_chain.py's own docstring: pytest-bdd binds step text per module, so
duplicating the handful of generic steps here keeps this file independently importable.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from algo_backtest.chain.audit import DecisionRow
from algo_backtest.cli import app
from algo_backtest.materialize import materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/run_hybrid_chain.feature")

_EURUSD = build_instrument("EURUSD")
_SWING_FIRST = datetime(2014, 5, 7, 13, 0, tzinfo=UTC)
_SWING_COUNT = 60


@pytest.fixture
def bctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root (zero-config => UTC). No Docker (guard steps)."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    monkeypatch.setenv("ALGO_BROKER__ADAPTER", "oanda")
    return {"data_root": data_root}


def _swing_bars(first: datetime, count: int = 60) -> list[QuoteBar]:
    """Triangular price swing (up then down), same shape as run_baseline_chain's fixture."""
    bars = []
    for i in range(count):
        offset = min(i, count - 1 - i)
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


@when(parsers.parse('I run "{command}"'))
def _run_cli(bctx: dict[str, Any], command: str) -> None:
    bctx["cli"] = CliRunner().invoke(app, command.split()[1:])


@given("materialized EUR/USD minute data with a price swing in 2014-05")
def _materialize_swing(bctx: dict[str, Any]) -> None:
    bars = _swing_bars(_SWING_FIRST, _SWING_COUNT)
    ParquetRepository(
        QuoteBar, price_path_for(bctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 5)
    ).put(bars)
    materialize_month(bctx["data_root"], _EURUSD, 2014, 5, ZoneInfo("UTC"))


_RUN_WINDOW_START = datetime(2014, 5, 7, tzinfo=UTC)
_RUN_WINDOW_MINUTES = 3 * 24 * 60  # 2014-05-07 through 2014-05-09 inclusive, plus margin


def _synthetic_event_feature_rows(event_intensity: float) -> list[GdeltFeature]:
    """One GdeltFeature row per minute of the whole `--from`/`--to` run window, all at
    `event_intensity` -- not just the 60-minute swing. LEAN delivers quote bars (holding
    the last real quote) across the full requested CLI window, not only the swing's own
    60 minutes, so F4's per-minute lookup must cover the same span the algorithm actually
    runs over or it fails fast on the first uncovered bar (confirmed: it does, exactly at
    the swing's last minute + 1)."""
    return [
        GdeltFeature(
            timestamp=_RUN_WINDOW_START + timedelta(minutes=i), event_intensity=event_intensity
        )
        for i in range(_RUN_WINDOW_MINUTES)
    ]


@given("a synthetic GDELT event-feature Parquet for 2014-05 with no active high-risk event")
def _synthetic_news_no_veto(bctx: dict[str, Any]) -> None:
    """0.0 is well above the smoke test's -0.5 veto threshold -- F4 never vetoes."""
    rows = _synthetic_event_feature_rows(0.0)
    path = event_feature_path(bctx["data_root"], "gdelt", 2014, 5)
    ParquetRepository(GdeltFeature, path).put(rows)


@given("a synthetic GDELT event-feature Parquet for 2014-05 with an active high-risk event")
def _synthetic_news_veto(bctx: dict[str, Any]) -> None:
    """-10.0 is well below the smoke test's -0.5 veto threshold -- F4 vetoes every bar."""
    rows = _synthetic_event_feature_rows(-10.0)
    path = event_feature_path(bctx["data_root"], "gdelt", 2014, 5)
    ParquetRepository(GdeltFeature, path).put(rows)


@when("I run hybrid over 2014-05-07 to 2014-05-09 with size 0.5")
def _run_hybrid_chain(bctx: dict[str, Any], require_docker: None) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "hybrid", "--symbol", "EURUSD",
            "--from", "2014-05-07", "--to", "2014-05-09", "--param", "size=0.5",
        ],
    )


@then(parsers.parse("the run command exits with code {code:d}"))
def _exit_code(bctx: dict[str, Any], code: int) -> None:
    assert bctx["cli"].exit_code == code, bctx["cli"].output


@then("the strategy run exits successfully")
def _exit_ok(bctx: dict[str, Any]) -> None:
    assert bctx["cli"].exit_code == 0, bctx["cli"].output


@then("the error says size must be in range")
def _size_range(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "size" in out and "(0, 1]" in out


@then("the error says params must be exactly")
def _params_must_be_exactly(bctx: dict[str, Any]) -> None:
    """Distinguishes a real `_check_keys` rejection from an unrelated failure (e.g. "no
    lean-data") that happens to also exit 2 -- both scenarios run against a fresh,
    unmaterialized data root, so exit code alone can't tell which check actually fired.
    """
    assert "params must be exactly" in bctx["cli"].output, bctx["cli"].output


@then("a metrics summary is reported")
def _metrics_reported(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "metrics:" in out and "total_return=" in out, out


@then("the run artifacts are written under the data root")
def _artifacts_written(bctx: dict[str, Any]) -> None:
    runs = bctx["data_root"] / "runs" / "hybrid"
    assert list(runs.glob("*/run.json")), f"no run.json under {runs}"
    assert list(runs.glob("*/trades.json")), f"no trades.json under {runs}"
    assert list(runs.glob("*/metrics.json")), f"no metrics.json under {runs}"


@then("the container log shows the F1-F7 hybrid chain actually evaluated a decision")
def _chain_evaluated(bctx: dict[str, Any]) -> None:
    """Prove FilterChain.run() executed inside LEAN with F4 wired in, not just CLI success.

    Mirrors run_baseline_chain.feature's own BASELINE_DECISION check, against `main.py`'s
    HYBRID_DECISION| line instead.
    """
    runs = bctx["data_root"] / "runs" / "hybrid"
    logs = list(runs.glob("*/log.txt"))
    assert logs, f"no log.txt under {runs}"
    assert any("HYBRID_DECISION|" in log.read_text() for log in logs), (
        f"no HYBRID_DECISION line in {[str(p) for p in logs]} -- the chain never ran"
    )


def _run_dir(bctx: dict[str, Any]) -> Path:
    """The single run directory this scenario's CLI invocation just created."""
    data_root: Path = bctx["data_root"]
    runs = list((data_root / "runs" / "hybrid").glob("*"))
    assert len(runs) == 1, f"expected exactly one hybrid run dir, found {runs}"
    return runs[0]


@then("decisions.parquet is written under the run's results directory")
def _decisions_parquet_written(bctx: dict[str, Any]) -> None:
    assert (_run_dir(bctx) / "decisions.parquet").exists()


@then("every decisions.parquet row's trade_id is null or a real trades.json entry order id")
def _decisions_trade_id_joins_trades_json(bctx: dict[str, Any]) -> None:
    """Prove decisions.parquet's trade_id is a real foreign key into trades.json.

    Same join proof as run_baseline_chain.feature's own scenario, run here against the
    hybrid chain (which additionally exercises F4/news on the join path).
    """
    run_dir = _run_dir(bctx)
    repo: ParquetRepository[DecisionRow] = ParquetRepository(
        DecisionRow, run_dir / "decisions.parquet"
    )
    rows = repo.read_all()
    trades = json.loads((run_dir / "trades.json").read_text())
    entry_order_ids = {str(trade["orderIds"][0]) for trade in trades if trade.get("orderIds")}
    for row in rows:
        assert row.trade_id is None or row.trade_id in entry_order_ids, (
            f"decisions.parquet trade_id {row.trade_id!r} matches no trades.json "
            f"entry order id in {sorted(entry_order_ids)}"
        )


@then("no trade was ever opened")
def _no_trade_opened(bctx: dict[str, Any]) -> None:
    """Every bar vetoed by F4's active high-risk event -> trades.json is empty."""
    trades = json.loads((_run_dir(bctx) / "trades.json").read_text())
    assert trades == [], f"expected no trades under an active-veto window, got {trades}"
