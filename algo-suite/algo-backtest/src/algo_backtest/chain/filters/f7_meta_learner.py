"""F7 — threshold-rule (meta-learner) filter (specs.md §11.3.2, `monografia/chapters/
03-methodology.tex` §"Phase two: deterministic execution as a filter chain").

"Meta-learner probability p̂_t ... plus accumulated filter_results" → "Aggregates the
recommendation list; emits BUY/SELL/HOLD per the equation" — the dissertation's terminal
rule (verbatim):

    BUY  if p̂_t > θ_high and r_t = bull and v_t = 0
    SELL if p̂_t < θ_low  and r_t = bear and v_t = 0
    HOLD otherwise

**2026-09-27 amendment (story 09):** the ``r_t`` agreement is a configurable gate,
``meta_learner.regime_gate`` in the strategy's `config.yaml`, alongside ``theta_high``
and ``theta_low``. With the gate off the rule is ``BUY if p̂_t > θ_high``, ``SELL if
p̂_t < θ_low``, ``HOLD`` otherwise. The September-2015 pilot found the fitted model
anti-aligned with F1's regime on every bar (p̂ < 0.5 in bull, > 0.49 in bear), so the
gated rule could never fire; see
`docs/stories/in-progress/09-six-month-training-september-pilot/progress.md`.

``v_t`` (the news-context veto flag) never needs an explicit check here: a veto from any
upstream filter (F4 included) already short-circuits `FilterChain.run()` to
``Decision.NO_TRADE`` before F7 ever runs (`chain/model.py`), so by construction F7 only
ever sees ``v_t = 0`` states. ``r_t`` (the trend regime) is read from F1's
``trend_score`` enrichment when the gate is on; ``p̂_t`` is this module's own
contribution: a **logistic meta-learner** combining one **LightGBM sub-model per feature
family** (PRD.md §1: "each feature family is scored by a LightGBM sub-model, and a
logistic meta-learner combines the sub-model outputs into a probability p̂_t").

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
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

import numpy as np
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.chain.params import require_bool, require_number
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
    and the ground-truth label (1 = price moved up at the model's horizon H, 0 = down).

    ``label_time`` is when the label became knowable (the close of the horizon bar).
    When set, `walk_forward_split` purges rows whose label is only knowable after their
    own span ends — otherwise a train/validation row's label would be computed from
    prices in the next, held-out span. ``None`` means the label is known at
    ``timestamp`` (no horizon), which never crosses a boundary.
    """

    timestamp: datetime
    features: Mapping[str, object]
    label: int
    label_time: datetime | None = None

    def known_by(self, boundary: date) -> bool:
        """Whether this row's label is knowable no later than the end of `boundary`."""
        known_at = self.label_time if self.label_time is not None else self.timestamp
        # The span ends at 00:00 of the day after `boundary`; a label closing exactly
        # then was known within the span.
        return known_at <= datetime.combine(
            boundary + timedelta(days=1), datetime.min.time(), tzinfo=known_at.tzinfo
        )


@dataclass(frozen=True)
class WalkForwardSplit:
    """The three chronological, non-overlapping spans a walk-forward training run uses."""

    train: tuple[TrainingRow, ...]
    validation: tuple[TrainingRow, ...]
    test: tuple[TrainingRow, ...]


def _span(rows: Sequence[TrainingRow], after: date | None, end: date) -> tuple[TrainingRow, ...]:
    """Rows dated in (after, end] whose labels are knowable by the end of `end`."""
    return tuple(
        row
        for row in rows
        if (after is None or after < row.timestamp.date())
        and row.timestamp.date() <= end
        and row.known_by(end)
    )


