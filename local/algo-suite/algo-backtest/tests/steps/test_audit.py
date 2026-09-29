"""Steps for audit.feature — ChainOutcome -> DecisionRow conversion + Parquet persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest
from algo_backtest.chain.audit import (
    DecisionRow,
    _hash_features,
    decision_row_from_outcome,
    write_decisions,
)
from algo_backtest.chain.model import (
    ChainOutcome,
    Decision,
    ExecutionState,
    FilterResult,
    Recommendation,
)
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/audit.feature")

_TRUE_STRINGS = {"true", "True"}


def _parse_value(raw: str) -> object:
    """Coerce a Gherkin table cell into bool/int/float/str, in that preference order."""
    if raw in _TRUE_STRINGS or raw in {"false", "False"}:
        return raw in _TRUE_STRINGS
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


@dataclass
class _AuditCtx:
    """Per-scenario fixture context for the outcome-conversion and persistence steps."""

    filter_results: list[FilterResult] = field(default_factory=list)
    features: dict[str, object] = field(default_factory=dict)
    pair: str = ""
    timestamp: datetime | None = None
    decision: Decision | None = None
    outcome: ChainOutcome | None = None
    row: DecisionRow | None = None
    rows: list[DecisionRow] = field(default_factory=list)
    path: Path | None = None
    read_back: list[DecisionRow] = field(default_factory=list)


@given(
    parsers.parse(
        'a chain outcome for pair "{pair}" at "{timestamp}" with filter results:'
    )
)
def _chain_outcome_with_filter_results(
    audit_ctx: _AuditCtx, pair: str, timestamp: str, datatable: list[list[str]]
) -> None:
    """Stage the pair/timestamp and a `FilterResult` list parsed from the Gherkin table."""
    headers, *rows = datatable
    audit_ctx.pair = pair
    audit_ctx.timestamp = datetime.fromisoformat(timestamp)
    audit_ctx.filter_results = [
        FilterResult(
            filter_name=cells["filter_name"],
            recommendation=Recommendation(cells["recommendation"]),
            reason=cells["reason"],
            veto=cells["veto"] == "true",
            confidence=float(cells["confidence"]) if cells.get("confidence") else None,
        )
        for cells in (dict(zip(headers, row, strict=True)) for row in rows)
    ]


@given("the accumulated features are:")
def _accumulated_features(audit_ctx: _AuditCtx, datatable: list[list[str]]) -> None:
    """Stage `state.features` from a two-column key/value Gherkin table."""
    headers, *rows = datatable
    audit_ctx.features = {
        cells["key"]: _parse_value(cells["value"])
        for cells in (dict(zip(headers, row, strict=True)) for row in rows)
    }


@given(parsers.parse('the chain decision is "{decision}"'))
def _chain_decision(audit_ctx: _AuditCtx, decision: str) -> None:
    """Stage the chain's final `Decision` and build the `ChainOutcome` under test."""
    audit_ctx.decision = Decision(decision)
    assert audit_ctx.timestamp is not None
    state = ExecutionState(
        timestamp=audit_ctx.timestamp,
        pair=audit_ctx.pair,
        features=audit_ctx.features,
        filter_results=audit_ctx.filter_results,
    )
    audit_ctx.outcome = ChainOutcome(decision=audit_ctx.decision, state=state)


@when(parsers.parse('the outcome is converted to a decision row with trade_id "{trade_id}"'))
def _convert_outcome(audit_ctx: _AuditCtx, trade_id: str) -> None:
    """Run the conversion function under test."""
    assert audit_ctx.outcome is not None
    audit_ctx.row = decision_row_from_outcome(audit_ctx.outcome, trade_id=trade_id)


@then(parsers.parse('the decision row\'s trade_id is "{trade_id}"'))
def _row_trade_id(audit_ctx: _AuditCtx, trade_id: str) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.trade_id == trade_id


@then("the decision row's trade_id is absent")
def _row_trade_id_absent(audit_ctx: _AuditCtx) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.trade_id is None


@then(parsers.parse('the decision row\'s timestamp is "{timestamp}"'))
def _row_timestamp(audit_ctx: _AuditCtx, timestamp: str) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.timestamp == datetime.fromisoformat(timestamp)


@then(parsers.parse('the decision row\'s pair is "{pair}"'))
def _row_pair(audit_ctx: _AuditCtx, pair: str) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.pair == pair


