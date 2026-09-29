"""Steps for f7_family_weights.feature: optional row-aligned sample weights in F7 family fits."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pytest
from algo_backtest.chain.filters import f7_meta_learner as f7
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    TrainedMetaLearner,
    TrainingRow,
    WalkForwardSplit,
    family_vector,
    train_meta_learner,
)
from lightgbm import LGBMClassifier
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f7_family_weights.feature")

_TRAIN_ROWS = 40
_TWO_FAMILIES = [FeatureFamily.TREND, FeatureFamily.INDICATOR]
_TREND_ONLY = [FeatureFamily.TREND]
_RAMP = [round(0.05 * i, 2) for i in range(1, _TRAIN_ROWS + 1)]


@dataclass(frozen=True)
class _ObservedFit:
    """What one LightGBM `fit` call received."""

    inputs: np.ndarray
    has_sample_weight: bool
    sample_weight: np.ndarray | None


class _RecordingClassifier(LGBMClassifier):  # type: ignore[misc]
    """An `LGBMClassifier` that records every `fit` call's arguments, then really fits."""

    observed: list[_ObservedFit] = []

    def fit(self, X: Any, y: Any, **kwargs: Any) -> Any:  # noqa: N803 - sklearn's name
        weight = kwargs.get("sample_weight")
        _RecordingClassifier.observed.append(
            _ObservedFit(
                inputs=np.asarray(X),
                has_sample_weight="sample_weight" in kwargs,
                sample_weight=None if weight is None else np.asarray(weight),
            )
        )
        return super().fit(X, y, **kwargs)


@dataclass
class _WeightsCtx:
    """Per-scenario state: the split, the weights, the trained models, observed fits."""

    split: WalkForwardSplit | None = None
    weights: list[float] | None = None
    trained: list[TrainedMetaLearner] = field(default_factory=list)
    observed: list[_ObservedFit] = field(default_factory=list)
    error: Exception | None = None


@pytest.fixture
def fw_ctx() -> _WeightsCtx:
    """A fresh per-scenario context."""
    return _WeightsCtx()


def _row(index: int, features: dict[str, object], label: int) -> TrainingRow:
    """One hourly row with a known label; the timestamp only orders the split."""
    return TrainingRow(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=index),
        features=features,
        label=label,
    )


def _correlated_features(rng: random.Random) -> tuple[dict[str, object], int]:
    """Trend and indicator readings whose label follows the trend direction, with noise."""
    direction = rng.choice([-1.0, 1.0])
    features: dict[str, object] = {
        "trend_direction": direction,
        "trend_strength": rng.uniform(20.0, 80.0),
        "higher_tf_trend_direction": rng.choice([-1.0, 0.0, 1.0]),
        "rsi": (70.0 if direction > 0 else 30.0) + rng.uniform(-5.0, 5.0),
        "macd_hist": direction * rng.uniform(0.0, 1e-4),
    }
    label = 1 if direction > 0 and rng.random() < 0.85 else (1 if rng.random() < 0.15 else 0)
    return features, label


def _synthetic_split() -> WalkForwardSplit:
    """40 seeded train rows plus validation/test rows that carry both classes."""
    rng = random.Random(19)
    rows = [_row(i, *_correlated_features(rng)) for i in range(_TRAIN_ROWS + 12)]
    return WalkForwardSplit(
        train=tuple(rows[:_TRAIN_ROWS]),
        validation=tuple(rows[_TRAIN_ROWS : _TRAIN_ROWS + 8]),
        test=tuple(rows[_TRAIN_ROWS + 8 :]),
    )


_IDENTICAL_TREND: dict[str, object] = {
    "trend_direction": 1.0,
    "trend_strength": 50.0,
    "higher_tf_trend_direction": 1.0,
}


