"""Run-boundary BDD with real configuration, canonical Parquet and manifest files."""

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import algo_backtest.run as run_module
import pytest
import yaml
from algo_backtest.lean_runner import LeanRun
from algo_backtest.leandata import write_lean_minute
from algo_backtest.strategies import load_strategy_chain_config
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/activity_run_provenance.feature")

_STRATEGY = "activity-provenance-candidate"
_INSTRUMENT = build_instrument("EURUSD")


@pytest.fixture
def activity_run(tmp_path: Path) -> dict[str, Any]:
    """Keep all run inputs and outputs inside this scenario's temporary directory."""
    return {
        "data_root": tmp_path / "data",
        "strategies_root": tmp_path / "strategies",
        "results_dir": tmp_path / "results",
        "paths": {},
        "originals": {},
    }


@given("an external volume-enabled strategy with canonical May and June quotes")
def external_activity_strategy(activity_run: dict[str, Any]) -> None:
    """Extend the real baseline and write genuine canonical and materialized quotes."""
    directory = activity_run["strategies_root"] / _STRATEGY
    directory.mkdir(parents=True)
    filters = list(load_strategy_chain_config("baseline").filters)
    filters.insert(-1, "volume_strength")
    (directory / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "extends": "baseline",
                "filters": filters,
                "volume_strength": {"lookback": 3, "min_relative_activity": 1.25},
            }
        )
    )
    for month, timestamp in (
        ("May", datetime(2014, 5, 30, 12, tzinfo=UTC)),
        ("June", datetime(2014, 6, 2, 12, tzinfo=UTC)),
    ):
        _write_month(activity_run, month, timestamp)
    activity_run["results_dir"].mkdir()


def _write_month(activity_run: dict[str, Any], month: str, timestamp: datetime) -> None:
    """Materialize the same real QuoteBar whose tick count will be bound by SHA-256."""
    bars = [
        QuoteBar(
            timestamp=timestamp,
            bid_open=1.38,
            bid_high=1.381,
            bid_low=1.379,
            bid_close=1.3805,
            ask_open=1.3801,
            ask_high=1.3811,
            ask_low=1.3791,
            ask_close=1.3806,
            tick_count=timestamp.month * 10,
        )
    ]
    root = activity_run["data_root"]
    path = price_path_for(root, _INSTRUMENT, "m1", timestamp.year, timestamp.month)
    ParquetRepository(QuoteBar, path).put(bars)
    write_lean_minute(root, _INSTRUMENT, bars, ZoneInfo("UTC"))
    activity_run["paths"][month] = path
    activity_run["originals"][path] = path.read_bytes()


def _expected_manifest(activity_run: dict[str, Any]) -> dict[str, Any]:
    """Independently hash the original bytes without calling the production helper."""
    return {
        "schema_version": 1,
        "source": "quote_tick_count",
        "files": {
            path.relative_to(activity_run["data_root"]).as_posix(): hashlib.sha256(
                content
            ).hexdigest()
            for path, content in activity_run["originals"].items()
        },
    }


