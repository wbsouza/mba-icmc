"""Steps for features/lean_smoke.feature — the testcontainers LEAN harness boots + runs.

"the backtest exits successfully" is the shared step in conftest.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/lean_smoke.feature")

_ALGOS = Path(__file__).parent.parent / "algos"


@given("the smoke algorithm")
def _smoke_algo(ctx: dict[str, Any]) -> None:
    """Select the no-data smoke algorithm."""
    ctx["algo_dir"] = _ALGOS / "smoke"


@when("I run it in the LEAN container")
def _run_smoke(ctx: dict[str, Any], lean_backtest: Any, tmp_path: Path) -> None:
    """Run it in the pinned LEAN image via the testcontainers harness."""
    results = tmp_path / "results"
    results.mkdir(exist_ok=True)
    ctx["run"] = lean_backtest(algo_dir=ctx["algo_dir"], results_dir=results)


@then(parsers.parse('the logs contain "{needle}"'))
def _logs_contain(ctx: dict[str, Any], needle: str) -> None:
    assert ctx["run"].grep(needle), ctx["run"].logs[-3000:]
