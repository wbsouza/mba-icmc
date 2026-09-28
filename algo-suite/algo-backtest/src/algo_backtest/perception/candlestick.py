"""Causal TA-Lib shapes over closed midpoint candles; no LEAN or IO dependency.

Uses the library's default candle settings (no process-global overrides). These
are shape recognizers, not independent trend confirmation or trading signals.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from math import isfinite
from numbers import Integral, Real

import numpy as np

from algo_backtest.perception.heikin_ashi import OHLC

# Fixed vocabulary consumed by F3 and F7. Priority is lexical within one polarity;
# opposing detections abstain instead of choosing the most convenient direction.
PATTERN_POLARITY = {
    "bullish_engulfing": 1,
    "hammer": 1,
    "morning_star": 1,
    "bearish_engulfing": -1,
    "shooting_star": -1,
    "evening_star": -1,
}
_HISTORY_SIZE = 64
_STAR_PENETRATION = 0.3


def _validate_detection(name: str, value: int) -> None:
    """Reject unsupported names and scores with invalid types or polarity."""
    if name not in PATTERN_POLARITY:
        raise ValueError(f"Unknown candle pattern {name!r}; repair the detector vocabulary")
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(
            f"Candle score for {name!r} must be an integer; repair the detector output"
        )
    if value * PATTERN_POLARITY[name] < 0:
        raise ValueError(
            f"Candle score for {name!r} has the wrong sign; repair the detector output"
        )


def select_pattern(detections: Mapping[str, int]) -> str | None:
    """Select the lexical first name within a polarity; opposing hits abstain.

    Scores are signed integers, with zero meaning inactive. Magnitude does not
    confer priority. Invalid names, types or contradictory signs raise ValueError.
    """
    for name, value in detections.items():
        _validate_detection(name, value)
    active = sorted(name for name, value in detections.items() if value)
    if not active or len({PATTERN_POLARITY[name] for name in active}) != 1:
        return None
    return active[0]


def _price(value: float, name: str) -> float:
    """Validate a real scalar before converting to TA-Lib's float64 representation."""
    message = f"Candle {name} must be a finite positive real number; repair the OHLC source"
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(message)
    try:
        price = float(value)
    except OverflowError as error:
        raise ValueError(message) from error
    if not isfinite(price) or price <= 0:
        raise ValueError(message)
    return price


def _validated_candle(candle: OHLC) -> OHLC:
    """Normalize numeric prices and reject impossible OHLC extrema before use."""
    fields = ("open", "high", "low", "close")
    normalized = OHLC(
        *(_price(value, name) for name, value in zip(fields, candle.values(), strict=True))
    )
    if (
        not normalized.low
        <= min(normalized.open, normalized.close)
        <= max(normalized.open, normalized.close)
        <= normalized.high
    ):
        raise ValueError("Candle OHLC ordering is invalid; repair the OHLC source")
    return normalized


def detect_pattern(candles: Sequence[OHLC]) -> str | None:
    """Return the final candle's shape using only the supplied closed-candle prefix.

    Each recognizer warms up independently. Empty input or no unambiguous hit
    returns None. Any invalid OHLC, including historical input, raises ValueError.
    """
    import talib

    if not candles:
        return None
    opens, highs, lows, closes = np.asarray(
        [_validated_candle(bar).values() for bar in candles], dtype=np.float64
    ).T
    engulfing = int(talib.CDLENGULFING(opens, highs, lows, closes)[-1])
    return select_pattern(
        {
            "bullish_engulfing": max(engulfing, 0),
            "bearish_engulfing": min(engulfing, 0),
            "hammer": int(talib.CDLHAMMER(opens, highs, lows, closes)[-1]),
            "shooting_star": int(talib.CDLSHOOTINGSTAR(opens, highs, lows, closes)[-1]),
            "morning_star": int(
                talib.CDLMORNINGSTAR(opens, highs, lows, closes, penetration=_STAR_PENETRATION)[-1]
            ),
            "evening_star": int(
                talib.CDLEVENINGSTAR(opens, highs, lows, closes, penetration=_STAR_PENETRATION)[-1]
            ),
        }
    )


class CandleDetector:
    """Bounded adapter for five recognizers whose default lookbacks are at most 12.

    Retains 64 candles, including the current observation. TA-Lib candle settings
    must remain at their defaults. Recomputed rolling sums can round differently
    from full-history sums at exact recognition thresholds; parity tests exercise
    representative fixtures, not a universal floating-point equivalence claim.
    """

    def __init__(self) -> None:
        """Retain 64 closed candles, exceeding every selected function's default lookback."""
        self._candles: deque[OHLC] = deque(maxlen=_HISTORY_SIZE)

    def update(self, candle: OHLC) -> str | None:
        """Consume one closed candle; invalid input raises ValueError without advancing."""
        self._candles.append(_validated_candle(candle))
        return detect_pattern(list(self._candles))
