"""Offline F7 meta-learner training for the "hybrid" strategy chain -- SMOKE TEST ONLY.

Extends `train_baseline_meta_learner.py`'s approach with the NEWS family
(`news_event_intensity`, `news_sentiment_score` -- `f7_meta_learner.py`'s
`FeatureFamily.NEWS`), which `strategies/hybrid/config.yaml`'s `meta_learner.families`
declares and `baseline`'s own script never populates. Trains and persists (`joblib`) a
`TrainedMetaLearner` so `algos/hybrid/main.py` has a model to load inside the LEAN
container. Same explicit non-claims as the baseline script:

  - Not a real methodology result (PRD.md Sec 4's walk-forward split spans months/years;
    this fits on whatever short window is passed in).
  - Indicators are computed here in plain Python, independent of the LEAN container;
    `algos/hybrid/main.py` computes the SAME features live from LEAN's own indicators at
    backtest time, so this script's numbers won't bit-for-bit match a live run.
  - `candlestick_pattern` (F3) is never populated here either -- same gap as baseline.
  - `news_sentiment_score` is never populated here -- real per-article sentiment is
    blocked on TD-48 (the same gap `algos/hybrid/main.py`'s F4NewsContextFilter itself
    degrades to ABSTAIN on). Only `news_event_intensity` (the real, materialized GDELT
    event feature) is a genuine training signal; the NEWS family vector's second
    component is intentionally always-missing, the same documented shape as PATTERN's
    always-missing `candlestick_pattern`, not silently included as if it were real.

Any model this script produces must not be cited as a real Chapter-4 result.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import joblib
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    TrainingRow,
    train_meta_learner,
    walk_forward_split,
)
from algo_core import layout
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path

_DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "src" / "algo_backtest" / "algos" / "hybrid"
    / "f7_meta_learner.joblib"
)
_HORIZON_MINUTES = 15
_EMA_FAST = 3
_EMA_SLOW = 8
_HTF_EMA = 60
_RSI_PERIOD = 14
_MACD_FAST = 12
_MACD_SLOW = 26
_MACD_SIGNAL = 9


def _mid(bar: QuoteBar) -> float:
    """Bid/ask midpoint -- the same price basis F1-F3's real LEAN indicators would use."""
    return (bar.bid_close + bar.ask_close) / 2.0


def _ema_series(values: list[float], period: int) -> list[float]:
    """Standard exponential moving average, seeded on the first value."""
    k = 2.0 / (period + 1)
    out: list[float] = []
    prev = values[0]
    for value in values:
        prev = value * k + prev * (1 - k)
        out.append(prev)
    return out


def _rsi_series(values: list[float], period: int) -> list[float]:
    """Wilder's RSI, seeded at 50.0 (neutral) until `period` bars have accumulated."""
    out = [50.0] * len(values)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    if len(values) <= period:
        return out
    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def _macd_hist_series(values: list[float]) -> list[float]:
    """MACD histogram: (fast EMA - slow EMA) minus its own signal-line EMA."""
    ema_fast, ema_slow = _ema_series(values, _MACD_FAST), _ema_series(values, _MACD_SLOW)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow, strict=True)]
    signal = _ema_series(macd_line, _MACD_SIGNAL)
    return [m - s for m, s in zip(macd_line, signal, strict=True)]


def _load_event_intensity(data_root: Path, year: int, month: int) -> dict[object, float]:
    """Read one month's real GDELT event-intensity feature Parquet as a timestamp index.

    Raises:
        ValueError: if the month's feature Parquet has not been built yet -- fail fast
            with the exact remediation command, mirroring f4_news_context.py's own
            "missing partition" error for the same file.
    """
    path = event_feature_path(data_root, "gdelt", year, month)
    if not path.exists():
        raise ValueError(
            f"missing real GDELT event-feature Parquet at {path} — build it first: "
            f"`algo-score events --kind gdelt --month {year:04d}-{month:02d}`"
        )
    rows = ParquetRepository(GdeltFeature, path).read_all()
    return {row.timestamp: row.event_intensity for row in rows if row.event_intensity is not None}


