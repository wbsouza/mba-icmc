"""Acceptance coverage of paired portfolio inputs, blocks, and read-only migration."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from algo_analyze.portfolio import load_portfolio_returns
from algo_analyze.reports import metrics_report, migration_inventory, significance_report
from algo_analyze.significance import paired_block_test, stationary_indices
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/portfolio_inference.feature")


def write_portfolio(path: Path, offset: float = 0.0) -> None:
    """Write actual engine-shape equity, deliberately unrelated to trade returns."""
    path.mkdir(parents=True, exist_ok=True)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    values, equity = [], 100000.0
    for i in range(121):
        values.append([int((start + timedelta(days=i)).timestamp()), equity])
        equity *= 1 + 0.005 * np.sin(i * 0.71 + offset) + 0.001 + offset * 0.0001
    artifacts = {
        "main.json": {"charts": {"Strategy Equity": {"series": {"Equity": {"values": values}}}}},
        "run.json": {
            "success": True,
            "symbol": "EURUSD",
            "start": "2020-01-01",
            "end": "2020-04-29",
        },
        "metrics.json": {
            "sharpe": 99.0,
            "total_return": 0.1,
            "max_drawdown": -0.1,
            "hit_rate": 0.5,
        },
        "trades.json": [{"return": 100}] * (2 if offset else 7),
        "inference-inputs.json": {
            "source": "main.json",
            "frequency": "calendar-day",
            "timezone": "UTC",
            "annualization": 365,
            "risk_free_daily": 0,
            "costs": "brokerage:fixture",
            "symbol": "EURUSD",
            "start": "2020-01-01",
            "end": "2020-04-30",
        },
    }
    for name, value in artifacts.items():
        (path / name).write_text(json.dumps(value))


@pytest.fixture
def pctx(tmp_path: Path) -> dict[str, Any]:
    """Allocate isolated paired artifacts."""
    return {"root": tmp_path, "a": tmp_path / "runs" / "a", "b": tmp_path / "runs" / "b"}


@given("complete paired engine portfolios")
def portfolios(pctx: dict[str, Any]) -> None:
    """Use deterministic, nondegenerate paired portfolios."""
    write_portfolio(pctx["a"])
    write_portfolio(pctx["b"], 1.0)
    pctx["original"] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in pctx["root"].rglob("*.json")
    }


@when("portfolio metrics are reported with registered search history")
def metrics(pctx: dict[str, Any]) -> None:
    """Supply explicit multi-trial provenance."""
    path = pctx["root"] / "selection.json"
    path.write_text(
        json.dumps(
            dict(n_trials=10, interim_looks=1, frequency="calendar-day",
                 provenance="registered development search",
                 trials=[{"run_id": f"candidate-{i}", "daily_sharpe": i / 100}
                         for i in range(20)])
        )
    )
    pctx["report"] = metrics_report(pctx["a"], path)


@then("probability and moments use daily engine equity with source hashes")
def metric_assert(pctx: dict[str, Any]) -> None:
    """Catch both trade-count and annualized-Sharpe mixing."""
    result = pctx["report"]
    assert result["schema_version"] == 2
    assert 0 <= result["deflated_sharpe_probability"] <= 1
    assert result["moments"]["n_returns"] == 120
    assert result["moments"]["observed_sharpe"] != 99
    assert result["descriptive_metrics"]["sharpe"] == 99
    assert len(result["portfolio"]["source_sha256"]) == 64
    assert len(result["selection"]["source_sha256"]) == 64
    assert result["selection"]["source_kind"] == "computed"
    assert result["selection"]["trial_count"] == 20


@when("paired portfolio significance is reported")
def significance(pctx: dict[str, Any]) -> None:
    """Exercise explicit primary and sensitivity settings."""
    try:
        pctx["report"] = significance_report(
            pctx["a"],
            pctx["b"],
            block_lengths=[5, 10],
            n_resamples=199,
            seed=7,
            block_rule="preregistered",
        )
    except ValueError as exc:
        pctx["error"] = str(exc)


@then("the bootstrap records effect interval settings and sensitivity")
def block_assert(pctx: dict[str, Any]) -> None:
    """Require effect and uncertainty metadata on paired daily observations."""
    report = pctx["report"]
    primary = report["primary"]
    assert report["status"] == "available"
    assert primary["method"] == "paired_stationary_bootstrap"
    assert primary["seed"] == 7 and primary["n_observations"] == 120
    assert primary["confidence_interval"][0] <= primary["effect"]
    assert primary["confidence_interval"][1] >= primary["effect"]
    assert report["sensitivity"][0]["block_length"] == 10


@when("stationary resampling indices are drawn twice")
def indices(pctx: dict[str, Any]) -> None:
    """Expose labeled row indices, not just a p-value."""
    pctx["indices"] = stationary_indices(120, 5, 199, 7)
    pctx["repeat"] = stationary_indices(120, 5, 199, 7)


@then("indices are reproducible with ordered circular continuations and pairing")
def index_assert(pctx: dict[str, Any]) -> None:
    """Labeled corresponding observations use identical rows; most transitions continue blocks."""
    ix = pctx["indices"]
    assert np.array_equal(ix, pctx["repeat"])
    assert np.mean(ix[:, 1:] == (ix[:, :-1] + 1) % 120) > 0.75
    a, b = np.arange(120), np.arange(120) + 1000
    assert np.all(b[ix] - a[ix] == 1000)
    args = dict(block_length=5, n_resamples=199, seed=7)
    ar, br = load_portfolio_returns(pctx["a"]), load_portfolio_returns(pctx["b"])
    assert paired_block_test(ar.returns, br.returns, **args) == paired_block_test(
        ar.returns, br.returns, **args
    )


@given(parsers.parse("the challenger portfolio has {problem}"))
def corrupt(pctx: dict[str, Any], problem: str) -> None:
    """Introduce exactly one coverage or integrity failure."""
    path = pctx["b"] / "main.json"
    data = json.loads(path.read_text())
    values = data["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    if problem == "missing day":
        values.pop(10)
    elif problem == "duplicate":
        values.insert(10, values[10])
    elif problem == "NaN equity":
        values[10][1] = float("nan")
    elif problem == "wrong symbol":
        contract = pctx["b"] / "inference-inputs.json"
        metadata = json.loads(contract.read_text())
        metadata["symbol"] = "USDJPY"
        contract.write_text(json.dumps(metadata))
    elif problem == "missing contract":
        (pctx["b"] / "inference-inputs.json").unlink()
    path.write_text(json.dumps(data))


@when(parsers.parse("block inference receives {problem}"))
def invalid_blocks(pctx: dict[str, Any], problem: str) -> None:
    """Insufficient dependence information cannot yield spurious significance."""
    n = 20 if problem == "short history" else 120
    a = np.arange(n, dtype=float).tolist()
    b = [x + (1 if problem == "constant differences" else 0) for x in a]
    length = 20 if problem == "insufficient blocks" else 5
    try:
        paired_block_test(a, b, block_length=length, n_resamples=199, seed=7)
    except ValueError as exc:
        pctx["error"] = str(exc)


@then(parsers.parse('portfolio inference diagnoses "{reason}"'))
def diagnosis(pctx: dict[str, Any], reason: str) -> None:
    """Accept structured unavailable output or an explicit invalid-artifact error."""
    assert reason in (pctx.get("error") or json.dumps(pctx["report"]))


@when("migration inventory is generated")
def inventory(pctx: dict[str, Any]) -> None:
    """Inventory without modifying the raw run artifacts."""
    pctx["report"] = migration_inventory(pctx["root"])


@then("legacy files remain unchanged and missing search history is identified")
def preserved(pctx: dict[str, Any]) -> None:
    """Historical bytes cannot acquire corrected statistical meaning by relabeling."""
    for name, digest in pctx["original"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    assert len(pctx["report"]["runs"]) == 2
    assert all("selection history" in run["reason"] for run in pctx["report"]["runs"])
