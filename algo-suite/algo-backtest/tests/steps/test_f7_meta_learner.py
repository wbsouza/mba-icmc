"""Steps for f7_meta_learner.feature — the F7 threshold-rule (meta-learner) filter."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f7_meta_learner import (
    F7Config,
    F7MetaLearnerFilter,
    FeatureFamily,
    TrainingRow,
    WalkForwardSplit,
    load_f7_config,
    train_meta_learner,
    walk_forward_split,
)
from algo_backtest.chain.model import ExecutionState, FilterResult
from algo_core.config import ConfigError
from algo_core.config.paths import ENV_CONF_DIR
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f7_meta_learner.feature")


@dataclass
class _StubMetaLearner:
    """A `TrainedMetaLearner`-shaped test double with a fixed p_hat, for terminal-rule tests.

    Records the exact `features` it was called with, so tests can prove F7 wires
    `state.features` straight through to the meta-learner rather than, say, a stale
    empty dict.
    """

    p_hat: float
    received_features: dict[str, object] | None = None

    def predict(self, features: dict[str, object]) -> float:
        self.received_features = features
        return self.p_hat


@dataclass
class _F7Ctx:
    """Per-scenario fixture context."""

    rows: list[TrainingRow] = field(default_factory=list)
    split: WalkForwardSplit | None = None
    split_error: Exception | None = None
    meta_learner_a: object | None = None
    meta_learner_b: object | None = None
    stub_meta_learner: _StubMetaLearner | None = None
    config: F7Config | None = None
    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    error: Exception | None = None
    loaded_config: F7Config | None = None
    config_error: Exception | None = None


@pytest.fixture
def f7_ctx() -> _F7Ctx:
    return _F7Ctx()


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw)


@given(parsers.parse("training rows on {dates}"))
def _training_rows(f7_ctx: _F7Ctx, dates: str) -> None:
    rng = random.Random(7)
    f7_ctx.rows = [
        TrainingRow(
            timestamp=datetime.combine(_parse_date(raw.strip()), datetime.min.time(), tzinfo=UTC),
            features={"trend_direction": rng.choice([-1.0, 1.0]), "trend_strength": 40.0},
            label=rng.randint(0, 1),
        )
        for raw in dates.split(",")
    ]


@when(
    parsers.parse(
        "the rows are walk-forward split at train_end {train_end}, "
        "validation_end {validation_end}, test_end {test_end}"
    )
)
def _split(f7_ctx: _F7Ctx, train_end: str, validation_end: str, test_end: str) -> None:
    f7_ctx.split = walk_forward_split(
        f7_ctx.rows,
        train_end=_parse_date(train_end),
        validation_end=_parse_date(validation_end),
        test_end=_parse_date(test_end),
    )


@when(
    parsers.parse(
        "the rows are walk-forward split at train_end {train_end}, "
        "validation_end {validation_end}, test_end {test_end} expecting failure"
    )
)
def _split_expect_failure(
    f7_ctx: _F7Ctx, train_end: str, validation_end: str, test_end: str
) -> None:
    try:
        f7_ctx.split = walk_forward_split(
            f7_ctx.rows,
            train_end=_parse_date(train_end),
            validation_end=_parse_date(validation_end),
            test_end=_parse_date(test_end),
        )
    except ValueError as exc:
        f7_ctx.split_error = exc


@then(parsers.parse("the train span has {count:d} rows"))
def _train_count(f7_ctx: _F7Ctx, count: int) -> None:
    assert f7_ctx.split is not None
    assert len(f7_ctx.split.train) == count


@then(parsers.parse("the validation span has {count:d} rows"))
def _validation_count(f7_ctx: _F7Ctx, count: int) -> None:
    assert f7_ctx.split is not None
    assert len(f7_ctx.split.validation) == count


@then(parsers.parse("the test span has {count:d} rows"))
def _test_count(f7_ctx: _F7Ctx, count: int) -> None:
    assert f7_ctx.split is not None
    assert len(f7_ctx.split.test) == count


@then(parsers.parse('the split fails naming "{fragment}"'))
def _split_fails(f7_ctx: _F7Ctx, fragment: str) -> None:
    assert f7_ctx.split_error is not None
    assert fragment in str(f7_ctx.split_error)


def _synthetic_features(rng: random.Random) -> tuple[dict[str, object], int]:
    """One deterministic-given-`rng` (features, label) pair, correlated so fitting isn't trivial."""
    trend_direction = rng.choice([-1.0, 1.0])
    rsi = 70.0 if trend_direction > 0 else 30.0
    label = 1 if trend_direction > 0 else 0
    features: dict[str, object] = {
        "trend_direction": trend_direction,
        "trend_strength": 50.0,
        "higher_tf_trend_direction": trend_direction,
        "rsi": rsi + rng.uniform(-2, 2),
        "macd_hist": trend_direction * rng.uniform(0.1, 0.5),
    }
    return features, label


