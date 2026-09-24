"""Steps for figures.feature: rendering vector PDF analysis figures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from algo_analyze.figures import (
    ablation_bars_figure,
    drawdown_curve_figure,
    equity_curve_figure,
)
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


@given("ablation rows:")
def _ablation_rows(fctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """Load ablation rows from a Gherkin data table."""
    header = datatable[0]
    fctx["rows"] = [
        {
            "run_id": row[header.index("run_id")],
            "delta_total_return": float(row[header.index("delta_total_return")]),
        }
        for row in datatable[1:]
    ]


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
