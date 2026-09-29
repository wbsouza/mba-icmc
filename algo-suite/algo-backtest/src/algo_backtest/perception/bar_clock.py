"""Causal aggregation of complete UTC minute quotes for live and batch perception.

Incomplete initial, final, and gap-interrupted buckets are intentionally omitted
from warmup collections. No quotes are invented and no partial bucket is flushed.
"""

from collections.abc import Iterable
from datetime import datetime, timedelta

from algo_core.bars import QuoteBar

_DAY_MINUTES = 1440
_MINUTE = timedelta(minutes=1)


class ClosedBarClock:
    """Aggregate ordered, unique minute quotes on exact UTC day boundaries.

    ``minutes`` must be a positive integer divisor of 1440 (booleans excluded).
    Call ``update`` only after each input minute has closed. The output timestamp
    is the bucket start, although the output becomes available at its end.
    """

    def __init__(self, minutes: int) -> None:
        """Initialize bounded aggregation state; reject unsupported minute periods."""
        if isinstance(minutes, bool) or not isinstance(minutes, int):
            raise ValueError("minutes must be an integer; use a positive divisor of 1440.")
        if minutes <= 0 or _DAY_MINUTES % minutes:
            raise ValueError(
                "minutes must be positive and divide 1440; choose an exact UTC bucket."
            )
        self._minutes = minutes
        self._period = timedelta(minutes=minutes)
        self._last_timestamp: datetime | None = None
        self._bucket: datetime | None = None
        self._aggregate: QuoteBar | None = None
        self._count = 0

    def update(self, bar: QuoteBar) -> QuoteBar | None:
        """Emit on the final expected minute, or return None during collection.

        All expected minutes must be present. Incomplete buckets are discarded
        when a later bucket starts, including after market breaks.

        Raises:
            ValueError: Timestamps are unaligned, duplicated, or out of order;
                rejected inputs do not change the clock state.
        """
        self._validate_timestamp(bar.timestamp)
        bucket = self._bucket_start(bar.timestamp)
        if bucket != self._bucket:
            self._bucket, self._aggregate, self._count = bucket, None, 0
        self._aggregate = bar if self._aggregate is None else _merge(self._aggregate, bar)
        self._count += 1
        self._last_timestamp = bar.timestamp
        if self._count == self._minutes and bar.timestamp + _MINUTE == bucket + self._period:
            return self._aggregate
        return None

    def _validate_timestamp(self, timestamp: datetime) -> None:
        """Reject invalid minute starts before changing aggregation state."""
        if timestamp.second or timestamp.microsecond:
            raise ValueError("timestamp must be minute-aligned; supply exact UTC minute starts.")
        if self._last_timestamp is not None and timestamp <= self._last_timestamp:
            raise ValueError(
                "timestamp must be strictly ordered and unique; sort minute bars and remove "
                "duplicates before updating the clock."
            )

    def _bucket_start(self, timestamp: datetime) -> datetime:
        """Floor a QuoteBar's validated UTC minute start to its day-anchored bucket."""
        midnight = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        minute_of_day = timestamp.hour * 60 + timestamp.minute
        return midnight + timedelta(minutes=minute_of_day // self._minutes * self._minutes)


def _merge(first: QuoteBar, latest: QuoteBar) -> QuoteBar:
    """Preserve the first open and timestamp, independent extrema, and latest close."""
    return QuoteBar(
        timestamp=first.timestamp,
        bid_open=first.bid_open,
        bid_high=max(first.bid_high, latest.bid_high),
        bid_low=min(first.bid_low, latest.bid_low),
        bid_close=latest.bid_close,
        ask_open=first.ask_open,
        ask_high=max(first.ask_high, latest.ask_high),
        ask_low=min(first.ask_low, latest.ask_low),
        ask_close=latest.ask_close,
        tick_count=first.tick_count + latest.tick_count,
    )


def aggregate_closed_bars(sequence: Iterable[QuoteBar], minutes: int) -> list[QuoteBar]:
    """Collect exactly the live clock's outputs, without flushing a partial tail.

    Accepts a sequence or one-pass stream of already closed UTC minute quotes.
    Apply any training/LEAN minute-stream normalization before this function.
    Invalid periods and timestamps raise ValueError just as in ClosedBarClock.
    """
    clock = ClosedBarClock(minutes)
    return [closed for bar in sequence if (closed := clock.update(bar)) is not None]
