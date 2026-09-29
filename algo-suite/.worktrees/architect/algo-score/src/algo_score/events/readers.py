"""Readers for canonical event Parquet inputs."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from algo_score.events.models import DailyValue


def read_gpr_daily_values(data_root: Path) -> list[DailyValue]:
    """Read GPR daily values from canonical transform output."""
    path = data_root / "parquet" / "events" / "gpr" / "data.parquet"
    if not path.exists():
        raise ValueError(f"missing GPR event Parquet: {path}")
    table = pq.read_table(path)  # type: ignore[no-untyped-call]
    return _table_daily_values(table, "period", "gpr")


def read_gdelt_daily_values(data_root: Path, start: date, end: date) -> list[DailyValue]:
    """Read GDELT events and aggregate by unweighted mean GoldsteinScale per day."""
    events: dict[date, list[float]] = {}
    for path in _gdelt_input_paths(data_root, start, end):
        if not path.exists():
            continue
        table = pq.read_table(path)  # type: ignore[no-untyped-call]
        for day, value in zip(
            table.column("event_date").to_pylist(),
            table.column("goldstein_scale").to_pylist(),
            strict=True,
        ):
            events.setdefault(_as_date(day), []).append(float(value))
    if not events:
        raise ValueError("missing GDELT event Parquet for requested window")
    return [
        DailyValue(day=day, value=sum(values) / len(values))
        for day, values in sorted(events.items())
    ]


def _table_daily_values(table: pa.Table, date_column: str, value_column: str) -> list[DailyValue]:
    """Extract sorted daily values from an Arrow table."""
    return sorted(
        (
            DailyValue(day=_as_date(day), value=float(value))
            for day, value in zip(
                table.column(date_column).to_pylist(),
                table.column(value_column).to_pylist(),
                strict=True,
            )
        ),
        key=lambda row: row.day,
    )


def _gdelt_input_paths(data_root: Path, start: date, end: date) -> list[Path]:
    """Return canonical monthly GDELT event partitions intersecting the date window."""
    root = data_root / "parquet" / "events" / "gdelt"
    paths = [root / "data.parquet"]
    paths.extend(
        root / f"year={year:04d}" / f"month={month:02d}" / "data.parquet"
        for year, month in _months(start, end)
    )
    return paths


def _months(start: date, end: date) -> Iterable[tuple[int, int]]:
    """Yield ``(year, month)`` pairs touched by an inclusive date window."""
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        yield cursor.year, cursor.month
        cursor = _next_month(cursor)


def _next_month(day: date) -> date:
    """Return the first day of the month after ``day``."""
    return date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)


def _as_date(value: object) -> date:
    """Normalize Arrow/Python date-like values to ``date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"expected date-like value, got {value!r}")
