"""Compose pure perception with chain settings for both training and LEAN closed bars."""

import dataclasses
from datetime import timedelta

from algo_backtest.chain.filters.f3_pattern import PatternConfig
from algo_backtest.chain.filters.volume_strength import VolumeConfig
from algo_backtest.perception.candle_catalog import CandleCatalog
from algo_backtest.perception.candle_context import ContextEvaluator
from algo_backtest.perception.candle_contract import ADMITTED_RULES, CandleConfig, ClosedBar
from algo_backtest.perception.candle_sequence import SequenceEvaluator
from algo_backtest.perception.candlestick import CandleDetector
from algo_backtest.perception.heikin_ashi import OHLC
from algo_backtest.perception.volume import RelativeTickActivity
from algo_core.bars import QuoteBar


class MarketSignals:
    """Opt-in signals leave historical models and their missing-pattern contract unchanged."""

    def __init__(
        self,
        pattern: PatternConfig | None,
        volume: VolumeConfig | None,
        *,
        bar_minutes: int,
        pair: str,
    ) -> None:
        """Construct only the producers explicitly enabled in the resolved configuration."""
        self._detector = CandleDetector() if pattern and pattern.detector == "talib" else None
        self._activity = RelativeTickActivity(volume.lookback) if volume else None
        self._bar_minutes = bar_minutes
        self._catalog: CandleCatalog | None = None
        self._context: ContextEvaluator | None = None
        self._sequence: SequenceEvaluator | None = None
        if pattern and pattern.detector == "expanded":
            candle_config = CandleConfig(
                enabled_rules=ADMITTED_RULES, timeframe_minutes=bar_minutes,
                policy_mode=pattern.mode,
            )
            self._catalog = CandleCatalog(candle_config, pair=pair)
            self._context = ContextEvaluator(candle_config)
            self._sequence = SequenceEvaluator(timeframe_minutes=bar_minutes)

    def update(self, bar: QuoteBar) -> dict[str, object]:
        """Consume one complete canonical candle, never a partly formed future bucket."""
        result: dict[str, object] = {"candlestick_pattern": None}
        mid_open = (bar.bid_open + bar.ask_open) / 2
        mid_high = (bar.bid_high + bar.ask_high) / 2
        mid_low = (bar.bid_low + bar.ask_low) / 2
        mid_close = (bar.bid_close + bar.ask_close) / 2
        if self._detector:
            candle = OHLC(mid_open, mid_high, mid_low, mid_close)
            result["candlestick_pattern"] = self._detector.update(candle)
        if self._catalog is not None and self._context is not None and self._sequence is not None:
            closed_bar = ClosedBar(
                bar.timestamp + timedelta(minutes=self._bar_minutes),
                mid_open, mid_high, mid_low, mid_close,
            )
            evidence = self._catalog.update(closed_bar)
            context = self._context.update(closed_bar)
            confirmation = self._sequence.update(closed_bar)
            result["candle_evidence"] = dataclasses.replace(
                evidence, context=context, confirmation=confirmation,
            )
        if self._activity:
            result["relative_tick_activity"] = self._activity.update(bar.tick_count)
        return result
