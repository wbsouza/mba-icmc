"""Steps for f7_model_io.feature — portable F7 model persistence."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    TrainedMetaLearner,
    TrainingRow,
    WalkForwardSplit,
    train_meta_learner,
    walk_forward_split,
)
from algo_backtest.chain.filters.f7_model_io import (
    BoosterFamilyModel,
    LogisticCombiner,
    dump_model,
    load_families,
    load_model,
    load_provenance,
    require_families,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f7_model_io.feature")

_FAMILIES = (
    FeatureFamily.TREND, FeatureFamily.INDICATOR, FeatureFamily.PATTERN, FeatureFamily.NEWS,
)


@dataclass
class _IoCtx:
    """Per-scenario fixture context."""

    path: Path
    trained: TrainedMetaLearner | None = None
    split: WalkForwardSplit | None = None
    loaded: TrainedMetaLearner | None = None
    error: ValueError | None = None
    provenance: dict[str, object] = field(default_factory=dict)


@pytest.fixture
def io_ctx(tmp_path: Path) -> _IoCtx:
    """A fresh per-scenario context."""
    return _IoCtx(path=tmp_path / "f7_meta_learner.json")


def synthetic_rows(seed: int = 7) -> list[TrainingRow]:
    """Three days of hourly rows whose label leans on trend and news, deterministically."""
    rng = random.Random(seed)
    rows = []
    for i in range(72):
        direction = rng.choice([-1.0, 1.0])
        intensity = rng.uniform(-3.0, 3.0)
        features: dict[str, object] = {
            "trend_direction": direction,
            "trend_strength": rng.uniform(0.0, 100.0),
            "higher_tf_trend_direction": rng.choice([-1.0, 0.0, 1.0]),
            "rsi": rng.uniform(20.0, 80.0),
            "macd_hist": rng.uniform(-1e-4, 1e-4),
            "candlestick_pattern": None,
            "news_event_intensity": intensity,
            "news_sentiment_score": None,
        }
        label = 1 if direction + 0.3 * intensity + rng.gauss(0.0, 0.5) > 0 else 0
        rows.append(
            TrainingRow(
                timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i),
                features=features,
                label=label,
            )
        )
    return rows


@given(
    "a meta-learner trained on seeded synthetic rows with the trend, indicator, pattern and "
    "news families"
)
def _trained(io_ctx: _IoCtx) -> None:
    io_ctx.split = walk_forward_split(
        synthetic_rows(),
        train_end=date(2024, 1, 1),
        validation_end=date(2024, 1, 2),
        test_end=date(2024, 1, 3),
    )
    io_ctx.trained = train_meta_learner(families=_FAMILIES, split=io_ctx.split)


@given(parsers.parse("a JSON file claiming F7 format version {version:d}"))
def _foreign(io_ctx: _IoCtx, version: int) -> None:
    io_ctx.path.write_text(
        json.dumps({"format": "algo-backtest/f7-meta-learner", "format_version": version})
    )


@when("the model is dumped to JSON and loaded back")
def _round_trip(io_ctx: _IoCtx) -> None:
    assert io_ctx.trained is not None
    dump_model(io_ctx.trained, io_ctx.path, {})
    io_ctx.loaded = load_model(io_ctx.path)


@when(
    parsers.parse(
        'the model is dumped to JSON with provenance strategy "{strategy}" and loaded back'
    )
)
def _round_trip_provenance(io_ctx: _IoCtx, strategy: str) -> None:
    assert io_ctx.trained is not None
    dump_model(io_ctx.trained, io_ctx.path, {"strategy": strategy})
    io_ctx.loaded = load_model(io_ctx.path)
    io_ctx.provenance = load_provenance(io_ctx.path)


@when("loading it as an F7 model fails")
def _load_fails(io_ctx: _IoCtx) -> None:
    with pytest.raises(ValueError) as excinfo:
        load_model(io_ctx.path)
    io_ctx.error = excinfo.value


@then("the loaded model's p_hat matches the trained model's on every test row")
def _same_predictions(io_ctx: _IoCtx) -> None:
    assert io_ctx.trained is not None and io_ctx.loaded is not None and io_ctx.split
    for row in io_ctx.split.test:
        assert io_ctx.loaded.predict(row.features) == pytest.approx(
            io_ctx.trained.predict(row.features), abs=1e-9
        )


@then("the loaded model carries no scikit-learn or pickled object")
def _no_sklearn(io_ctx: _IoCtx) -> None:
    assert io_ctx.loaded is not None
    assert isinstance(io_ctx.loaded.meta_model, LogisticCombiner)
    assert all(isinstance(m, BoosterFamilyModel) for m in io_ctx.loaded.family_models.values())
    json.loads(io_ctx.path.read_text())  # plain JSON, nothing to unpickle


@then(parsers.parse('the document\'s provenance strategy is "{strategy}"'))
def _provenance(io_ctx: _IoCtx, strategy: str) -> None:
    assert io_ctx.provenance == {"strategy": strategy}


@then(parsers.parse('the model failure names "{fragment}"'))
def _failure(io_ctx: _IoCtx, fragment: str) -> None:
    assert io_ctx.error is not None and fragment in str(io_ctx.error)


@then(
    "each F7-driven strategy's bundled model has exactly its config.yaml meta_learner families"
)
def _bundled_models_match() -> None:
    """Guards the committed artifacts themselves, not just the runtime check."""
    import algo_backtest
    from algo_backtest.run import STRATEGIES
    from algo_backtest.strategies import load_strategy_chain_config

    algos = Path(algo_backtest.__file__).parent / "algos"
    chain_strategies = {n: s for n, s in STRATEGIES.items() if s.model_file}
    assert set(chain_strategies) == {"baseline", "baseline-dsha", "hybrid"}
    for name, spec in chain_strategies.items():
        assert spec.model_file is not None
        families = load_families(algos / spec.algo_dir / spec.model_file)
        declared = load_strategy_chain_config(name).meta_learner_families
        assert sorted(f.value for f in families) == sorted(declared), name


@when(parsers.parse('families "{trained}" are required to match "{declared}"'))
def _require_mismatch(io_ctx: _IoCtx, trained: str, declared: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        require_families(
            [FeatureFamily(f.strip()) for f in trained.split(",")],
            [f.strip() for f in declared.split(",")],
            where="fixture",
        )
    io_ctx.error = excinfo.value
