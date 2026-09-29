"""Steps for figures.feature: rendering vector PDF analysis figures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from algo_analyze.ablation import AblationRow
from algo_analyze.figures import (
    ablation_bars_figure,
    drawdown_curve_figure,
    equity_curve_figure,
)
from algo_backtest.artifacts import RunManifest, write_run_artifacts
from algo_backtest.metrics import Metrics
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/figures.feature")


@pytest.fixture
def fctx(tmp_path: Path) -> dict[str, Any]:
    """Create isolated paths for figure scenarios."""
    run_dir = tmp_path / "runs" / "figures" / "baseline-ma"
    run_dir.mkdir(parents=True)
    return {"run_dir": run_dir, "out": tmp_path / "figures" / "figure.pdf"}


@given(parsers.parse("a run directory with trade returns {values}"))
def _run_with_trade_returns(fctx: dict[str, Any], values: str) -> None:
    """Create a run directory with a deterministic trade-return ledger."""
    returns = [float(value.strip()) for value in values.split(",")]
    _write_trades(fctx["run_dir"], returns)


@given("a run directory with zero closed trades")
def _run_with_zero_closed_trades(fctx: dict[str, Any]) -> None:
    """Create a run directory with an empty trade ledger."""
    _write_trades(fctx["run_dir"], [])


@given("a run directory without trade artifacts")
def _run_without_trade_artifacts(fctx: dict[str, Any]) -> None:
    """Leave the run directory without a trades.json file."""


@given("a run directory with absolute PnL trades")
def _run_with_absolute_pnl_trades(fctx: dict[str, Any]) -> None:
    """Create a ledger that must not be mistaken for fractional returns."""
    (fctx["run_dir"] / "trades.json").write_text(
        json.dumps([{"profitLoss": 125.0}, {"profitLoss": -40.0}])
    )


@given("a run directory with a null trade return")
def _run_with_null_trade_return(fctx: dict[str, Any]) -> None:
    """Create a ledger with invalid null return data."""
    (fctx["run_dir"] / "trades.json").write_text(json.dumps([{"return": None}]))


@given("a run directory with malformed trades JSON")
def _run_with_malformed_json(fctx: dict[str, Any]) -> None:
    """Create a trades.json that is not valid JSON at all."""
    (fctx["run_dir"] / "trades.json").write_text("{ not valid json")


@given("a run directory whose trades ledger is a JSON object")
def _run_with_object_ledger(fctx: dict[str, Any]) -> None:
    """Create a trades.json holding a JSON object instead of a list."""
    (fctx["run_dir"] / "trades.json").write_text(json.dumps({"return": 0.01}))


@given("a run directory with a non-object trade element")
def _run_with_non_object_trade(fctx: dict[str, Any]) -> None:
    """Create a trades.json whose list contains a non-object element."""
    (fctx["run_dir"] / "trades.json").write_text(json.dumps([0.01]))


@given("a run directory with a non-finite trade return")
def _run_with_non_finite_return(fctx: dict[str, Any]) -> None:
    """Create a ledger whose return is not a finite number."""
    (fctx["run_dir"] / "trades.json").write_text(json.dumps([{"return": float("nan")}]))


@given(parsers.parse("a run directory with a trade return of {value:g}"))
def _run_with_return_value(fctx: dict[str, Any], value: float) -> None:
    """Create a ledger with a single trade at the given fractional return."""
    _write_trades(fctx["run_dir"], [value])


@given("a run directory with a non-numeric trade return")
def _run_with_non_numeric_return(fctx: dict[str, Any]) -> None:
    """Create a ledger whose return is a non-numeric JSON value (not a string or number)."""
    (fctx["run_dir"] / "trades.json").write_text(json.dumps([{"return": [1, 2]}]))


@given("a completed run written through write_run_artifacts with priced closed trades")
def _run_from_write_run_artifacts(fctx: dict[str, Any]) -> None:
    """Build a real completed-run directory via the producer, not a hand-written fixture."""
    write_run_artifacts(
        fctx["run_dir"],
        RunManifest(
            strategy="baseline-ma", symbol="EURUSD", start="2014-05-07", end="2014-05-09",
            params={}, success=True, closed_trades=2,
            broker_adapter="oanda",
        ),
        closed_trades=[
            {"entryPrice": 1.1000, "quantity": 10000, "profitLoss": 55.0},
            {"entryPrice": 1.1050, "quantity": 10000, "profitLoss": -22.0},
        ],
        metrics=Metrics(total_return=0.003, sharpe=1.1, max_drawdown=-0.02, hit_rate=0.5),
    )


@given("ablation rows:")
def _ablation_rows(fctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """Load ablation rows from a Gherkin data table as real AblationRow instances."""
    header = datatable[0]
    fctx["rows"] = [
        AblationRow(
            run_id=row[header.index("run_id")],
            strategy="baseline-ma",
            symbol="EURUSD",
            start="2014-05-07",
            end="2014-05-09",
            total_return=0.0,
            sharpe=0.0,
            max_drawdown=0.0,
            hit_rate=0.0,
            delta_total_return=float(row[header.index("delta_total_return")]),
        )
        for row in datatable[1:]
    ]


@given("no ablation rows")
def _no_ablation_rows(fctx: dict[str, Any]) -> None:
    """An empty ablation row sequence."""
    fctx["rows"] = []


@when("I render the equity curve figure")
def _render_equity(fctx: dict[str, Any]) -> None:
    """Render the equity curve figure."""
    fctx["figure"] = equity_curve_figure(fctx["run_dir"], fctx["out"])


@when("I render the equity curve figure expecting failure")
def _render_equity_failing(fctx: dict[str, Any]) -> None:
    """Capture an expected equity rendering failure."""
    try:
        equity_curve_figure(fctx["run_dir"], fctx["out"])
    except (FileNotFoundError, ValueError) as exc:
        fctx["error"] = exc
    else:
        pytest.fail("equity_curve_figure unexpectedly succeeded")


@when("I render the drawdown curve figure")
def _render_drawdown(fctx: dict[str, Any]) -> None:
    """Render the drawdown curve figure."""
    fctx["figure"] = drawdown_curve_figure(fctx["run_dir"], fctx["out"])


@when("I render the ablation bars figure")
def _render_ablation(fctx: dict[str, Any]) -> None:
    """Render the ablation bars figure."""
    fctx["figure"] = ablation_bars_figure(fctx["rows"], fctx["out"])


@when("I render the ablation bars figure expecting failure")
def _render_ablation_failing(fctx: dict[str, Any]) -> None:
    """Capture an expected ablation rendering failure."""
    try:
        ablation_bars_figure(fctx["rows"], fctx["out"])
    except (FileNotFoundError, ValueError) as exc:
        fctx["error"] = exc
    else:
        pytest.fail("ablation_bars_figure unexpectedly succeeded")


@then("the figure PDF is valid and non-empty")
def _valid_pdf(fctx: dict[str, Any]) -> None:
    """Assert the generated file is a non-empty PDF document."""
    path = fctx["figure"]
    assert path.is_file()
    assert path.stat().st_size > 1_000
    content = path.read_bytes()
    assert content.startswith(b"%PDF")
    assert b"/Type /Page" in content
    assert b"/Subtype /Image" not in content


@then(parsers.parse('figure rendering fails with FileNotFoundError naming "{text}"'))
def _file_error_names(fctx: dict[str, Any], text: str) -> None:
    """Assert a figure rendering FileNotFoundError names the expected artifact."""
    assert isinstance(fctx["error"], FileNotFoundError)
    assert text in str(fctx["error"])


@then(parsers.parse('figure rendering fails with ValueError naming "{text}"'))
def _value_error_names(fctx: dict[str, Any], text: str) -> None:
    """Assert a figure rendering ValueError names the expected artifact issue."""
    assert isinstance(fctx["error"], ValueError)
    assert text in str(fctx["error"])


def _write_trades(run_dir: Path, returns: list[float]) -> None:
    """Write a minimal ``trades.json`` fixture with fractional trade returns."""
    (run_dir / "trades.json").write_text(
        json.dumps([{"return": value} for value in returns])
    )
