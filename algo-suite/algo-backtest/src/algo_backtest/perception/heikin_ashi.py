"""Wilder-smoothed OHLC → Heikin-Ashi → LWMA-smoothed trend.

The first HA candle uses (smoothed open + smoothed close) / 2 for its
open. Only ready Wilder samples enter the HA recurrence and the second
pass, making readiness exactly ``period1 + period2 - 1`` input bars.
This streaming initialization deliberately inherits LEAN's warm-up semantics;
it does not reproduce MT4's historical-array initialization.

The reference classifier calls a far >= near reading *down*, including ties.
These direction-reordered extremes are not the final HA open/close buffers.
The default second period is the original MQL value 2; the later Java system
explicitly selected 1 instead.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OHLC:
    """One candle in open/high/low/close order."""

    open: float
    high: float
    low: float
    close: float

    def values(self) -> tuple[float, float, float, float]:
        """Return the stable field order expected by native smoothing and TradeBar."""
        return self.open, self.high, self.low, self.close


@dataclass(frozen=True)
class HeikinAshi:
    """Pre-second-pass candle and its direction-reordered extremes."""

    ohlc: OHLC
    near: float
    far: float


def heikin_ashi_transform(ohlc: OHLC, previous: HeikinAshi | None = None) -> HeikinAshi:
    """Transform smoothed OHLC using the previous unsmoothed HA candle."""
    close = sum(ohlc.values()) / 4.0
    open_ = (
        (ohlc.open + ohlc.close) / 2.0
        if previous is None
        else (previous.ohlc.open + previous.ohlc.close) / 2.0
    )
    high = max(ohlc.high, open_, close)
    low = min(ohlc.low, open_, close)
    near, far = (low, high) if open_ < close else (high, low)
    return HeikinAshi(OHLC(open_, high, low, close), near, far)


def classify_direction(near: float, far: float) -> float:
    """Preserve the reference's binary classification, including down on ties."""
    return -1.0 if far >= near else 1.0


def validate_period(value: int, name: str) -> None:
    """Reject invalid periods before attempting to load the LEAN runtime."""
    if type(value) is not int or value < 1:
        raise ValueError(
            f"{name} must be a positive integer; got {value!r}. Set it to 1 or greater."
        )
