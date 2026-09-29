"""Steps for candles_expanded_integration.feature — Story 22/23 T7's native LEAN gate.

Proves the shared candle_catalog/candle_context/candle_sequence producer reaches a
real backtest through `pattern.detector: expanded`, not just unit-tested in isolation.
The sine-cycle materialization step ("materialized EUR/USD minute data with a
four-hour sine cycle over ... to ...") is registered in tests/steps/conftest.py and
reused as-is; only the CLI invocation and assertions are specific to this scenario
(candles-expanded takes no --model, unlike the F7 chain strategies).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.cli import app
from pytest_bdd import parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/candles_expanded_integration.feature")


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


@when(
    "I run candles-expanded over the 2014-05-08 to 2014-05-09 test span with cash 10000"
)
def _run_candles_expanded(bctx: dict[str, Any], require_docker: None) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "candles-expanded", "--symbol", "EURUSD",
            "--from", "2014-05-08", "--to", "2014-05-09",
            "--param", "cash=10000",
        ],
    )


@then("the strategy run exits successfully")
def _exit_ok(bctx: dict[str, Any]) -> None:
    assert bctx["cli"].exit_code == 0, bctx["cli"].output


@then(parsers.parse('the run artifacts are written under the data root for "{name}"'))
def _artifacts_written(bctx: dict[str, Any], name: str) -> None:
    runs = bctx["data_root"] / "runs" / name
    assert list(runs.glob("*/run.json")), f"no run.json under {runs}"
    assert list(runs.glob("*/trades.json")), f"no trades.json under {runs}"
    assert list(runs.glob("*/metrics.json")), f"no metrics.json under {runs}"


@then(
    parsers.parse(
        "the container log shows the F1-F7 chain actually evaluated a decision for "
        '"{name}"'
    )
)
def _chain_evaluated(bctx: dict[str, Any], name: str) -> None:
    """`candles-expanded` runs on the `baseline` LEAN algorithm (no F4 => algo_dir
    "baseline", chain_algorithm.py's fixed `log_tag = "BASELINE""), so its
    `BASELINE_DECISION|...` debug line proves `FilterChain.run()` actually executed
    the expanded-catalog F3 filter inside the container, not just that the CLI exited 0.
    """
    runs = bctx["data_root"] / "runs" / name
    logs = list(runs.glob("*/log.txt"))
    assert logs, f"no log.txt under {runs}"
    assert any("BASELINE_DECISION|" in log.read_text() for log in logs), (
        f"no BASELINE_DECISION line in {[str(p) for p in logs]} -- the chain never ran"
    )
