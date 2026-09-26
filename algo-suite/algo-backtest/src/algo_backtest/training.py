"""Offline F7 training-data assembly shared by `scripts/train_{baseline,hybrid}_meta_learner.py`.

Keeps train and serve on one feature definition: every row's features come from
`chain.wiring.price_features` (the same function `engine/chain_algorithm.py` calls live)
over plain-Python re-implementations of LEAN's EMA/RSI/MACD, and news lookups are keyed
on the bar's *decision time* (bar start + one minute), which is what LEAN's `self.time`
is inside `on_data` — so a feature never sees a later value at train time than it would
at backtest time.

SMOKE-TEST scope, not a methodology result (docs/technical-debt.md TD-51): the label is
a simple fixed-horizon up/down move, and `candlestick_pattern`/`news_sentiment_score`
are always missing (no detector; TD-48) — deliberately, in the same shape as live.
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

from algo_backtest.chain.filters.f7_meta_learner import TrainedMetaLearner, TrainingRow
from algo_backtest.chain.filters.f7_model_io import dump_model
from algo_backtest.chain.wiring import (
    EMA_FAST_PERIOD,
    EMA_HTF_PERIOD,
    EMA_SLOW_PERIOD,
    MACD_FAST_PERIOD,
    MACD_SIGNAL_PERIOD,
    MACD_SLOW_PERIOD,
    RSI_PERIOD,
    price_features,
)
from algo_backtest.market_hours import lean_delivers
from algo_backtest.months import months_between

HORIZON_MINUTES = 15
# Bars before every LEAN indicator the features read is ready (EMA 60 needs 60 samples,
# MACD 26/9 needs 34, Wilder RSI 14 needs 15): the live algorithm skips them, so
# training does too — they would be rows the model is never asked to score.
WARMUP_BARS = max(EMA_HTF_PERIOD, MACD_SLOW_PERIOD + MACD_SIGNAL_PERIOD - 1, RSI_PERIOD + 1) - 1
BAR_DURATION = timedelta(minutes=1)
_RSI_NEUTRAL = 50.0
_MANIFEST_PACKAGES = ("lightgbm", "scikit-learn", "numpy", "pyarrow")


def mid(bar: QuoteBar) -> float:
    """Bid/ask close midpoint — LEAN's `Security.price` for a forex quote bar."""
    return (bar.bid_close + bar.ask_close) / 2.0


def ema_series(values: Sequence[float], period: int) -> list[float]:
    """LEAN's `ExponentialMovingAverage`: a running SMA until `period` samples, then EMA.

    Seeding matters for train/serve parity: an EMA seeded on the first value instead
    differs from LEAN's by ~1e-4 on the 60-period HTF EMA for hours, enough to flip
    `higher_tf_trend_direction` (proven by `feature_parity.feature`).
    """
    k = 2.0 / (period + 1)
    out: list[float] = []
    total = 0.0
    for i, value in enumerate(values):
        if i < period:
            total += value
            out.append(total / (i + 1))
        else:
            out.append(value * k + out[-1] * (1 - k))
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    """RSI from Wilder-smoothed average gain/loss."""
    return 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


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


def macd_hist_series(values: Sequence[float]) -> list[float]:
    """LEAN's MACD histogram: (fast EMA - slow EMA) minus its signal-line EMA.

    As in LEAN, the signal EMA only starts consuming the MACD line once the slow EMA is
    ready (its `MACD_SLOW_PERIOD`-th sample); before that the histogram is 0.0 — those
    bars are inside `WARMUP_BARS` and never become rows.
    """
    fast = ema_series(values, MACD_FAST_PERIOD)
    slow = ema_series(values, MACD_SLOW_PERIOD)
    line = [f - s for f, s in zip(fast, slow, strict=True)]
    ready = MACD_SLOW_PERIOD - 1
    signal = ema_series(line[ready:], MACD_SIGNAL_PERIOD)
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
    from the data is filled forward from the previous bar's close, as LEAN does.
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
    """A flat bar at `minute` carrying `previous`'s closing quotes (LEAN fill-forward)."""
    return QuoteBar(
        timestamp=minute,
        bid_open=previous.bid_close, bid_high=previous.bid_close,
        bid_low=previous.bid_close, bid_close=previous.bid_close,
        ask_open=previous.ask_close, ask_high=previous.ask_close,
        ask_low=previous.ask_close, ask_close=previous.ask_close,
        tick_count=0,
    )


def build_training_rows(
    bars: Sequence[QuoteBar], event_intensity: Mapping[datetime, float] | None = None
) -> list[TrainingRow]:
    """Labeled `TrainingRow`s from m1 bars (+ NEWS features when given).

    Rows are built over `lean_bar_stream(bars)` — the exact bar sequence the live
    algorithm's LEAN indicators consume — so indicator state, warm-up and the label
    horizon (counted in delivered bars) match the backtest.

    Label: 1 if the mid price is strictly higher `HORIZON_MINUTES` bars later, else 0
    (flat is 0). `label_time` is the close of that horizon bar, so
    `walk_forward_split` can purge rows whose label reaches into the next span. The
    first `WARMUP_BARS` bars (the live algorithm never decides before its LEAN
    indicators are ready) and the last `HORIZON_MINUTES` bars (no label) yield no row.
    """
    bars = lean_bar_stream(bars)
    prices = [mid(bar) for bar in bars]
    fast = ema_series(prices, EMA_FAST_PERIOD)
    slow = ema_series(prices, EMA_SLOW_PERIOD)
    htf = ema_series(prices, EMA_HTF_PERIOD)
    rsi = rsi_series(prices, RSI_PERIOD)
    macd = macd_hist_series(prices)
    rows: list[TrainingRow] = []
    for i in range(WARMUP_BARS, len(bars) - HORIZON_MINUTES):
        features = price_features(
            price=prices[i],
            ema_fast=fast[i],
            ema_slow=slow[i],
            ema_htf=htf[i],
            rsi=rsi[i],
            macd_hist=macd[i],
        )
        if event_intensity is not None:
            features |= _news_features(event_intensity, bars[i].timestamp + BAR_DURATION)
        horizon = i + HORIZON_MINUTES
        rows.append(
            TrainingRow(
                timestamp=bars[i].timestamp,
                features=features,
                label=1 if prices[horizon] > prices[i] else 0,
                label_time=bars[horizon].timestamp + BAR_DURATION,
            )
        )
    return rows


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
            "horizon_minutes": HORIZON_MINUTES,
            "inputs": {
                path.relative_to(data_root).as_posix(): file_digest(path) for path in inputs
            },
            "packages": _package_versions(),
        },
    )
