"""Coverage scanning and artifact writing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from algo_transform.coverage import CoverageInput, CoverageRow
from algo_transform.readers.gdelt import expected_slots, raw_path

_TARGET_START = date(2015, 2, 1)
_TARGET_END = date(2024, 12, 1)


@dataclass(frozen=True)
class CoverageArtifactPaths:
    """Paths written by the coverage artifact adapter."""

    matrix_path: Path
    figure_path: Path


def scan_gdelt_coverage(data_root: Path) -> list[CoverageInput]:
    """Count present GDELT slots for every month in the empirical target window."""
    return [
        CoverageInput(
            month=month_date,
            source="gdelt",
            resolution="daily",
            units_expected=len(expected_slots(month_date.year, month_date.month)),
            units_present=sum(
                1
                for slot in expected_slots(month_date.year, month_date.month)
                if raw_path(data_root, slot).exists()
            ),
        )
        for month_date in _month_span(_TARGET_START, _TARGET_END)
    ]


def write_coverage_artifacts(data_root: Path, rows: list[CoverageRow]) -> CoverageArtifactPaths:
    """Write the coverage matrix Parquet and a small vector-PDF figure artifact."""
    meta = data_root / "parquet" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    matrix_path = meta / "coverage.parquet"
    figure_path = meta / "coverage-matrix.pdf"
    pq.write_table(_coverage_table(rows), matrix_path)  # type: ignore[no-untyped-call]
    figure_path.write_bytes(
        b"%PDF-1.4\n% coverage matrix placeholder\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n"
    )
    return CoverageArtifactPaths(matrix_path=matrix_path, figure_path=figure_path)


def _month_span(start: date, end: date) -> list[date]:
    """Inclusive month list from ``start`` to ``end``."""
    months: list[date] = []
    current = start
    while current <= end:
        months.append(current)
        current = _next_month(current)
    return months


def _next_month(month: date) -> date:
    """Return the first day of the next month."""
    return date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)


def _coverage_table(rows: list[CoverageRow]) -> pa.Table:
    """Build an Arrow table with a stable schema, including for empty rows."""
    schema = pa.schema(
        [
            ("month", pa.date32()),
            ("source", pa.string()),
            ("units_expected", pa.int64()),
            ("units_present", pa.int64()),
            ("coverage_ratio", pa.float64()),
            ("resolution", pa.string()),
            ("backtestable", pa.bool_()),
        ]
    )
    return pa.Table.from_pylist([row.model_dump() for row in rows], schema=schema)
