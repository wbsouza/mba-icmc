"""Offline F7 training-data assembly shared by `scripts/train_{baseline,hybrid}_meta_learner.py`.

Keeps train and serve on one feature definition: every row's features come from
`chain.wiring.price_features` (the same function `engine/chain_algorithm.py` calls live)
over plain-Python re-implementations of LEAN's EMA/RSI/MACD/ATR/Minimum/Maximum and
config-selected DSHA direction features. EMA-based strategies can use complete,
UTC-anchored multi-minute bars. News lookups use the closed bar's decision time
(start + configured duration), matching LEAN rather than looking into its future.
`MarketSignals` supplies the same optional TA-Lib labels and relative quote activity
offline and online. Activity is a separate veto, not an additional F7 feature family.

SMOKE-TEST scope, not a methodology result (docs/technical-debt.md TD-51): the label is
a simple fixed-horizon up/down move over delivered complete bars; market closures
can extend its elapsed duration. Candlesticks are missing only when disabled, while
`news_sentiment_score` remains missing (TD-48), in the same shape as live.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from importlib import metadata
from pathlib import Path

from algo_core import layout
from algo_core.bars import QuoteBar
from algo_core.instrument import Instrument
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path

from algo_backtest.chain.filters.f3_pattern import PatternConfig
from algo_backtest.chain.filters.f7_meta_learner import TrainedMetaLearner, TrainingRow
from algo_backtest.chain.filters.f7_model_io import dump_model
from algo_backtest.chain.filters.volume_strength import VolumeConfig
from algo_backtest.chain.market_signals import MarketSignals
from algo_backtest.chain.price_features import PriceFeatureConfig, warmup_bars
from algo_backtest.chain.wiring import price_features
from algo_backtest.market_hours import exchange_time, lean_delivers
from algo_backtest.months import BAR_DURATION, months_between
from algo_backtest.perception.bar_clock import aggregate_closed_bars
from algo_backtest.perception.config import PerceptionConfig
from algo_backtest.perception.heikin_ashi import OHLC
from algo_backtest.perception.offline import OfflineMultiTimeframeHeikinAshi

_RSI_NEUTRAL = 50.0
_MANIFEST_PACKAGES = ("lightgbm", "scikit-learn", "numpy", "pyarrow", "TA-Lib")


def mid(bar: QuoteBar) -> float:
    """Bid/ask close midpoint — LEAN's `Security.price` for a forex quote bar."""
    return (bar.bid_close + bar.ask_close) / 2.0


def _smoothed_series(values: Sequence[float], period: int, k: float) -> list[float]:
    """A running SMA until `period` samples, then `value * k + previous * (1 - k)`.

    The seeding LEAN's `ExponentialMovingAverage` and `WilderMovingAverage` share; only
    the smoothing constant `k` differs.
    """
    out: list[float] = []
    total = 0.0
    for i, value in enumerate(values):
        if i < period:
            total += value
            out.append(total / (i + 1))
        else:
            out.append(value * k + out[-1] * (1 - k))
    return out


def ema_series(values: Sequence[float], period: int) -> list[float]:
    """LEAN's `ExponentialMovingAverage`: a running SMA until `period` samples, then EMA.

    Seeding matters for train/serve parity: an EMA seeded on the first value instead
    differs from LEAN's by ~1e-4 on the 60-period HTF EMA for hours, enough to flip
    `higher_tf_trend_direction` (proven by `feature_parity.feature`).
    """
    return _smoothed_series(values, period, 2.0 / (period + 1))


def _true_range(bar: QuoteBar, previous_close: float | None) -> float:
    """LEAN's `AverageTrueRange.ComputeTrueRange` on mid prices: high - low on the first
    bar, else the largest of high - low, |high - previous close|, |low - previous close|."""
    high = (bar.bid_high + bar.ask_high) / 2.0
    low = (bar.bid_low + bar.ask_low) / 2.0
    if previous_close is None:
        return high - low
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def atr_series(bars: Sequence[QuoteBar], period: int) -> list[float]:
    """Wilder's ATR per bar, exactly as LEAN's `AverageTrueRange(period, WILDERS)` (in price units).

    True ranges come from bid/ask-midpoint high/low/close (a LEAN forex `QuoteBar`'s
    `High`/`Low`/`Close`, as `mid()` is its `Close`); the smoother is LEAN's Wilder
    moving average — the simple mean of the first `period` true ranges, then
    `(tr + (period - 1) * previous) / period`. Ready after `period` bars, since the
    first true range needs no previous close; `price_features.warmup_bars` relies on that.
    """
    ranges: list[float] = []
    previous_close: float | None = None
    for bar in bars:
        ranges.append(_true_range(bar, previous_close))
        previous_close = mid(bar)
    return _smoothed_series(ranges, period, 1.0 / period)