@given(parsers.parse("a synthetic walk-forward training split with {n:d} labeled rows"))
def _synthetic_split(f7_ctx: _F7Ctx, n: int) -> None:
    rng = random.Random(42)
    # Spread rows chronologically over 28 days so train/validation/test are each non-empty:
    # days 1-20 -> train, 21-25 -> validation, 26-28 -> test.
    rows = []
    for i in range(n):
        features, label = _synthetic_features(rng)
        day = min(28, (i * 28 // n) + 1)
        rows.append(
            TrainingRow(
                timestamp=datetime(2020, 1, day, tzinfo=UTC), features=features, label=label
            )
        )
    f7_ctx.split = walk_forward_split(
        rows,
        train_end=date(2020, 1, 20),
        validation_end=date(2020, 1, 25),
        test_end=date(2020, 1, 28),
    )


@when(
    parsers.parse(
        "the meta-learner is trained twice with random_state {seed:d} on the trend "
        "and indicator families"
    )
)
def _train_twice(f7_ctx: _F7Ctx, seed: int) -> None:
    assert f7_ctx.split is not None
    families = [FeatureFamily.TREND, FeatureFamily.INDICATOR]
    f7_ctx.meta_learner_a = train_meta_learner(families, f7_ctx.split, random_state=seed)
    f7_ctx.meta_learner_b = train_meta_learner(families, f7_ctx.split, random_state=seed)


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


@given(
    "a walk-forward split where trend_direction predicts UP in train but the true label "
    "is DOWN, and the reverse in validation"
)
def _inverted_train_validation_split(f7_ctx: _F7Ctx) -> None:
    """Build train/validation spans with an inverted trend_direction-to-label mapping.

    Train: trend_direction=+1 rows are labeled UP, -1 rows labeled DOWN, so the TREND
    family's LightGBM model (fit only on train) learns "high P(up) for +1". Validation
    carries the identical feature pattern but the OPPOSITE label assignment (+1 rows
    labeled DOWN, -1 rows labeled UP) -- since the family model's own prediction for a
    +1 row is fixed regardless of validation labels, this makes the logistic combiner's
    fitted coefficient sign depend entirely on whether it is calibrated against
    split.train (positive) or split.validation (negative). A regression back to
    split.train would flip the held-out prediction below.
    """
    train_rows = [_trend_row(d, 1.0, 1) for d in range(1, 6)] + [
        _trend_row(d, -1.0, 0) for d in range(6, 11)
    ]
    validation_rows = [_trend_row(d, 1.0, 0) for d in range(11, 14)] + [
        _trend_row(d, -1.0, 1) for d in range(14, 17)
    ]
    test_rows = [_trend_row(17, 1.0, 1), _trend_row(18, -1.0, 0)]
    f7_ctx.split = WalkForwardSplit(
        train=tuple(train_rows), validation=tuple(validation_rows), test=tuple(test_rows)
    )


@when("the meta-learner is trained on the trend family alone")
def _train_trend_only(f7_ctx: _F7Ctx) -> None:
    assert f7_ctx.split is not None
    f7_ctx.meta_learner_a = train_meta_learner([FeatureFamily.TREND], f7_ctx.split)


@then(parsers.parse("a held-out UP-trend row's p_hat is below {threshold:g}"))
def _held_out_p_hat_below(f7_ctx: _F7Ctx, threshold: float) -> None:
    assert f7_ctx.meta_learner_a is not None
    held_out = {"trend_direction": 1.0, "trend_strength": 50.0, "higher_tf_trend_direction": 1.0}
    p_hat = f7_ctx.meta_learner_a.predict(held_out)  # type: ignore[attr-defined]
    assert p_hat < threshold, (
        f"expected p_hat < {threshold}, got {p_hat} -- the combiner may be calibrated on "
        "split.train instead of split.validation"
    )


@then("both trained meta-learners predict the same p_hat for the same held-out row")
def _same_prediction(f7_ctx: _F7Ctx) -> None:
    assert f7_ctx.split is not None
    assert f7_ctx.meta_learner_a is not None
    assert f7_ctx.meta_learner_b is not None
    held_out = f7_ctx.split.test[0]
    p_a = f7_ctx.meta_learner_a.predict(held_out.features)  # type: ignore[attr-defined]
    p_b = f7_ctx.meta_learner_b.predict(held_out.features)  # type: ignore[attr-defined]
    assert p_a == p_b


@given(parsers.parse("a stub meta-learner predicting p_hat {p_hat:g}"))
def _stub_meta_learner(f7_ctx: _F7Ctx, p_hat: float) -> None:
    f7_ctx.stub_meta_learner = _StubMetaLearner(p_hat=p_hat)


@given(parsers.parse("theta_high {theta_high:g} and theta_low {theta_low:g}"))
def _config(f7_ctx: _F7Ctx, theta_high: float, theta_low: float) -> None:
    f7_ctx.config = F7Config(theta_high=theta_high, theta_low=theta_low)


@given(parsers.parse("trend_score {trend_score:g} in state.features"))
def _trend_score(f7_ctx: _F7Ctx, trend_score: float) -> None:
    f7_ctx.features["trend_score"] = trend_score


@when("F7 applies to the state")
def _apply(f7_ctx: _F7Ctx) -> None:
    assert f7_ctx.stub_meta_learner is not None and f7_ctx.config is not None
    news_filter = F7MetaLearnerFilter(meta_learner=f7_ctx.stub_meta_learner, config=f7_ctx.config)  # type: ignore[arg-type]
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f7_ctx.features)
    )
    f7_ctx.result = news_filter.apply(state)