def walk_forward_split(
    rows: Sequence[TrainingRow], *, train_end: date, validation_end: date, test_end: date
) -> WalkForwardSplit:
    """Partition `rows` into chronological train/validation/test spans (PRD.md §4).

    ``train`` covers everything up to and including ``train_end``; ``validation`` the
    open interval through ``validation_end``; ``test`` through ``test_end``. Boundaries
    must be strictly increasing and every span must be non-empty — an empty span means
    the caller's window doesn't actually cover any data, which is a configuration
    mistake to fail fast on, not silently train on two-thirds of a walk-forward split.

    Rows whose label only becomes knowable after their span's end (``TrainingRow.
    label_time``) are purged, so no fitted row's label depends on a later span's prices
    and changing held-out data cannot change what the models were fitted on.
    """
    if not train_end < validation_end < test_end:
        raise ValueError(
            f"{_FILTER_NAME}: walk-forward boundaries must be strictly increasing, got "
            f"train_end={train_end!r}, validation_end={validation_end!r}, "
            f"test_end={test_end!r}"
        )
    train = _span(rows, None, train_end)
    validation = _span(rows, train_end, validation_end)
    test = _span(rows, validation_end, test_end)
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


class ProbabilityCombiner(Protocol):
    """The meta-learner's combiner contract: family P(up)s in, `[P(0), P(1)]` rows out.

    Satisfied by a fitted sklearn `LogisticRegression` (training) and by
    `f7_model_io.LogisticCombiner` (a model reloaded from its portable JSON form).
    """

    def predict_proba(self, inputs: np.ndarray) -> Any:
        """Class probabilities per input row."""
        ...


@dataclass(frozen=True)
class TrainedMetaLearner:
    """The fitted per-family sub-models plus the logistic combiner over their outputs."""

    families: tuple[FeatureFamily, ...]
    family_models: Mapping[FeatureFamily, FamilyPredictor]
    meta_model: ProbabilityCombiner

    def predict(self, features: Mapping[str, object]) -> float:
        """Combine every family's P(up) into the meta-learner's calibrated p̂_t."""
        family_probas = [
            self.family_models[family].predict_proba_up(family_vector(family, features))
            for family in self.families
        ]
        combined: Any = self.meta_model.predict_proba(np.asarray([family_probas]))
        return float(combined[0, 1])


def train_meta_learner(
    families: Sequence[FeatureFamily],
    split: WalkForwardSplit,
    *,
    random_state: int = _DEFAULT_RANDOM_STATE,
) -> TrainedMetaLearner:
    """Fit one LightGBM sub-model per family on `split.train`, then a logistic meta-learner
    combining the families' out-of-sample probabilities (from `split.validation`) into p̂_t.

    The meta-learner is deliberately calibrated on `split.validation`, never on
    `split.train`: fitting it on the same rows the family models were trained on would
    let each family's in-sample overfit leak straight into the combiner, inflating and
    miscalibrating p̂_t. `split.test` is reserved for evaluation only and is never
    consumed here.

    Deterministic given `families`, `split` and `random_state`: every `Booster` and the
    `LogisticRegression` pin the same seed, so two calls with identical inputs produce
    bit-identical predictions (`f7_meta_learner.feature`'s reproducibility scenario
    proves this).

    Raises:
        ValueError: if `families` is empty, or if `split.validation` doesn't contain
            both classes (a degenerate walk-forward window the logistic combiner
            cannot be fit on) — fail fast rather than silently returning a
            single-class-biased combiner.
    """
    if not families:
        raise ValueError(f"{_FILTER_NAME}: at least one feature family is required to train")
    family_models = {
        family: _fit_family(family, split.train, random_state=random_state)
        for family in families
    }
    meta_inputs = _family_predictions(family_models, families, split.validation)
    labels = np.array([row.label for row in split.validation])
    if len(set(labels.tolist())) < 2:
        raise ValueError(
            f"{_FILTER_NAME}: split.validation has only one label class "
            f"({len(split.validation)} rows) — the logistic combiner cannot be calibrated "
            "on a single-class validation span. Widen validation_end or the training "
            "window so validation covers both classes."
        )
    meta_model = LogisticRegression(random_state=random_state, max_iter=1000)
    meta_model.fit(meta_inputs, labels)
    return TrainedMetaLearner(
        families=tuple(families), family_models=family_models, meta_model=meta_model
    )


