"""Market-data value objects: observations of the market, not instrument identity.

Kept apart from ``instrument.py`` on purpose: ``Instrument`` defines *what* a
tradable thing is; ``Tick`` and (later) ``QuoteBar`` are *observations* of it.
Both are the typed ``M`` written through the ``Repository`` (TD-5). Vocabulary
follows LEAN's. See ../../../algo-transform/SPEC.md §3.1.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Timeframe(StrEnum):
    """A Forex bar timeframe (MT5-style set); also the price-path segment.

    The value is the lowercase label (``m1``…``d1``); ``minutes`` is its bar
    length. ``floor`` maps a timestamp to the start of the bar that contains it
    (anchored at midnight UTC), so ticks can be resampled to any timeframe
    directly. All supported timeframes divide a day, so the midnight anchor is
    exact. Strategy filters may each read a different timeframe (multi-timeframe
    analysis); the choice per filter is selected empirically in simulation.
    """

    M1 = "m1"
    M5 = "m5"
    M15 = "m15"
    M30 = "m30"
    H1 = "h1"
    H4 = "h4"
    D1 = "d1"

    @property
    def minutes(self) -> int:
        """The timeframe's bar length in minutes."""
        return _TIMEFRAME_MINUTES[self]

    def floor(self, timestamp: datetime) -> datetime:
        """The start of the bar (of this timeframe) that contains ``timestamp``."""
        midnight = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed_min = int((timestamp - midnight).total_seconds()) // 60
        bucket = (elapsed_min // self.minutes) * self.minutes
        return midnight + timedelta(minutes=bucket)


_TIMEFRAME_MINUTES: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.D1: 1440,
}


def _ensure_utc(value: datetime) -> datetime:
    """Reject a naive or non-UTC datetime (the stage's UTC contract)."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"timestamp must be timezone-aware UTC; got {value!r}")
    return value


class Tick(BaseModel):
    """One decoded quote tick. ``timestamp`` is UTC; ``bid``/``ask`` are prices.

    Cheap domain invariants are enforced so a decoder bug surfaces as a validation
    error rather than silently flowing into resampling and Parquet: the timestamp
    must be timezone-aware UTC, and volumes are non-negative. (Bid/ask ordering is
    deliberately *not* enforced: a crossed quote is rare but valid market data, and
    rejecting it would discard a whole hour of good ticks.)
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    bid: float
    ask: float
    bid_volume: float = Field(ge=0.0)
    ask_volume: float = Field(ge=0.0)

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class QuoteBar(BaseModel):
    """A minute bid/ask OHLC bar with tick volume (LEAN ``QuoteBar``).

    ``timestamp`` is the UTC start of the minute. Canonical price representation
    is bid OHLC + ask OHLC + tick count; mid/spread are derived downstream.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float
    tick_count: int = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)
