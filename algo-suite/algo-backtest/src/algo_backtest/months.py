"""Calendar-month partition helpers for year=/month= Parquet layouts."""

from __future__ import annotations

from datetime import date


def months_between(start: date, end: date) -> list[tuple[int, int]]:
    """Every (year, month) the inclusive [start, end] window touches, in calendar order.

    Raises:
        ValueError: if ``start`` is after ``end``.
    """
    if start > end:
        raise ValueError(f"window start {start} is after its end {end}")
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months
