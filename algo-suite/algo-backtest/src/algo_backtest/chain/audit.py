"""decisions.parquet audit trail (Spec 04f, specs.md §11.3.4).

Converts a `ChainOutcome` (`chain/model.py`, Spec 04b) into a `DecisionRow` and
persists a batch of rows via `algo_core`'s `ParquetRepository`. `ChainOutcome`'s
dataclasses (`ExecutionState`, `FilterResult`) are internal to the chain's
run-loop mechanics; `DecisionRow` is the separate, pydantic-typed persistence
shape the Repository serde layer needs (nested `list[BaseModel]` fields dump
cleanly to a Parquet `list<struct<...>>` column — a plain dataclass does not).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from algo_backtest.chain.model import ChainOutcome, FilterResult
from algo_core.repository.parquet import ParquetRepository
from pydantic import BaseModel


class FilterResultRow(BaseModel):
    """One `FilterResult` mirrored into a `DecisionRow.filter_results` struct entry."""

    filter_name: str
    recommendation: str
    reason: str
    confidence: float | None
    veto: bool
    enrichment: dict[str, object]
    metadata: dict[str, object]


class DecisionRow(BaseModel):
    """One audit-trail row (specs.md §11.3.4): a single chain invocation.

    `trade_id` is not part of the original §11.3.4 column table; it is added here
    because Spec 04h (hybrid integration) and Spec 05c (ablation) join this table
    against the future `trades.parquet` by trade, and §11.3.4 assumes that join key
    without naming a column for it.
    """

    trade_id: str
    timestamp: datetime
    pair: str
    features_hash: str
    filter_results: list[FilterResultRow]
    final_decision: str
    vetoed_by: str | None


def _hash_features(features: dict[str, object]) -> str:
    """Hash a feature dict deterministically for the `features_hash` column.

    Dict iteration order reflects insertion, not content, so two feature dicts built
    in a different order would hash differently without a sorted-key serialization first.
    """
    payload = json.dumps(features, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _filter_result_row(result: FilterResult) -> FilterResultRow:
    """Map one chain-internal `FilterResult` dataclass onto its persistence row shape."""
    return FilterResultRow(
        filter_name=result.filter_name,
        recommendation=result.recommendation.value,
        reason=result.reason,
        confidence=result.confidence,
        veto=result.veto,
        enrichment=result.enrichment,
        metadata=result.metadata,
    )


def decision_row_from_outcome(outcome: ChainOutcome, trade_id: str) -> DecisionRow:
    """Convert a `ChainOutcome` into a `DecisionRow` ready for the audit-trail Parquet file.

    Hashes `outcome.state.features` as it stands at chain completion — the accumulated
    feature set after every filter's enrichment — since `ChainOutcome` preserves no
    separate pre-chain snapshot to hash instead (see its own aliasing caveat in
    `chain/model.py`). `vetoed_by` names the first `FilterResult` with `veto=True` in
    `outcome.state.filter_results`, or `None` when the chain reached its terminal
    decision-maker without a veto.
    """
    vetoed_by = next(
        (result.filter_name for result in outcome.state.filter_results if result.veto),
        None,
    )
    return DecisionRow(
        trade_id=trade_id,
        timestamp=outcome.state.timestamp,
        pair=outcome.state.pair,
        features_hash=_hash_features(outcome.state.features),
        filter_results=[_filter_result_row(r) for r in outcome.state.filter_results],
        final_decision=outcome.decision.value,
        vetoed_by=vetoed_by,
    )


def write_decisions(rows: list[DecisionRow], path: Path) -> None:
    """Write a batch of `DecisionRow`s to `path` as the `decisions.parquet` audit trail."""
    ParquetRepository(DecisionRow, path).put(rows)
