"""Orchestrate one epoch's weighted training (Story 19, T9; RWT-01, RWT-06, RWT-09, RWT-11,
RWT-24, RWT-30).

Builds one policy epoch from watermark-visible mature ledger rows only (RWT-01, RWT-24),
fits the family and combiner stages with each policy's weighting (uniform, or exponential
for E), calibrates the separate threshold span with the freshly fitted model's own scores,
and publishes the result as one immutable `bundle` (RWT-11). No row after the epoch's
preparation cutoff `C` is ever read, and `split.test` is always empty: a fit never requires
future test labels (RWT-30). Eligibility is decided by `schedule.select_rows` alone, so
trade execution, vetoes and realized profit can never influence which rows are fitted or
weighted (RWT-09).

`train_epoch` always refits when called; "freezing" a policy (F) is a scheduling decision
made by the caller (T10's cycle coordinator), not something this module detects — F's
later-epoch spans are anchored to the schedule's first `D` by `schedule.stage_spans`, so a
repeated call for F reproduces the exact same rows, weights and (RWT-30) model payload hash.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    TrainingRow,
    WalkForwardSplit,
    train_meta_learner,
)
from algo_backtest.retraining import bundle as bundle_module
from algo_backtest.retraining.bundle import BundleDescription, PublishResult
from algo_backtest.retraining.ingestion import Ledger, SourceRow, require_label_time
from algo_backtest.retraining.schedule import Epoch, Span, select_rows, stage_spans
from algo_backtest.retraining.thresholds import ScoredRow, calibrate_thresholds
from algo_backtest.retraining.weights import (
    SupportMinima,
    check_support,
    effective_n,
    exponential_weights,
    normalize_mean_one,
    uniform_weights,
)

_MODULE = "retraining.trainer"


@dataclass(frozen=True)
class TrainingSettings:
    """Everything one `train_epoch` call needs beyond the ledger and the epoch itself."""

    half_life_days: float
    seed: int
    families: tuple[FeatureFamily, ...]
    family_minima: SupportMinima
    combiner_minima: SupportMinima
    threshold_min_rows: int
    config_sha256: str
    protocol_sha256: str


@dataclass(frozen=True)
class StageProvenance:
    """One fitting stage's admitted rows and weights, raw and mean-one normalized."""

    weighting: str
    half_life_days: float | None
    row_keys: tuple[str, ...]
    raw_weights: tuple[float, ...]
    weights: tuple[float, ...]
    n_eff: float

    @property
    def rows(self) -> int:
        """How many rows this stage admitted."""
        return len(self.row_keys)


@dataclass(frozen=True)
class EpochResult:
    """One policy epoch's complete, published outcome."""

    policy: str
    seed: int
    bundle_id: str
    reused: bool
    manifest: Mapping[str, Any]
    theta_low: float
    theta_high: float
    family: StageProvenance
    combiner: StageProvenance
    threshold_row_keys: tuple[str, ...]
    ledger_watermark: datetime
    deployment: Span
    activation_boundary: datetime


def _default_clock() -> datetime:
    """The real wall-clock UTC instant."""
    return datetime.now(UTC)


def _watermark_at_cutoff(ledger: Ledger, cutoff: datetime) -> datetime:
    """The latest persisted availability at or before `cutoff` — the watermark this epoch's
    fit was actually prepared against, independent of maturity and of any later-consumed
    data whose availability falls after `cutoff` (RWT-30 future-tail independence).

    Raises:
        ValueError: no row is visible at or before `cutoff`; consume data before training.
    """
    visible = ledger.rows(ledger.visible_keys(cutoff))
    if not visible:
        raise ValueError(
            f"{_MODULE}: no row is visible at or before {cutoff.isoformat()}; consume a "
            "batch before training this epoch"
        )
    return max(row.available_at for row in visible)


def _class_counts(labels: Sequence[int]) -> dict[str, int]:
    """Raw per-class row counts, string-keyed for JSON-safe manifest storage."""
    counts: dict[str, int] = {}
    for label in labels:
        key = str(label)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _stage_weights(
    admitted: Sequence[SourceRow], span_end: datetime, *, policy: str, half_life_days: float
) -> StageProvenance:
    """Uniform weights for every policy except E, which weights by age to `span_end`."""
    if policy == "E":
        raw = exponential_weights([row.available_at for row in admitted], span_end, half_life_days)
        normalized = normalize_mean_one(raw)
        weighting, used_half_life = "exponential", half_life_days
    else:
        raw = uniform_weights(len(admitted))
        normalized = raw
        weighting, used_half_life = "uniform", None
    return StageProvenance(
        weighting=weighting,
        half_life_days=used_half_life,
        row_keys=tuple(row.key for row in admitted),
        raw_weights=raw,
        weights=normalized,
        n_eff=effective_n(raw),
    )


def _training_rows(
    admitted: Sequence[SourceRow], features: Mapping[str, Mapping[str, object]]
) -> tuple[TrainingRow, ...]:
    """`TrainingRow`s for `admitted`, features looked up by key from the caller's source."""
    return tuple(
        TrainingRow(
            timestamp=row.available_at,
            features=features[row.key],
            label=row.label,
            label_time=row.label_time,
        )
        for row in admitted
    )


