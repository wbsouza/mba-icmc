"""`decisions.parquet` rows -> `decisions` + `decision_filters` rows.

Every chain invocation is kept (the audit trail); the row whose `final_decision` is
BUY/SELL with a `trade_id` is the entry decision of that trade (`is_entry = 1`). The F7
probability is lifted into `p_hat` from the meta-learner's enrichment so the viewer can
plot it without unpacking the filter rows. F3's detected pattern name is extracted from
its reason text (`detected candlestick pattern 'hammer'`, or the older `pattern=hammer`
form) into `decision_filters.pattern_name`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algo_analyze.resultsdb.artifacts import DECISIONS_FILE, field

_PATTERN_FORMS = (
    re.compile(r"detected candlestick pattern '([a-z_]+)'"),
    re.compile(r"\bpattern=([a-z_]+)"),
)
_ENTRY_DECISIONS = frozenset({"BUY", "SELL"})


@dataclass(frozen=True)
class FilterRow:
    """One `decision_filters` row."""

    position: int
    filter_name: str
    recommendation: str
    veto: bool
    reason: str
    pattern_name: str | None


@dataclass(frozen=True)
class DecisionRow:
    """One `decisions` row with its filter rows."""

    trade_id: str | None
    timestamp: datetime
    final_decision: str
    vetoed_by: str | None
    p_hat: float | None
    is_entry: bool
    filters: tuple[FilterRow, ...]


def extract_pattern(reason: str) -> str | None:
    """The candlestick pattern named by an F3 reason, `None` when it names none."""
    for form in _PATTERN_FORMS:
        match = form.search(reason)
        if match is not None:
            return match.group(1)
    return None


def _p_hat(filters: Sequence[Mapping[str, Any]]) -> float | None:
    """The meta-learner's probability from any filter's enrichment (`None` when absent)."""
    for result in filters:
        enrichment = result.get("enrichment")
        if isinstance(enrichment, Mapping) and enrichment.get("p_hat") is not None:
            return float(enrichment["p_hat"])
    return None


def _timestamp(value: Any, path: Path) -> datetime:
    """The row's UTC timestamp (pyarrow yields an aware datetime; ISO text is accepted)."""
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(moment, datetime):
        raise ValueError(f"{path.name} in {path.parent} has a non-datetime timestamp {value!r}")
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)


def _filter_row(position: int, result: Mapping[str, Any], path: Path) -> FilterRow:
    """One `filter_results` struct -> one `decision_filters` row."""
    name = str(field(result, "filter_name", path))
    reason = str(field(result, "reason", path))
    return FilterRow(
        position=position, filter_name=name,
        recommendation=str(field(result, "recommendation", path)),
        veto=bool(field(result, "veto", path)), reason=reason,
        pattern_name=extract_pattern(reason) if name.lower().startswith("f3") else None,
    )


def decision_rows(rows: Sequence[Mapping[str, Any]], run_dir: Path) -> list[DecisionRow]:
    """Every `decisions.parquet` row -> `DecisionRow` (filters in chain order)."""
    path = run_dir / DECISIONS_FILE
    out: list[DecisionRow] = []
    for row in rows:
        results = field(row, "filter_results", path) or []
        decision = str(field(row, "final_decision", path))
        trade_id = row.get("trade_id")
        out.append(DecisionRow(
            trade_id=None if trade_id is None else str(trade_id),
            timestamp=_timestamp(field(row, "timestamp", path), path),
            final_decision=decision, vetoed_by=row.get("vetoed_by"), p_hat=_p_hat(results),
            is_entry=decision in _ENTRY_DECISIONS and trade_id is not None,
            filters=tuple(_filter_row(i, r, path) for i, r in enumerate(results)),
        ))
    return out
