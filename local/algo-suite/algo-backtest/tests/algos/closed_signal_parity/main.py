"""Probe production closed-bar clock, native indicators, pattern and tick-activity reader."""

import json
from dataclasses import replace
from datetime import UTC

from AlgorithmImports import *
from engine.chain_algorithm import ChainAlgorithm

from algo_backtest.chain.filters.f3_pattern import PatternConfig
from algo_backtest.chain.filters.volume_strength import VolumeConfig
from algo_backtest.chain.price_features import PriceFeatureConfig
from algo_backtest.chain.wiring import PnlWindows
from algo_backtest.strategies import load_strategy_chain_config


class main(ChainAlgorithm):
    """Exercise actual production helpers without placing orders."""

    strategy_name = "closed_signal_parity"

    def initialize(self):
        """Use small periods to reach readiness on M1/H1/H4 within five trading days."""
        self.set_time_zone(TimeZones.UTC)
        self.set_start_date(2014, 5, 5)
        self.set_end_date(2014, 5, 9)
        self._symbol = self.add_forex("EURUSD", Resolution.MINUTE, Market.OANDA).symbol
        periods = PriceFeatureConfig(
            ema_fast=2, ema_slow=3, ema_higher_tf=4, rsi_period=3,
            macd_fast=2, macd_slow=4, macd_signal=2, atr_period=3,
            swing_lookback_bars=4, bar_minutes=int(self.get_parameter("minutes")))
        config = replace(load_strategy_chain_config("baseline"), price_features=periods,
                         pattern=PatternConfig(detector="talib"),
                         volume_strength=VolumeConfig(lookback=3))
        self._subscribe_indicators(config.perception, config.price_features)
        self._configure_signals(config)
        self._pnl = PnlWindows()
        self._economics = None
        self._observations = []

    def on_data(self, data):
        """Persist the production feature builder only after a complete ready candle."""
        if self._symbol not in data.quote_bars:
            return
        if not self._closed_signal_bar(data.quote_bars[self._symbol]):
            return
        if self._indicators_ready():
            self._observations.append({
                "end": self.utc_time.replace(tzinfo=UTC).isoformat(),
                "features": self._features(),
            })

    def on_end_of_algorithm(self):
        """Keep a full precision JSON artifact, not rounded debug strings."""
        from pathlib import Path

        Path("/Results/signal-observations.json").write_text(json.dumps(self._observations))