@given("a mocked LEAN runner that produces a successful result")
def mocked_container(activity_run: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace only the external engine boundary; observe artifacts at container entry."""

    def engine(algo_dir: Path, results_dir: Path, **options: Any) -> LeanRun:
        """Observe the manifest before any simulated engine work and return real result IO."""
        assert algo_dir.is_dir()
        activity_run["manifest_at_start"] = json.loads(
            (results_dir / "activity-inputs.json").read_text()
        )
        activity_run["mounts"] = options["data_mounts"]
        activity_run["parameters"] = options["parameters"]
        activity_run["resolved"] = yaml.safe_load(
            options["algo_files"]["strategy.yaml"].read_text()
        )
        if "mutate_month" in activity_run:
            _mutate_count(activity_run["paths"][activity_run["mutate_month"]])
        (results_dir / "main.json").write_text(
            json.dumps({"totalPerformance": {"closedTrades": []}})
        )
        return LeanRun(exit_code=0, logs="", results_dir=results_dir)

    activity_run["container"] = Mock(side_effect=engine)
    monkeypatch.setattr(run_module, "run_lean", activity_run["container"])


def _mutate_count(path: Path) -> None:
    """Change only tick activity in the temporary canonical input during engine execution."""
    repository = ParquetRepository(QuoteBar, path)
    bars = repository.read_all()
    bars[0] = bars[0].model_copy(update={"tick_count": bars[0].tick_count + 1})
    repository.put(bars)


@given(parsers.parse("the mocked container changes only the {month} tick count during execution"))
def mutate_during_execution(activity_run: dict[str, Any], month: str) -> None:
    """Defer mutation until after the run has recorded its original input manifest."""
    activity_run["mutate_month"] = month


@given(parsers.parse("the {month} canonical partition is missing but materialized quotes remain"))
def missing_partition(activity_run: dict[str, Any], month: str) -> None:
    """Delete only the temporary Parquet fixture, retaining its actual LEAN day zip."""
    activity_run["paths"][month].unlink()
    assert run_module.lean_data_covers(
        activity_run["data_root"], _INSTRUMENT, date(2014, 5, 30), date(2014, 6, 2)
    )


@when("the external volume strategy is run across May and June")
def run_activity_strategy(activity_run: dict[str, Any]) -> None:
    """Exercise production strategy resolution, manifests, container wiring and result parsing."""
    activity_run["result"] = run_module.run_strategy(
        _STRATEGY,
        data_root=activity_run["data_root"],
        instrument=_INSTRUMENT,
        start=date(2014, 5, 30),
        end=date(2014, 6, 2),
        params={"cash": "10000"},
        results_dir=activity_run["results_dir"],
        timeout=1,
        broker_adapter="oanda",
        strategies_root=activity_run["strategies_root"],
    )


@when("the external volume strategy is run expecting rejection")
def rejected_activity_run(activity_run: dict[str, Any]) -> None:
    """Capture the production failure rather than a stand-in validation result."""
    with pytest.raises(ValueError) as error:
        run_activity_strategy(activity_run)
    activity_run["error"] = str(error.value)


@then("the container saw the complete schema-1 quote activity manifest before starting")
def manifest_before_container(activity_run: dict[str, Any]) -> None:
    """Writing provenance only after engine execution would fail this observation."""
    activity_run["container"].assert_called_once()
    assert activity_run["manifest_at_start"] == _expected_manifest(activity_run)


@then("the activity data mount and resolved strategy enable canonical tick lookup")
def activity_wiring(activity_run: dict[str, Any]) -> None:
    """Ensure the external volume setting reaches both the mount and staged configuration."""
    assert activity_run["mounts"]["activity/parquet/forex"] == (
        activity_run["data_root"] / "parquet/forex"
    )
    assert activity_run["parameters"]["activity_data_root"] == "/Lean/Data/activity"
    assert activity_run["parameters"]["chain_config"] == _STRATEGY
    assert activity_run["resolved"]["volume_strength"] == {
        "lookback": 3,
        "min_relative_activity": 1.25,
    }
    assert "volume_strength" in activity_run["resolved"]["filters"]


@then("the run succeeds with the original activity manifest preserved")
def successful_activity_run(activity_run: dict[str, Any]) -> None:
    """The normal results parser accepts the mocked engine's actual result artifact."""
    result = activity_run["result"]
    assert result.success and result.closed_trades == 0
    assert result.raw_results_path == activity_run["results_dir"] / "main.json"
    original_manifest_preserved(activity_run)


@then("the saved activity manifest still records the original input bytes")
def original_manifest_preserved(activity_run: dict[str, Any]) -> None:
    """A failed run must not overwrite its initial provenance with mutated input hashes."""
    recorded = json.loads((activity_run["results_dir"] / "activity-inputs.json").read_text())
    assert recorded == _expected_manifest(activity_run)


@then("both canonical input files are unchanged")
def untouched_inputs(activity_run: dict[str, Any]) -> None:
    """Successful orchestration reads canonical evidence without rewriting it."""
    for path, content in activity_run["originals"].items():
        assert path.read_bytes() == content


@then("the container was called exactly once")
def one_container_call(activity_run: dict[str, Any]) -> None:
    """Distinguish a post-execution provenance rejection from preflight failures."""
    activity_run["container"].assert_called_once()
    assert activity_run["manifest_at_start"] == _expected_manifest(activity_run)


@then("the run error reports changed canonical tick activity and says to discard the run")
def changed_input_error(activity_run: dict[str, Any]) -> None:
    """Require the specific provenance failure and an explicit remediation."""
    assert "canonical tick activity changed" in activity_run["error"]
    assert "discard" in activity_run["error"]
    assert "result" not in activity_run


@then(parsers.parse("only the {month} canonical digest changed"))
def only_selected_digest_changes(activity_run: dict[str, Any], month: str) -> None:
    """Prove the mutation touched the intended canonical month, not an unrelated artifact."""
    changed = [
        path
        for path, content in activity_run["originals"].items()
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(content).digest()
    ]
    assert changed == [activity_run["paths"][month]]


@then("the container was never called")
def no_container_call(activity_run: dict[str, Any]) -> None:
    """Missing canonical evidence must stop before allocating a container."""
    activity_run["container"].assert_not_called()


@then(
    parsers.parse("the run error identifies the missing {month} partition and download remediation")
)
def missing_input_error(activity_run: dict[str, Any], month: str) -> None:
    """Identify the exact absent canonical month and the action needed to restore it."""
    assert str(activity_run["paths"][month]) in activity_run["error"]
    assert "download/transform" in activity_run["error"]


@then("no activity manifest or engine result was written")
def no_partial_artifacts(activity_run: dict[str, Any]) -> None:
    """A partial input set must not be recorded as a complete run manifest."""
    for name in ("activity-inputs.json", "main.json"):
        assert not (activity_run["results_dir"] / name).exists()
