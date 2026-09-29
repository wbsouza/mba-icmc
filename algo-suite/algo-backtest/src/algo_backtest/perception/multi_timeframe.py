"""Primary and closed-higher-timeframe HA perception over LEAN quote bars."""

from __future__ import annotations

from datetime import timedelta
from importlib import import_module
from typing import Any

from algo_backtest.perception.heikin_ashi import (
    OHLC,
    validate_period,
)


def _ohlc(bar: Any) -> OHLC:
    """Read LEAN QuoteBar midpoint properties or TradeBar OHLC."""
    return OHLC(float(bar.open), float(bar.high), float(bar.low), float(bar.close))


class MultiTimeframeHeikinAshi:
    """Expose F1 direction features only after both timeframes are ready.

    QuoteBar OHLC properties are LEAN's bid/ask midpoint candle. The native
    TradeBarConsolidator receives that candle, preserving LEAN's bucket and
    session-edge semantics. Scanning at each input end time closes a completed
    bucket immediately, without needing a future input or using an incomplete
    higher-timeframe candle.
    """

    def __init__(self, period1: int = 6, period2: int = 2, higher_tf_minutes: int = 60) -> None:
        """Compose independent primary and higher-timeframe native indicator state."""
        validate_period(higher_tf_minutes, "higher_tf_minutes")
        if higher_tf_minutes < 2:
            raise ValueError("higher_tf_minutes must be at least 2; use a higher timeframe.")
        from algo_backtest.perception.lean_indicator import DoubleSmoothedHeikinAshiTrend

        self._primary = DoubleSmoothedHeikinAshiTrend(period1, period2)
        self._higher = DoubleSmoothedHeikinAshiTrend(period1, period2)
        self._trade_bar = import_module("QuantConnect.Data.Market").TradeBar
        consolidators = import_module("QuantConnect.Data.Consolidators")
        self._consolidator = consolidators.TradeBarConsolidator(
            timedelta(minutes=higher_tf_minutes)
        )
        self._consolidator.data_consolidated += self._on_consolidated

    def update(self, quote_bar: Any) -> None:
        """Consume one completed primary quote bar, then close elapsed buckets."""
        candle = _ohlc(quote_bar)
        trade_bar = self._trade_bar(
            quote_bar.time,
            quote_bar.symbol,
            *candle.values(),
            0,
            quote_bar.period,
        )
        self._primary.update(trade_bar)
        self._consolidator.update(trade_bar)
        self._consolidator.scan(quote_bar.end_time)

    def _on_consolidated(self, sender: Any, bar: Any) -> None:
        """Advance higher-timeframe state only when its candle has closed."""
        self._higher.update(bar)

    @property
    def is_ready(self) -> bool:
        """Whether both independent timeframe histories have warmed up."""
        return self._primary.is_ready and self._higher.is_ready

    def features(self) -> dict[str, float]:
        """Return only this candidate's two directions, leaving strength upstream."""
        if not self.is_ready:
            raise ValueError(
                "MultiTimeframeHeikinAshi is not ready; feed enough completed primary "
                "and higher-timeframe bars and check is_ready before requesting features."
            )
        return {
            "trend_direction": self._primary.direction,
            "higher_tf_trend_direction": self._higher.direction,
        }
