"""Steps for experiment_spec.feature — loading + validating an experiment spec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.experiment import Experiment, Run, load_experiment
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/experiment_spec.feature")


@pytest.fixture
def cctx(tmp_path: Path) -> dict[str, Any]:
    """Holds the written spec path + the loaded experiment / error."""
    return {"dir": tmp_path}


def _write_spec(cctx: dict[str, Any], spec: dict[str, Any]) -> None:
    """Write an experiment spec to a temp YAML and remember its path."""
    path = cctx["dir"] / "experiment.yaml"
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    cctx["spec_path"] = path


def _run(cells: dict[str, str]) -> dict[str, Any]:
    """Build one run dict from a Gherkin table row, nesting fast/slow/size."""
    run: dict[str, Any] = {}
    params: dict[str, Any] = {}
    for key, value in cells.items():
        if key in ("fast", "slow"):
            params[key] = int(value)
        elif key == "size":
            params[key] = float(value)
        else:
            run[key] = value
    if params:
        run["params"] = params
    return run


@given("an experiment spec with runs:")
def _spec_with_table(cctx: dict[str, Any], datatable: list[list[str]]) -> None:
    headers, *rows = datatable
    runs = [_run(dict(zip(headers, row, strict=True))) for row in rows]
    _write_spec(cctx, {"experiment": "test-experiment", "runs": runs})


@given('an experiment spec with a run carrying an unknown "leverage" field')
def _spec_unknown_field(cctx: dict[str, Any]) -> None:
    _write_spec(cctx, {
        "experiment": "test-experiment",
        "runs": [{
            "id": "x", "strategy": "baseline-ma", "symbol": "EURUSD",
            "from": "2014-05-07", "to": "2014-05-09", "leverage": 2,
        }],
    })


@given("an experiment spec with no runs")
def _spec_no_runs(cctx: dict[str, Any]) -> None:
    _write_spec(cctx, {"experiment": "test-experiment", "runs": []})


@given("an experiment spec with runs but no experiment name")
def _spec_no_name(cctx: dict[str, Any]) -> None:
    _write_spec(cctx, {"runs": [{
        "id": "x", "strategy": "baseline-ma", "symbol": "EURUSD",
        "from": "2014-05-07", "to": "2014-05-09",
    }]})


@when("I load the experiment")
def _load(cctx: dict[str, Any]) -> None:
    cctx["experiment"] = load_experiment(cctx["spec_path"])


@when("I load the experiment expecting failure")
def _load_failing(cctx: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        load_experiment(cctx["spec_path"])
    cctx["error"] = str(exc_info.value)


def _by_id(experiment: Experiment, run_id: str) -> Run:
    """The run with the given id (the spec guarantees uniqueness)."""
    return next(r for r in experiment.runs if r.run_id == run_id)


@then(parsers.parse("the experiment has {n:d} runs"))
def _count(cctx: dict[str, Any], n: int) -> None:
    assert len(cctx["experiment"].runs) == n


@then(parsers.parse('run "{rid}" runs baseline-ma on EURUSD over {start} to {end}'))
def _runs_over(cctx: dict[str, Any], rid: str, start: str, end: str) -> None:
    run = _by_id(cctx["experiment"], rid)
    assert run.strategy == "baseline-ma" and run.symbol == "EURUSD"
    assert run.start.isoformat() == start and run.end.isoformat() == end


@then(parsers.parse('run "{rid}" has params fast {fast:d}, slow {slow:d} and size {size:g}'))
def _has_params(cctx: dict[str, Any], rid: str, fast: int, slow: int, size: float) -> None:
    run = _by_id(cctx["experiment"], rid)
    assert run.params == {"fast": str(fast), "slow": str(slow), "size": str(size)}


@then("loading fails naming the duplicate run id")
def _dup(cctx: dict[str, Any]) -> None:
    assert "duplicate" in cctx["error"] and "dup" in cctx["error"]


@then("loading fails saying the run is invalid")
def _invalid(cctx: dict[str, Any]) -> None:
    assert "invalid" in cctx["error"]


@then("loading fails saying the experiment has no runs")
def _no_runs(cctx: dict[str, Any]) -> None:
    assert "no runs" in cctx["error"]


@then("loading fails saying the experiment name is required")
def _name_required(cctx: dict[str, Any]) -> None:
    assert "experiment" in cctx["error"] and "required" in cctx["error"]


@then("loading fails naming the unknown field")
def _unknown(cctx: dict[str, Any]) -> None:
    assert "unknown" in cctx["error"] and "leverage" in cctx["error"]