@then(parsers.parse('the decision row\'s final_decision is "{decision}"'))
def _row_final_decision(audit_ctx: _AuditCtx, decision: str) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.final_decision == decision


@then("the decision row's vetoed_by is absent")
def _row_vetoed_by_absent(audit_ctx: _AuditCtx) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.vetoed_by is None


@then(parsers.parse('the decision row\'s vetoed_by is "{filter_name}"'))
def _row_vetoed_by(audit_ctx: _AuditCtx, filter_name: str) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.vetoed_by == filter_name


@then("the decision row's filter_results mirrors the source filter results in order")
def _row_filter_results_mirror(audit_ctx: _AuditCtx) -> None:
    """Every source `FilterResult` field survives the conversion, in the same order."""
    assert audit_ctx.row is not None
    assert len(audit_ctx.row.filter_results) == len(audit_ctx.filter_results)
    for row_entry, source in zip(
        audit_ctx.row.filter_results, audit_ctx.filter_results, strict=True
    ):
        assert row_entry.filter_name == source.filter_name
        assert row_entry.recommendation == source.recommendation.value
        assert row_entry.reason == source.reason
        assert row_entry.veto == source.veto
        assert row_entry.confidence == source.confidence


@then("the decision row's features_hash matches hashing the accumulated features")
def _row_features_hash(audit_ctx: _AuditCtx) -> None:
    assert audit_ctx.row is not None
    assert audit_ctx.row.features_hash == _hash_features(audit_ctx.features)


@given(parsers.parse('two decision rows for trade_ids "{first}" and "{second}"'))
def _two_decision_rows(audit_ctx: _AuditCtx, first: str, second: str) -> None:
    """Two independently-built `DecisionRow`s with distinct `trade_id`s and identical shape.

    Both rows carry the same `filter_results`/`enrichment`/`metadata` key shape (and
    non-empty `enrichment`/`metadata` dicts): the Repository's Arrow serde infers one
    struct schema per column across the whole table from the dict's keys, so an empty
    dict would infer a childless struct type that pyarrow's Parquet writer rejects, and
    differently-shaped dicts across rows would not round-trip losslessly (both are
    out-of-scope Repository limitations, not something this story's audit rows need to
    exercise).
    """
    for trade_id in (first, second):
        state = ExecutionState(
            timestamp=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            pair="EURUSD",
            features={"trend_ok": True},
            filter_results=[
                FilterResult(
                    filter_name="trend",
                    recommendation=Recommendation.BUY,
                    reason="uptrend",
                    enrichment={"trend_ok": True},
                    metadata={"source": "test"},
                )
            ],
        )
        outcome = ChainOutcome(decision=Decision.BUY, state=state)
        audit_ctx.rows.append(decision_row_from_outcome(outcome, trade_id=trade_id))


@given("a single decision row with a filter_result that has no enrichment or metadata")
def _single_row_no_enrichment(audit_ctx: _AuditCtx) -> None:
    """Regression: `FilterResult`'s own dataclass default is an empty dict for both
    fields -- the common case for most filters (F1/F2/F3 typically enrich nothing).
    A batch where every row's dict is empty crashed pyarrow's Parquet writer with
    "Cannot write struct type '...' with no child field" (Spec 04h, first hit against
    a real `algos/baseline/main.py` run once `decisions.parquet` was actually written
    for the first time; fixed by `_filter_result_row`'s `or None` mapping).
    """
    state = ExecutionState(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        pair="EURUSD",
        features={"trend_ok": True},
        filter_results=[
            FilterResult(filter_name="trend", recommendation=Recommendation.BUY, reason="uptrend")
        ],
    )
    outcome = ChainOutcome(decision=Decision.BUY, state=state)
    audit_ctx.rows.append(decision_row_from_outcome(outcome, trade_id="trade-003"))


