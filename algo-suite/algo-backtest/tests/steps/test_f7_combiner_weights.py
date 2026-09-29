"""Steps for f7_combiner_weights.feature: independent row-aligned combiner-stage weights."""

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
from sklearn.linear_model import LogisticRegression

scenarios("../features/f7_combiner_weights.feature")

_TRAIN_ROWS = 40
_VALIDATION_ROWS = 8
_TWO_FAMILIES = [FeatureFamily.TREND, FeatureFamily.INDICATOR]
_TREND_ONLY = [FeatureFamily.TREND]
_FAMILY_RAMP = [round(0.05 * i, 2) for i in range(1, _TRAIN_ROWS + 1)]
_COMBINER_RAMP = [round(0.25 * i, 2) for i in range(1, _VALIDATION_ROWS + 1)]
_HELD_OUT_FEATURES: dict[str, object] = {
    "trend_direction": 1.0,
    "trend_strength": 65.0,
    "higher_tf_trend_direction": 1.0,
    "rsi": 60.0,
    "macd_hist": 0.00005,
}
_IDENTICAL_VALIDATION_FEATURES: dict[str, object] = {
    "trend_direction": 1.0,
    "trend_strength": 50.0,
    "higher_tf_trend_direction": 1.0,
}


@dataclass(frozen=True)
class _ObservedFit:
    """What one `fit` call received."""

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


class _RecordingLogisticRegression(LogisticRegression):  # type: ignore[misc]
    """A `LogisticRegression` that records every `fit` call's arguments, then really fits."""

    observed: list[_ObservedFit] = []

    def fit(self, X: Any, y: Any, **kwargs: Any) -> Any:  # noqa: N803 - sklearn's name
        weight = kwargs.get("sample_weight")
        _RecordingLogisticRegression.observed.append(
            _ObservedFit(
                inputs=np.asarray(X),
                has_sample_weight="sample_weight" in kwargs,
                sample_weight=None if weight is None else np.asarray(weight),
            )
        )
        return super().fit(X, y, **kwargs)


@dataclass
class _CombinerCtx:
    """Per-scenario state: the split, both weight vectors, trained models, observed fits."""

    split: WalkForwardSplit | None = None
    family_weights: list[float] | None = None
    combiner_weights: list[float] | None = None
    trained: list[TrainedMetaLearner] = field(default_factory=list)
    lgbm_observed: list[_ObservedFit] = field(default_factory=list)
    logreg_observed: list[_ObservedFit] = field(default_factory=list)
    error: Exception | None = None


@pytest.fixture
def cw_ctx() -> _CombinerCtx:
    """A fresh per-scenario context."""
    return _CombinerCtx()


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
    """40 seeded train rows, 8 validation rows and 4 test rows, all carrying both classes."""
    rng = random.Random(19)
    rows = [_row(i, *_correlated_features(rng)) for i in range(_TRAIN_ROWS + 12)]
    return WalkForwardSplit(
        train=tuple(rows[:_TRAIN_ROWS]),
        validation=tuple(rows[_TRAIN_ROWS : _TRAIN_ROWS + _VALIDATION_ROWS]),
        test=tuple(rows[_TRAIN_ROWS + _VALIDATION_ROWS :]),
    )


def _trend_row(day: int, trend_direction: float, label: int) -> TrainingRow:
    """One TREND-only training row: a fixed trend_direction/label pair on a given day."""
    return TrainingRow(
        timestamp=datetime(2020, 1, day, tzinfo=UTC),
        features={
            "trend_direction": trend_direction,
            "trend_strength": 50.0,
            "higher_tf_trend_direction": trend_direction,
        },
        label=label,
    )


def _balanced_identical_validation_split() -> WalkForwardSplit:
    """A regular train span, then 40 validation rows with identical features, 20 UP, 20 DOWN."""
    rng = random.Random(31)
    train = [_row(i, *_correlated_features(rng)) for i in range(_TRAIN_ROWS)]
    validation = [
        _row(100 + i, dict(_IDENTICAL_VALIDATION_FEATURES), 1 if i < 20 else 0) for i in range(40)
    ]
    test = [_row(200 + i, *_correlated_features(rng)) for i in range(4)]
    return WalkForwardSplit(train=tuple(train), validation=tuple(validation), test=tuple(test))


def _train(
    cw_ctx: _CombinerCtx, families: list[FeatureFamily], **kwargs: Any
) -> TrainedMetaLearner:
    """Train on the scenario's split with exactly the given keyword arguments."""
    assert cw_ctx.split is not None
    trained = train_meta_learner(families, cw_ctx.split, random_state=42, **kwargs)
    cw_ctx.trained.append(trained)
    return trained


