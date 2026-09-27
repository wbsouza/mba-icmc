# Integration probe (feature_parity.feature): runs ChainAlgorithm's production indicator
# subscription and feature builder (no chain, no orders) and logs every bar's price
# features, so the test can compare them with algo_backtest.training's rows.
import json

from algo_backtest.chain.wiring import PnlWindows
from algo_backtest.perception.config import parse_perception_config
from algo_backtest.strategies import load_strategy_chain_config
from AlgorithmImports import *  # noqa: F403
from engine.chain_algorithm import ChainAlgorithm  # noqa: E402

_PRICE_KEYS = (
    "trend_direction", "trend_strength", "higher_tf_trend_direction", "rsi", "macd_hist", "atr_pips",
)


class main(ChainAlgorithm):  # noqa: N801
    """Log `_features()`'s price half once every indicator is ready."""

    strategy_name = "feature_parity"
    log_tag = "PARITY"

    def initialize(self) -> None:
        """One-day EURUSD minute run with the production indicator subscription."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        day = self.get_parameter("day")
        self.set_start_date(int(day[:4]), int(day[4:6]), int(day[6:8]))
        self.set_end_date(int(day[:4]), int(day[4:6]), int(day[6:8]))
        self._symbol = self.add_forex("EURUSD", Resolution.MINUTE, Market.OANDA).symbol  # noqa: F405
        config = load_strategy_chain_config(self.get_parameter("chain_config") or "baseline")
        raw = dict(config.raw)
        settings = self.get_parameter("smoothing")
        if settings:
            raw["double_smoothed_heikin_ashi"] = json.loads(settings)
        self._subscribe_indicators(parse_perception_config(raw))
        self._pnl = PnlWindows()

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Log this bar's decision time and price features."""
        if self._symbol not in data.quote_bars:
            return
        if self._trend_perception is not None:
            self._trend_perception.update(data.quote_bars[self._symbol])
        if not self._indicators_ready():
            return
        features = self._features()
        payload = {key: features[key] for key in _PRICE_KEYS}
        self.debug(f"PARITY|{self.utc_time}|{json.dumps(payload)}")

    def on_end_of_algorithm(self) -> None:
        """Nothing to persist."""
