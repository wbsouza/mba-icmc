"""Steps for artifacts.feature — persisting a run manifest + closed-trade ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.artifacts import RunManifest, write_run_artifacts
from algo_backtest.metrics import Metrics
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/artifacts.feature")


@pytest.fixture
def art_ctx(tmp_path: Path) -> dict[str, Any]:
    """A results dir for the run."""
    results = tmp_path / "results"
    results.mkdir()
    return {"results": results}


@given(parsers.parse("a finished baseline run reporting {n:d} closed trades"))
def _finished_run(art_ctx: dict[str, Any], n: int) -> None:
    art_ctx["closed_trades"] = [{"trade": i} for i in range(n)]
    art_ctx["metrics"] = Metrics(
        total_return=0.02, sharpe=1.5, max_drawdown=0.1, hit_rate=0.6
    )
    art_ctx["manifest"] = RunManifest(
        strategy="baseline-ma", symbol="EURUSD", start="2014-05-07", end="2014-05-09",
        params={"fast": "3", "slow": "8", "size": "0.5"}, success=True, closed_trades=n,
    )


@when("I write its run artifacts")
def _write(art_ctx: dict[str, Any]) -> None:
    art_ctx["artifacts"] = write_run_artifacts(
        art_ctx["results"], art_ctx["manifest"],
        art_ctx["closed_trades"], art_ctx["metrics"],
    )


@then(parsers.parse('run.json records strategy "{strategy}", symbol "{symbol}" and the window'))
def _run_json(art_ctx: dict[str, Any], strategy: str, symbol: str) -> None:
    doc = json.loads(art_ctx["artifacts"].run_json.read_text())
    assert doc["strategy"] == strategy
    assert doc["symbol"] == symbol
    assert doc["start"] == "2014-05-07" and doc["end"] == "2014-05-09"


@then(parsers.parse("trades.json lists {n:d} closed trades"))
def _trades_json(art_ctx: dict[str, Any], n: int) -> None:
    trades = json.loads(art_ctx["artifacts"].trades_json.read_text())
    assert len(trades) == n


@then("metrics.json records the four headline metrics")
def _metrics_json(art_ctx: dict[str, Any]) -> None:
    doc = json.loads(art_ctx["artifacts"].metrics_json.read_text())
    assert doc == art_ctx["metrics"].as_dict()
