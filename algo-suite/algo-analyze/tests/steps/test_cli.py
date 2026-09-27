"""Steps for cli.feature: end-to-end CLI wiring of metrics/significance/ablation/figures."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from math import sin
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
    parsers.parse('a completed run "{run_id}" with sharpe {sharpe:f} and trade returns {values}')
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


@given(parsers.parse('a completed run "{run_id}" whose run manifest is not JSON'))
def _corrupt_manifest_run(cctx: dict[str, Any], run_id: str) -> None:
    """Create a run whose metrics exist but whose run.json cannot be parsed."""
    run_dir = _run_dir(cctx, run_id)
    _write_metrics(run_dir, sharpe=0.1)
    _write_trades(run_dir, [0.01])
    (run_dir / "run.json").write_text("{")
    (run_dir / "inference-inputs.json").write_text(json.dumps({
        "source": "main.json", "frequency": "calendar-day", "timezone": "UTC",
        "annualization": 365, "risk_free_daily": 0, "costs": "brokerage:fixture",
        "symbol": "EURUSD", "start": "2020-01-01", "end": "2020-04-30",
    }))


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
    cctx["snapshot"] = _artifact_digests(cctx)
    cctx["result"] = CliRunner().invoke(app, args[1:])


def _artifact_digests(cctx: dict[str, Any]) -> dict[str, str]:
    """Hash every file under the data root so a command can be proven read-only."""
    import hashlib

    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(cctx["data_root"].rglob("*")) if p.is_file()}


@when(parsers.parse('I run the console entry point with "{argument}"'))
def _entry_point(cctx: dict[str, Any], argument: str, monkeypatch: pytest.MonkeyPatch,
                 capsys: pytest.CaptureFixture[str]) -> None:
    """Call the installed `main()` exactly as the console script would."""
    from algo_analyze.cli import main

    monkeypatch.setattr("sys.argv", ["algo-analyze", argument])
    with pytest.raises(SystemExit) as exit_info:
        main()
    cctx["entry_exit"] = exit_info.value.code
    cctx["entry_out"] = capsys.readouterr().out


@then("the entry point exits 0 and prints the package version")
def _entry_version(cctx: dict[str, Any]) -> None:
    """The console script must exit cleanly and print exactly the installed version."""
    from importlib.metadata import version as pkg_version

    assert cctx["entry_exit"] == 0
    assert cctx["entry_out"].strip() == pkg_version("algo-analyze")


@then(parsers.parse('the inventory lists "{run_id}" as {status} for "{reason}"'))
def _inventory_entry(cctx: dict[str, Any], run_id: str, status: str, reason: str) -> None:
    """Every discovered run carries a status and a reason naming the missing prerequisite."""
    payload = json.loads(cctx["result"].output)
    entry = next(r for r in payload["runs"] if r["run"] == f"runs/{run_id}")
    assert entry["status"] == status, entry
    assert reason in entry["reason"], entry


@then("no saved run artifact was modified")
def _read_only(cctx: dict[str, Any]) -> None:
    """Byte-for-byte proof that the command never writes into historical run directories."""
    assert _artifact_digests(cctx) == cctx["snapshot"]


@when(parsers.parse('I run "{command}"'))
def _run(cctx: dict[str, Any], command: str) -> None:
    _invoke(cctx, command)


@then(parsers.parse("the command exits {code:d}"))
def _exit_code(cctx: dict[str, Any], code: int) -> None:
    assert cctx["result"].exit_code == code, cctx["result"].output


@then(parsers.parse('the error names "{text}"'))
def _error_names(cctx: dict[str, Any], text: str) -> None:
    assert text in cctx["result"].output, cctx["result"].output


@then("the metrics output has an unavailable probability with a reason")
def _null_deflated_sharpe(cctx: dict[str, Any]) -> None:
    """Unavailable inference retains a separate descriptive headline."""
    payload = json.loads(cctx["result"].output)
    assert payload["schema_version"] == 2
    assert payload["deflated_sharpe_probability"] is None
    assert payload["status"] == "unavailable" and payload["reason"]
    assert payload["descriptive_metrics"]["sharpe"] == 1.0
    assert "deflated_sharpe" not in payload


@then(parsers.parse("the significance output records unavailable data and seed {seed:d}"))
def _significance_seed(cctx: dict[str, Any], seed: int) -> None:
    """Legacy trade files cannot yield a corrected p-value."""
    payload = json.loads(cctx["result"].output)
    assert payload["status"] == "unavailable"
    assert payload["n_resamples"] == 200
    assert payload["seed"] == seed
    assert "inference-inputs.json" in payload["reason"]


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


@given(parsers.parse('engine equity and selection history for CLI run "{run_id}"'))
def _engine_cli_run(cctx: dict[str, Any], run_id: str) -> None:
    """Write independent engine-shape fixtures with 120 daily intervals and unrelated trades."""
    run_dir = _run_dir(cctx, run_id)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    offset = 1 if run_id == "hyb-eq" else 0
    equity, points = 100000.0, []
    for i in range(121):
        points.append([int((start + timedelta(days=i)).timestamp()), equity])
        equity *= 1 + 0.005 * sin(i * 0.71 + offset) + 0.001
    _write_metrics(run_dir, sharpe=99.0)
    _write_trades(run_dir, [10.0] * (2 + offset))
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "success": True,
                "symbol": "EURUSD",
                "start": "2020-01-01",
                "end": "2020-04-29",
            }
        )
    )
    (run_dir / "main.json").write_text(
        json.dumps(
            {
                "charts": {"Strategy Equity": {"series": {"Equity": {"values": points}}}},
            }
        )
    )
    (run_dir / "inference-inputs.json").write_text(
        json.dumps(
            {
                "source": "main.json",
                "frequency": "calendar-day",
                "timezone": "UTC",
                "annualization": 365,
                "risk_free_daily": 0,
                "costs": "engine cost model",
                "symbol": "EURUSD",
                "start": "2020-01-01",
                "end": "2020-04-30",
            }
        )
    )
    selection = cctx["data_root"] / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "n_trials": 10,
                "trial_count": 20,
                "interim_looks": 1,
                "trial_sharpe_std": 0.02,
                "frequency": "calendar-day",
                "provenance": "registered development search",
            }
        )
    )
    cctx["selection"] = selection


def _edit_main(cctx: dict[str, Any], run_id: str, mutate: Any) -> None:
    """Apply one in-place change to a run's main.json document."""
    path = cctx["data_root"] / "runs" / run_id / "main.json"
    data = json.loads(path.read_text())
    mutate(data["charts"]["Strategy Equity"]["series"])
    path.write_text(json.dumps(data))