@when(parsers.parse('F7 applies to a state missing "{missing_key}"'))
def _apply_missing(f7_ctx: _F7Ctx, missing_key: str) -> None:
    assert f7_ctx.stub_meta_learner is not None and f7_ctx.config is not None
    features = {k: v for k, v in f7_ctx.features.items() if k != missing_key}
    news_filter = F7MetaLearnerFilter(meta_learner=f7_ctx.stub_meta_learner, config=f7_ctx.config)  # type: ignore[arg-type]
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=features
    )
    try:
        f7_ctx.result = news_filter.apply(state)
    except KeyError as exc:
        f7_ctx.error = exc


@then(parsers.parse('F7 recommends "{reco}"'))
def _recommends(f7_ctx: _F7Ctx, reco: str) -> None:
    assert f7_ctx.result is not None
    assert f7_ctx.result.recommendation.value == reco


@then("F7's result does not veto")
def _no_veto(f7_ctx: _F7Ctx) -> None:
    assert f7_ctx.result is not None
    assert f7_ctx.result.veto is False


@then(parsers.parse('F7\'s filter_name is "{name}"'))
def _filter_name(f7_ctx: _F7Ctx, name: str) -> None:
    assert f7_ctx.result is not None
    assert f7_ctx.result.filter_name == name


