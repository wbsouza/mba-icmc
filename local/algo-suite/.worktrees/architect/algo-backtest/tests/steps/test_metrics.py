"""Steps for metrics.feature — extracting the four headline metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.cli import app
from algo_backtest.metrics import extract_metrics
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/metrics.feature")


@pytest.fixture
def met_ctx(tmp_path: Path) -> dict[str, Any]:
    """A run directory for the result JSON."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    return {"run_dir": run_dir}


@given(
    parsers.parse(
        "a LEAN result with portfolio statistics {ret:g}, {sharpe:g}, {dd:g}, {wr:g}"
    )
)
def _result_with_stats(
    met_ctx: dict[str, Any], ret: float, sharpe: float, dd: float, wr: float
) -> None:
    result = {
        "totalPerformance": {
            "closedTrades": [],
            "portfolioStatistics": {
                "totalNetProfit": ret, "sharpeRatio": sharpe,
                "drawdown": dd, "winRate": wr,
            },
        }
    }
    result_json = met_ctx["run_dir"] / "main.json"
    result_json.write_text(json.dumps(result))
    met_ctx["result_json"] = result_json


@given("a LEAN result with no portfolio statistics")
def _result_without_stats(met_ctx: dict[str, Any]) -> None:
    result_json = met_ctx["run_dir"] / "main.json"
    result_json.write_text(json.dumps({"totalPerformance": {"closedTrades": []}}))
    met_ctx["result_json"] = result_json


@given("a LEAN result whose total net profit is not a number")
def _result_non_numeric(met_ctx: dict[str, Any]) -> None:
    result = {
        "totalPerformance": {
            "closedTrades": [],
            "portfolioStatistics": {
                "totalNetProfit": "n/a", "sharpeRatio": 1.0,
                "drawdown": 0.0, "winRate": 0.0,
            },
        }
    }
    result_json = met_ctx["run_dir"] / "main.json"
    result_json.write_text(json.dumps(result))
    met_ctx["result_json"] = result_json


@given("a run directory whose metrics.json is corrupt")
def _corrupt_metrics_json(met_ctx: dict[str, Any]) -> None:
    (met_ctx["run_dir"] / "metrics.json").write_text("{ not valid json")


@when("I extract the metrics")
def _extract(met_ctx: dict[str, Any]) -> None:
    met_ctx["metrics"] = extract_metrics(met_ctx["result_json"])


@when("I extract the metrics expecting failure")
def _extract_failing(met_ctx: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        extract_metrics(met_ctx["result_json"])
    met_ctx["error"] = str(exc_info.value)


@when("I run the metrics command on that run directory")
def _run_metrics_cli(met_ctx: dict[str, Any]) -> None:
    met_ctx["cli"] = CliRunner().invoke(app, ["metrics", "--run", str(met_ctx["run_dir"])])


@then(parsers.parse("total return is {value:g}"))
def _total_return(met_ctx: dict[str, Any], value: float) -> None:
    assert met_ctx["metrics"].total_return == value


@then(parsers.parse("the Sharpe ratio is {value:g}"))
def _sharpe(met_ctx: dict[str, Any], value: float) -> None:
    assert met_ctx["metrics"].sharpe == value


@then(parsers.parse("the max drawdown is {value:g}"))
def _drawdown(met_ctx: dict[str, Any], value: float) -> None:
    assert met_ctx["metrics"].max_drawdown == value


@then(parsers.parse("the hit rate is {value:g}"))
def _hit_rate(met_ctx: dict[str, Any], value: float) -> None:
    assert met_ctx["metrics"].hit_rate == value


@then(parsers.parse("the output reports total_return {ret:g} and sharpe {sharpe:g}"))
def _cli_reports(met_ctx: dict[str, Any], ret: float, sharpe: float) -> None:
    out = met_ctx["cli"].output
    assert met_ctx["cli"].exit_code == 0, out
    assert f"total_return={ret}" in out and f"sharpe={sharpe}" in out


@then("extraction fails telling me the backtest may not have finished")
def _extraction_failed(met_ctx: dict[str, Any]) -> None:
    assert "portfolioStatistics" in met_ctx["error"]
    assert "may not" in met_ctx["error"] and "finished" in met_ctx["error"]


@then(parsers.parse("the metrics command exits with code {code:d}"))
def _metrics_exit(met_ctx: dict[str, Any], code: int) -> None:
    assert met_ctx["cli"].exit_code == code, met_ctx["cli"].output


@then("the error tells me the metrics artifact is invalid")
def _artifact_invalid(met_ctx: dict[str, Any]) -> None:
    out = met_ctx["cli"].output
    assert "not a valid metrics artifact" in out, out
