"""LEAN custom indicator, imported only inside the LEAN runtime.

Follows QuantConnect's manual PythonIndicator update contract:
https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/custom-indicators
Native smoothing implementations reviewed for this composition:
https://github.com/QuantConnect/Lean/blob/master/Indicators/WilderMovingAverage.cs
https://github.com/QuantConnect/Lean/blob/master/Indicators/LinearWeightedMovingAverage.cs
HA seeding/recurrence reference:
https://github.com/QuantConnect/Lean/blob/master/Indicators/HeikinAshi.cs
"""

from __future__ import annotations

from datetime import datetime
from importlib import import_module
from typing import Any

from algo_backtest.perception.heikin_ashi import (
    OHLC,
    HeikinAshi,
    classify_direction,
    heikin_ashi_transform,
    validate_period,
)

_indicators = import_module("QuantConnect.Indicators")
PythonIndicator = _indicators.PythonIndicator


class DoubleSmoothedHeikinAshiTrend(PythonIndicator):  # type: ignore[misc, valid-type]
    """Manually updated PythonIndicator with native Wilder and LWMA passes.

    ``value``/``current`` are zero placeholders during warm-up; callers must
    check ``is_ready``. ``direction`` fails fast instead. Only completed
    TradeBars should be passed to ``update``; automatic registration must not
    be combined with this manual event publishing path.
    """

    def __init__(self, period1: int = 6, period2: int = 2) -> None:
        """Allocate native smoothing passes after validating both bar periods."""
        validate_period(period1, "period1")
        validate_period(period2, "period2")
        super().__init__()
        self.name = f"DoubleSmoothedHeikinAshiTrend({period1},{period2})"
        self.warm_up_period = period1 + period2 - 1
        self.time = datetime.min
        self.value = 0.0
        self.samples = 0
        self._first = tuple(_indicators.WilderMovingAverage(period1) for _ in range(4))
        self._second = tuple(_indicators.LinearWeightedMovingAverage(period2) for _ in range(4))
        self._previous: HeikinAshi | None = None

    def reset(self) -> None:
        """Restart native smoothing, HA recurrence, and published indicator state."""
        for indicator in (*self._first, *self._second):
            indicator.reset()
        self._previous = None
        self.time = datetime.min
        self.value = 0.0
        self.samples = 0
        super().reset()

    def update(self, input: Any) -> bool:
        """Advance one completed TradeBar and publish the current reading."""
        self.time = input.end_time
        self.samples += 1
        candle = OHLC(float(input.open), float(input.high), float(input.low), float(input.close))
        self._advance(candle)
        if self.is_ready:
            self.value = self.direction
        self.current = _indicators.IndicatorDataPoint(self.time, self.value)
        self.on_updated(self.current)
        return self.is_ready

    def _advance(self, ohlc: OHLC) -> None:
        """Feed ready Wilder candles through HA recurrence and four LWMA buffers."""
        for indicator, value in zip(self._first, ohlc.values(), strict=True):
            indicator.update(self.time, value)
        if not all(indicator.is_ready for indicator in self._first):
            return
        smoothed = OHLC(*(float(indicator.current.value) for indicator in self._first))
        candle = heikin_ashi_transform(smoothed, self._previous)
        self._previous = candle
        values = candle.near, candle.far, candle.ohlc.open, candle.ohlc.close
        for indicator, value in zip(self._second, values, strict=True):
            indicator.update(self.time, value)

    @property
    def is_ready(self) -> bool:
        """Whether all second-pass buffers contain their required history."""
        return all(indicator.is_ready for indicator in self._second)

    @property
    def smoothed_values(self) -> tuple[float, float, float, float]:
        """Ready near, far, HA open, HA close (the four reference buffers)."""
        if not self.is_ready:
            raise ValueError(
                "DoubleSmoothedHeikinAshiTrend is not ready; feed at least "
                f"{self.warm_up_period} completed bars and check is_ready before reading outputs."
            )
        near, far, open_, close = self._second
        return (
            float(near.current.value),
            float(far.current.value),
            float(open_.current.value),
            float(close.current.value),
        )

    @property
    def direction(self) -> float:
        """Preserve down for far >= near, and reject premature reads."""
        near, far, _, _ = self.smoothed_values
        return classify_direction(near, far)