@then(parsers.parse('F7\'s reason mentions "{fragment}"'))
def _reason_mentions(f7_ctx: _F7Ctx, fragment: str) -> None:
    assert f7_ctx.result is not None
    assert fragment in f7_ctx.result.reason


@then(parsers.parse("F7's confidence is {expected:g}"))
def _confidence(f7_ctx: _F7Ctx, expected: float) -> None:
    assert f7_ctx.result is not None
    assert f7_ctx.result.confidence == pytest.approx(expected)


@then(parsers.parse('F7 enriches "{key}" with value {value:g}'))
def _enriches(f7_ctx: _F7Ctx, key: str, value: float) -> None:
    assert f7_ctx.result is not None
    assert f7_ctx.result.enrichment[key] == pytest.approx(value)


@then("the meta-learner was called with the state's own features")
def _called_with_state_features(f7_ctx: _F7Ctx) -> None:
    assert f7_ctx.stub_meta_learner is not None
    assert f7_ctx.stub_meta_learner.received_features == f7_ctx.features


@then(parsers.parse('applying F7 fails naming "{fragment}"'))
def _apply_fails(f7_ctx: _F7Ctx, fragment: str) -> None:
    assert f7_ctx.error is not None
    assert fragment in str(f7_ctx.error)


@pytest.fixture
def meta_learner_conf_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Clean ALGO_ env + isolated conf dir so `load_f7_config` is deterministic."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    conf = tmp_path / "conf"
    conf.mkdir()
    monkeypatch.setenv(ENV_CONF_DIR, str(conf))
    return conf


def _write_backtest_yaml(conf_dir: Path, meta_learner: dict[str, Any]) -> None:
    (conf_dir / "backtest.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "meta_learner": meta_learner})
    )


@given(
    parsers.parse(
        "a meta_learner config with theta_high={theta_high:g}, theta_low={theta_low:g}"
    )
)
def _meta_learner_config_file(
    f7_ctx: _F7Ctx, meta_learner_conf_dir: Path, theta_high: float, theta_low: float
) -> None:
    _write_backtest_yaml(
        meta_learner_conf_dir, {"theta_high": theta_high, "theta_low": theta_low}
    )


@given(parsers.parse('a meta_learner config missing "{missing_key}"'))
def _meta_learner_config_missing(
    f7_ctx: _F7Ctx, meta_learner_conf_dir: Path, missing_key: str
) -> None:
    defaults = {"theta_high": 0.55, "theta_low": 0.45}
    del defaults[missing_key]
    _write_backtest_yaml(meta_learner_conf_dir, defaults)


@when("the F7 config is loaded")
def _load_f7_config(f7_ctx: _F7Ctx) -> None:
    try:
        f7_ctx.loaded_config = load_f7_config()
    except ConfigError as exc:
        f7_ctx.config_error = exc


@then(parsers.parse("the loaded F7 config has theta_high {expected:g}"))
def _loaded_theta_high(f7_ctx: _F7Ctx, expected: float) -> None:
    assert f7_ctx.config_error is None, f"unexpected error: {f7_ctx.config_error}"
    assert f7_ctx.loaded_config is not None
    assert f7_ctx.loaded_config.theta_high == pytest.approx(expected)


@then(parsers.parse("the loaded F7 config has theta_low {expected:g}"))
def _loaded_theta_low(f7_ctx: _F7Ctx, expected: float) -> None:
    assert f7_ctx.config_error is None, f"unexpected error: {f7_ctx.config_error}"
    assert f7_ctx.loaded_config is not None
    assert f7_ctx.loaded_config.theta_low == pytest.approx(expected)


@then(parsers.parse('loading the F7 config fails naming "{fragment}"'))
def _load_f7_config_fails(f7_ctx: _F7Ctx, fragment: str) -> None:
    assert f7_ctx.config_error is not None
    assert fragment in str(f7_ctx.config_error)