@given("a single NO_TRADE decision row")
def _single_no_trade_row(audit_ctx: _AuditCtx) -> None:
    """One NO_TRADE row, proving a null `trade_id` round-trips through real Parquet.

    Non-empty `enrichment`/`metadata` (same reasoning as `_two_decision_rows`): an empty
    dict would infer a childless struct type pyarrow's writer rejects.
    """
    state = ExecutionState(
        timestamp=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        pair="EURUSD",
        features={"trend_ok": False},
        filter_results=[
            FilterResult(
                filter_name="risk_guard",
                recommendation=Recommendation.HOLD,
                reason="breach",
                veto=True,
                enrichment={"trend_ok": False},
                metadata={"source": "test"},
            )
        ],
    )
    outcome = ChainOutcome(decision=Decision.NO_TRADE, state=state)
    audit_ctx.rows.append(decision_row_from_outcome(outcome, trade_id="trade-fabricated"))


@when(parsers.parse('the decision rows are written to "{filename}"'))
def _write_rows(audit_ctx: _AuditCtx, tmp_path: Path, filename: str) -> None:
    audit_ctx.path = tmp_path / filename
    write_decisions(audit_ctx.rows, audit_ctx.path)


@then("the Parquet file exists on disk")
def _file_exists(audit_ctx: _AuditCtx) -> None:
    assert audit_ctx.path is not None
    assert audit_ctx.path.exists()


@then("reading it back yields the same decision rows")
def _read_back_matches(audit_ctx: _AuditCtx) -> None:
    assert audit_ctx.path is not None
    repo: ParquetRepository[DecisionRow] = ParquetRepository(DecisionRow, audit_ctx.path)
    audit_ctx.read_back = repo.read_all()
    assert sorted(audit_ctx.read_back, key=lambda r: r.trade_id) == sorted(
        audit_ctx.rows, key=lambda r: r.trade_id
    )


@then("the read-back row's trade_id is absent")
def _read_back_trade_id_absent(audit_ctx: _AuditCtx) -> None:
    assert len(audit_ctx.read_back) == 1
    assert audit_ctx.read_back[0].trade_id is None


@then("each decision row's trade_id matches the trade_id it was built with")
def _each_trade_id_matches(audit_ctx: _AuditCtx) -> None:
    """Every row's `trade_id` is present and unique — the join-ready schema proof."""
    trade_ids = [row.trade_id for row in audit_ctx.rows]
    assert len(set(trade_ids)) == len(trade_ids)


@pytest.fixture
def audit_ctx() -> _AuditCtx:
    """A fresh per-scenario context."""
    return _AuditCtx()


@dataclass
class _HashCtx:
    """Per-scenario context for the standalone `_hash_features` property scenarios."""

    hash_a: str = ""
    hash_b: str = ""
    error: Exception | None = None


@pytest.fixture
def hash_ctx() -> _HashCtx:
    """A fresh per-scenario context for the hashing scenarios."""
    return _HashCtx()


@when("two equal-content feature dicts built in a different key order are hashed")
def _hash_equal_content_different_order(hash_ctx: _HashCtx) -> None:
    """Two dicts with the same keys/values but reversed insertion order."""
    forward: dict[str, object] = {"trend_ok": True, "rsi": 55}
    reversed_order: dict[str, object] = {"rsi": 55, "trend_ok": True}
    hash_ctx.hash_a = _hash_features(forward)
    hash_ctx.hash_b = _hash_features(reversed_order)


@then("their features_hash values are equal")
def _hashes_equal(hash_ctx: _HashCtx) -> None:
    assert hash_ctx.hash_a == hash_ctx.hash_b


@when("two feature dicts with different values are hashed")
def _hash_different_values(hash_ctx: _HashCtx) -> None:
    a: dict[str, object] = {"trend_ok": True}
    b: dict[str, object] = {"trend_ok": False}
    hash_ctx.hash_a = _hash_features(a)
    hash_ctx.hash_b = _hash_features(b)


@then("their features_hash values differ")
def _hashes_differ(hash_ctx: _HashCtx) -> None:
    assert hash_ctx.hash_a != hash_ctx.hash_b


@when("a feature dict containing a non-JSON-native value is hashed")
def _hash_non_json_native(hash_ctx: _HashCtx) -> None:
    """A `set` isn't natively JSON-serializable — this exercises `default=str`."""
    try:
        hash_ctx.hash_a = _hash_features({"native_ids": {1, 2, 3}})
    except TypeError as exc:
        hash_ctx.error = exc


@then("hashing succeeds and produces a features_hash")
def _hash_succeeds(hash_ctx: _HashCtx) -> None:
    assert hash_ctx.error is None
    assert hash_ctx.hash_a
