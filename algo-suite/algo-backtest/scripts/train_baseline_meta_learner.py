"""Offline F7 meta-learner training for the "baseline" strategy chain -- SMOKE TEST ONLY.

Trains and persists (`joblib`) a `TrainedMetaLearner` (per `chain/filters/f7_meta_learner.py`)
so `algos/baseline/main.py` has a model to load inside the LEAN container. This exists to
*exercise* the already-built, already-tested F1-F7 wiring end to end -- it is explicitly
NOT a real methodology result:

  - The real methodology trains F7 on a walk-forward split spanning months/years of data
    (PRD.md Sec 4). This script fits it on whatever short window is passed in (a smoke test
    used a single 7-day window), which is nowhere near enough data for a statistically
    meaningful model -- `walk_forward_split` only requires each span be non-empty and
    contain both label classes, not that the spans be *large enough to mean anything*.
  - Indicators are computed here in plain Python (EMA/RSI/MACD-histogram, a simple
    EMA-gap proxy for "trend strength" in place of a real ADX) directly from the
    canonical minute Parquet, independent of the LEAN container -- `algos/baseline/main.py`
    computes the SAME features live from LEAN's own indicators at backtest time, so this
    script's numbers won't bit-for-bit match a live run, only be the same shape of signal.
  - `candlestick_pattern` (F3's feature) is never populated here (F3 has no real detector
    wired yet -- see `f3_pattern.py`'s own docstring), so the PATTERN family is intentionally
    left out of training, not silently included as an all-missing column.

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

_DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "src" / "algo_backtest" / "algos" / "baseline"
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


def build_training_rows(bars: list[QuoteBar]) -> list[TrainingRow]:
    """Turn raw minute bars into labeled TrainingRows using plain-Python indicator proxies.

    Label: 1 if the mid price is higher `_HORIZON_MINUTES` later, else 0 -- a simple
    fixed-horizon up/down label, not the full methodology's labeling scheme.
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
            # feature build. Included (not omitted) so the PATTERN family below sees the
            # same all-NaN shape at train time it will at inference time (family_vector
            # treats a missing key as NaN either way, but this keeps the two paths
            # visibly, deliberately identical rather than one path omitting the key).
            "candlestick_pattern": None,
        }
        label = 1 if prices[i + _HORIZON_MINUTES] > prices[i] else 0
        rows.append(TrainingRow(timestamp=ordered[i].timestamp, features=features, label=label))
    return rows


def main() -> None:
    """CLI entry point: read materialized minute Parquet, build rows, split, train, persist."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--train-end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--validation-end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--test-end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args()

    instrument = build_instrument(args.symbol)
    price_path = layout.price_path_for(layout.data_root(), instrument, "m1", args.year, args.month)
    bars = ParquetRepository(QuoteBar, price_path).read_all()
    rows = build_training_rows(bars)
    split = walk_forward_split(
        rows,
        train_end=date.fromisoformat(args.train_end),
        validation_end=date.fromisoformat(args.validation_end),
        test_end=date.fromisoformat(args.test_end),
    )
    # All three families config.yaml's meta_learner.families declares (trend, indicator,
    # pattern) -- omitting PATTERN here silently drifted from that declared config
    # (2026-09-26 PR #33 review). PATTERN's vector is all-NaN (no real detector), which
    # LightGBM splits around same as any other missing feature; it does not need to be
    # informative to keep training and the declared config in agreement.
    model = train_meta_learner(
        families=(FeatureFamily.TREND, FeatureFamily.INDICATOR, FeatureFamily.PATTERN),
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
