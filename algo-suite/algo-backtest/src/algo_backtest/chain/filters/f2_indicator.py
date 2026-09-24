"""F2 — indicator (oscillator confirmation) filter (specs.md §11.3.2, Spec 04c).

"Recommends direction confirmed by oscillators; ABSTAIN on no-information bars." No
upstream perception layer populates `ExecutionState.features` from real LEAN indicators
yet (`engine/algorithm.py` — future 04a/04h integration work), so this filter defines
and documents its own minimal feature-key contract, proven here with synthetic
`ExecutionState` fixtures (`tests/features/f2_indicator.feature`).

**Feature-key contract** (read from `state.features`, both optional/nullable):

- ``rsi`` (float | None, ``[0, 100]``): the RSI reading, or ``None``/absent on a
  no-information bar (e.g. still warming up). Above 50 is a bullish bias, below 50
  bearish.
- ``macd_hist`` (float | None): the MACD histogram (signal-line distance), or
  ``None``/absent on a no-information bar. Positive is bullish momentum, negative
  bearish.

A **no-information bar** is either oscillator being absent or `None` — F2 needs both
readings to confirm a direction, so it abstains rather than guess from a partial
signal. F2 never vetoes: a lack of confirmation is "no opinion this bar", not a hard
stop. When both are present, F2 recommends BUY/SELL only when they agree on direction;
disagreement (e.g. RSI bullish but MACD histogram bearish) yields NEUTRAL — a call, but
not a confirmed one.
"""

from __future__ import annotations

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation


def _bullish(rsi: float, macd_hist: float) -> bool:
    """Both oscillators agree on an uptrend."""
    return rsi > 50.0 and macd_hist > 0.0


def _bearish(rsi: float, macd_hist: float) -> bool:
    """Both oscillators agree on a downtrend."""
    return rsi < 50.0 and macd_hist < 0.0


class F2IndicatorFilter:
    """The chain's oscillator-confirmation gate: implements `Filter.apply()`."""

    def apply(self, state: ExecutionState) -> FilterResult:
        """ABSTAIN on a no-information bar; otherwise recommend by oscillator agreement."""
        rsi = state.features.get("rsi")
        macd_hist = state.features.get("macd_hist")
        if rsi is None or macd_hist is None:
            return FilterResult(
                filter_name="F2_indicator",
                recommendation=Recommendation.ABSTAIN,
                reason=f"no-information bar: rsi={rsi!r}, macd_hist={macd_hist!r}",
            )
        rsi = float(rsi)  # type: ignore[arg-type]
        macd_hist = float(macd_hist)  # type: ignore[arg-type]
        if not 0.0 <= rsi <= 100.0:
            raise ValueError(
                f"F2IndicatorFilter: rsi must be in [0, 100], got {rsi!r} — check the "
                "upstream indicator computation"
            )
        if _bullish(rsi, macd_hist):
            recommendation = Recommendation.BUY
        elif _bearish(rsi, macd_hist):
            recommendation = Recommendation.SELL
        else:
            recommendation = Recommendation.NEUTRAL
        return FilterResult(
            filter_name="F2_indicator",
            recommendation=recommendation,
            reason=f"rsi={rsi}, macd_hist={macd_hist}",
        )