def _balanced_identical_split() -> WalkForwardSplit:
    """40 train rows with identical trend features, 20 UP then 20 DOWN; validation both classes."""
    train = [_row(i, dict(_IDENTICAL_TREND), 1 if i < 20 else 0) for i in range(_TRAIN_ROWS)]
    validation = [
        _row(100, dict(_IDENTICAL_TREND), 1),
        _row(101, {**_IDENTICAL_TREND, "trend_direction": -1.0}, 0),
        _row(102, dict(_IDENTICAL_TREND), 1),
        _row(103, {**_IDENTICAL_TREND, "trend_direction": -1.0}, 0),
    ]
    return WalkForwardSplit(train=tuple(train), validation=tuple(validation), test=())


def _train(fw_ctx: _WeightsCtx, families: list[FeatureFamily], **kwargs: Any) -> TrainedMetaLearner:
    """Train on the scenario's split with exactly the given keyword arguments."""
    assert fw_ctx.split is not None
    trained = train_meta_learner(families, fw_ctx.split, random_state=42, **kwargs)
    fw_ctx.trained.append(trained)
    return trained


# --- Given ---------------------------------------------------------------------------------


@given("a synthetic walk-forward training split with 40 labeled rows")
def _split(fw_ctx: _WeightsCtx) -> None:
    fw_ctx.split = _synthetic_split()
    assert len(fw_ctx.split.train) == _TRAIN_ROWS


@given(
    "a walk-forward split whose 40 train rows share identical trend features, the first 20 "
    "labeled UP and the last 20 labeled DOWN"
)
def _identical_split(fw_ctx: _WeightsCtx) -> None:
    fw_ctx.split = _balanced_identical_split()


