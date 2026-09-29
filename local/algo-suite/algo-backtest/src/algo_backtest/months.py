"""Calendar helpers shared by the backtest's time contracts: the minute-bar duration
and the year=/month= Parquet partitions a window touches."""

from __future__ import annotations

from datetime import date, timedelta

# One minute bar: its start + BAR_DURATION is its end, i.e. the decision time LEAN
# evaluates it at (`self.time` in on_data) — shared by F4's decision window and F7
# training's news keying so the two cannot drift apart.
BAR_DURATION = timedelta(minutes=1)


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
