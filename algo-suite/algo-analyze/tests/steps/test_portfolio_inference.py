"""Acceptance coverage of paired portfolio inputs, blocks, and read-only migration."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from algo_analyze.deflated import InferenceUnavailable
from algo_analyze.portfolio import load_portfolio_returns
from algo_analyze.reports import metrics_report, migration_inventory, significance_report
from algo_analyze.significance import paired_block_test, stationary_indices
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/portfolio_inference.feature")


@pytest.fixture
def pctx(tmp_path: Path) -> dict[str, Any]:
    """Allocate isolated paired artifacts."""
    return {"root": tmp_path, "a": tmp_path / "runs" / "a", "b": tmp_path / "runs" / "b"}


@given("complete paired engine portfolios")
def portfolios(pctx: dict[str, Any], portfolio_factory: Callable[..., None]) -> None:
    """Use deterministic, nondegenerate paired portfolios."""
    portfolio_factory(pctx["a"])
    portfolio_factory(pctx["b"], 1.0)
    pctx["original"] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in pctx["root"].rglob("*.json")
    }


# Independent constants for the 20-row ledger 0.00..0.19 (mpmath, 50 digits): sample SD is
# 0.01*sqrt(35); the Eq. 2 threshold uses N=10 with that dispersion.
LEDGER_SD = 0.05916079783099616
LEDGER_THRESHOLD = 0.09315449177094589


@when("portfolio metrics are reported with registered search history")
def metrics(pctx: dict[str, Any]) -> None:
    """Supply explicit multi-trial provenance as a ledger the analyzer must compute from."""
    path = pctx["root"] / "selection.json"
    path.write_text(
        json.dumps(
            dict(n_trials=10, interim_looks=1, frequency="calendar-day",
                 provenance="registered development search",
                 trials=[{"run_id": f"candidate-{i}", "daily_sharpe": i / 100}
                         for i in range(20)])
        )
    )
    pctx["selection"] = path
    try:
        pctx["report"] = metrics_report(pctx["a"], path)
    except InferenceUnavailable as exc:
        pctx["error_kind"], pctx["error"] = "unavailable", str(exc)
    except ValueError as exc:
        pctx["error_kind"], pctx["error"] = "error", str(exc)


@then("the ledger supplies the independently computed dispersion and threshold")
def ledger_values(pctx: dict[str, Any]) -> None:
    """A constant or declared dispersion must fail here; only the ledger's SD is acceptable."""
    result = pctx["report"]
    assert result["selection"]["trial_sharpe_std"] == pytest.approx(LEDGER_SD, abs=1e-15, rel=0)
    assert result["selection_threshold"] == pytest.approx(LEDGER_THRESHOLD, abs=1e-12, rel=0)
    assert result["selection"]["trial_count"] == 20
    assert result["selection"]["source_sha256"] == _sha256(pctx["selection"])
    assert result["portfolio"]["source_sha256"] == _sha256(pctx["a"] / "main.json")
    assert result["portfolio"]["contract_provenance"] == "declared"


