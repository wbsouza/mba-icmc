"""Resample decoded ticks into QuoteBars at a chosen timeframe (UTC grid).

Pure, in-memory, dependency-free: a function of a tick sequence and a
``Timeframe`` (MT5-style m1…d1). Exact-duplicate ticks ``(timestamp, bid, ask)``
are dropped; a bar with no ticks yields **no bar** (a gap, never forward-filled
here). The bar timestamp is the start of the bar. See ../SPEC.md §6.1.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from algo_core.bars import QuoteBar, Tick, Timeframe


def resample(ticks: Iterable[Tick], timeframe: Timeframe) -> list[QuoteBar]:
    """Aggregate ticks into one bid/ask OHLC QuoteBar per ``timeframe`` bar with ticks."""
    buckets: dict[datetime, list[Tick]] = {}
    for tick in _deduplicated(ticks):
        buckets.setdefault(timeframe.floor(tick.timestamp), []).append(tick)
    return [_bar(start, sorted(group, key=_when)) for start, group in sorted(buckets.items())]


def _deduplicated(ticks: Iterable[Tick]) -> list[Tick]:
    """Drop exact-duplicate ticks, keeping the first occurrence."""
    seen: set[tuple[datetime, float, float]] = set()
    unique: list[Tick] = []
    for tick in ticks:
        key = (tick.timestamp, tick.bid, tick.ask)
        if key not in seen:
            seen.add(key)
            unique.append(tick)
    return unique


def _when(tick: Tick) -> datetime:
    return tick.timestamp


def _bar(minute: datetime, ticks: list[Tick]) -> QuoteBar:
    """Build one minute's QuoteBar from its time-ordered ticks."""
    bids = [tick.bid for tick in ticks]
    asks = [tick.ask for tick in ticks]
    return QuoteBar(
        timestamp=minute,
        bid_open=bids[0], bid_high=max(bids), bid_low=min(bids), bid_close=bids[-1],
        ask_open=asks[0], ask_high=max(asks), ask_low=min(asks), ask_close=asks[-1],
        tick_count=len(ticks),
    )
