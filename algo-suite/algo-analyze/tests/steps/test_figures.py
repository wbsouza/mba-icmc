"""Steps for figures.feature: rendering vector PDF analysis figures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
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


def _write_trades(run_dir: Path, returns: list[float]) -> None:
    """Write a minimal ``trades.parquet`` fixture with trade returns."""
    table = pa.table({"return": pa.array(returns, type=pa.float64())})
    pq.write_table(table, run_dir / "trades.parquet")
