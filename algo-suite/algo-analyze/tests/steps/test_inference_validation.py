"""Failure-mode acceptance tests for scientific input integrity and numerical bounds."""

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from algo_analyze.deflated import deflated_sharpe, return_moments
from algo_analyze.reports import metrics_report, migration_inventory, significance_report
from algo_analyze.significance import paired_block_test
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/inference_validation.feature")


@pytest.fixture
def evidence(tmp_path: Path, portfolio_factory: Callable[..., None]) -> dict[str, Any]:
    """Keep every corrupt artifact isolated from saved experiments."""
    return {"root": tmp_path, "run": tmp_path / "runs" / "one", "write": portfolio_factory}


@given("valid inference evidence")
def valid_evidence(evidence: dict[str, Any]) -> None:
    """Supply a complete calendar and explicit registered selection history."""
    evidence["write"](evidence["run"])
    path = evidence["run"] / "selection.json"
    path.write_text(json.dumps(dict(n_trials=10, trial_count=20, interim_looks=1,
                                   trial_sharpe_std=.02, frequency="calendar-day",
                                   provenance="registered development search")))
    evidence["selection"] = path


def _change_equity(data: dict[str, Any], change: str) -> None:
    """Alter one engine chart contract condition."""
    series = data["charts"]["Strategy Equity"]["series"]["Equity"]
    rows = series["values"]
    changes = {
        "nonlist values": lambda: series.update(values={}),
        "malformed point": lambda: rows.__setitem__(0, [1]),
        "boolean timestamp": lambda: rows[0].__setitem__(0, True),
        "text equity": lambda: rows[0].__setitem__(1, "100"),
        "zero equity": lambda: rows[0].__setitem__(1, 0),
        "overflow return": lambda: rows[0].__setitem__(1, 1e-320),
        "candle points": lambda: series.update(values=_candles(rows)),
        "duplicate": lambda: rows.insert(10, rows[10]),
        "consistent Return series": lambda: _add_return_series(data, rows, 0.0),
        "mismatching Return series": lambda: _add_return_series(data, rows, 1e-4),
        "text Return percent": lambda: data["charts"]["Strategy Equity"]["series"].update(
            Return={"values": [[rows[1][0], "0.1"]]}),
        "malformed Return point": lambda: data["charts"]["Strategy Equity"]["series"].update(
            Return={"values": [[rows[1][0], 0.1, 0.2]]}),
        "null Return series": lambda: series_of(data).update(Return=None),
        "null Return values": lambda: series_of(data).update(Return={"values": None}),
        "empty Return object": lambda: series_of(data).update(Return={}),
        "duplicate Return timestamps": lambda: series_of(data).update(
            Return={"values": [[rows[1][0], 99.0], [rows[1][0], 0.0]]}),
        "missing charts": lambda: data.pop("charts"),
    }
    changes[change]()


def series_of(data: dict[str, Any]) -> dict[str, Any]:
    """Return the Strategy Equity series container of a main.json document."""
    container: dict[str, Any] = data["charts"]["Strategy Equity"]["series"]
    return container


def _candles(rows: list[list[float]]) -> list[list[float]]:
    """Build LEAN-shaped end-stamped candles: open is the previous mark, close is this one."""
    candles = []
    for previous, row in zip([rows[0], *rows[:-1]], rows, strict=True):
        open_, close = previous[1], row[1]
        candles.append([row[0], open_, max(open_, close) + 1, min(open_, close) - 1, close])
    return candles


def _add_return_series(data: dict[str, Any], rows: list[list[float]], error: float) -> None:
    """Add LEAN's daily Return series (percent, 7 significant digits) with an optional error."""
    values = []
    for previous, row in zip(rows, rows[1:], strict=False):
        percent = float(f"{(row[1] / previous[1] - 1) * 100:.7g}")
        values.append([row[0], percent])
    values[5][1] += error
    data["charts"]["Strategy Equity"]["series"]["Return"] = {"values": values, "unit": "%"}