def _mid_low(bar: QuoteBar) -> float:
    """Bid/ask low midpoint — a LEAN forex `QuoteBar.Low` (`Field.LOW`)."""
    return (bar.bid_low + bar.ask_low) / 2.0


def _mid_high(bar: QuoteBar) -> float:
    """Bid/ask high midpoint — a LEAN forex `QuoteBar.High` (`Field.HIGH`)."""
    return (bar.bid_high + bar.ask_high) / 2.0


def swing_levels(bars: Sequence[QuoteBar], lookback: int) -> list[tuple[float, float]]:
    """Per bar, (lowest mid low, highest mid high) over the last `lookback` bars, that bar included.

    LEAN's `Minimum(lookback)` over `Field.LOW` and `Maximum(lookback)` over
    `Field.HIGH`: both are rolling windows that include the current bar and, before
    `lookback` bars have arrived, span whatever has (those bars are inside
    `price_features.warmup_bars` and never become rows).
    """
    lows = [_mid_low(bar) for bar in bars]
    highs = [_mid_high(bar) for bar in bars]
    return [
        (min(lows[max(0, i + 1 - lookback) : i + 1]), max(highs[max(0, i + 1 - lookback) : i + 1]))
        for i in range(len(bars))
    ]


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    """Match LEAN's Math.Round(nonnegative AverageLoss, 10) == 0 overflow guard.

    The half-even rounding boundary is inclusive at 5e-11. Python's binary
    round(5e-11, 10) rounds upward, so use the equivalent nonnegative interval.
    """
    return 100.0 if avg_loss <= 5e-11 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def rsi_series(values: Sequence[float], period: int) -> list[float]:
    """Wilder's RSI, neutral (50.0) until `period` bars have accumulated."""
    out = [_RSI_NEUTRAL] * len(values)
    if len(values) <= period:
        return out
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(delta, 0.0) for delta in deltas]
    losses = [max(-delta, 0.0) for delta in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def macd_hist_series(values: Sequence[float], periods: PriceFeatureConfig) -> list[float]:
    """LEAN's MACD histogram: (fast EMA - slow EMA) minus its signal-line EMA.

    As in LEAN, the signal EMA only starts consuming the MACD line once the slow EMA is
    ready (its `macd_slow`-th sample); before that the histogram is 0.0 — those bars are
    inside `warmup_bars(periods)` and never become rows.
    """
    fast = ema_series(values, periods.macd_fast)
    slow = ema_series(values, periods.macd_slow)
    line = [f - s for f, s in zip(fast, slow, strict=True)]
    ready = periods.macd_slow - 1
    signal = ema_series(line[ready:], periods.macd_signal)
    histogram = [m - s for m, s in zip(line[ready:], signal, strict=True)]
    return [0.0] * min(ready, len(line)) + histogram


def price_partitions(data_root: Path, instrument: Instrument, start: date, end: date) -> list[Path]:
    """The m1 price partitions an inclusive [start, end] window reads, in month order."""
    return [
        layout.price_path_for(data_root, instrument, "m1", year, month)
        for year, month in months_between(start, end)
    ]


def event_partitions(data_root: Path, start: date, end: date) -> list[Path]:
    """The GDELT event-feature partitions an inclusive [start, end] window reads."""
    return [
        event_feature_path(data_root, "gdelt", year, month)
        for year, month in months_between(start, end)
    ]


def _require(paths: Sequence[Path], remediation: str) -> None:
    """Fail fast, naming every missing partition — a mid-window gap shifts the split."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise ValueError(f"missing Parquet partitions {missing} — {remediation}")


def load_m1_bars(data_root: Path, instrument: Instrument, start: date, end: date) -> list[QuoteBar]:
    """Every m1 bar of the inclusive [start, end] window, sorted by timestamp.

    Raises:
        ValueError: if any touched month's price partition is missing.
    """
    paths = price_partitions(data_root, instrument, start, end)
    _require(paths, "download/transform those months first")
    bars = [
        bar
        for path in paths
        for bar in ParquetRepository(QuoteBar, path).read_all()
        if start <= bar.timestamp.date() <= end
    ]
    return sorted(bars, key=lambda bar: bar.timestamp)


def load_event_intensity(data_root: Path, start: date, end: date) -> dict[datetime, float]:
    """The real GDELT event-intensity feature for the window, keyed by minute.

    Raises:
        ValueError: if any touched month's event-feature partition has not been built.
    """
    paths = event_partitions(data_root, start, end)
    _require(paths, f"build them first: `algo-score events --kind gdelt --from {start} --to {end}`")
    return {
        row.timestamp: row.event_intensity
        for path in paths
        for row in ParquetRepository(GdeltFeature, path).read_all()
        if row.event_intensity is not None
    }


def _news_features(
    event_intensity: Mapping[datetime, float], decision_time: datetime
) -> dict[str, object]:
    """The NEWS family inputs as of `decision_time`; sentiment is always missing (TD-48)."""
    intensity = event_intensity.get(decision_time)
    if intensity is None:
        raise ValueError(
            f"no GDELT event_intensity at decision time {decision_time!r} — the event-feature "
            "partitions do not cover this minute; rebuild them via `algo-score events --kind gdelt`"
        )
    return {"news_event_intensity": intensity, "news_sentiment_score": None}


def lean_bar_stream(bars: Sequence[QuoteBar]) -> list[QuoteBar]:
    """The minute bars LEAN's `on_data` (and its indicators) would see for `bars`.

    Time-ordered, only minutes the exchange is open (`market_hours.lean_delivers`),
    and every open minute between the first and last bar present: a minute missing
    from the data is filled forward as a clone of the previous bar, as LEAN does.
    """
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    if not ordered:
        return []
    by_minute = {bar.timestamp: bar for bar in ordered}
    stream: list[QuoteBar] = []
    minute, last = ordered[0].timestamp, ordered[-1].timestamp
    while minute <= last:
        if lean_delivers(minute):
            bar = by_minute.get(minute)
            if bar is None and stream:
                bar = _filled_forward(stream[-1], minute)
            if bar is not None:
                stream.append(bar)
        minute += BAR_DURATION
    return stream


def _filled_forward(previous: QuoteBar, minute: datetime) -> QuoteBar:
    """`previous` re-stamped at `minute` with zero volume — LEAN's fill-forward bar.

    LEAN's `FillForwardEnumerator` emits `previous.Clone(fillForward=True)`: the whole
    bid/ask open/high/low/close carries over and only the sizes are zeroed. Flattening
    the bar to the previous close would zero the ATR's true range on every filled minute.
    """
    return QuoteBar(
        timestamp=minute,
        bid_open=previous.bid_open, bid_high=previous.bid_high,
        bid_low=previous.bid_low, bid_close=previous.bid_close,
        ask_open=previous.ask_open, ask_high=previous.ask_high,
        ask_low=previous.ask_low, ask_close=previous.ask_close,
        tick_count=0,
    )


def _perception_features(
    bars: Sequence[QuoteBar], perception: PerceptionConfig
) -> list[dict[str, float] | None]:
    """Update every delivered bar, retaining only ready, closed-bucket directions."""
    if perception.source == "ema":
        return [{} for _ in bars]
    indicator = OfflineMultiTimeframeHeikinAshi(
        perception.period1, perception.period2, perception.higher_tf_minutes
    )
    features = []
    for bar in bars:
        candle = OHLC(
            (bar.bid_open + bar.ask_open) / 2,
            (bar.bid_high + bar.ask_high) / 2,
            (bar.bid_low + bar.ask_low) / 2,
            (bar.bid_close + bar.ask_close) / 2,
        )
        indicator.update(exchange_time(bar.timestamp), candle)
        features.append(indicator.features() if indicator.is_ready else None)
    return features


def build_training_rows(
    bars: Sequence[QuoteBar], event_intensity: Mapping[datetime, float] | None = None,
    *, instrument: Instrument,
    perception: PerceptionConfig | None = None,
    price_features_config: PriceFeatureConfig | None = None,
    horizon_minutes: int = 15,
    pattern_config: PatternConfig | None = None,
    volume_config: VolumeConfig | None = None,
) -> list[TrainingRow]:
    """Labeled `TrainingRow`s from m1 bars (+ NEWS features when given).

    Rows are built over `lean_bar_stream(bars)` — the exact bar sequence the live
    algorithm's LEAN indicators consume — so indicator state, warm-up and the label
    horizon (counted in delivered bars) match the backtest.

    Label: 1 if the mid price is strictly higher `horizon_minutes / bar_minutes`
    complete decision bars later, else 0
    (flat is 0). `label_time` is the close of that horizon bar, so
    `walk_forward_split` can purge rows whose label reaches into the next span. The
    first `warmup_bars(price_features_config)` bars and any additional DSHA warm-up bars
    yield no row, matching live readiness. The last horizon's bars have no label.
    Perception, the indicator periods and the horizon come from the strategy config
    (`config.perception`, `config.price_features`, `config.f7.label_horizon_minutes`);
    omitted means the documented defaults. `instrument` supplies the pip
    (`Instrument.unit_size`: 0.0001 on a 5-digit pair, 0.01 on a JPY pair — the value
    the live side derives from LEAN's minimum price variation) that scales the row's
    `atr_pips`, `swing_low_pips` and `swing_high_pips`; it is required so no pip is ever
    assumed.
    """
    periods = price_features_config or PriceFeatureConfig()
    horizon_bars = _horizon_bars(horizon_minutes, periods.bar_minutes)
    bars = _training_bars(bars, periods, perception)
    signals = MarketSignals(pattern_config, volume_config)
    signal_features = [signals.update(bar) for bar in bars]
    duration = timedelta(minutes=periods.bar_minutes)
    directions = _perception_features(bars, perception or PerceptionConfig())
    prices = [mid(bar) for bar in bars]
    fast = ema_series(prices, periods.ema_fast)
    slow = ema_series(prices, periods.ema_slow)
    htf = ema_series(prices, periods.ema_higher_tf)
    rsi = rsi_series(prices, periods.rsi_period)
    macd = macd_hist_series(prices, periods)
    atr = atr_series(bars, periods.atr_period)
    swings = swing_levels(bars, periods.swing_lookback_bars)
    pip = instrument.unit_size
    rows: list[TrainingRow] = []
    for i in range(warmup_bars(periods), len(bars) - horizon_bars):
        direction = directions[i]
        if direction is None:
            continue
        features = price_features(
            price=prices[i],
            ema_fast=fast[i],
            ema_slow=slow[i],
            ema_htf=htf[i],
            rsi=rsi[i],
            macd_hist=macd[i],
            atr_pips=atr[i] / pip,
            swing_low_pips=(prices[i] - swings[i][0]) / pip,
            swing_high_pips=(swings[i][1] - prices[i]) / pip,
        )
        features.update(direction)
        features.update(signal_features[i])
        if event_intensity is not None:
            features |= _news_features(event_intensity, bars[i].timestamp + duration)
        horizon = i + horizon_bars
        rows.append(
            TrainingRow(
                timestamp=bars[i].timestamp,
                features=features,
                label=1 if prices[horizon] > prices[i] else 0,
                label_time=bars[horizon].timestamp + duration,
            )
        )
    return rows


def _horizon_bars(minutes: int, bar_minutes: int) -> int:
    """Require an explicit whole number of decision bars, rather than silently rounding."""
    if type(minutes) is not int or minutes < bar_minutes or minutes % bar_minutes:
        raise ValueError(
            "label_horizon_minutes must be a positive multiple of bar_minutes; retrain"
        )
    return minutes // bar_minutes


def _training_bars(
    bars: Sequence[QuoteBar], periods: PriceFeatureConfig, perception: PerceptionConfig | None
) -> list[QuoteBar]:
    """Aggregate the delivered minute stream without changing DSHA's minute-only contract."""
    if periods.bar_minutes != 1 and perception is not None and perception.source != "ema":
        raise ValueError("multi-minute decision bars require EMA perception; use M1 for DSHA")
    return aggregate_closed_bars(lean_bar_stream(bars), periods.bar_minutes)


def file_digest(path: Path) -> str:
    """Hex SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_versions() -> dict[str, str]:
    """Installed versions of the packages a persisted model depends on."""
    return {name: metadata.version(name) for name in _MANIFEST_PACKAGES}


def save_model(
    model: TrainedMetaLearner,
    out_path: Path,
    provenance: Mapping[str, object],
    *,
    data_root: Path,
    inputs: Sequence[Path],
    horizon_minutes: int = 15,
) -> None:
    """Persist `model` as a portable JSON document with its training provenance embedded.

    Provenance = the caller's (strategy, symbol, window, split bounds, row counts,
    families, git revision) plus the label horizon, the SHA-256 of every input partition
    (paths relative to `data_root`, so no machine-local path is committed) and the
    training library versions — enough to tell exactly what a committed model was
    trained on and to detect when it no longer matches. See `f7_model_io` for why the
    model itself is not pickled.
    """
    dump_model(
        model,
        out_path,
        {
            **provenance,
            "horizon_minutes": horizon_minutes,
            "inputs": {
                path.relative_to(data_root).as_posix(): file_digest(path) for path in inputs
            },
            "packages": _package_versions(),
        },
    )
