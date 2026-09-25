"""Steps for cli.feature: end-to-end CLI wiring of metrics/significance/ablation/figures."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from algo_analyze.cli import app
from algo_core.logging import configure_logging
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/cli.feature")


@pytest.fixture
def cctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root (zero-config), matching the other CLI-level fixtures.

    Configures structlog to stderr (what the real `main()` entry point does) since
    `CliRunner` invokes `app` directly, bypassing `main()` — without this, structlog's
    unconfigured default writes to stdout and pollutes the JSON this module asserts on.
    """
    configure_logging()
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {"data_root": data_root}


def _run_dir(cctx: dict[str, Any], run_id: str) -> Path:
    """Return (and create) the scenario's run directory."""
    run_dir = cctx["data_root"] / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_manifest(run_dir: Path, run_id: str) -> None:
    """Write a minimal, valid run manifest (the fields ablation.py requires)."""
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "strategy": run_id,
                "symbol": "EURUSD",
                "start": "2014-05-07",
                "end": "2014-05-09",
                "params": {},
                "success": True,
                "closed_trades": 0,
            }
        )
    )


def _write_metrics(run_dir: Path, *, sharpe: float = 0.0, total_return: float = 0.0) -> None:
    """Write a metrics.json artifact with the given headline sharpe/total_return."""
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "total_return": total_return,
                "sharpe": sharpe,
                "max_drawdown": -0.1,
                "hit_rate": 0.5,
            }
        )
    )


def _write_trades(run_dir: Path, returns: list[float]) -> None:
    """Write a trades.json ledger with the given fractional returns."""
    (run_dir / "trades.json").write_text(json.dumps([{"return": value} for value in returns]))


@given(
    parsers.parse(
        'a completed run "{run_id}" with sharpe {sharpe:f} and trade returns {values}'
    )
)
def _completed_run_with_returns(
    cctx: dict[str, Any], run_id: str, sharpe: float, values: str
) -> None:
    """Create a completed run with a headline sharpe and an explicit trade-return ledger."""
    run_dir = _run_dir(cctx, run_id)
    returns = [float(v.strip()) for v in values.split(",")]
    _write_manifest(run_dir, run_id)
    _write_metrics(run_dir, sharpe=sharpe)
    _write_trades(run_dir, returns)


@given(parsers.parse('a completed run "{run_id}" with total return {total_return:f}'))
def _completed_run_with_total_return(
    cctx: dict[str, Any], run_id: str, total_return: float
) -> None:
    """Create a completed run for the ablation scenarios (only total_return matters there)."""
    run_dir = _run_dir(cctx, run_id)
    _write_manifest(run_dir, run_id)
    _write_metrics(run_dir, total_return=total_return)
    _write_trades(run_dir, [0.01, 0.02])


@given(parsers.parse('a run "{run_id}" without a metrics artifact'))
def _run_without_metrics(cctx: dict[str, Any], run_id: str) -> None:
    """Create a run directory that intentionally lacks metrics.json."""
    _run_dir(cctx, run_id)


@given(parsers.parse('a run "{run_id}" without a trades artifact'))
def _run_without_trades(cctx: dict[str, Any], run_id: str) -> None:
    """Create a run directory that intentionally lacks trades.json."""
    _run_dir(cctx, run_id)


def _invoke(cctx: dict[str, Any], command: str) -> None:
    """Run a full `algo-analyze ...` command line through the CLI runner."""
    args = command.split()
    assert args[0] == "algo-analyze", command
    cctx["result"] = CliRunner().invoke(app, args[1:])


@when(parsers.parse('I run "{command}"'))
def _run(cctx: dict[str, Any], command: str) -> None:
    _invoke(cctx, command)


@then(parsers.parse("the command exits {code:d}"))
def _exit_code(cctx: dict[str, Any], code: int) -> None:
    assert cctx["result"].exit_code == code, cctx["result"].output


@then(parsers.parse('the error names "{text}"'))
def _error_names(cctx: dict[str, Any], text: str) -> None:
    assert text in cctx["result"].output, cctx["result"].output


@then("the metrics output has a numeric deflated_sharpe")
def _numeric_deflated_sharpe(cctx: dict[str, Any]) -> None:
    payload = json.loads(cctx["result"].output)
    assert isinstance(payload["deflated_sharpe"], int | float), payload


@then("the metrics output has a null deflated_sharpe with a note")
def _null_deflated_sharpe(cctx: dict[str, Any]) -> None:
    payload = json.loads(cctx["result"].output)
    assert payload["deflated_sharpe"] is None, payload
    assert "note" in payload and payload["note"], payload


@then("the metrics output flags the deflated Sharpe for investigation")
def _flags_deflated_sharpe(cctx: dict[str, Any]) -> None:
    payload = json.loads(cctx["result"].output)
    assert payload["flags"], payload
    assert any("investigate" in flag for flag in payload["flags"]), payload


@then(parsers.parse("the significance output records seed {seed:d}"))
def _significance_seed(cctx: dict[str, Any], seed: int) -> None:
    payload = json.loads(cctx["result"].output)
    assert "p_value" in payload, payload
    assert payload["n_permutations"] == 200, payload
    assert payload["seed"] == seed, payload


@then(parsers.parse('the ablation output has delta_total_return {delta:f} for "{run_id}"'))
def _ablation_delta(cctx: dict[str, Any], delta: float, run_id: str) -> None:
    rows = json.loads(cctx["result"].output)
    row = next(r for r in rows if r["run_id"] == run_id)
    assert row["delta_total_return"] == pytest.approx(delta), row


@then("an ablation figure PDF is written")
def _ablation_figure_written(cctx: dict[str, Any]) -> None:
    out = cctx["data_root"] / "analysis" / "ablation.pdf"
    assert out.is_file() and out.stat().st_size > 1_000, out


@then("both figure PDFs are written")
def _both_figures_written(cctx: dict[str, Any]) -> None:
    figures_dir = cctx["data_root"] / "runs" / "r5" / "figures"
    equity = figures_dir / "equity.pdf"
    drawdown = figures_dir / "drawdown.pdf"
    assert equity.is_file() and equity.stat().st_size > 1_000, equity
    assert drawdown.is_file() and drawdown.stat().st_size > 1_000, drawdown