def _change_metadata(data: dict[str, Any], change: str) -> None:
    """Corrupt one manifest field without mixing unrelated conditions."""
    changes = {
        "unsuccessful": ("success", False), "wrong timezone": ("timezone", "US/Eastern"),
        "empty costs": ("costs", ""), "wrong frequency": ("frequency", "year"),
        "boolean n_trials": ("n_trials", True), "excessive n_trials": ("n_trials", 21),
        "empty provenance": ("provenance", ""), "reversed dates": ("end", "2019-12-30"),
    }
    if change.startswith("missing "):
        data.pop(change.removeprefix("missing "))
    elif change in _LEDGERS:
        data.clear()
        data.update(_LEDGERS[change])
    else:
        key, value = changes[change]
        data[key] = value


_LEDGER_META = {"n_trials": 2, "interim_looks": 1, "frequency": "calendar-day",
                "provenance": "registered ledger"}
_LEDGERS: dict[str, Any] = {
    "ledger with text sharpe": {**_LEDGER_META, "trials": [0.01, "0.02", 0.03]},
    "ledger with NaN sharpe": {**_LEDGER_META, "trials": [0.01, float("nan"), 0.03]},
    "single trial ledger": {**_LEDGER_META, "trials": [{"daily_sharpe": 0.01}]},
    "ledger below declared n_trials": {**_LEDGER_META, "n_trials": 5, "trials": [0.01, 0.02]},
    "ledger with text n_trials": {**_LEDGER_META, "n_trials": "2", "trials": [0.01, 0.02]},
    "nonlist trials": {**_LEDGER_META, "trial_count": 2, "trial_sharpe_std": 0.02,
                       "trials": {"broken": "ledger"}},
    "null trials": {**_LEDGER_META, "trial_count": 2, "trial_sharpe_std": 0.02, "trials": None},
    "ledger declaring dispersion": {**_LEDGER_META, "trial_sharpe_std": 0.5,
                                    "trials": [0.01, 0.02]},
}


@given(parsers.parse("artifact {artifact} has {change}"))
def changed_artifact(evidence: dict[str, Any], artifact: str, change: str) -> None:
    """Write malformed evidence in its actual on-disk form."""
    path = evidence["run"] / artifact
    if change == "absent":
        path.unlink()
        return
    if change in ("invalid JSON", "nonobject", "scalar JSON"):
        path.write_text({"invalid JSON": "{", "nonobject": "[]", "scalar JSON": "3"}[change])
        return
    data = json.loads(path.read_text())
    if artifact == "main.json":
        _change_equity(data, change)
    else:
        _change_metadata(data, change)
    path.write_text(json.dumps(data))
    if change == "reversed dates":
        contract = evidence["run"] / "inference-inputs.json"
        data = json.loads(contract.read_text())
        data["end"] = "2019-12-31"
        contract.write_text(json.dumps(data))


@when("the evidence is analyzed")
def analyze_evidence(evidence: dict[str, Any]) -> None:
    """Use the public report boundary with real artifact reads."""
    try:
        evidence["result"] = metrics_report(evidence["run"], evidence["selection"])
    except ValueError as exc:
        evidence["error"] = str(exc)


@given("the run window covers only three daily returns")
def three_returns(evidence: dict[str, Any]) -> None:
    """Shrink the declared window and manifest to four midnight endpoints."""
    run = evidence["run"]
    for name, end in (("run.json", "2020-01-03"), ("inference-inputs.json", "2020-01-04")):
        data = json.loads((run / name).read_text())
        data["end"] = end
        (run / name).write_text(json.dumps(data))


@then(parsers.parse('the evidence is "{outcome}" mentioning "{diagnostic}"'))
def channel(evidence: dict[str, Any], outcome: str, diagnostic: str) -> None:
    """Assert the channel (error vs unavailable report) and the diagnostic on that channel."""
    if outcome == "error":
        assert "result" not in evidence, evidence.get("result")
        assert diagnostic in evidence["error"]
    else:
        assert "error" not in evidence, evidence.get("error")
        assert evidence["result"]["status"] == "unavailable"
        assert diagnostic in evidence["result"]["reason"]


