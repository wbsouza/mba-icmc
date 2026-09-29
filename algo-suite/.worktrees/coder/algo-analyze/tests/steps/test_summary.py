"""Steps for summary.feature — aggregating experiment manifests into the Chapter-4 CSV."""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import Any

import pytest
from algo_analyze.cli import app
from algo_analyze.summary import SUMMARY_COLUMNS
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/summary.feature")


@pytest.fixture
def sctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root (zero-config)."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {"data_root": data_root, "out": tmp_path / "summary.csv"}


def _row(experiment: str, run_id: str, strategy: str = "baseline-ma") -> dict[str, Any]:
    """A full, valid manifest row (all canonical columns)."""
    return {
        "experiment": experiment, "run_id": run_id, "strategy": strategy,
        "symbol": "EURUSD", "from": "2014-05-07", "to": "2014-05-09",
        "success": True, "closed_trades": 0, "total_return": 0.0, "sharpe": 0.0,
        "max_drawdown": 0.0, "hit_rate": 0.0,
        "run_dir": f"runs/experiments/{experiment}/{run_id}",
    }


def _experiment_dir(sctx: dict[str, Any], name: str) -> Path:
    directory = sctx["data_root"] / "runs" / "experiments" / name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_manifest(sctx: dict[str, Any], name: str, rows: list[dict[str, Any]]) -> None:
    manifest = {"experiment": name, "generated_at": "2020-01-01T00:00:00+00:00", "runs": rows}
    (_experiment_dir(sctx, name) / "experiment.json").write_text(json.dumps(manifest, indent=2))


def _ids(spec: str) -> list[str]:
    return [token.strip() for token in spec.split(",")]


@given(parsers.parse('a successful experiment "{name}" with runs "{ids}"'))
def _successful_experiment(sctx: dict[str, Any], name: str, ids: str) -> None:
    _write_manifest(sctx, name, [_row(name, rid) for rid in _ids(ids)])


@given(parsers.parse(
    'a successful experiment "{name}" with a baseline-ma and a baseline-meanrev run'
))
def _mixed_experiment(sctx: dict[str, Any], name: str) -> None:
    _write_manifest(sctx, name, [
        _row(name, "ma", strategy="baseline-ma"),
        _row(name, "mr", strategy="baseline-meanrev"),
    ])


@given(parsers.parse('a failed experiment "{name}"'))
def _failed_experiment(sctx: dict[str, Any], name: str) -> None:
    (_experiment_dir(sctx, name) / "experiment-error.json").write_text(
        json.dumps({"experiment": name, "failed_run": "x", "completed_runs": []})
    )


@given(parsers.parse('an experiment "{name}" with both a manifest and an error artifact'))
def _both_artifacts(sctx: dict[str, Any], name: str) -> None:
    _write_manifest(sctx, name, [_row(name, "a1")])
    error = _experiment_dir(sctx, name) / "experiment-error.json"
    error.write_text(json.dumps({"experiment": name}))


@given(parsers.parse('a successful experiment "{name}" whose manifest is corrupt'))
def _corrupt_manifest(sctx: dict[str, Any], name: str) -> None:
    (_experiment_dir(sctx, name) / "experiment.json").write_text("{ not valid json")


@given(parsers.parse('a successful experiment "{name}" whose row has an unknown column'))
def _unknown_column(sctx: dict[str, Any], name: str) -> None:
    row = _row(name, "a1")
    row["leverage"] = 2
    _write_manifest(sctx, name, [row])


@given(parsers.parse('a successful experiment "{name}" whose row is labeled experiment "{label}"'))
def _mislabeled_row(sctx: dict[str, Any], name: str, label: str) -> None:
    row = _row(name, "a1")
    row["experiment"] = label
    _write_manifest(sctx, name, [row])


@given(parsers.parse('a successful experiment "{name}" with a failed run'))
def _failed_run_row(sctx: dict[str, Any], name: str) -> None:
    row = _row(name, "a1")
    row["success"] = False
    _write_manifest(sctx, name, [row])


