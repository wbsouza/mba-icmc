"""Minute-grid expansion helpers for event features."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta

from algo_score.events.models import DailyValue

# A daily aggregate summarizes the whole UTC day, so it is only knowable once that day
# has ended: day D's value becomes visible at 00:00 UTC on D+1, never at 00:00 on D.
# Exposing it on D itself leaks up to 24h of future information into every backtest bar
# (and into F7's training labels) that reads this feature.
PUBLICATION_LAG = timedelta(days=1)


def forward_filled_values(
    daily_values: list[DailyValue], minutes: list[datetime]
) -> list[float | None]:
    """Forward-fill daily values onto ``minutes`` without inventing earlier values.

    Each minute carries the most recent daily value whose day ended *before* that
    minute's UTC day began (``PUBLICATION_LAG``) — never the same day's aggregate.
    """
    by_day = {row.day: row.value for row in daily_values}
    current: float | None = None
    values: list[float | None] = []
    for minute in minutes:
        daily_value = by_day.get(minute.date() - PUBLICATION_LAG)
        if daily_value is not None:
            current = daily_value
        values.append(current)
    return values


def partitioned_minutes(start: date, end: date) -> Iterable[tuple[int, int, list[datetime]]]:
    """Yield UTC minute grids grouped by output year/month partition."""
    cursor = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    stop = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    while cursor < stop:
        year, month = cursor.year, cursor.month
        partition: list[datetime] = []
        while cursor < stop and cursor.year == year and cursor.month == month:
            partition.append(cursor)
            cursor += timedelta(minutes=1)
        yield year, month, partition