@then("the evidence reproduces the line-series moments")
def candle_moments(evidence: dict[str, Any]) -> None:
    """Candle close must give exactly the returns an [epoch,value] export gives."""
    from algo_analyze.deflated import return_moments
    from algo_analyze.portfolio import load_portfolio_returns

    reference = evidence["root"] / "line-reference"
    evidence["write"](reference)
    expected = return_moments(load_portfolio_returns(reference).returns)
    assert evidence["result"]["status"] == "available"
    assert evidence["result"]["moments"]["observed_sharpe"] == expected["observed_sharpe"]
    assert evidence["result"]["moments"]["kurtosis"] == expected["kurtosis"]


@then(parsers.parse('the evidence diagnostic includes "{diagnostic}"'))
def diagnosis(evidence: dict[str, Any], diagnostic: str) -> None:
    """Require precise diagnostics rather than a generic exception or NaN output."""
    assert diagnostic in (evidence.get("error") or json.dumps(evidence.get("result")))


@then("the evidence has 120 daily observations and a finite probability")
def valid_result(evidence: dict[str, Any]) -> None:
    """Valid evidence yields the full daily grid and a finite probability."""
    result = evidence["result"]
    assert result["status"] == "available"
    assert result["moments"]["n_returns"] == 120
    assert math.isfinite(result["deflated_sharpe_probability"])


@when("paired evidence has different cost assumptions")
def mismatched_costs(evidence: dict[str, Any]) -> None:
    """Same timestamps do not excuse incompatible net-return conventions."""
    other = evidence["root"] / "runs" / "other"
    evidence["write"](other, 1.)
    contract = other / "inference-inputs.json"
    data = json.loads(contract.read_text())
    data["costs"] = "different fees"
    contract.write_text(json.dumps(data))
    try:
        significance_report(evidence["root"], "one", "other", block_lengths=[5],
                            n_resamples=199, seed=7, block_rule="development rule")
    except ValueError as exc:
        evidence["error"] = str(exc)


@when("paired evidence has an unsupported sensitivity length")
def unavailable_sensitivity(evidence: dict[str, Any]) -> None:
    """Keep all prespecified sensitivity entries even when one has too few blocks."""
    other = evidence["root"] / "runs" / "other"
    evidence["write"](other, 1.)
    evidence["result"] = significance_report(evidence["root"], "one", "other",
                                             block_lengths=[5, 20], n_resamples=199, seed=7,
                                             block_rule="development rule")


@then("the primary inference is available and the sensitivity explains insufficient blocks")
def sensitivity_diagnostic(evidence: dict[str, Any]) -> None:
    """Do not silently omit a failed sensitivity analysis."""
    assert evidence["result"]["status"] == "available"
    result = evidence["result"]["sensitivity"][0]
    assert result["status"] == "unavailable"
    assert "10 expected blocks" in result["reason"]


@when("the evidence inventory is generated")
def inventory(evidence: dict[str, Any]) -> None:
    """Inventory catches a malformed run while keeping the scan usable."""
    evidence["result"] = migration_inventory(evidence["root"])


@then("the inventory identifies one invalid run")
def invalid_inventory(evidence: dict[str, Any]) -> None:
    """The invalid entry cannot be mistaken for corrected inference."""
    assert len(evidence["result"]["runs"]) == 1
    assert evidence["result"]["runs"][0]["status"] == "invalid"


@when(parsers.parse("block settings are {problem}"))
def invalid_settings(evidence: dict[str, Any], problem: str) -> None:
    """Exercise settings through public report or public numerical boundaries."""
    try:
        if problem in ("duplicated", "missing rule"):
            significance_report(evidence["root"], "one", "one", block_lengths=[5, 5],
                                n_resamples=199, seed=7,
                                block_rule="" if problem == "missing rule" else "registered")
            return
        _invalid_block_call(problem)
    except ValueError as exc:
        evidence["error"] = str(exc)


def _invalid_block_call(problem: str) -> None:
    """Vary one numerical setting or paired observation contract."""
    settings: dict[str, Any] = dict(block_length=3, n_resamples=199, seed=7, alpha=.05)
    changes = {"zero resamples": ("n_resamples", 0), "negative seed": ("seed", -1),
               "invalid alpha": ("alpha", 0), "unresolved alpha": ("alpha", .001)}
    if problem in changes:
        key, value = changes[problem]
        settings[key] = value
    a, b = [0.] * 60, np.sin(np.arange(60)).tolist()
    if problem == "unequal lengths":
        b.pop()
    elif problem == "nonfinite returns":
        b[0] = float("nan")
    elif problem == "difference overflow":
        a, b = [-1e308] * 60, [1e308] * 60
    paired_block_test(a, b, **settings)


