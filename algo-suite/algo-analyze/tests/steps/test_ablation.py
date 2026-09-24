"""Steps for ablation.feature: comparing completed run metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from algo_analyze.ablation import AblationRow, build_ablation_table
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/ablation.feature")


@pytest.fixture
def actx(tmp_path: Path) -> dict[str, Any]:
    """Create an isolated context for ablation scenarios."""
    return {"root": tmp_path, "run_dirs": []}


@given(parsers.parse('a completed run "{run_id}" with total return {total_return:f}'))
def _completed_run(actx: dict[str, Any], run_id: str, total_return: float) -> None:
    """Create a completed run directory with run and metrics artifacts."""
    run_dir = _run_dir(actx, run_id)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "strategy": run_id,
                "symbol": "EURUSD",
                "start": "2014-05-07",
                "end": "2014-05-09",
                "params": {},
                "success": True,
                "closed_trades": 2,
            }
        )
    )
    _write_metrics(run_dir, total_return)
    actx["run_dirs"].append(run_dir)


@given(parsers.parse('a run "{run_id}" without metrics'))
def _run_without_metrics(actx: dict[str, Any], run_id: str) -> None:
    """Create a run directory that intentionally lacks metrics.json."""
    run_dir = _run_dir(actx, run_id)
    (run_dir / "run.json").write_text(json.dumps({"strategy": run_id}))
    actx["run_dirs"].append(run_dir)


@given(parsers.parse('a missing run "{run_id}"'))
def _missing_run(actx: dict[str, Any], run_id: str) -> None:
    """Register a run directory path that does not exist."""
    actx["run_dirs"].append(_run_path(actx, run_id))


@when(parsers.parse('I build the ablation table with baseline "{baseline}"'))
def _build_table(actx: dict[str, Any], baseline: str) -> None:
    """Build the ablation table for the scenario's run directories."""
    actx["rows"] = build_ablation_table(actx["run_dirs"], baseline=baseline)


@when(parsers.parse('I build the ablation table with baseline "{baseline}" expecting failure'))
def _build_table_failing(actx: dict[str, Any], baseline: str) -> None:
    """Capture the failure raised while building the ablation table."""
    try:
        build_ablation_table(actx["run_dirs"], baseline=baseline)
    except (FileNotFoundError, ValueError) as exc:
        actx["error"] = exc
    else:
        pytest.fail("build_ablation_table unexpectedly succeeded")


@then(parsers.parse("the ablation table has {count:d} rows"))
def _row_count(actx: dict[str, Any], count: int) -> None:
    """Assert the ablation table row count."""
    assert len(actx["rows"]) == count


@then(parsers.parse('run "{run_id}" has total return delta {delta:f}'))
def _total_return_delta(actx: dict[str, Any], run_id: str, delta: float) -> None:
    """Assert a run's total-return delta against the baseline."""
    row = _row_by_id(actx["rows"], run_id)
    assert row.delta_total_return == pytest.approx(delta)


@then(parsers.parse('ablation fails with ValueError naming "{text}"'))
def _value_error_names(actx: dict[str, Any], text: str) -> None:
    """Assert a ValueError names the expected missing baseline."""
    assert isinstance(actx["error"], ValueError)
    assert text in str(actx["error"])


@then(parsers.parse('ablation fails with FileNotFoundError naming "{text}"'))
def _file_error_names(actx: dict[str, Any], text: str) -> None:
    """Assert a FileNotFoundError names the expected run."""
    assert isinstance(actx["error"], FileNotFoundError)
    assert text in str(actx["error"])


def _run_dir(actx: dict[str, Any], run_id: str) -> Path:
    """Create and return a scenario run directory."""
    run_dir = _run_path(actx, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _run_path(actx: dict[str, Any], run_id: str) -> Path:
    """Return the scenario path for a run identifier."""
    return actx["root"] / "runs" / "experiments" / "baseline-comparison" / run_id


def _write_metrics(run_dir: Path, total_return: float) -> None:
    """Write a metrics artifact with a known total return and stable other metrics."""
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "total_return": total_return,
                "sharpe": 1.25,
                "max_drawdown": -0.2,
                "hit_rate": 0.5,
            }
        )
    )


def _row_by_id(rows: list[AblationRow], run_id: str) -> AblationRow:
    """Find an ablation row by run identifier."""
    for row in rows:
        if row.run_id == run_id:
            return row
    raise AssertionError(f"missing row {run_id!r}: {rows}")
