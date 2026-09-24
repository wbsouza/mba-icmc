"""Filesystem paths for event-derived feature output."""

from __future__ import annotations

from pathlib import Path


def feature_root(data_root: Path, kind: str) -> Path:
    """Build the root directory for one event-feature kind."""
    return data_root / "parquet" / "events" / "_features" / kind


def feature_path(data_root: Path, kind: str, year: int, month: int) -> Path:
    """Build the event-feature partition path for ``kind``."""
    return (
        feature_root(data_root, kind) / f"year={year:04d}" / f"month={month:02d}" / "data.parquet"
    )