@when(parsers.parse("return moments receive {problem}"))
def invalid_moments(evidence: dict[str, Any], problem: str) -> None:
    """Finite source values can still overflow centering and deserve a diagnostic."""
    values = {"short history": [1, 2, 3], "nonfinite history": [1, 2, 3, float("nan")],
              "constant history": [1] * 4, "centering overflow": [1.7e308] * 3 + [-1.7e308]}
    try:
        return_moments(values[problem])
    except ValueError as exc:
        evidence["error"] = str(exc)


@when(parsers.parse("DSR receives {problem}"))
def invalid_dsr(evidence: dict[str, Any], problem: str) -> None:
    """Never serialize an overflow as a probability or selection threshold."""
    args: dict[str, Any] = dict(observed_sharpe=.2, n_returns=100, skew=0., kurtosis=3.,
                                n_trials=10, trial_sharpe_std=.1, provenance="registered")
    changes = {"huge Sharpe": {"observed_sharpe": 1e308},
               "huge variance": {"observed_sharpe": 1e100, "kurtosis": 1e308},
               "huge skew": {"skew": 1e308},
               "threshold overflow": {"n_trials": 1000, "trial_sharpe_std": 1e308},
               "missing provenance": {"provenance": ""}}
    args.update(changes[problem])
    try:
        deflated_sharpe(**args)
    except ValueError as exc:
        evidence["error"] = str(exc)


@when(parsers.parse("significance CLI receives {option} without portfolio data"))
def missing_cli(evidence: dict[str, Any], option: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid settings must be actionable even before a simulation has produced equity."""
    from algo_analyze.cli import app
    from typer.testing import CliRunner

    monkeypatch.setenv("ALGO_DATA_ROOT", str(evidence["root"] / "empty"))
    monkeypatch.setenv("ALGO_CONF_DIR", str(evidence["root"] / "conf"))
    args = ["significance", "--runs", "missing-a", "--runs", "missing-b", "--block-rule", "prior"]
    if not option.startswith("--block-length"):
        args.extend(["--block-length", "5"])
    evidence["cli"] = CliRunner().invoke(app, [*args, *option.split()])


@then(parsers.parse('the CLI rejects the setting with "{diagnostic}"'))
def rejected_cli(evidence: dict[str, Any], diagnostic: str) -> None:
    """Reject invalid invocation instead of reporting unavailable evidence successfully."""
    assert evidence["cli"].exit_code == 2
    assert diagnostic in evidence["cli"].output


@when("inference dependency contracts are checked against boundary violations")
def architecture_contract(evidence: dict[str, Any]) -> None:
    """Exercise direct and relative import boundary violations without mutating production."""
    from inference_quality import architecture_errors

    violations = [("deflated", "import pathlib"), ("significance", "import algo_backtest"),
                  ("portfolio", "from .cli import main"),
                  ("reports", "from algo_backtest.engine import something"),
                  ("deflated", '__import__("os")')]
    evidence["violations"] = [architecture_errors(module, source) for module, source in violations]
    evidence["permitted"] = architecture_errors("significance", "import numpy")


@then("the architecture checker rejects each violation and accepts permitted imports")
def architecture_assert(evidence: dict[str, Any]) -> None:
    """A checker that merely prints passing summaries must fail this test."""
    assert all(evidence["violations"])
    assert not evidence["permitted"]


@when("the inference quality gate sees an unexecuted numerical module")
def uncovered_module(evidence: dict[str, Any]) -> None:
    """Feed valid coverage JSON shape with zero executed statements to the real gate."""
    from inference_quality import score_module

    evidence["quality_errors"] = score_module("deflated", {
        "algo_analyze/deflated.py": {"executed_lines": [], "missing_lines": [1, 2, 3]},
    })


@then("the quality checker reports coverage below its fixed threshold")
def uncovered_assert(evidence: dict[str, Any]) -> None:
    """Coverage enforcement remains deterministic regardless of function complexity."""
    assert any("below 95%" in error for error in evidence["quality_errors"])
