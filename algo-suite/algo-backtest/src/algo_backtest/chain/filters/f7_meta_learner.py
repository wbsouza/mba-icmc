"""F7 — threshold-rule (meta-learner) filter (specs.md §11.3.2, `monografia/chapters/
03-methodology.tex` §"Phase two: deterministic execution as a filter chain").

"Meta-learner probability p̂_t ... plus accumulated filter_results" → "Aggregates the
recommendation list; emits BUY/SELL/HOLD per the equation" — the dissertation's terminal
rule (verbatim):

    BUY  if p̂_t > θ_high and r_t = bull and v_t = 0
    SELL if p̂_t < θ_low  and r_t = bear and v_t = 0
    HOLD otherwise

``v_t`` (the news-context veto flag) never needs an explicit check here: a veto from any
upstream filter (F4 included) already short-circuits `FilterChain.run()` to
``Decision.NO_TRADE`` before F7 ever runs (`chain/model.py`), so by construction F7 only
ever sees ``v_t = 0`` states. ``r_t`` (the trend regime) is read from F1's
``trend_score`` enrichment; ``p̂_t`` is this module's own contribution: a **logistic
meta-learner** combining one **LightGBM sub-model per feature family** (PRD.md §1: "each
feature family is scored by a LightGBM sub-model, and a logistic meta-learner combines
the sub-model outputs into a probability p̂_t").

**Feature families** (one LightGBM sub-model each, matching the filters that already
enrich `state.features` — TD-29's market-activity family has no filter consumer yet and
is intentionally not included here):

    - TREND:     trend_direction, trend_strength, higher_tf_trend_direction (F1)
    - INDICATOR: rsi, macd_hist (F2)
    - PATTERN:   candlestick_pattern, encoded to a signed polarity (F3)
    - NEWS:      news_event_intensity, news_sentiment_score (F4)

A **baseline** meta-learner omits the NEWS family from ``families``; a **hybrid**
meta-learner includes it (PRD.md §1: "The two differ only in feature families ... hybrid
adds the news family"). Missing per-bar readings (e.g. no sentiment this minute, no
pattern this bar) are encoded as `NaN`, which LightGBM's split-finding natively treats as
a distinct "missing" branch rather than a value to impute or fail on.

Training is **walk-forward** (PRD.md §4: "train / validation / test" contiguous date
spans, non-overlapping and chronological — the model is only ever asked to explain the
future, never trained on it) and **reproducible**: every `Booster`/`LogisticRegression`
fit pins `random_state` (monografia §"Reproducibility": "LightGBM: random_state=42 on
every Booster").
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol

import numpy as np
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_core.config import Impact, ParameterSpec, resolve
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression

_FILTER_NAME = "f7_meta_learner"
_DEFAULT_RANDOM_STATE = 42
# Small, fixed grid (monografia §"Reproducibility": "LightGBM hyperparameters restricted
# to the small explicit grid") — a full hyperparameter search is Chapter-4/06 scope, not
# this story's; these defaults exist to make a per-family booster fit reproducibly on a
# modest number of rows, not to be tuned here.
_LGBM_PARAMS: dict[str, Any] = {
    "n_estimators": 50,
    "max_depth": 3,
    "min_child_samples": 1,
    "verbosity": -1,
}


class FeatureFamily(StrEnum):
    """One LightGBM sub-model family, named after the upstream filter that produces it."""

    TREND = "trend"
    INDICATOR = "indicator"
    PATTERN = "pattern"
    NEWS = "news"


_PATTERN_POLARITY = {
    # Kept in sync with f3_pattern.py's `_BULLISH_PATTERNS`/`_BEARISH_PATTERNS` vocabulary.
    "bullish_engulfing": 1.0,
    "hammer": 1.0,
    "morning_star": 1.0,
    "bearish_engulfing": -1.0,
    "shooting_star": -1.0,
    "evening_star": -1.0,
}

_FAMILY_KEYS: Mapping[FeatureFamily, tuple[str, ...]] = {
    FeatureFamily.TREND: ("trend_direction", "trend_strength", "higher_tf_trend_direction"),
    FeatureFamily.INDICATOR: ("rsi", "macd_hist"),
    FeatureFamily.PATTERN: ("candlestick_pattern",),
    FeatureFamily.NEWS: ("news_event_intensity", "news_sentiment_score"),
}


def _as_float(value: object) -> float:
    """Coerce one `state.features` reading to a float, `NaN` for missing/absent."""
    if value is None:
        return math.nan
    if isinstance(value, str):
        polarity = _PATTERN_POLARITY.get(value)
        if polarity is None:
            raise ValueError(
                f"{_FILTER_NAME}: unrecognized candlestick_pattern {value!r} — known "
                f"patterns are {sorted(_PATTERN_POLARITY)!r}"
            )
        return polarity
    return float(value)  # type: ignore[arg-type]


def family_vector(family: FeatureFamily, features: Mapping[str, object]) -> list[float]:
    """Extract one family's numeric feature vector from `state.features` (or a training row).

    A key absent from `features` is treated the same as an explicit `None` — `NaN`, not a
    hard failure: unlike F1/F5's mandatory contracts, a feature family the upstream filter
    hasn't populated yet (or legitimately has nothing to say this bar) is exactly the
    "missing value" LightGBM is designed to split around.
    """
    return [_as_float(features.get(key)) for key in _FAMILY_KEYS[family]]


@dataclass(frozen=True)
class TrainingRow:
    """One labeled training example: a timestamp, raw `state.features`-shaped readings,
    and the ground-truth label (1 = price moved up at the model's horizon H, 0 = down)."""

    timestamp: datetime
    features: Mapping[str, object]
    label: int


@dataclass(frozen=True)
class WalkForwardSplit:
    """The three chronological, non-overlapping spans a walk-forward training run uses."""

    train: tuple[TrainingRow, ...]
    validation: tuple[TrainingRow, ...]
    test: tuple[TrainingRow, ...]


def walk_forward_split(
    rows: Sequence[TrainingRow], *, train_end: date, validation_end: date, test_end: date
) -> WalkForwardSplit:
    """Partition `rows` into chronological train/validation/test spans (PRD.md §4).

    ``train`` covers everything up to and including ``train_end``; ``validation`` the
    open interval through ``validation_end``; ``test`` through ``test_end``. Boundaries
    must be strictly increasing and every span must be non-empty — an empty span means
    the caller's window doesn't actually cover any data, which is a configuration
    mistake to fail fast on, not silently train on two-thirds of a walk-forward split.
    """
    if not train_end < validation_end < test_end:
        raise ValueError(
            f"{_FILTER_NAME}: walk-forward boundaries must be strictly increasing, got "
            f"train_end={train_end!r}, validation_end={validation_end!r}, "
            f"test_end={test_end!r}"
        )
    train = tuple(row for row in rows if row.timestamp.date() <= train_end)
    validation = tuple(
        row for row in rows if train_end < row.timestamp.date() <= validation_end
    )
    test = tuple(row for row in rows if validation_end < row.timestamp.date() <= test_end)
    for name, span in (("train", train), ("validation", validation), ("test", test)):
        if not span:
            raise ValueError(
                f"{_FILTER_NAME}: the {name!r} walk-forward span is empty for boundaries "
                f"train_end={train_end!r}, validation_end={validation_end!r}, "
                f"test_end={test_end!r} — widen the window or check the input rows' dates"
            )
    return WalkForwardSplit(train=train, validation=validation, test=test)


class FamilyPredictor(Protocol):
    """One family sub-model's contract: a feature vector in, a calibrated P(up) out."""

    def predict_proba_up(self, vector: Sequence[float]) -> float:
        """Return the calibrated probability of an upward move for one feature vector."""
        ...


@dataclass(frozen=True)
class LightGBMFamilyModel:
    """`FamilyPredictor` backed by one fitted `lightgbm.LGBMClassifier`."""

    booster: LGBMClassifier

    def predict_proba_up(self, vector: Sequence[float]) -> float:
        """Predict P(up) for one row via the fitted booster."""
        proba: Any = self.booster.predict_proba(np.asarray([vector], dtype=float))
        return float(proba[0, 1])


@dataclass(frozen=True)
class TrainedMetaLearner:
    """The fitted per-family sub-models plus the logistic combiner over their outputs."""

    families: tuple[FeatureFamily, ...]
    family_models: Mapping[FeatureFamily, FamilyPredictor]
    meta_model: LogisticRegression

    def predict(self, features: Mapping[str, object]) -> float:
        """Combine every family's P(up) into the meta-learner's calibrated p̂_t."""
        family_probas = [
            self.family_models[family].predict_proba_up(family_vector(family, features))
            for family in self.families
        ]
        combined: Any = self.meta_model.predict_proba(np.asarray([family_probas]))
        return float(combined[0, 1])


def train_meta_learner(
    rows: Sequence[TrainingRow],
    families: Sequence[FeatureFamily],
    split: WalkForwardSplit,
    *,
    random_state: int = _DEFAULT_RANDOM_STATE,
) -> TrainedMetaLearner:
    """Fit one LightGBM sub-model per family on `split.train`, then a logistic meta-learner
    combining the families' in-sample probabilities into p̂_t.

    Deterministic given `rows`, `families`, `split` and `random_state`: every `Booster`
    and the `LogisticRegression` pin the same seed, so two calls with identical inputs
    produce bit-identical predictions (`f7_meta_learner.feature`'s reproducibility
    scenario proves this).
    """
    if not families:
        raise ValueError(f"{_FILTER_NAME}: at least one feature family is required to train")
    family_models = {
        family: _fit_family(family, split.train, random_state=random_state)
        for family in families
    }
    meta_inputs = np.array(
        [
            [
                family_models[family].predict_proba_up(family_vector(family, row.features))
                for family in families
            ]
            for row in split.train
        ]
    )
    labels = np.array([row.label for row in split.train])
    meta_model = LogisticRegression(random_state=random_state, max_iter=1000)
    meta_model.fit(meta_inputs, labels)
    return TrainedMetaLearner(
        families=tuple(families), family_models=family_models, meta_model=meta_model
    )


def _fit_family(
    family: FeatureFamily, train: Sequence[TrainingRow], *, random_state: int
) -> LightGBMFamilyModel:
    """Fit one family's LightGBM sub-model on the walk-forward train split."""
    inputs = np.array([family_vector(family, row.features) for row in train])
    labels = np.array([row.label for row in train])
    booster = LGBMClassifier(random_state=random_state, **_LGBM_PARAMS)
    booster.fit(inputs, labels)
    return LightGBMFamilyModel(booster=booster)


_SCHEMA_VERSION = 1
_SCHEMA: tuple[ParameterSpec, ...] = (
    ParameterSpec(name="meta_learner.theta_high", impact=Impact.TRADING, reference_value=0.55),
    ParameterSpec(name="meta_learner.theta_low", impact=Impact.TRADING, reference_value=0.45),
)


@dataclass(frozen=True)
class F7Config:
    """The terminal rule's two calibrated thresholds (never learned by the model)."""

    theta_high: float
    theta_low: float


def load_f7_config() -> F7Config:
    """Resolve `meta_learner.theta_{high,low}` via the shared `algo_core.config` loader.

    Raises:
        ConfigError: (`MissingTradingParameter`) if a threshold is absent from config —
            a hard stop, per CLAUDE.md's fail-fast policy.
    """
    result = resolve("backtest", _SCHEMA, _SCHEMA_VERSION)
    return F7Config(
        theta_high=float(result.values["meta_learner.theta_high"]),
        theta_low=float(result.values["meta_learner.theta_low"]),
    )


def _regime(features: Mapping[str, object]) -> str:
    """Read the trend regime `r_t` from F1's `trend_score` enrichment: bull/bear/neutral."""
    trend_score = features.get("trend_score")
    if trend_score is None:
        raise KeyError(
            f"{_FILTER_NAME}: required state.features key 'trend_score' is missing — F7 "
            "must run after F1 in the chain (F1 enriches it); check config.yaml's filter order"
        )
    score = float(trend_score)  # type: ignore[arg-type]
    if score > 0.0:
        return "bull"
    if score < 0.0:
        return "bear"
    return "neutral"


@dataclass
class F7MetaLearnerFilter:
    """The chain's terminal threshold-rule gate: implements `Filter.apply()`.

    Never vetoes — by the terminal rule's own equation, HOLD is a recommendation, not a
    gate (`FilterResult.veto` stays `False` in every branch).
    """

    meta_learner: TrainedMetaLearner
    config: F7Config = field(default_factory=load_f7_config)

    def apply(self, state: ExecutionState) -> FilterResult:
        """Compute p̂_t, read the trend regime, and apply the terminal BUY/SELL/HOLD rule."""
        p_hat = self.meta_learner.predict(state.features)
        regime = _regime(state.features)
        if p_hat > self.config.theta_high and regime == "bull":
            recommendation = Recommendation.BUY
        elif p_hat < self.config.theta_low and regime == "bear":
            recommendation = Recommendation.SELL
        else:
            recommendation = Recommendation.HOLD
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=recommendation,
            reason=f"p_hat={p_hat:.4f}, regime={regime}, theta_high={self.config.theta_high}, "
            f"theta_low={self.config.theta_low}",
            confidence=p_hat,
            enrichment={"p_hat": p_hat},
        )
