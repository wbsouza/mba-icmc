"""Build and persist minute-bucketed event-derived features."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from algo_core.repository.parquet import ParquetRepository

from algo_score.events.features import EventFeature, EventFeatureSpec, feature_rows, spec_for
from algo_score.events.grid import PUBLICATION_LAG, partitioned_minutes
from algo_score.events.models import DailyValue, EventFeatureReport
from algo_score.events.paths import feature_path, feature_root
from algo_score.events.readers import read_gdelt_daily_values, read_gpr_daily_values


def build_event_features(data_root: Path, kind: str, start: date, end: date) -> EventFeatureReport:
    """Build ``kind`` event features for the inclusive date window."""
    spec = spec_for(kind)
    # The day before `start` is read too: its aggregate is what `start`'s own minutes
    # carry under the grid's publication lag.
    daily_values = _read_daily_values(data_root, spec, start - PUBLICATION_LAG, end)
    return _write_features(data_root, spec, daily_values, start, end)


def _read_daily_values(
    data_root: Path, spec: EventFeatureSpec, start: date, end: date
) -> list[DailyValue]:
    """Read canonical daily values for ``spec`` from the matching source adapter."""
    if spec.kind == "gpr":
        return read_gpr_daily_values(data_root)
    if spec.kind == "gdelt":
        return read_gdelt_daily_values(data_root, start, end)
    raise ValueError(f"event kind {spec.kind!r} has no reader adapter.")


def _write_features(
    data_root: Path,
    spec: EventFeatureSpec,
    daily_values: list[DailyValue],
    start: date,
    end: date,
) -> EventFeatureReport:
    """Expand daily values to minutes and merge them into one Parquet partition per month.

    A partial-month build only replaces the minutes it was asked for: rows an existing
    partition holds outside [start, end] are kept unchanged (e.g. building May 1 - June 1
    must not truncate an already-complete June partition to June 1).
    """
    output_root = feature_root(data_root, spec.kind)
    total = 0
    for year, month, minutes in partitioned_minutes(start, end):
        repository = ParquetRepository(spec.model, feature_path(data_root, spec.kind, year, month))
        rebuilt = feature_rows(spec, daily_values, minutes)
        repository.put(_merge_outside(repository, rebuilt, minutes[0], minutes[-1]))
        total += len(minutes)
    return EventFeatureReport(kind=spec.kind, rows=total, output_root=output_root)


def _merge_outside(
    repository: ParquetRepository[EventFeature],
    rebuilt: list[EventFeature],
    first: datetime,
    last: datetime,
) -> list[EventFeature]:
    """`rebuilt` plus the partition's existing rows outside [first, last], time-ordered."""
    if not repository.exists():
        return rebuilt
    kept = [row for row in repository.read_all() if not first <= row.timestamp <= last]
    return sorted([*kept, *rebuilt], key=lambda row: row.timestamp)
