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


def _baseline_manifest(closed_trades: int) -> RunManifest:
    """A minimal manifest for the normalization scenarios (its contents are unchecked)."""
    return RunManifest(
        strategy="baseline-ma", symbol="EURUSD", start="2014-05-07", end="2014-05-09",
        params={}, success=True, closed_trades=closed_trades,
    )


@given(
    parsers.parse(
        "a finished run with a closed trade priced at entry {entry:g}, "
        "quantity {quantity:g} and profit {profit:g}"
    )
)
def _finished_run_priced_trade(
    art_ctx: dict[str, Any], entry: float, quantity: float, profit: float
) -> None:
    """A closed trade with the raw LEAN fields the normalizer keys off."""
    art_ctx["closed_trades"] = [
        {"entryPrice": entry, "quantity": quantity, "profitLoss": profit}
    ]
    art_ctx["metrics"] = Metrics(total_return=0.0, sharpe=0.0, max_drawdown=0.0, hit_rate=0.0)
    art_ctx["manifest"] = _baseline_manifest(1)


@given(parsers.parse("a finished run with a closed trade reporting only profitLoss {profit:g}"))
def _finished_run_pnl_only_trade(art_ctx: dict[str, Any], profit: float) -> None:
    """A closed trade that lacks the pricing fields needed to compute a return."""
    art_ctx["closed_trades"] = [{"profitLoss": profit}]
    art_ctx["metrics"] = Metrics(total_return=0.0, sharpe=0.0, max_drawdown=0.0, hit_rate=0.0)
    art_ctx["manifest"] = _baseline_manifest(1)


@given(
    parsers.parse(
        "a finished run with a closed trade priced at entry {entry:g}, "
        "quantity {quantity:g} and an infinite profit"
    )
)
def _finished_run_infinite_profit_trade(
    art_ctx: dict[str, Any], entry: float, quantity: float
) -> None:
    """A closed trade whose cost basis is fine but whose computed return is not finite."""
    art_ctx["closed_trades"] = [
        {"entryPrice": entry, "quantity": quantity, "profitLoss": float("inf")}
    ]
    art_ctx["metrics"] = Metrics(total_return=0.0, sharpe=0.0, max_drawdown=0.0, hit_rate=0.0)
    art_ctx["manifest"] = _baseline_manifest(1)


@given(
    parsers.parse(
        "a finished run with a closed trade priced at entry {entry:g}, "
        "quantity {quantity:g}, profit {profit:g} and a bogus raw return of {bogus:g}"
    )
)
def _finished_run_trade_with_bogus_return(
    art_ctx: dict[str, Any], entry: float, quantity: float, profit: float, bogus: float
) -> None:
    """A closed trade carrying a pre-existing `return` that must not be trusted as-is."""
    art_ctx["closed_trades"] = [
        {"entryPrice": entry, "quantity": quantity, "profitLoss": profit, "return": bogus}
    ]
    art_ctx["metrics"] = Metrics(total_return=0.0, sharpe=0.0, max_drawdown=0.0, hit_rate=0.0)
    art_ctx["manifest"] = _baseline_manifest(1)


@then(parsers.parse("trades.json trade {index:d} has a normalized return of {value:g}"))
def _trade_has_return(art_ctx: dict[str, Any], index: int, value: float) -> None:
    trades = json.loads(art_ctx["artifacts"].trades_json.read_text())
    assert trades[index]["return"] == pytest.approx(value)


@then(parsers.parse("trades.json trade {index:d} has no normalized return field"))
def _trade_has_no_return(art_ctx: dict[str, Any], index: int) -> None:
    trades = json.loads(art_ctx["artifacts"].trades_json.read_text())
    assert "return" not in trades[index]


@then(parsers.parse("trades.json trade {index:d} still reports its raw profitLoss of {value:g}"))
def _trade_keeps_raw_profit_loss(art_ctx: dict[str, Any], index: int, value: float) -> None:
    trades = json.loads(art_ctx["artifacts"].trades_json.read_text())
    assert trades[index]["profitLoss"] == pytest.approx(value)


@then(parsers.parse("trades.json trade {index:d} still reports a non-finite raw profitLoss"))
def _trade_keeps_non_finite_profit_loss(art_ctx: dict[str, Any], index: int) -> None:
    trades = json.loads(art_ctx["artifacts"].trades_json.read_text())
    assert trades[index]["profitLoss"] == float("inf")