def build_training_rows(
    bars: list[QuoteBar], event_intensity: dict[object, float]
) -> list[TrainingRow]:
    """Turn raw minute bars + real GDELT event intensity into labeled TrainingRows.

    Label: 1 if the mid price is higher `_HORIZON_MINUTES` later, else 0 -- a simple
    fixed-horizon up/down label, not the full methodology's labeling scheme. Raises
    (via dict lookup) if a bar's timestamp is uncovered by `event_intensity` -- the same
    fail-fast contract F4's own `_event_intensity_at` enforces at backtest time, so a
    training run and a live run demand the same coverage rather than one silently
    tolerating gaps the other would reject.
    """
    ordered = sorted(bars, key=lambda b: b.timestamp)
    prices = [_mid(b) for b in ordered]
    ema_fast = _ema_series(prices, _EMA_FAST)
    ema_slow = _ema_series(prices, _EMA_SLOW)
    ema_htf = _ema_series(prices, _HTF_EMA)
    rsi = _rsi_series(prices, _RSI_PERIOD)
    macd_hist = _macd_hist_series(prices)

    rows: list[TrainingRow] = []
    for i in range(len(ordered) - _HORIZON_MINUTES):
        if ema_fast[i] > ema_slow[i]:
            trend_direction = 1.0
        elif ema_fast[i] < ema_slow[i]:
            trend_direction = -1.0
        else:
            trend_direction = 0.0
        trend_strength = min(abs(ema_fast[i] - ema_slow[i]) / prices[i] * 10_000.0, 100.0)
        higher_tf_trend_direction = (
            1.0 if prices[i] > ema_htf[i] else (-1.0 if prices[i] < ema_htf[i] else 0.0)
        )
        features = {
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "higher_tf_trend_direction": higher_tf_trend_direction,
            "rsi": rsi[i],
            "macd_hist": macd_hist[i],
            # No real candlestick detector -- always missing, same as main.py's live
            # feature build (mirrors train_baseline_meta_learner.py's own reasoning).
            "candlestick_pattern": None,
            "news_event_intensity": event_intensity[ordered[i].timestamp],
            # No real per-article sentiment materialized yet (TD-48) -- always missing,
            # the NEWS family's second component, same "deliberately missing, not
            # silently included" shape as candlestick_pattern above.
            "news_sentiment_score": None,
        }
        label = 1 if prices[i + _HORIZON_MINUTES] > prices[i] else 0
        rows.append(TrainingRow(timestamp=ordered[i].timestamp, features=features, label=label))
    return rows


def main() -> None:
    """CLI entry point: read materialized minute + GDELT Parquet, build rows, split, train."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--train-end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--validation-end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--test-end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args()

    data_root = layout.data_root()
    instrument = build_instrument(args.symbol)
    price_path = layout.price_path_for(data_root, instrument, "m1", args.year, args.month)
    bars = ParquetRepository(QuoteBar, price_path).read_all()
    event_intensity = _load_event_intensity(data_root, args.year, args.month)
    rows = build_training_rows(bars, event_intensity)
    split = walk_forward_split(
        rows,
        train_end=date.fromisoformat(args.train_end),
        validation_end=date.fromisoformat(args.validation_end),
        test_end=date.fromisoformat(args.test_end),
    )
    # Four families, matching strategies/hybrid/config.yaml's meta_learner.families
    # exactly (baseline's own script covers the first three only -- 2026-09-26 PR #33
    # review already flagged a train/config family-list drift once; kept in agreement
    # here deliberately).
    model = train_meta_learner(
        families=(
            FeatureFamily.TREND,
            FeatureFamily.INDICATOR,
            FeatureFamily.PATTERN,
            FeatureFamily.NEWS,
        ),
        split=split,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    print(
        f"rows={len(rows)} train={len(split.train)} validation={len(split.validation)} "
        f"test={len(split.test)}"
    )
    print(f"model_saved={out_path}")


if __name__ == "__main__":
    main()
