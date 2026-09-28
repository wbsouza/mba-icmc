"""Causal candlestick context over bounded closed bars (Story 22, T4; Story 23, T3).

Produces separately typed context evidence (CND-06) from the retained closed bars
only: the T-line EMA(8) seeded like ``training.ema_series`` (running mean until the
period, then exponential), the stochastic 12,3,3 with simple smoothing and strict
80/20 zones, simple-moving-average levels with the dimensionless distance
``(close - sma) / sma`` and the trend derived from the T-line position. Every
indicator reports its own readiness (CND-04); a zero-range stochastic window is
UNDEFINED rather than NaN. Values are recomputed from the retained window (at most
256 bars), so evidence at a bar never depends on later bars (CND-05); with k = 2/9
the weight of any bar older than the window is below 1e-27. Story 23 adds an opt-in
Fibonacci retracement confluence field (BEXT-07..10): the causal swing high/low over
``fibonacci_lookback_bars`` anchors 38.2/50/61.8% retracement levels, UNDEFINED on a
zero-range swing, WARMUP before the lookback is satisfied, and absent (``None``)
whenever ``ContextConfig.fibonacci_enabled`` is ``False`` so every other field stays
byte-identical to Story 22. Pure: no chain, engine or LEAN dependency.
"""

from __future__ import annotations

from collections.abc import Sequence

from algo_backtest.perception.candle_contract import (
    FIBONACCI_LEVELS,
    READY,
    UNDEFINED,
    WARMUP,
    CandleConfig,
    CandleHistory,
    ClosedBar,
    ContextConfig,
    ContextEvidence,
    FibonacciEvidence,
    IndicatorValue,
    LevelEvidence,
    StochasticEvidence,
)

_WARMING = IndicatorValue(None, WARMUP)
_UNDEFINED_VALUE = IndicatorValue(None, UNDEFINED)
FIB_TOLERANCE_RATIO = 0.10


def ema_value(closes: Sequence[float], period: int) -> IndicatorValue:
    """EMA(period) of ``closes`` seeded with the running mean of the first ``period`` closes."""
    if len(closes) < period:
        return _WARMING
    k = 2.0 / (period + 1)
    value = sum(closes[:period]) / period
    for close in closes[period:]:
        value = close * k + value * (1 - k)
    return IndicatorValue(value, READY)


def _raw_k(bars: Sequence[ClosedBar], end: int, period: int) -> IndicatorValue:
    """Raw %K of the bar at index ``end`` over the ``period`` bars ending there."""
    if end + 1 < period:
        return _WARMING
    window = bars[end + 1 - period : end + 1]
    highest, lowest = max(bar.high for bar in window), min(bar.low for bar in window)
    if highest == lowest:
        return _UNDEFINED_VALUE
    return IndicatorValue(100.0 * (bars[end].close - lowest) / (highest - lowest), READY)


def _smoothed(values: Sequence[IndicatorValue], length: int) -> IndicatorValue:
    """Simple mean of the last ``length`` readings; WARMUP or UNDEFINED propagates."""
    if len(values) < length:
        return _WARMING
    tail = values[-length:]
    if any(value.status == WARMUP for value in tail):
        return _WARMING
    if any(value.status == UNDEFINED for value in tail):
        return _UNDEFINED_VALUE
    return IndicatorValue(sum(v.value for v in tail if v.value is not None) / length, READY)


def stochastic_evidence(bars: Sequence[ClosedBar], config: ContextConfig) -> StochasticEvidence:
    """Raw %K, slow %K = SMA(k_smooth) of raw, %D = SMA(d) of slow, and the %D zone."""
    span = config.stochastic_k_smooth + config.stochastic_d - 1
    first = max(0, len(bars) - span)
    raws = [_raw_k(bars, end, config.stochastic_k) for end in range(first, len(bars))]
    slows = [_smoothed(raws[: index + 1], config.stochastic_k_smooth) for index in range(len(raws))]
    raw = raws[-1] if raws else _WARMING
    slow = slows[-1] if slows else _WARMING
    d = _smoothed(slows, config.stochastic_d)
    return StochasticEvidence(raw, slow, d, _zone(d, config))


def _zone(d: IndicatorValue, config: ContextConfig) -> str:
    """OVERBOUGHT above the upper level, OVERSOLD below the lower one, else NEUTRAL."""
    if d.value is None:
        return UNDEFINED
    if d.value > config.overbought:
        return "OVERBOUGHT"
    if d.value < config.oversold:
        return "OVERSOLD"
    return "NEUTRAL"


