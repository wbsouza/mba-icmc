"""Compose pure perception with chain settings for both training and LEAN closed bars."""

from algo_backtest.chain.filters.f3_pattern import PatternConfig
from algo_backtest.chain.filters.volume_strength import VolumeConfig
from algo_backtest.perception.candlestick import CandleDetector
from algo_backtest.perception.heikin_ashi import OHLC
from algo_backtest.perception.volume import RelativeTickActivity
from algo_core.bars import QuoteBar


class MarketSignals:
    """Opt-in signals leave historical models and their missing-pattern contract unchanged."""

    def __init__(self, pattern: PatternConfig | None, volume: VolumeConfig | None) -> None:
        """Construct only the producers explicitly enabled in the resolved configuration."""
        self._detector = CandleDetector() if pattern and pattern.detector == "talib" else None
        self._activity = RelativeTickActivity(volume.lookback) if volume else None

    def update(self, bar: QuoteBar) -> dict[str, object]:
        """Consume one complete canonical candle, never a partly formed future bucket."""
        result: dict[str, object] = {"candlestick_pattern": None}
        if self._detector:
            candle = OHLC(
                (bar.bid_open + bar.ask_open) / 2, (bar.bid_high + bar.ask_high) / 2,
                (bar.bid_low + bar.ask_low) / 2, (bar.bid_close + bar.ask_close) / 2,
            )
            result["candlestick_pattern"] = self._detector.update(candle)
        if self._activity:
            result["relative_tick_activity"] = self._activity.update(bar.tick_count)
        return result
