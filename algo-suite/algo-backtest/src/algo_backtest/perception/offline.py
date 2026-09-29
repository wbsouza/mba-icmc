"""Host DSHA replay matching the native indicator's completed-minute contract.

Wilder and LWMA follow QuantConnect/Lean's Indicators implementations. Decimal
smoothing crosses a float boundary at the shared HA transform, just as the
PythonIndicator does. Buckets follow PeriodCountConsolidatorBase and DateTime
RoundDown: intervals up to one day round from year one; longer intervals start
at the first observed bar. Missing minutes are never invented.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from decimal import Decimal

from algo_backtest.perception.heikin_ashi import (
    OHLC,
    HeikinAshi,
    classify_direction,
    heikin_ashi_transform,
    validate_period,
)


def _decimal(value: float) -> Decimal:
    """Match the native double-to-decimal bridge's fifteen significant digits."""
    return Decimal(format(value, ".15g"))


class OfflineDoubleSmoothedHeikinAshi:
    """Replay native Wilder → shared HA → LWMA without importing the CLR."""

    def __init__(self, period1: int = 6, period2: int = 2) -> None:
        """Validate smoothing lengths and allocate bounded history."""
        validate_period(period1, "period1")
        validate_period(period2, "period2")
        self._period1 = period1
        self._period2 = period2
        self._alpha = Decimal(1) / period1
        self._samples = 0
        self._first = [Decimal(0)] * 4
        self._seed = [Decimal(0)] * 4
        self._second: deque[tuple[Decimal, ...]] = deque(maxlen=period2)
        self._previous: HeikinAshi | None = None

    def update(self, ohlc: OHLC) -> None:
        """Advance all four price fields and feed only ready first-pass values."""
        self._samples += 1
        self._smooth_first(ohlc)
        if self._samples < self._period1:
            return
        candle = heikin_ashi_transform(OHLC(*(float(v) for v in self._first)), self._previous)
        self._previous = candle
        values = candle.near, candle.far, candle.ohlc.open, candle.ohlc.close
        self._second.append(tuple(_decimal(value) for value in values))

    def _smooth_first(self, ohlc: OHLC) -> None:
        """Seed Wilder with SMA, then use the native recurrence order."""
        for index, value in enumerate(ohlc.values()):
            current = _decimal(value)
            if self._samples < self._period1:
                self._seed[index] += current
                self._first[index] = self._seed[index] / self._samples
            else:
                self._first[index] = (
                    current * self._alpha + self._first[index] * (1 - self._alpha)
                )

    @property
    def is_ready(self) -> bool:
        """Require period1 + period2 − 1 completed candles."""
        return len(self._second) == self._period2

    @property
    def smoothed_values(self) -> tuple[float, float, float, float]:
        """Return near, far, HA open and HA close after both smoothing passes."""
        if not self.is_ready:
            raise ValueError("Offline DSHA is not ready; feed enough completed bars first.")
        denominator = self._period2 * (self._period2 + 1) // 2
        values = [Decimal(0)] * 4
        for weight, candle in enumerate(self._second, start=1):
            for index, value in enumerate(candle):
                values[index] += value * weight
        near, far, open_, close = (float(value / denominator) for value in values)
        return near, far, open_, close

    @property
    def direction(self) -> float:
        """Use the same binary classifier as native serving, including ties."""
        near, far, _, _ = self.smoothed_values
        return classify_direction(near, far)


class OfflineMultiTimeframeHeikinAshi:
    """Expose primary and closed higher-timeframe directions for model training."""

    def __init__(self, period1: int = 6, period2: int = 2, higher_tf_minutes: int = 60) -> None:
        """Allocate independent replay indicators and an empty higher bucket."""
        validate_period(higher_tf_minutes, "higher_tf_minutes")
        if higher_tf_minutes < 2:
            raise ValueError("higher_tf_minutes must be at least 2; use a higher timeframe.")
        self._primary = OfflineDoubleSmoothedHeikinAshi(period1, period2)
        self._higher = OfflineDoubleSmoothedHeikinAshi(period1, period2)
        self._period = timedelta(minutes=higher_tf_minutes)
        self._bucket: tuple[datetime, OHLC] | None = None

    def update(self, timestamp: datetime, ohlc: OHLC) -> None:
        """Consume a minute at its exchange-local START time, then scan its end.

        Native QuoteBar timestamps use the subscription data timezone even when
        the algorithm clock is UTC. Training callers must convert accordingly.
        """
        self._primary.update(ohlc)
        self._close_elapsed(timestamp)
        self._aggregate(timestamp, ohlc)
        self._close_elapsed(timestamp + timedelta(minutes=1))

    def _aggregate(self, timestamp: datetime, ohlc: OHLC) -> None:
        """Create or extend one OHLC bucket without synthesizing absent minutes."""
        if self._bucket is None:
            self._bucket = self._rounded_time(timestamp), ohlc
            return
        start, previous = self._bucket
        self._bucket = start, OHLC(
            previous.open,
            max(previous.high, ohlc.high),
            min(previous.low, ohlc.low),
            ohlc.close,
        )

    def _rounded_time(self, timestamp: datetime) -> datetime:
        """Match LEAN's tick-origin rounding and longer-than-day exception."""
        if self._period > timedelta(days=1):
            return timestamp
        origin = datetime.min.replace(tzinfo=timestamp.tzinfo)
        return timestamp - (timestamp - origin) % self._period

    def _close_elapsed(self, timestamp: datetime) -> None:
        """Publish an observed bucket when its entire time interval has elapsed."""
        if self._bucket is None:
            return
        start, candle = self._bucket
        if timestamp < start + self._period:
            return
        self._higher.update(candle)
        self._bucket = None

    @property
    def is_ready(self) -> bool:
        """Require independent ready primary and closed higher candle histories."""
        return self._primary.is_ready and self._higher.is_ready

    def features(self) -> dict[str, float]:
        """Return the same two direction fields as native runtime perception."""
        if not self.is_ready:
            raise ValueError("Offline DSHA is not ready; feed enough completed bars first.")
        return {
            "trend_direction": self._primary.direction,
            "higher_tf_trend_direction": self._higher.direction,
        }
