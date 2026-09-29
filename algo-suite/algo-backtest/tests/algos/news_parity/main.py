# Integration probe (feature_parity.feature): builds ChainAlgorithm's production
# ExecutionState each bar and applies the production F4 filter (the hybrid strategy's
# news index + config) to it, logging the news_event_intensity F4 looked up, so the
# test can compare it with algo_backtest.training's row for the same bar.
from pathlib import Path

from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter,
    load_news_context_window,
)
from algo_backtest.chain.wiring import PnlWindows, parse_yyyymmdd
from algo_backtest.strategies import load_strategy_chain_config
from AlgorithmImports import *  # noqa: F403
from engine.chain_algorithm import ChainAlgorithm  # noqa: E402


class main(ChainAlgorithm):  # noqa: N801
    """Log F4's per-bar news lookup once every indicator is ready."""

    strategy_name = "news_parity"
    log_tag = "NEWS"

    def initialize(self) -> None:
        """One-day EURUSD minute run: production indicators, state and F4 index."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        day = parse_yyyymmdd(self.get_parameter("day"))
        self.set_start_date(day.year, day.month, day.day)
        self.set_end_date(day.year, day.month, day.day)
        self._symbol = self.add_forex("EURUSD", Resolution.MINUTE, Market.OANDA).symbol  # noqa: F405
        self._subscribe_indicators()
        self._economics = load_strategy_chain_config("hybrid").capital_mgmt
        self._pnl = PnlWindows()
        index = load_news_context_window(
            Path(self.get_parameter("news_data_root")), "EURUSD", day, day
        )
        news_context = load_strategy_chain_config("hybrid").news_context
        assert news_context is not None, "hybrid config.yaml must declare news_context"
        self._f4 = F4NewsContextFilter(index=index, config=news_context)

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Apply F4 to this bar's production state; log what it looked up."""
        if not self._indicators_ready() or self._symbol not in data.quote_bars:
            return
        result = self._f4.apply(self._state())
        self.debug(f"NEWS|{self.utc_time}|{result.enrichment['news_event_intensity']!r}")

    def on_end_of_algorithm(self) -> None:
        """Nothing to persist."""
