"""Steps for run_baseline_chain.feature — the F1-F7 "baseline" chain wiring smoke test.

pytest-bdd binds step text per module, not globally across collected files, so the
handful of generic steps this feature shares with run_baseline.feature (CLI invocation,
exit-code/error assertions, swing-data materialization, artifact checks) are
self-contained here rather than cross-imported from test_run_baseline.py — same step
text, same behavior, kept independently importable. Only "bctx" and "require_docker"
are true fixtures (from conftest.py), not step functions, so no duplication there.
"""

from __future__ import annotations

import os
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

scenarios("../features/run_baseline_chain.feature")

_EURUSD = build_instrument("EURUSD")


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
    """Triangular price swing (up then down), same shape as run_baseline.feature's fixture."""
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
    bars = _swing_bars(datetime(2014, 5, 7, 13, 0, tzinfo=UTC))
    ParquetRepository(
        QuoteBar, price_path_for(bctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 5)
    ).put(bars)
    materialize_month(bctx["data_root"], _EURUSD, 2014, 5, ZoneInfo("UTC"))


@when("I run baseline over 2014-05-07 to 2014-05-09 with size 0.5")
def _run_baseline_chain(bctx: dict[str, Any], require_docker: None) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "baseline", "--symbol", "EURUSD",
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


@then("a metrics summary is reported")
def _metrics_reported(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "metrics:" in out and "total_return=" in out, out


@then("the run artifacts are written under the data root")
def _artifacts_written(bctx: dict[str, Any]) -> None:
    runs = bctx["data_root"] / "runs" / "baseline"
    assert list(runs.glob("*/run.json")), f"no run.json under {runs}"
    assert list(runs.glob("*/trades.json")), f"no trades.json under {runs}"
    assert list(runs.glob("*/metrics.json")), f"no metrics.json under {runs}"


@then("the container log shows the F1-F7 chain actually evaluated a decision")
def _chain_evaluated(bctx: dict[str, Any]) -> None:
    """Prove FilterChain.run() executed inside LEAN, not just that the CLI exited 0.

    CLI success + written artifacts can't distinguish "the chain ran" from "the chain
    was silently skipped" -- main.py logs one BASELINE_DECISION|... line (LEAN's own
    debug-message throttling collapses repeats, so at least one, not necessarily many)
    every time `on_data` reaches `self._chain.run(state)`. LEAN persists its container
    stdout as `log.txt` in the run's own results directory, so this reads that real
    file rather than needing a second, CLI-bypassing `run_lean()` call.
    """
    runs = bctx["data_root"] / "runs" / "baseline"
    logs = list(runs.glob("*/log.txt"))
    assert logs, f"no log.txt under {runs}"
    assert any("BASELINE_DECISION|" in log.read_text() for log in logs), (
        f"no BASELINE_DECISION line in {[str(p) for p in logs]} -- the chain never ran"
    )