def level_evidence(closes: Sequence[float], period: int) -> LevelEvidence:
    """SMA(period) of the closes and the normalized distance of the last close to it."""
    if len(closes) < period:
        return LevelEvidence(period, _WARMING, None)
    sma = sum(closes[-period:]) / period
    return LevelEvidence(period, IndicatorValue(sma, READY), (closes[-1] - sma) / sma)


def _t_line_position(close: float, ema: IndicatorValue) -> str:
    """ABOVE, BELOW or ON the T-line; WARMUP while the EMA warms up."""
    if ema.value is None:
        return WARMUP
    if close > ema.value:
        return "ABOVE"
    if close < ema.value:
        return "BELOW"
    return "ON"


_TREND = {"ABOVE": "UP", "BELOW": "DOWN", "ON": "FLAT", WARMUP: WARMUP}


def fibonacci_evidence(bars: Sequence[ClosedBar], config: ContextConfig) -> FibonacciEvidence:
    """Retracement confluence between the causal swing high and low (BEXT-07..09).

    The swing is the max high / min low over the last ``fibonacci_lookback_bars`` closed
    bars, ending at the evaluated bar. Whichever extreme occurred more recently (a tie
    resolves to the high) fixes the leg: the high more recent means a rising leg (levels
    descend from the high), the low more recent means a falling leg (levels ascend from
    the low). ``level`` is the nearest ratio the close is within tolerance of, or
    ``None``.
    """
    lookback = config.fibonacci_lookback_bars
    if len(bars) < lookback:
        return FibonacciEvidence(_WARMING, _WARMING, None, WARMUP)
    window = bars[-lookback:]
    high = max(bar.high for bar in window)
    low = min(bar.low for bar in window)
    swing_high, swing_low = IndicatorValue(high, READY), IndicatorValue(low, READY)
    if high == low:
        return FibonacciEvidence(swing_high, swing_low, None, UNDEFINED)
    high_index = max(index for index, bar in enumerate(window) if bar.high == high)
    low_index = max(index for index, bar in enumerate(window) if bar.low == low)
    rising = high_index >= low_index
    current = bars[-1]
    tolerance = FIB_TOLERANCE_RATIO * (current.high - current.low)
    level: float | None = None
    best_distance: float | None = None
    for ratio in FIBONACCI_LEVELS:
        price = high - ratio * (high - low) if rising else low + ratio * (high - low)
        distance = abs(current.close - price)
        if distance <= tolerance and (best_distance is None or distance < best_distance):
            level, best_distance = ratio, distance
    return FibonacciEvidence(swing_high, swing_low, level, READY)


def evaluate_context(bars: Sequence[ClosedBar], config: ContextConfig) -> ContextEvidence:
    """Context evidence for the final bar of ``bars`` (validated, oldest first, non-empty)."""
    closes = [bar.close for bar in bars]
    ema = ema_value(closes, config.ema_period)
    position = _t_line_position(closes[-1], ema)
    stochastic = stochastic_evidence(bars, config)
    levels = tuple(level_evidence(closes, period) for period in config.sma_periods)
    statuses = [ema.status, stochastic.raw_k.status, stochastic.slow_k.status, stochastic.d.status]
    statuses.extend(level.sma.status for level in levels)
    fibonacci = fibonacci_evidence(bars, config) if config.fibonacci_enabled else None
    if fibonacci is not None:
        statuses.append(fibonacci.status)
    return ContextEvidence(
        close_time=bars[-1].close_time,
        history_count=len(bars),
        ema=ema,
        t_line_position=position,
        stochastic=stochastic,
        levels=levels,
        trend=_TREND[position],
        status=WARMUP if WARMUP in statuses else READY,
        fibonacci=fibonacci,
    )


class ContextEvaluator:
    """Streaming context evaluator bound to a validated, bounded closed-bar history."""

    def __init__(self, config: CandleConfig) -> None:
        """Bind the configuration; indicator parameters come from ``config.context``."""
        self._config = config
        self._history = CandleHistory(config)

    @property
    def history(self) -> CandleHistory:
        """The bounded validated history behind the evaluator."""
        return self._history

    def update(self, bar: ClosedBar) -> ContextEvidence:
        """Consume one closed bar and report its context; invalid input raises first."""
        self._history.offer(bar)
        return evaluate_context(self._history.bars, self._config.context)
