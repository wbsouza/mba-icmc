"""Build and persist minute-bucketed event-derived features."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from algo_core.repository.parquet import ParquetRepository

from algo_score.events.features import EventFeatureSpec, feature_rows, spec_for
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
    """Expand daily values to minutes and write one Parquet partition per month."""
    output_root = feature_root(data_root, spec.kind)
    total = 0
    for year, month, minutes in partitioned_minutes(start, end):
        path = feature_path(data_root, spec.kind, year, month)
        ParquetRepository(spec.model, path).put(feature_rows(spec, daily_values, minutes))
        total += len(minutes)
    return EventFeatureReport(kind=spec.kind, rows=total, output_root=output_root)