@given("no experiments have run")
def _no_experiments(sctx: dict[str, Any]) -> None:
    pass  # empty data root


def _invoke(sctx: dict[str, Any], out: Path) -> None:
    sctx["cli"] = CliRunner().invoke(app, ["summary", "--out", str(out)])


@when("I aggregate the experiments")
def _aggregate(sctx: dict[str, Any]) -> None:
    _invoke(sctx, sctx["out"])
    assert sctx["cli"].exit_code == 0, sctx["cli"].output
    sctx["rows"] = list(csv.DictReader(io.StringIO(sctx["out"].read_text())))


@when("I aggregate the experiments expecting failure")
def _aggregate_failing(sctx: dict[str, Any]) -> None:
    _invoke(sctx, sctx["out"])


@when("I write the summary twice")
def _write_twice(sctx: dict[str, Any]) -> None:
    first, second = sctx["data_root"] / "a.csv", sctx["data_root"] / "b.csv"
    _invoke(sctx, first)
    assert sctx["cli"].exit_code == 0, sctx["cli"].output
    _invoke(sctx, second)
    assert sctx["cli"].exit_code == 0, sctx["cli"].output
    sctx["bytes"] = (first.read_bytes(), second.read_bytes())


@then(parsers.parse("the summary has {n:d} rows"))
def _row_count(sctx: dict[str, Any], n: int) -> None:
    assert len(sctx["rows"]) == n, sctx["rows"]


@then(parsers.parse("the summary has {n:d} row"))
def _row_count_singular(sctx: dict[str, Any], n: int) -> None:
    assert len(sctx["rows"]) == n, sctx["rows"]


@then("the summary columns are exactly the canonical set")
def _columns(sctx: dict[str, Any]) -> None:
    header = sctx["out"].read_text().splitlines()[0]
    assert header == ",".join(SUMMARY_COLUMNS), header


@then("the rows are ordered alpha/a1, alpha/a2, beta/b1, beta/b2")
def _order(sctx: dict[str, Any]) -> None:
    ordered = [(r["experiment"], r["run_id"]) for r in sctx["rows"]]
    assert ordered == [("alpha", "a1"), ("alpha", "a2"), ("beta", "b1"), ("beta", "b2")], ordered


@then(parsers.parse('the summary has both a "{a}" and a "{b}" strategy row'))
def _both_strategies(sctx: dict[str, Any], a: str, b: str) -> None:
    strategies = {r["strategy"] for r in sctx["rows"]}
    assert {a, b} <= strategies, strategies


@then(parsers.parse('the summary contains run "{rid}"'))
def _contains(sctx: dict[str, Any], rid: str) -> None:
    assert any(r["run_id"] == rid for r in sctx["rows"]), sctx["rows"]


@then("aggregation fails telling me to run an experiment first")
def _fail_no_experiments(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "experiment run" in sctx["cli"].output


@then("aggregation fails naming the inconsistent experiment")
def _fail_inconsistent(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "both experiment.json and experiment-error.json" in sctx["cli"].output


@then("aggregation fails naming the corrupt manifest")
def _fail_corrupt(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "corrupt" in sctx["cli"].output and "experiment.json" in sctx["cli"].output


@then("aggregation fails naming the wrong columns")
def _fail_columns(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "wrong columns" in sctx["cli"].output and "leverage" in sctx["cli"].output


@then("aggregation fails naming the mismatched experiment label")
def _fail_mismatch(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "labeled experiment" in sctx["cli"].output and "beta" in sctx["cli"].output


@then("aggregation fails saying only successful runs are aggregated")
def _fail_unsuccessful(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "successful runs" in sctx["cli"].output


@then("aggregation fails naming the duplicate run identity")
def _fail_duplicate(sctx: dict[str, Any]) -> None:
    assert sctx["cli"].exit_code == 2
    assert "duplicate" in sctx["cli"].output and "a1" in sctx["cli"].output


@then("both CSV files are byte-identical")
def _byte_identical(sctx: dict[str, Any]) -> None:
    first, second = sctx["bytes"]
    assert first == second
