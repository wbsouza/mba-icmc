"""Steps for retraining_provider_engine.feature (Story 19 T11/T12 minimum-viable slice).

Fits one real T9 epoch bundle from the project's real EUR/USD data root, then runs the
unmodified production `ChainAlgorithm.initialize()` natively in LEAN with that bundle as
its F7 model (`bundle_registry`/`bundle_id` instead of `model_path`), proving the new
on-demand provider (`retraining.provider.load_active`) loads and predicts through the
real engine end to end.
"""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.chain.filters.f7_meta_learner import FeatureFamily
from algo_backtest.retraining.ingestion import Batch, Ledger, SourceRow
from algo_backtest.retraining.schedule import EXPANDING_START, Epoch
from algo_backtest.retraining.trainer import TrainingSettings, train_epoch
from algo_backtest.retraining.weights import REGISTERED_MINIMA
from algo_backtest.strategies import load_strategy_chain_config, resolved_yaml
from algo_backtest.training import build_training_rows, load_m1_bars
from algo_core import layout
from algo_core.instrument import build_instrument
from pytest_bdd import given, scenarios, then, when

scenarios("../features/retraining_provider_engine.feature")


@pytest.fixture
def bctx() -> dict[str, Any]:
    """Mutable per-scenario context."""
    return {}


@given(
    "one real T9 epoch bundle fitted for policy U deploying 2016-01, published to a fresh registry"
)
def _fit_bundle(bctx: dict[str, Any], tmp_path: Path) -> None:
    """Fit+validate+publish one real bundle (T9's `train_epoch`) over real EUR/USD bars.

    Family/combiner/threshold spans follow `schedule.stage_spans` for policy U exactly
    as production would compute them for the 2016-01 deployment epoch: family
    [2015-03-02, 2015-11-01), combiner [2015-11-01, 2015-12-01), threshold
    [2015-12-01, 2015-12-31).
    """
    data_root = layout.data_root()
    if not (data_root / "parquet" / "forex" / "EURUSD" / "m1").is_dir():
        pytest.skip(
            f"real EUR/USD M1 parquet not found under {data_root}; set ALGO_DATA_ROOT to "
            "the project's data root (same requirement as scripts/train_baseline_meta_learner.py)"
        )

    instrument = build_instrument("EURUSD")
    config = load_strategy_chain_config("baseline")
    assert config.f7 is not None

    bars = load_m1_bars(data_root, instrument, date(2015, 3, 2), date(2016, 1, 31))
    rows = build_training_rows(
        bars,
        instrument=instrument,
        perception=config.perception,
        price_features_config=config.price_features,
        horizon_minutes=config.f7.label_horizon_minutes,
        pattern_config=config.pattern,
        volume_config=config.volume_strength,
    )
    source_rows = tuple(
        SourceRow(
            key=row.timestamp.isoformat(),
            available_at=row.timestamp,
            label_time=row.label_time,
            label=row.label,
        )
        for row in rows
    )
    features = {row.timestamp.isoformat(): row.features for row in rows}

    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()
    ledger = Ledger.open(ledger_dir).consume(
        Batch(partition="eurusd-m1-2015-03-02_2016-01-31", rows=source_rows)
    )

    epoch = Epoch(
        start=datetime(2016, 1, 1, tzinfo=UTC),
        end=datetime(2016, 2, 1, tzinfo=UTC),
        schedule_start=EXPANDING_START,
    )
    settings = TrainingSettings(
        half_life_days=90.0,
        seed=1337,
        families=(FeatureFamily.TREND, FeatureFamily.INDICATOR, FeatureFamily.PATTERN),
        family_minima=REGISTERED_MINIMA["family"],
        combiner_minima=REGISTERED_MINIMA["combiner"],
        threshold_min_rows=REGISTERED_MINIMA["threshold"].min_rows,
        config_sha256="0" * 64,
        protocol_sha256="0" * 64,
    )
    registry = tmp_path / "registry"
    registry.mkdir()
    result = train_epoch("U", epoch, ledger, features, registry, settings)
    assert result.family.rows >= REGISTERED_MINIMA["family"].min_rows
    assert result.combiner.rows >= REGISTERED_MINIMA["combiner"].min_rows
    bctx["bundle_id"] = result.bundle_id
    bctx["registry"] = registry
    bctx["config"] = config


@when(
    "the baseline chain runs natively over the bundle's deployment window with that "
    "bundle as its F7 model"
)
def _run_native(bctx: dict[str, Any], tmp_path: Path, lean_backtest) -> None:  # noqa: ANN001
    """Assemble a fresh algo dir (fixture main.py + the fitted bundle) and run real LEAN."""
    algo_dir = tmp_path / "algo"
    shutil.copytree(Path(__file__).parents[1] / "algos" / "bundle_provider_baseline", algo_dir)
    shutil.copytree(bctx["registry"], algo_dir / "bundle_registry")
    (algo_dir / "bundle_id.txt").write_text(bctx["bundle_id"])

    strategy_yaml = tmp_path / "strategy.yaml"
    strategy_yaml.write_text(resolved_yaml(bctx["config"]))

    data_root = layout.data_root()
    results = tmp_path / "results"
    results.mkdir()
    bctx["result"] = lean_backtest(
        algo_dir=algo_dir,
        results_dir=results,
        data_mounts={
            "forex/oanda/minute/eurusd": data_root / "lean-data/forex/oanda/minute/eurusd",
        },
        algo_files={"strategy.yaml": strategy_yaml},
        parameters={
            "symbol": "EURUSD",
            "start": "20160104",
            "end": "20160108",
            "cash": "10000",
            "broker_adapter": "oanda",
        },
    )


@then("the strategy run exits successfully")
def _exit_ok(bctx: dict[str, Any]) -> None:
    assert bctx["result"].exit_code == 0, bctx["result"].logs[-12000:]


@then("the container log shows the algorithm loaded the published bundle")
def _bundle_loaded(bctx: dict[str, Any]) -> None:
    logs = bctx["result"].logs
    assert f"BUNDLEPROVIDER_BUNDLE_ID={bctx['bundle_id']}" in logs, logs[-12000:]
    assert "BUNDLEPROVIDER_MODEL_SHA256=" in logs, logs[-12000:]


@then("the container log shows the F1-F7 chain actually evaluated a decision")
def _chain_ran(bctx: dict[str, Any]) -> None:
    assert "BUNDLEPROVIDER_DECISION|" in bctx["result"].logs, bctx["result"].logs[-12000:]


@then("a metrics summary is reported")
def _metrics(bctx: dict[str, Any]) -> None:
    logs = bctx["result"].logs
    assert "STATISTICS:: Net Profit" in logs, logs[-12000:]
    assert "STATISTICS:: Win Rate" in logs, logs[-12000:]
