"""Steps for experiment_run.feature — running an experiment (unit via a fake runner; one
real-engine integration scenario)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from algo_backtest.experiment import Experiment, Run, run_experiment
from algo_backtest.materialize import materialize_month
from algo_backtest.results import RunResult
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import lean_data_dir_for, price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/experiment_run.feature")

_EURUSD = build_instrument("EURUSD")
_WINDOW = (date(2014, 5, 7), date(2014, 5, 9))


@pytest.fixture
def rctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root (zero-config => UTC)."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {"data_root": data_root}


_MA_PARAMS = {"fast": "3", "slow": "8", "size": "0.5", "cash": "10000"}


def _experiment(n: int) -> Experiment:
    """An experiment of n EUR/USD baseline-ma runs over the covered window."""
    runs = tuple(
        Run(
            run_id=f"run-{i}", strategy="baseline-ma", symbol="EURUSD",
            start=_WINDOW[0], end=_WINDOW[1], params=dict(_MA_PARAMS),
        )
        for i in range(n)
    )
    return Experiment(name="test-experiment", runs=runs)


def _make_covered_eurusd(data_root: Path) -> None:
    """Create a dummy day-zip so lean_data_covers() passes (filename-date only)."""
    directory = lean_data_dir_for(data_root, _EURUSD, "minute")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "20140507_quote.zip").write_bytes(b"")


def _fake_runner(fail_ids: frozenset[str] = frozenset()) -> Callable[..., RunResult]:
    """A run_strategy stand-in: writes a flat result JSON, fails ids in fail_ids."""
    def runner(strategy: str, *, results_dir: Path, **_: Any) -> RunResult:
        main = results_dir / "main.json"
        main.write_text(json.dumps({
            "totalPerformance": {
                "closedTrades": [],
                "portfolioStatistics": {
                    "totalNetProfit": 0.0, "sharpeRatio": 0.0,
                    "drawdown": 0.0, "winRate": 0.0,
                },
            }
        }))
        return RunResult(
            success=results_dir.name not in fail_ids, closed_trades=0, raw_results_path=main
        )
    return runner


@given(parsers.parse("an experiment of {n:d} runs over covered EUR/USD data"))
def _experiment_covered(rctx: dict[str, Any], n: int) -> None:
    _make_covered_eurusd(rctx["data_root"])
    rctx["experiment"] = _experiment(n)
    rctx["runner"] = _fake_runner()


@given("an experiment of 2 runs over covered EUR/USD data whose first run fails")
def _experiment_first_fails(rctx: dict[str, Any]) -> None:
    _make_covered_eurusd(rctx["data_root"])
    experiment = _experiment(2)
    rctx["experiment"] = experiment
    rctx["runner"] = _fake_runner(fail_ids=frozenset({experiment.runs[0].run_id}))


@given("an experiment of 2 runs over covered EUR/USD data whose second run fails")
def _experiment_second_fails(rctx: dict[str, Any]) -> None:
    _make_covered_eurusd(rctx["data_root"])
    experiment = _experiment(2)
    rctx["experiment"] = experiment
    rctx["runner"] = _fake_runner(fail_ids=frozenset({experiment.runs[1].run_id}))


@given("an experiment of 1 run over a window with no materialized data")
def _experiment_no_data(rctx: dict[str, Any]) -> None:
    rctx["experiment"] = _experiment(1)  # no day-zips created
    rctx["runner"] = _fake_runner()


@when("I run the experiment")
def _run(rctx: dict[str, Any]) -> None:
    rctx["result"] = run_experiment(
        rctx["experiment"], data_root=rctx["data_root"], timeout=1, runner=rctx["runner"],
        broker_adapter="oanda",
    )


@when("I run the experiment again")
def _run_again(rctx: dict[str, Any]) -> None:
    rctx["dirs_first"] = [o.run_dir for o in rctx["result"].outcomes]
    rctx["result2"] = run_experiment(
        rctx["experiment"], data_root=rctx["data_root"], timeout=1, runner=rctx["runner"],
        broker_adapter="oanda",
    )


@when("I re-run the experiment with only its first run")
def _rerun_shrunk(rctx: dict[str, Any]) -> None:
    full = rctx["experiment"]
    shrunk = Experiment(name=full.name, runs=full.runs[:1])
    rctx["experiment"] = shrunk
    rctx["result"] = run_experiment(
        shrunk, data_root=rctx["data_root"], timeout=1, runner=rctx["runner"],
        broker_adapter="oanda",
    )


@when("I run the experiment expecting failure")
def _run_failing(rctx: dict[str, Any]) -> None:
    with pytest.raises((ValueError, RuntimeError)) as exc_info:
        run_experiment(
            rctx["experiment"], data_root=rctx["data_root"], timeout=1, runner=rctx["runner"],
            broker_adapter="oanda",
        )
    rctx["error"] = str(exc_info.value)


def _experiment_base(rctx: dict[str, Any]) -> Path:
    """The experiment-level directory under the data root."""
    return rctx["data_root"] / "runs" / "experiments" / rctx["experiment"].name


@then("each run has its own directory under runs/experiments/<experiment>")
def _own_dirs(rctx: dict[str, Any]) -> None:
    base = _experiment_base(rctx)
    for outcome in rctx["result"].outcomes:
        assert outcome.run_dir.parent == base and outcome.run_dir.is_dir()


@then("each run directory holds run.json, trades.json and metrics.json")
def _artifacts(rctx: dict[str, Any]) -> None:
    for outcome in rctx["result"].outcomes:
        for name in ("run.json", "trades.json", "metrics.json"):
            assert (outcome.run_dir / name).is_file(), name


_ROW_COLUMNS = (
    "experiment", "run_id", "strategy", "symbol", "from", "to", "success",
    "closed_trades", "total_return", "sharpe", "max_drawdown", "hit_rate", "run_dir",
)


def _assert_manifest(manifest_path: Path, expected: int) -> list[dict[str, Any]]:
    """Assert the manifest lists `expected` rows, each with the full F2 column set."""
    doc = json.loads(manifest_path.read_text())
    rows = doc["runs"]
    assert len(rows) == expected, rows
    for row in rows:
        for column in _ROW_COLUMNS:
            assert column in row, (column, row)
    return rows


@then(parsers.parse("the experiment manifest lists {n:d} runs each with a metrics row"))
def _manifest_lists(rctx: dict[str, Any], n: int) -> None:
    _assert_manifest(rctx["result"].manifest_path, n)


@then(parsers.parse("the experiment manifest still lists {n:d} runs each with a metrics row"))
def _manifest_still_lists(rctx: dict[str, Any], n: int) -> None:
    _assert_manifest(rctx["result2"].manifest_path, n)


@then("the run directories are the same paths as the first run")
def _same_dirs(rctx: dict[str, Any]) -> None:
    assert [o.run_dir for o in rctx["result2"].outcomes] == rctx["dirs_first"]


@then("the experiment fails telling me to materialize that window first")
def _coverage_fail(rctx: dict[str, Any]) -> None:
    assert "materialize" in rctx["error"]


@then("no experiment manifest is written")
def _no_manifest(rctx: dict[str, Any]) -> None:
    assert not (_experiment_base(rctx) / "experiment.json").exists()


@then("only the first run's directory remains under runs/experiments/<experiment>")
def _only_first_dir(rctx: dict[str, Any]) -> None:
    base = _experiment_base(rctx)
    subdirs = sorted(p.name for p in base.iterdir() if p.is_dir())
    assert subdirs == ["run-0"], subdirs


@then("an experiment error artifact names the failed run")
def _error_artifact(rctx: dict[str, Any]) -> None:
    error_path = _experiment_base(rctx) / "experiment-error.json"
    assert error_path.is_file()
    doc = json.loads(error_path.read_text())
    assert doc["failed_run"] == rctx["experiment"].runs[0].run_id


@then("the experiment error names the failed run and lists the completed ones")
def _error_completed(rctx: dict[str, Any]) -> None:
    doc = json.loads((_experiment_base(rctx) / "experiment-error.json").read_text())
    assert doc["failed_run"] == "run-1"
    assert doc["completed_runs"] == ["run-0"]


# --- integration: a real experiment on the LEAN engine -------------------------------


def _flat_bars(first: datetime, count: int = 60) -> list[QuoteBar]:
    """A flat price — fast/slow SMA never cross, so the baseline never trades."""
    bid, ask = 1.38000, 1.38010
    return [
        QuoteBar(
            timestamp=first + timedelta(minutes=i),
            bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
            ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
            tick_count=1,
        )
        for i in range(count)
    ]


@given("materialized EUR/USD minute data with a flat price in 2014-05")
def _materialize_flat(rctx: dict[str, Any]) -> None:
    ParquetRepository(
        QuoteBar, price_path_for(rctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 5)
    ).put(_flat_bars(datetime(2014, 5, 7, 13, 0, tzinfo=UTC)))
    materialize_month(rctx["data_root"], _EURUSD, 2014, 5, ZoneInfo("UTC"))


@given("a baseline experiment spec for that data")
def _baseline_experiment(rctx: dict[str, Any]) -> None:
    rctx["experiment"] = _experiment(1)


@given("a baseline-meanrev experiment spec for that data")
def _meanrev_experiment(rctx: dict[str, Any]) -> None:
    run = Run(
        run_id="mr", strategy="baseline-meanrev", symbol="EURUSD",
        start=_WINDOW[0], end=_WINDOW[1],
        params={"window": "5", "band": "0.001", "size": "0.5", "cash": "10000"},
    )
    rctx["experiment"] = Experiment(name="test-experiment", runs=(run,))


@when("I run the experiment on the engine")
def _run_engine(rctx: dict[str, Any], require_docker: None) -> None:
    timeout = int(os.environ.get("LEAN_TEST_TIMEOUT", "600"))
    rctx["result"] = run_experiment(
        rctx["experiment"], data_root=rctx["data_root"], timeout=timeout,
        broker_adapter="oanda",
    )


@then(parsers.parse("the experiment manifest has {n:d} run row"))
def _manifest_has(rctx: dict[str, Any], n: int) -> None:
    _assert_manifest(rctx["result"].manifest_path, n)


@then("that run reports zero total return and zero max drawdown")
def _flat_run_zero(rctx: dict[str, Any]) -> None:
    rows = _assert_manifest(rctx["result"].manifest_path, 1)
    assert rows[0]["total_return"] == 0.0, rows[0]
    assert rows[0]["max_drawdown"] == 0.0, rows[0]