def _sha256(path: Path) -> str:
    """Independent digest of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@given("a run written by the backtest artifact producer with engine equity")
def producer_run(pctx: dict[str, Any]) -> None:
    """Produce run.json, trades.json, metrics.json and inference-inputs.json via the producer."""
    from algo_backtest.artifacts import RunManifest, write_run_artifacts
    from algo_backtest.metrics import Metrics

    run = pctx["root"] / "runs" / "prod"
    run.mkdir(parents=True)
    write_run_artifacts(
        run,
        RunManifest(strategy="baseline", symbol="EURUSD", start="2020-01-01", end="2020-04-29",
                    params={}, success=True, closed_trades=0, broker_adapter="oanda"),
        closed_trades=[],
        metrics=Metrics(total_return=0.0, sharpe=0.0, max_drawdown=0.0, hit_rate=0.0),
    )
    start = datetime(2020, 1, 1, tzinfo=UTC)
    values, equity = [], 100000.0
    for i in range(121):
        values.append([int((start + timedelta(days=i)).timestamp()), equity])
        equity *= 1 + 0.004 * np.sin(i * 0.53) + 0.0005
    (run / "main.json").write_text(json.dumps(
        {"charts": {"Strategy Equity": {"series": {"Equity": {"values": values}}}}}))
    pctx["a"] = run


@given("the contract costs are edited after production")
def tampered_contract(pctx: dict[str, Any]) -> None:
    """Change the sidecar bytes without touching the digest the producer recorded."""
    contract = pctx["a"] / "inference-inputs.json"
    data = json.loads(contract.read_text())
    data["costs"] = "brokerage:oanda"  # same label, different bytes (formatting)
    contract.write_text(json.dumps(data, indent=4))


@given("the manifest records a different brokerage adapter")
def adapter_mismatch(pctx: dict[str, Any]) -> None:
    """Keep the sidecar and its digest intact but change the adapter the manifest resolved."""
    manifest = pctx["a"] / "run.json"
    data = json.loads(manifest.read_text())
    data["broker_adapter"] = "interactive-brokers"
    manifest.write_text(json.dumps(data, indent=2))


@given(parsers.parse("the manifest keeps only its {kept} field"))
def one_field_manifest(pctx: dict[str, Any], kept: str) -> None:
    """Drop the other producer field so verification must key on the remaining one."""
    manifest = pctx["a"] / "run.json"
    data = json.loads(manifest.read_text())
    for field in ("inference_inputs_sha256", "broker_adapter"):
        if field != kept:
            data.pop(field)
    manifest.write_text(json.dumps(data, indent=2))


@given("the contract names a different brokerage adapter")
def contract_adapter_mismatch(pctx: dict[str, Any]) -> None:
    """Change the sidecar's cost model so it no longer names the manifest's adapter."""
    contract = pctx["a"] / "inference-inputs.json"
    data = json.loads(contract.read_text())
    data["costs"] = "brokerage:interactive-brokers"
    contract.write_text(json.dumps(data, indent=2))


@then("the contract is producer-verified and its digest equals the manifest record")
def producer_verified(pctx: dict[str, Any]) -> None:
    """Producer-generated contracts are accepted only when bytes and adapter agree with run.json."""
    result = pctx["report"]
    manifest = json.loads((pctx["a"] / "run.json").read_text())
    assert result["status"] == "available"
    assert result["portfolio"]["contract_provenance"] == "producer-verified"
    assert result["portfolio"]["contract_sha256"] == manifest["inference_inputs_sha256"]
    assert result["portfolio"]["contract_sha256"] == _sha256(pctx["a"] / "inference-inputs.json")
    assert result["portfolio"]["costs"] == "brokerage:oanda"


@given(parsers.parse('complete paired engine portfolios under "{first}" and "{second}"'))
def nested_portfolios(pctx: dict[str, Any], portfolio_factory: Callable[..., None],
                      first: str, second: str) -> None:
    """Two runs sharing a basename in different experiment directories."""
    pctx["ids"] = (first, second)
    portfolio_factory(pctx["root"] / "runs" / first)
    portfolio_factory(pctx["root"] / "runs" / second, 1.0)


@when("paired portfolio significance is reported for the nested runs")
def nested_significance(pctx: dict[str, Any]) -> None:
    """Identify runs by their relative identifiers, as the CLI receives them."""
    first, second = pctx["ids"]
    pctx["report"] = significance_report(pctx["root"], first, second, block_lengths=[5],
                                         n_resamples=199, seed=7, block_rule="preregistered")


@then(parsers.parse('the report names "{first}" and "{second}"'))
def nested_names(pctx: dict[str, Any], first: str, second: str) -> None:
    """Basenames alone would collide; the full relative identifier must survive."""
    assert pctx["report"]["status"] == "available"
    assert (pctx["report"]["run_a"], pctx["report"]["run_b"]) == (first, second)


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
            pctx["root"],
            "a",
            "b",
            block_lengths=[5, 10],
            n_resamples=199,
            seed=7,
            block_rule="preregistered",
        )
    except InferenceUnavailable as exc:
        pctx["error_kind"], pctx["error"] = "unavailable", str(exc)
    except ValueError as exc:
        pctx["error_kind"], pctx["error"] = "error", str(exc)


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
    except InferenceUnavailable as exc:
        pctx["error_kind"], pctx["error"] = "unavailable", str(exc)
    except ValueError as exc:
        pctx["error_kind"], pctx["error"] = "error", str(exc)


@then(parsers.parse('portfolio inference is "{outcome}" diagnosing "{reason}"'))
def diagnosis(pctx: dict[str, Any], outcome: str, reason: str) -> None:
    """Assert the channel: an unavailable report (or InferenceUnavailable) versus a hard error."""
    if outcome == "error":
        assert pctx.get("error_kind") == "error", pctx.get("report") or pctx.get("error_kind")
        assert reason in pctx["error"]
    elif "report" in pctx:
        assert "error" not in pctx
        assert pctx["report"]["status"] == "unavailable", pctx["report"]
        assert reason in pctx["report"]["reason"]
    else:
        assert pctx["error_kind"] == "unavailable", pctx["error"]
        assert reason in pctx["error"]


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
