"""Exercise strategy wiring with actual native perception and unrelated account inputs."""
from types import SimpleNamespace

from algo_backtest.engine.chain_algorithm import ChainAlgorithm
from algo_backtest.perception.config import PerceptionConfig
from algo_backtest.perception.multi_timeframe import MultiTimeframeHeikinAshi


def verify_source_wiring(bar):
    """Prove selection, warm-up ordering, readiness gates and isolated direction override."""
    indicator = SimpleNamespace(is_ready=True, current=SimpleNamespace(value=10),
                                signal=SimpleNamespace(current=SimpleNamespace(value=2)))
    receiver = SimpleNamespace(_symbol=bar.symbol,
                               ema=lambda *args: indicator,
                               rsi=lambda *args: indicator,
                               macd=lambda *args: indicator)
    ChainAlgorithm._subscribe_indicators(receiver)
    assert receiver._trend_perception is None
    assert ChainAlgorithm._indicators_ready(receiver)
    indicator.is_ready = False
    assert not ChainAlgorithm._indicators_ready(receiver)
    indicator.is_ready = True
    ChainAlgorithm._subscribe_indicators(receiver, PerceptionConfig(
        source="double_smoothed_heikin_ashi", period1=1, period2=1, higher_tf_minutes=2))
    candidate = receiver._trend_perception
    assert isinstance(candidate, MultiTimeframeHeikinAshi)
    assert not ChainAlgorithm._indicators_ready(receiver)
    receiver._indicators_ready = lambda: ChainAlgorithm._indicators_ready(receiver)
    ChainAlgorithm.on_data(receiver, SimpleNamespace(quote_bars={}))
    assert candidate._primary.samples == 0
    ChainAlgorithm.on_data(receiver, SimpleNamespace(quote_bars={bar.symbol: bar}))
    assert candidate._primary.samples == 1
    assert not ChainAlgorithm._indicators_ready(receiver)
    candidate._higher.update(bar)
    assert ChainAlgorithm._indicators_ready(receiver)
    indicator.is_ready = False
    assert not ChainAlgorithm._indicators_ready(receiver)
    indicator.is_ready = True
    receiver._ema_htf = SimpleNamespace(is_ready=True, current=SimpleNamespace(value=20))
    receiver.securities = {bar.symbol: SimpleNamespace(price=12)}
    receiver.portfolio = SimpleNamespace(invested=False, total_portfolio_value=100000,
        total_unrealized_profit=0, total_holdings_value=0, cash=100000, margin_remaining=100000)
    receiver.time = bar.end_time
    receiver._pnl = SimpleNamespace(update=lambda *args: (0, 0))
    candidate_features = ChainAlgorithm._features(receiver)
    receiver._trend_perception = None
    ema_features = ChainAlgorithm._features(receiver)
    assert candidate_features["trend_direction"] == candidate._primary.direction
    assert candidate_features["higher_tf_trend_direction"] == candidate._higher.direction
    assert candidate_features["trend_direction"] != ema_features["trend_direction"]
    assert candidate_features["higher_tf_trend_direction"] != ema_features["higher_tf_trend_direction"]
    for key in ema_features.keys() - {"trend_direction", "higher_tf_trend_direction"}:
        assert candidate_features[key] == ema_features[key], key