def _family_predictions(
    family_models: Mapping[FeatureFamily, LightGBMFamilyModel],
    families: Sequence[FeatureFamily],
    rows: Sequence[TrainingRow],
) -> np.ndarray:
    """Each family model's `predict_proba_up` for every row, as a (rows, families) matrix."""
    return np.array(
        [
            [
                family_models[family].predict_proba_up(family_vector(family, row.features))
                for family in families
            ]
            for row in rows
        ]
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


_SECTION = "meta_learner"


@dataclass(frozen=True)
class F7Config:
    """The terminal rule's parameters: two calibrated thresholds plus the regime gate.

    `regime_gate=True` is the dissertation's rule (BUY needs F1's bull regime, SELL its
    bear regime); `False` trades on p̂ alone (2026-09-27 pilot amendment, story 09). None
    of these is learned by the model.
    """

    theta_high: float
    theta_low: float
    regime_gate: bool
    label_horizon_minutes: int = 15


def parse_f7_config(section: Mapping[str, Any], *, strategy: str) -> F7Config:
    """F7's parameters from a strategy config.yaml `meta_learner` section (fail fast).

    `label_horizon_minutes` — how far ahead the training label looks — defaults to 15.

    Raises:
        ValueError: a key is missing, a threshold is not a probability strictly inside
            (0, 1), `theta_low` is not strictly below `theta_high`, `regime_gate` is
            not a YAML boolean, or the horizon is not a positive integer.
    """
    theta_high = _probability(section, "theta_high", strategy)
    theta_low = _probability(section, "theta_low", strategy)
    if theta_low >= theta_high:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.theta_low ({theta_low}) must be strictly below "
            f"theta_high ({theta_high}) — the HOLD band between them cannot be empty"
        )
    regime_gate = require_bool(section, "regime_gate", section=_SECTION, strategy=strategy)
    return F7Config(
        theta_high=theta_high, theta_low=theta_low, regime_gate=regime_gate,
        label_horizon_minutes=_horizon(section, strategy),
    )


def _horizon(section: Mapping[str, Any], strategy: str) -> int:
    """`label_horizon_minutes`: a positive integer, defaulting to 15 when absent."""
    value = section.get("label_horizon_minutes", 15)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.label_horizon_minutes must be a positive "
            f"integer number of bars, got {value!r}"
        )
    return value


def _probability(section: Mapping[str, Any], key: str, strategy: str) -> float:
    """A required threshold strictly inside (0, 1)."""
    value = require_number(section, key, section=_SECTION, strategy=strategy)
    if not 0.0 < value < 1.0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.{key} must be a probability strictly inside "
            f"(0, 1), got {value!r}"
        )
    return value


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


def _threshold_rule(p_hat: float, config: F7Config) -> Recommendation:
    """BUY above `theta_high`, SELL below `theta_low`, HOLD inside the band (strict)."""
    if p_hat > config.theta_high:
        return Recommendation.BUY
    if p_hat < config.theta_low:
        return Recommendation.SELL
    return Recommendation.HOLD


def _regime_agrees(recommendation: Recommendation, regime: str) -> bool:
    """Whether F1's regime points the same way as the threshold rule's direction."""
    if recommendation is Recommendation.BUY:
        return regime == "bull"
    if recommendation is Recommendation.SELL:
        return regime == "bear"
    return True


@dataclass
class F7MetaLearnerFilter:
    """The chain's terminal threshold-rule gate: implements `Filter.apply()`.

    Never vetoes — by the terminal rule's own equation, HOLD is a recommendation, not a
    gate (`FilterResult.veto` stays `False` in every branch). `config` comes from the
    strategy's `config.yaml` (`parse_f7_config`), never from a code constant.
    """

    meta_learner: TrainedMetaLearner
    config: F7Config

    def apply(self, state: ExecutionState) -> FilterResult:
        """Compute p̂_t and apply the terminal rule, consulting F1's regime only when gated."""
        p_hat = self.meta_learner.predict(state.features)
        recommendation = _threshold_rule(p_hat, self.config)
        regime = "n/a"
        if self.config.regime_gate:
            regime = _regime(state.features)
            if not _regime_agrees(recommendation, regime):
                recommendation = Recommendation.HOLD
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=recommendation,
            reason=f"p_hat={p_hat:.4f}, theta_high={self.config.theta_high}, "
            f"theta_low={self.config.theta_low}, regime_gate={self.config.regime_gate}, "
            f"regime={regime}",
            confidence=p_hat,
            enrichment={"p_hat": p_hat},
        )