@given(parsers.parse('run "{run_id}" has a duplicated equity timestamp'))
def _duplicate_timestamp(cctx: dict[str, Any], run_id: str) -> None:
    """Malformed equity: an artifact defect, never repaired."""
    _edit_main(cctx, run_id, lambda s: s["Equity"]["values"].insert(10, s["Equity"]["values"][10]))


@given(parsers.parse('run "{run_id}" lacks one midnight equity endpoint'))
def _missing_endpoint(cctx: dict[str, Any], run_id: str) -> None:
    """Missing evidence: inference is unavailable, never gap-filled."""
    _edit_main(cctx, run_id, lambda s: s["Equity"]["values"].pop(10))


@given(parsers.parse('run "{run_id}" has a null Return series'))
def _null_return(cctx: dict[str, Any], run_id: str) -> None:
    """A malformed optional series must classify as invalid, not abort the scan."""
    _edit_main(cctx, run_id, lambda s: s.update(Return=None))


@then(parsers.parse('the significance output is unavailable for "{reason}"'))
def _significance_unavailable(cctx: dict[str, Any], reason: str) -> None:
    """Missing endpoints surface as an unavailable report on the success channel."""
    payload = json.loads(cctx["result"].output)
    assert payload["status"] == "unavailable"
    assert reason in payload["reason"], payload


@when(parsers.parse('I run corrected metrics for CLI run "{run_id}"'))
def _corrected_metrics(cctx: dict[str, Any], run_id: str) -> None:
    """Pass a real JSON manifest through the CLI option parser."""
    cctx["result"] = CliRunner().invoke(
        app, ["metrics", "--run", run_id, "--selection", str(cctx["selection"])]
    )


@then("the corrected CLI probability records daily moments and source hashes")
def _corrected_probability(cctx: dict[str, Any]) -> None:
    """Assert valid corrected inference never uses headline Sharpe or closed trade count."""
    result = json.loads(cctx["result"].output)
    assert result["schema_version"] == 2 and result["status"] == "available"
    assert 0 <= result["deflated_sharpe_probability"] <= 1
    assert result["descriptive_metrics"]["sharpe"] == 99
    assert result["moments"]["n_returns"] == 120
    assert result["moments"]["observed_sharpe"] != 99
    assert result["portfolio"]["source_sha256"] == _sha256(
        cctx["data_root"] / "runs" / "complete" / "main.json")
    assert result["selection"]["source_sha256"] == _sha256(cctx["selection"])
    assert "deflated_sharpe" not in result


def _sha256(path: Path) -> str:
    """Independent digest of a file's exact bytes."""
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


@then("the corrected CLI significance records pairing effect interval and sensitivity")
def _corrected_significance(cctx: dict[str, Any]) -> None:
    """Require the complete inference contract on the public command surface."""
    result = json.loads(cctx["result"].output)
    assert result["schema_version"] == 2 and result["status"] == "available"
    primary = result["primary"]
    assert primary["method"] == "paired_stationary_bootstrap"
    assert primary["n_observations"] == 120 and primary["seed"] == 7
    assert 0 < primary["p_value"] <= 1
    assert primary["confidence_interval"][0] <= primary["effect"]
    assert primary["confidence_interval"][1] >= primary["effect"]
    assert result["sensitivity"][0]["block_length"] == 10
    assert (result["run_a"], result["run_b"]) == ("base-eq", "hyb-eq")
    for arm, run_id in (("portfolio_a", "base-eq"), ("portfolio_b", "hyb-eq")):
        main = cctx["data_root"] / "runs" / run_id / "main.json"
        assert result[arm]["source_sha256"] == _sha256(main)