# --- Given ---------------------------------------------------------------------------------


@given(
    "a synthetic walk-forward training split with 40 train rows, 8 validation rows and 4 test rows"
)
def _split(cw_ctx: _CombinerCtx) -> None:
    cw_ctx.split = _synthetic_split()
    assert len(cw_ctx.split.train) == _TRAIN_ROWS
    assert len(cw_ctx.split.validation) == _VALIDATION_ROWS
    assert len(cw_ctx.split.test) == 4


@given("LightGBM fits are observed")
def _observe_lgbm(cw_ctx: _CombinerCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingClassifier.observed = cw_ctx.lgbm_observed
    monkeypatch.setattr(f7, "LGBMClassifier", _RecordingClassifier)


@given("LogisticRegression fits are observed")
def _observe_logreg(cw_ctx: _CombinerCtx, monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingLogisticRegression.observed = cw_ctx.logreg_observed
    monkeypatch.setattr(f7, "LogisticRegression", _RecordingLogisticRegression)


@given("family_weights are the 40 values 0.05, 0.10, 0.15, ... up to 2.00")
def _ramp_family_weights(cw_ctx: _CombinerCtx) -> None:
    cw_ctx.family_weights = list(_FAMILY_RAMP)


@given("combiner_weights are the 8 values 0.25, 0.50, 0.75, ... up to 2.00")
def _ramp_combiner_weights(cw_ctx: _CombinerCtx) -> None:
    cw_ctx.combiner_weights = list(_COMBINER_RAMP)


@given(parsers.parse("family_weights are {count:d} values of 1.0"))
def _unit_family_weights(cw_ctx: _CombinerCtx, count: int) -> None:
    cw_ctx.family_weights = [1.0] * count


@given(parsers.parse("combiner_weights are {count:d} values of 1.0"))
def _unit_combiner_weights(cw_ctx: _CombinerCtx, count: int) -> None:
    cw_ctx.combiner_weights = [1.0] * count


@given(
    parsers.parse(
        "combiner_weights are 8 values of 1.0 except position {position:d} which is {value}"
    )
)
def _one_bad_combiner_weight(cw_ctx: _CombinerCtx, position: int, value: str) -> None:
    weights = [1.0] * _VALIDATION_ROWS
    weights[position] = float(value)
    cw_ctx.combiner_weights = weights


@given(parsers.parse("a walk-forward split whose validation labels are {labels}"))
def _split_with_validation_labels(cw_ctx: _CombinerCtx, labels: str) -> None:
    """A mixed-label train span, then one validation row per listed label (alternating
    trend_direction so the features themselves are never degenerate)."""
    import yaml

    train_rows = [_trend_row(d, 1.0, 1) for d in range(1, 6)] + [
        _trend_row(d, -1.0, 0) for d in range(6, 11)
    ]
    validation_rows = [
        _trend_row(11 + i, 1.0 if i % 2 == 0 else -1.0, int(label))
        for i, label in enumerate(yaml.safe_load(labels))
    ]
    cw_ctx.split = WalkForwardSplit(
        train=tuple(train_rows),
        validation=tuple(validation_rows),
        test=(_trend_row(20, 1.0, 1),),
    )


@given(
    "a walk-forward split where trend_direction predicts UP in train but the true label "
    "is DOWN, and the reverse in validation"
)
def _inverted_train_validation_split(cw_ctx: _CombinerCtx) -> None:
    train_rows = [_trend_row(d, 1.0, 1) for d in range(1, 6)] + [
        _trend_row(d, -1.0, 0) for d in range(6, 11)
    ]
    validation_rows = [_trend_row(d, 1.0, 0) for d in range(11, 14)] + [
        _trend_row(d, -1.0, 1) for d in range(14, 17)
    ]
    test_rows = [_trend_row(17, 1.0, 1), _trend_row(18, -1.0, 0)]
    cw_ctx.split = WalkForwardSplit(
        train=tuple(train_rows), validation=tuple(validation_rows), test=tuple(test_rows)
    )


@given(
    "a walk-forward split whose 40 validation rows share identical features, the first 20 "
    "labeled UP and the last 20 labeled DOWN"
)
def _identical_validation_split(cw_ctx: _CombinerCtx) -> None:
    cw_ctx.split = _balanced_identical_validation_split()


# --- When ------------------------------------------------------------------------------------


@when("the meta-learner is trained with the legacy call on the trend and indicator families")
def _train_legacy(cw_ctx: _CombinerCtx) -> None:
    _train(cw_ctx, _TWO_FAMILIES)


@when(
    "the meta-learner is trained with combiner_weights omitted on the trend and indicator families"
)
def _train_combiner_omitted(cw_ctx: _CombinerCtx) -> None:
    _train(cw_ctx, _TWO_FAMILIES, combiner_weights=None)


@when(
    "the meta-learner is trained with 8 combiner_weights of 1.0 on the trend and indicator families"
)
def _train_unit_combiner(cw_ctx: _CombinerCtx) -> None:
    _train(cw_ctx, _TWO_FAMILIES, combiner_weights=[1.0] * _VALIDATION_ROWS)


@when(
    "the meta-learner is trained with those family_weights and combiner_weights on the trend "
    "and indicator families"
)
def _train_both_weights(cw_ctx: _CombinerCtx) -> None:
    _train(
        cw_ctx,
        _TWO_FAMILIES,
        family_weights=cw_ctx.family_weights,
        combiner_weights=cw_ctx.combiner_weights,
    )


@when("the meta-learner is trained with those combiner_weights on the trend and indicator families")
def _train_combiner_only(cw_ctx: _CombinerCtx) -> None:
    _train(cw_ctx, _TWO_FAMILIES, combiner_weights=cw_ctx.combiner_weights)


@when(
    parsers.parse(
        "the meta-learner is trained with {count:d} combiner_weights of 0.5 on the trend and "
        "indicator families"
    )
)
def _train_half_combiner(cw_ctx: _CombinerCtx, count: int) -> None:
    _train(cw_ctx, _TWO_FAMILIES, combiner_weights=[0.5] * count)


@when(
    "the test rows are replaced by 4 different rows and the meta-learner is trained again with "
    "8 combiner_weights of 0.5 on the trend and indicator families"
)
def _train_with_different_test(cw_ctx: _CombinerCtx) -> None:
    assert cw_ctx.split is not None
    rng = random.Random(97)
    new_test = tuple(_row(300 + i, *_correlated_features(rng)) for i in range(4))
    cw_ctx.split = WalkForwardSplit(
        train=cw_ctx.split.train, validation=cw_ctx.split.validation, test=new_test
    )
    _train(cw_ctx, _TWO_FAMILIES, combiner_weights=[0.5] * _VALIDATION_ROWS)


@when("the meta-learner is trained on the trend family alone with uniform combiner_weights of 1.0")
def _train_trend_alone_uniform(cw_ctx: _CombinerCtx) -> None:
    assert cw_ctx.split is not None
    _train(cw_ctx, _TREND_ONLY, combiner_weights=[1.0] * len(cw_ctx.split.validation))


@when(
    parsers.re(
        r"^the meta-learner is trained on the trend family with (?:combiner_weights omitted|"
        r"the first 20 combiner weights (?P<head>[\d.]+) and the last 20 weights (?P<tail>[\d.]+))$"
    )
)
def _train_trend_weighting_effect(cw_ctx: _CombinerCtx, head: str | None, tail: str | None) -> None:
    if head is None:
        _train(cw_ctx, _TREND_ONLY)
    else:
        assert tail is not None
        _train(cw_ctx, _TREND_ONLY, combiner_weights=[float(head)] * 20 + [float(tail)] * 20)


@when(
    "training the meta-learner with those family_weights and combiner_weights on the trend "
    "family fails"
)
def _train_both_fails(cw_ctx: _CombinerCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _train(
            cw_ctx,
            _TREND_ONLY,
            family_weights=cw_ctx.family_weights,
            combiner_weights=cw_ctx.combiner_weights,
        )
    cw_ctx.error = exc_info.value


@when("training the meta-learner with those combiner_weights on the trend family fails")
def _train_combiner_only_fails(cw_ctx: _CombinerCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _train(cw_ctx, _TREND_ONLY, combiner_weights=cw_ctx.combiner_weights)
    cw_ctx.error = exc_info.value


@when(
    parsers.parse(
        "training the meta-learner with {count:d} combiner_weights of 1.0 on the trend family fails"
    )
)
def _train_unit_combiner_fails(cw_ctx: _CombinerCtx, count: int) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _train(cw_ctx, _TREND_ONLY, combiner_weights=[1.0] * count)
    cw_ctx.error = exc_info.value


@when(
    parsers.parse(
        "training the meta-learner with the combiner_weights {values} on the trend family fails"
    )
)
def _train_literal_combiner_fails(cw_ctx: _CombinerCtx, values: str) -> None:
    weights = [float(part.strip()) for part in values.split(",")]
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _train(cw_ctx, _TREND_ONLY, combiner_weights=weights)
    cw_ctx.error = exc_info.value


# --- Then ----------------------------------------------------------------------------------


@then("both trained meta-learners predict the same p_hat for the same held-out row")
def _same_p_hat(cw_ctx: _CombinerCtx) -> None:
    first, second = cw_ctx.trained[-2], cw_ctx.trained[-1]
    assert first.predict(_HELD_OUT_FEATURES) == second.predict(_HELD_OUT_FEATURES)


@then("both trained meta-learners have identical combiner coefficients and intercept")
def _same_combiner_params(cw_ctx: _CombinerCtx) -> None:
    first, second = cw_ctx.trained[-2], cw_ctx.trained[-1]
    first_model: Any = first.meta_model
    second_model: Any = second.meta_model
    assert np.array_equal(first_model.coef_, second_model.coef_)
    assert np.array_equal(first_model.intercept_, second_model.intercept_)


@then(parsers.re(r"^(?P<count>\d+) LightGBM fits? (?:was|were) observed$"))
def _lgbm_fit_count(cw_ctx: _CombinerCtx, count: str) -> None:
    assert len(cw_ctx.lgbm_observed) == int(count)


@then(parsers.re(r"^(?P<count>\d+) LogisticRegression fits? (?:was|were) observed$"))
def _logreg_fit_count(cw_ctx: _CombinerCtx, count: str) -> None:
    assert len(cw_ctx.logreg_observed) == int(count)


@then("no observed fit received a sample_weight")
def _lgbm_no_weight(cw_ctx: _CombinerCtx) -> None:
    for fit in cw_ctx.lgbm_observed:
        assert not fit.has_sample_weight


@then("no observed LogisticRegression fit received a sample_weight")
def _logreg_no_weight(cw_ctx: _CombinerCtx) -> None:
    for fit in cw_ctx.logreg_observed:
        assert not fit.has_sample_weight


@then(
    "every observed fit received sample_weight equal to 0.05, 0.10, 0.15, ... up to 2.00 in "
    "that order"
)
def _lgbm_ramp_weight(cw_ctx: _CombinerCtx) -> None:
    for fit in cw_ctx.lgbm_observed:
        assert fit.has_sample_weight
        assert fit.sample_weight is not None
        assert fit.sample_weight.tolist() == _FAMILY_RAMP


@then(
    "the observed LogisticRegression fit received sample_weight equal to 0.25, 0.50, 0.75, "
    "... up to 2.00 in that order"
)
def _logreg_ramp_weight(cw_ctx: _CombinerCtx) -> None:
    (fit,) = cw_ctx.logreg_observed
    assert fit.has_sample_weight
    assert fit.sample_weight is not None
    assert fit.sample_weight.tolist() == _COMBINER_RAMP


@then(
    "the observed LogisticRegression fit received 8 input rows equal to the families' P(up) "
    "on split.validation in order"
)
def _logreg_inputs_match_predictions(cw_ctx: _CombinerCtx) -> None:
    (fit,) = cw_ctx.logreg_observed
    trained = cw_ctx.trained[-1]
    assert cw_ctx.split is not None
    expected = np.array(
        [
            [
                trained.family_models[family].predict_proba_up(family_vector(family, row.features))
                for family in _TWO_FAMILIES
            ]
            for row in cw_ctx.split.validation
        ]
    )
    assert np.array_equal(fit.inputs, expected)


@then(parsers.parse('the training failure names "{fragment}"'))
def _failure_names(cw_ctx: _CombinerCtx, fragment: str) -> None:
    assert cw_ctx.error is not None
    assert fragment in str(cw_ctx.error)


@then("a held-out UP-trend row's p_hat is below 0.5")
def _held_out_p_hat_below(cw_ctx: _CombinerCtx) -> None:
    (model,) = cw_ctx.trained
    held_out = {"trend_direction": 1.0, "trend_strength": 50.0, "higher_tf_trend_direction": 1.0}
    p_hat = model.predict(held_out)
    assert p_hat < 0.5, (
        f"expected p_hat < 0.5, got {p_hat} -- the combiner may be calibrated on split.train "
        "instead of split.validation"
    )


@then(
    parsers.re(
        r"^the meta-learner's p_hat for those features is "
        r"(?P<relation>exactly|above|below) (?P<bound>[\d.]+)$"
    )
)
def _p_hat_effect(cw_ctx: _CombinerCtx, relation: str, bound: str) -> None:
    (model,) = cw_ctx.trained
    p_hat = model.predict(_IDENTICAL_VALIDATION_FEATURES)
    limit = float(bound)
    if relation == "exactly":
        assert p_hat == limit
    elif relation == "above":
        assert p_hat > limit
    else:
        assert p_hat < limit
