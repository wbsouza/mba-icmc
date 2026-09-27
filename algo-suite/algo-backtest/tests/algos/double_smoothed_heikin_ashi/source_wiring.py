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
    observed = {"ema_selected": receiver._trend_perception is None,
                "ema_ready": ChainAlgorithm._indicators_ready(receiver)}
    indicator.is_ready = False
    observed["ema_unready"] = ChainAlgorithm._indicators_ready(receiver)
    indicator.is_ready = True
    ChainAlgorithm._subscribe_indicators(receiver, PerceptionConfig(
        source="double_smoothed_heikin_ashi", period1=1, period2=1, higher_tf_minutes=2))
    candidate = receiver._trend_perception
    observed["candidate_selected"] = isinstance(candidate, MultiTimeframeHeikinAshi)
    observed["candidate_initial_ready"] = ChainAlgorithm._indicators_ready(receiver)
    receiver._indicators_ready = lambda: ChainAlgorithm._indicators_ready(receiver)
    ChainAlgorithm.on_data(receiver, SimpleNamespace(quote_bars={}))
    observed["empty_samples"] = candidate._primary.samples
    ChainAlgorithm.on_data(receiver, SimpleNamespace(quote_bars={bar.symbol: bar}))
    observed["first_samples"] = candidate._primary.samples
    observed["primary_only_ready"] = ChainAlgorithm._indicators_ready(receiver)
    candidate._higher.update(bar)
    observed["both_ready"] = ChainAlgorithm._indicators_ready(receiver)
    indicator.is_ready = False
    observed["other_indicator_unready"] = ChainAlgorithm._indicators_ready(receiver)
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
    observed.update(candidate_features=candidate_features, ema_features=ema_features,
                    primary_direction=candidate._primary.direction,
                    higher_direction=candidate._higher.direction)
    return observed