@given("LightGBM fits are observed")
def _observe(fw_ctx: _WeightsCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingClassifier.observed = fw_ctx.observed
    monkeypatch.setattr(f7, "LGBMClassifier", _RecordingClassifier)


@given("family_weights are the 40 values 0.05, 0.10, 0.15, ... up to 2.00")
def _ramp_weights(fw_ctx: _WeightsCtx) -> None:
    fw_ctx.weights = list(_RAMP)


@given(parsers.parse("family_weights are {count:d} values of 1.0"))
def _unit_weights(fw_ctx: _WeightsCtx, count: int) -> None:
    fw_ctx.weights = [1.0] * count


@given(
    parsers.parse(
        "family_weights are 40 values of 1.0 except position {position:d} which is {value}"
    )
)
def _one_bad_weight(fw_ctx: _WeightsCtx, position: int, value: str) -> None:
    weights = [1.0] * _TRAIN_ROWS
    weights[position] = float(value)
    fw_ctx.weights = weights


# --- When ----------------------------------------------------------------------------------


@when("the meta-learner is trained with the legacy call on the trend and indicator families")
def _train_legacy(fw_ctx: _WeightsCtx) -> None:
    _train(fw_ctx, _TWO_FAMILIES)


@when("the meta-learner is trained with family_weights omitted on the trend and indicator families")
def _train_omitted(fw_ctx: _WeightsCtx) -> None:
    _train(fw_ctx, _TWO_FAMILIES, family_weights=None)


@when(
    "the meta-learner is trained with 40 family_weights of 1.0 on the trend and indicator families"
)
def _train_unit(fw_ctx: _WeightsCtx) -> None:
    _train(fw_ctx, _TWO_FAMILIES, family_weights=[1.0] * _TRAIN_ROWS)


@when("the meta-learner is trained with those family_weights on the trend and indicator families")
def _train_with_weights(fw_ctx: _WeightsCtx) -> None:
    _train(fw_ctx, _TWO_FAMILIES, family_weights=fw_ctx.weights)


@when("training the meta-learner with those family_weights on the trend family fails")
def _train_fails(fw_ctx: _WeightsCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _train(fw_ctx, _TREND_ONLY, family_weights=fw_ctx.weights)
    fw_ctx.error = exc_info.value


@when(
    parsers.re(
        r"^the meta-learner is trained on the trend family with (?:family_weights omitted|"
        r"the first 20 weights (?P<head>[\d.]+) and the last 20 weights (?P<tail>[\d.]+))$"
    )
)
def _train_effect(fw_ctx: _WeightsCtx, head: str | None, tail: str | None) -> None:
    if head is None:
        _train(fw_ctx, _TREND_ONLY)
    else:
        assert tail is not None
        _train(fw_ctx, _TREND_ONLY, family_weights=[float(head)] * 20 + [float(tail)] * 20)


# --- Then ----------------------------------------------------------------------------------


def _trend_p_up(model: TrainedMetaLearner, features: dict[str, object]) -> float:
    """The trend family sub-model's P(up) for `features`."""
    return model.family_models[FeatureFamily.TREND].predict_proba_up(
        family_vector(FeatureFamily.TREND, features)
    )


@then("both trained meta-learners predict the same p_hat for the same held-out row")
def _same_p_hat(fw_ctx: _WeightsCtx) -> None:
    assert fw_ctx.split is not None
    first, second = fw_ctx.trained
    held_out = fw_ctx.split.validation[0].features
    assert first.predict(held_out) == second.predict(held_out)


@then("both trained meta-learners' trend family P(up) is identical on every train row")
def _same_trend_p_up(fw_ctx: _WeightsCtx) -> None:
    assert fw_ctx.split is not None
    first, second = fw_ctx.trained
    for row in fw_ctx.split.train:
        assert _trend_p_up(first, dict(row.features)) == _trend_p_up(second, dict(row.features))


@then(parsers.parse("{count:d} LightGBM fits were observed"))
def _fit_count(fw_ctx: _WeightsCtx, count: int) -> None:
    assert len(fw_ctx.observed) == count


@then(
    "every observed fit received sample_weight equal to 0.05, 0.10, 0.15, ... up to 2.00 in "
    "that order"
)
def _fits_received_ramp(fw_ctx: _WeightsCtx) -> None:
    for fit in fw_ctx.observed:
        assert fit.has_sample_weight
        assert fit.sample_weight is not None
        assert fit.sample_weight.tolist() == _RAMP


@then("every observed fit received 40 input rows in split.train order")
def _fits_received_train_rows(fw_ctx: _WeightsCtx) -> None:
    """Each fit's matrix equals the family vectors of split.train, row for row; the family
    is recognized by its column count (trend 3, indicator 2)."""
    assert fw_ctx.split is not None
    by_width = {
        len(family_vector(family, {})): np.array(
            [family_vector(family, row.features) for row in fw_ctx.split.train]
        )
        for family in _TWO_FAMILIES
    }
    for fit in fw_ctx.observed:
        assert fit.inputs.shape[0] == _TRAIN_ROWS
        expected = by_width[fit.inputs.shape[1]]
        assert np.array_equal(fit.inputs, expected, equal_nan=True)


@then("no observed fit received a sample_weight")
def _fits_received_no_weight(fw_ctx: _WeightsCtx) -> None:
    for fit in fw_ctx.observed:
        assert not fit.has_sample_weight


@then(parsers.parse('the training failure names "{fragment}"'))
def _failure_names(fw_ctx: _WeightsCtx, fragment: str) -> None:
    assert fw_ctx.error is not None
    assert fragment in str(fw_ctx.error)


@then(
    parsers.re(
        r"^the trend family's P\(up\) for those features is "
        r"(?P<relation>exactly|above|below) (?P<bound>[\d.]+)$"
    )
)
def _trend_effect(fw_ctx: _WeightsCtx, relation: str, bound: str) -> None:
    (model,) = fw_ctx.trained
    p_up = _trend_p_up(model, dict(_IDENTICAL_TREND))
    limit = float(bound)
    if relation == "exactly":
        assert p_up == limit
    elif relation == "above":
        assert p_up > limit
    else:
        assert p_up < limit
