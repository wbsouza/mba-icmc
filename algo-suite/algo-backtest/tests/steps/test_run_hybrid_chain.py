"""Steps for run_hybrid_chain.feature — the F1-F7 "hybrid" chain (with F4/news) wiring
smoke test.

Self-contained (own swing/materialization helpers), same rationale as
test_run_baseline_chain.py's own docstring: pytest-bdd binds step text per module, so
duplicating the handful of generic steps here keeps this file independently importable.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import algo_backtest
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


@when(
    "I run hybrid over the 2014-05-08 to 2014-05-09 test span with size 0.5, cash 10000 "
    "and that model"
)
def _run_hybrid_with_model(bctx: dict[str, Any], require_docker: None) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "hybrid", "--symbol", "EURUSD",
            "--from", "2014-05-08", "--to", "2014-05-09", "--param", "size=0.5",
            "--param", "cash=10000",
            "--model", str(bctx["model"]),
        ],
    )


@when(parsers.parse("I run hybrid over {first} to {last} with size 0.5 and cash 10000"))
def _run_hybrid_chain(bctx: dict[str, Any], require_docker: None, first: str, last: str) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "hybrid", "--symbol", "EURUSD",
            "--from", first, "--to", last, "--param", "size=0.5",
            "--param", "cash=10000",
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


@then("no trade was ever opened")
def _no_trade_opened(bctx: dict[str, Any]) -> None:
    """trades.json holds closed trades only -- necessary, not sufficient (see next step)."""
    trades = json.loads((_run_dir(bctx) / "trades.json").read_text())
    assert trades == [], f"expected no trades under an active-veto window, got {trades}"


@then("at least one decisions.parquet row is joined to a trades.json trade")
def _decisions_join_nonempty(bctx: dict[str, Any]) -> None:
    """Without this, the join proof above passes vacuously when no trade ever filled."""
    run_dir = _run_dir(bctx)
    rows = ParquetRepository(DecisionRow, run_dir / "decisions.parquet").read_all()
    trades = json.loads((run_dir / "trades.json").read_text())
    closed_ids = {str(trade["orderIds"][0]) for trade in trades if trade.get("orderIds")}
    joined = [row for row in rows if row.trade_id in closed_ids]
    assert joined, (
        f"no decisions.parquet row joins a closed trades.json trade ({len(rows)} rows, "
        f"{len(trades)} closed trades) -- the join is unproven"
    )


@then("every decisions.parquet row is a NO_TRADE vetoed by f4_news_context")
def _every_row_vetoed(bctx: dict[str, Any]) -> None:
    """The real proof of the veto: trades.json alone would also be empty for a position
    that opened and was never closed, so assert on the audit trail itself."""
    rows = ParquetRepository(DecisionRow, _run_dir(bctx) / "decisions.parquet").read_all()
    assert rows, "no decisions.parquet rows -- the chain never ran"
    vetoed = ("NO_TRADE", "f4_news_context")
    offenders = [r for r in rows if (r.final_decision, r.vetoed_by) != vetoed]
    assert not offenders, f"{len(offenders)}/{len(rows)} rows were not F4 vetoes: {offenders[:3]}"


@then("the error names the missing 2014-05 GDELT event-feature partition and how to build it")
def _missing_news_error(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    expected = event_feature_path(bctx["data_root"], "gdelt", 2014, 5)
    assert str(expected) in out and "algo-score events --kind gdelt" in out, out


@when("I run hybrid with the bundled baseline model as --model")
def _run_with_baseline_model(bctx: dict[str, Any]) -> None:
    model = Path(algo_backtest.__file__).parent / "algos" / "baseline" / "f7_meta_learner.json"
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "hybrid", "--symbol", "EURUSD", "--from", "2014-05-07",
            "--to", "2014-05-09", "--param", "size=0.5",
            "--param", "cash=10000", "--model", str(model),
        ],
    )


@then("the error names the model's families and the strategy's declared families")
def _families_error(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "was trained on families" in out and "meta_learner.families" in out, out


@then(
    parsers.parse(
        'the error names decision minute "{minute}" and the command building through "{day}"'
    )
)
def _final_minute_error(bctx: dict[str, Any], minute: str, day: str) -> None:
    out = bctx["cli"].output
    assert minute in out and f"--to {day}" in out, out


@then(parsers.parse('decisions.parquet has a row at "{ts}"'))
def _row_at(bctx: dict[str, Any], ts: str) -> None:
    rows = ParquetRepository(DecisionRow, _run_dir(bctx) / "decisions.parquet").read_all()
    assert any(row.timestamp == datetime.fromisoformat(ts) for row in rows), rows[-3:]


@then(parsers.parse('the remediation command built through "{day}"'))
def _remediation_through(bctx: dict[str, Any], day: str) -> None:
    assert bctx["remediation"].endswith(f"--to {day}"), bctx["remediation"]


@then("the 2014-06 GDELT feature partition still covers every minute of June")
def _june_intact(bctx: dict[str, Any]) -> None:
    path = event_feature_path(bctx["data_root"], "gdelt", 2014, 6)
    minutes = sorted(row.timestamp for row in ParquetRepository(GdeltFeature, path).read_all())
    assert len(minutes) == 30 * 24 * 60
    assert (minutes[0], minutes[-1]) == (
        datetime(2014, 6, 1, tzinfo=UTC),
        datetime(2014, 6, 30, 23, 59, tzinfo=UTC),
    )


@then(
    parsers.parse(
        'the error names {count:d} uncovered decision minutes starting "{first}"'
    )
)
def _interior_gap_error(bctx: dict[str, Any], count: int, first: str) -> None:
    out = bctx["cli"].output
    assert f"{count} decision minutes (first {first}" in out, out
    assert "algo-score events --kind gdelt" in out, out


@then(
    parsers.parse(
        "after the remediation command printed for a {start} to {end} run has been run, "
        "the run has no news coverage problems"
    )
)
def _remediation_closes_gap(bctx: dict[str, Any], start: str, end: str) -> None:
    from algo_backtest.chain.filters.f4_news_context import (
        news_build_command,
        news_coverage_problems,
    )
    from algo_score.cli import app as score_app

    first, last = date.fromisoformat(start), date.fromisoformat(end)
    result = CliRunner().invoke(score_app, news_build_command(first, last).split()[1:])
    assert result.exit_code == 0, result.output
    assert news_coverage_problems(bctx["data_root"], "EURUSD", first, last) == []
