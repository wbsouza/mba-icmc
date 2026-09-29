"""Steps for run_result.feature — parsing LEAN /Results into a RunResult.

The fixture result JSON mirrors the real shape discovered against the pinned engine:
`totalPerformance.closedTrades` is a list whose length is the closed-trade count.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.results import parse_results
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/run_result.feature")


@pytest.fixture
def rr_ctx(tmp_path: Path) -> dict[str, Any]:
    """A fresh results directory per scenario."""
    results = tmp_path / "results"
    results.mkdir()
    return {"results": results}


def _write_result_json(results: Path, closed_trades: int) -> None:
    """Write a minimal `main.json` with `closed_trades` round-trips, real-shaped."""
    doc = {
        "orders": {str(i): {} for i in range(closed_trades * 2)},
        "totalPerformance": {
            "closedTrades": [{"trade": i} for i in range(closed_trades)],
            "tradeStatistics": {"totalNumberOfTrades": closed_trades},
        },
        "statistics": {"Total Orders": str(closed_trades * 2)},
    }
    (results / "main.json").write_text(json.dumps(doc))


@given(parsers.parse("a LEAN results directory reporting {n:d} closed trade"))
@given(parsers.parse("a LEAN results directory reporting {n:d} closed trades"))
def _results_with_trades(rr_ctx: dict[str, Any], n: int) -> None:
    _write_result_json(rr_ctx["results"], n)


@given("a summary sibling is also present")
def _summary_sibling(rr_ctx: dict[str, Any]) -> None:
    """Write a `main-summary.json` that also carries closedTrades (a derived sibling)."""
    doc = {"totalPerformance": {"closedTrades": [{"trade": 0}]}}
    (rr_ctx["results"] / "main-summary.json").write_text(json.dumps(doc))


@given("a second, differently-named primary result file is also present")
def _second_primary(rr_ctx: dict[str, Any]) -> None:
    """Write another non-derived result JSON, so two primary results compete."""
    doc = {"totalPerformance": {"closedTrades": [{"trade": 0}]}}
    (rr_ctx["results"] / "other.json").write_text(json.dumps(doc))


@given("an empty LEAN results directory")
def _empty_results(rr_ctx: dict[str, Any]) -> None:
    pass  # the fixture already made an empty dir


@given(parsers.parse('its result JSON has a null "{field}" field'))
def _null_field(rr_ctx: dict[str, Any], field: str) -> None:
    """Overwrite `main.json`, setting `field` to JSON `null` (not merely absent)."""
    path = rr_ctx["results"] / "main.json"
    doc = json.loads(path.read_text())
    doc[field] = None
    path.write_text(json.dumps(doc))


@when("I parse it as a successful run")
def _parse_ok(rr_ctx: dict[str, Any]) -> None:
    rr_ctx["result"] = rr_ctx["error"] = None
    try:
        rr_ctx["result"] = parse_results(rr_ctx["results"], success=True)
    except Exception as exc:  # noqa: BLE001 — asserted in the Then steps
        rr_ctx["error"] = exc


@when("I parse it as a failed run")
def _parse_failed(rr_ctx: dict[str, Any]) -> None:
    rr_ctx["result"] = rr_ctx["error"] = None
    try:
        rr_ctx["result"] = parse_results(rr_ctx["results"], success=False)
    except Exception as exc:  # noqa: BLE001 — asserted in the Then steps
        rr_ctx["error"] = exc


@then("the run is reported successful")
def _ok(rr_ctx: dict[str, Any]) -> None:
    assert rr_ctx["result"].success is True


@then("the run is reported unsuccessful")
def _not_ok(rr_ctx: dict[str, Any]) -> None:
    assert rr_ctx["result"].success is False


@then(parsers.parse("it reports {n:d} closed trade"))
@then(parsers.parse("it reports {n:d} closed trades"))
def _closed(rr_ctx: dict[str, Any], n: int) -> None:
    assert rr_ctx["result"].closed_trades == n


@then("the raw results path points at the result JSON")
def _raw_path(rr_ctx: dict[str, Any]) -> None:
    assert rr_ctx["result"].raw_results_path == rr_ctx["results"] / "main.json"


@then("no error is reported")
def _no_error(rr_ctx: dict[str, Any]) -> None:
    assert rr_ctx["result"].error is None


@then("parsing fails with a missing-result error")
def _missing(rr_ctx: dict[str, Any]) -> None:
    assert isinstance(rr_ctx["error"], FileNotFoundError)


@then("parsing fails with an ambiguous-result error")
def _ambiguous(rr_ctx: dict[str, Any]) -> None:
    assert isinstance(rr_ctx["error"], ValueError)
    assert "ambiguous" in str(rr_ctx["error"]).lower()