def _rows_sha256(
    family: StageProvenance, combiner: StageProvenance, threshold_keys: Sequence[str]
) -> str:
    """sha256 of the ordered stage row keys (design.md "EpochBundle": `hashes.rows_sha256`)."""
    payload = {
        "family": list(family.row_keys),
        "combiner": list(combiner.row_keys),
        "threshold": list(threshold_keys),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _data_sha256(ledger: Ledger, cutoff: datetime) -> str:
    """sha256 over the identities of partitions visible at or before `cutoff`
    (design.md's `hashes.data_sha256`) — a partition consumed later, whose rows are all
    after `cutoff`, never contributed to this fit and must not affect this hash."""
    payload = {
        name: {"path": record.path, "sha256": record.sha256, "row_count": record.row_count}
        for name, record in ledger.visible_partitions(cutoff).items()
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def train_epoch(
    policy: str,
    epoch: Epoch,
    ledger: Ledger,
    features: Mapping[str, Mapping[str, object]],
    registry: Path,
    settings: TrainingSettings,
    *,
    clock: Callable[[], datetime] = _default_clock,
) -> EpochResult:
    """Build and publish one policy epoch from `ledger`'s watermark-visible mature rows.

    Raises:
        ValueError: the ledger has no data yet; a stage's support falls below its
            registered minimum (RWT-06, before any fit); the combiner span has fewer
            than two classes with positive weight; or publication fails (RWT-11, RWT-15).
    """
    spans = stage_spans(epoch, policy)
    cutoff = spans.threshold.end
    watermark = _watermark_at_cutoff(ledger, cutoff)
    mature_rows = ledger.rows(ledger.mature_keys(cutoff))

    family_admitted = select_rows(mature_rows, spans.family)
    combiner_admitted = select_rows(mature_rows, spans.combiner)
    threshold_admitted = select_rows(mature_rows, spans.threshold)

    family = _stage_weights(
        family_admitted, spans.family.end, policy=policy, half_life_days=settings.half_life_days
    )
    combiner = _stage_weights(
        combiner_admitted, spans.combiner.end, policy=policy, half_life_days=settings.half_life_days
    )
    check_support(
        [row.label for row in family_admitted],
        family.raw_weights,
        settings.family_minima,
        stage="family",
    )
    check_support(
        [row.label for row in combiner_admitted],
        combiner.raw_weights,
        settings.combiner_minima,
        stage="combiner",
    )

    split = WalkForwardSplit(
        train=_training_rows(family_admitted, features),
        validation=_training_rows(combiner_admitted, features),
        test=(),
    )
    fit_started = time.perf_counter()
    trained = train_meta_learner(
        list(settings.families),
        split,
        random_state=settings.seed,
        family_weights=list(family.weights),
        combiner_weights=list(combiner.weights),
    )
    training_duration_seconds = time.perf_counter() - fit_started

    scored_rows = tuple(
        ScoredRow(
            key=row.key,
            available_at=row.available_at,
            label_time=require_label_time(row),
            score=trained.predict(features[row.key]),
        )
        for row in threshold_admitted
    )
    calibrated = calibrate_thresholds(
        scored_rows, spans.threshold, minimum_rows=settings.threshold_min_rows
    )

    description = BundleDescription(
        policy=policy,
        seed=settings.seed,
        spans={
            "family": {"start": spans.family.start, "end": spans.family.end},
            "combiner": {"start": spans.combiner.start, "end": spans.combiner.end},
            "threshold": {"start": spans.threshold.start, "end": spans.threshold.end},
            "deployment": {"start": spans.deployment.start, "end": spans.deployment.end},
        },
        activation_boundary=epoch.start,
        ledger_watermark=watermark,
        stages={
            "family": {
                "weighting": family.weighting,
                "half_life_days": family.half_life_days,
                "rows": family.rows,
                "per_class": _class_counts([row.label for row in family_admitted]),
                "n_eff": family.n_eff,
                "raw_weight_min": min(family.raw_weights),
                "raw_weight_max": max(family.raw_weights),
            },
            "combiner": {
                "weighting": combiner.weighting,
                "half_life_days": combiner.half_life_days,
                "rows": combiner.rows,
                "per_class": _class_counts([row.label for row in combiner_admitted]),
                "n_eff": combiner.n_eff,
                "raw_weight_min": min(combiner.raw_weights),
                "raw_weight_max": max(combiner.raw_weights),
            },
            "threshold": {"rows": calibrated.rows},
        },
        theta_low=calibrated.theta_low,
        theta_high=calibrated.theta_high,
        rows_sha256=_rows_sha256(family, combiner, calibrated.row_keys),
        data_sha256=_data_sha256(ledger, cutoff),
        config_sha256=settings.config_sha256,
        protocol_sha256=settings.protocol_sha256,
        training_duration_seconds=training_duration_seconds,
    )
    published: PublishResult = bundle_module.publish(trained, description, registry, clock=clock)

    return EpochResult(
        policy=policy,
        seed=settings.seed,
        bundle_id=published.bundle_id,
        reused=published.reused,
        manifest=published.manifest,
        theta_low=calibrated.theta_low,
        theta_high=calibrated.theta_high,
        family=family,
        combiner=combiner,
        threshold_row_keys=calibrated.row_keys,
        ledger_watermark=watermark,
        deployment=spans.deployment,
        activation_boundary=epoch.start,
    )
