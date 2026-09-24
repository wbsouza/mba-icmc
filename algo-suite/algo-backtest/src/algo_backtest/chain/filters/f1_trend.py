"""F1 — trend-regime filter (specs.md §11.3.2, Spec 04c).

"Recommends BUY/SELL aligned with the multi-timeframe trend; vetoes if direction
conflicts." No upstream perception layer populates `ExecutionState.features` from real
LEAN indicators yet (`engine/algorithm.py` — future 04a/04h integration work), so this
filter defines and documents its own minimal feature-key contract, proven here with
synthetic `ExecutionState` fixtures (`tests/features/f1_trend.feature`).

**Feature-key contract** (read from `state.features`, all required — a missing key is a
hard, explained failure per the workspace's fail-fast policy, not a silent default):

- ``trend_direction`` (float): signed slope of the primary-timeframe EMA. Positive =
  uptrend, negative = downtrend, zero = flat.
- ``trend_strength`` (float, ``[0, 100]``): an ADX-style trend-strength reading for the
  primary timeframe.
- ``higher_tf_trend_direction`` (float): same sign convention as ``trend_direction``,
  computed on a coarser timeframe — the multi-timeframe confirmation input.

A **direction conflict** is ``trend_direction`` and ``higher_tf_trend_direction``
disagreeing in sign (both nonzero, opposite signs): the primary timeframe wants to
trade against the higher timeframe's regime, so the filter vetoes rather than pick a
side. When aligned (or the higher timeframe is flat), the filter recommends BUY/SELL
by the sign of ``trend_direction`` (NEUTRAL if the primary timeframe itself is flat)
and enriches ``trend_score`` — ``trend_direction * trend_strength / 100`` — for
downstream filters (specs.md §11.3.1's `"trend_score"` enrichment example).
"""

from __future__ import annotations

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation

_REQUIRED_KEYS = ("trend_direction", "trend_strength", "higher_tf_trend_direction")


def _read_required(state: ExecutionState) -> tuple[float, float, float]:
    """Read F1's three required feature keys, failing fast with a remediation hint.

    A key counts as missing if it's absent *or* present with value `None` —
    `state.features.get(key) is None`, matching F2/F3's own "no-information-yet"
    convention, not Python's `in` operator (which a present-but-`None` value would
    incorrectly pass, falling through to `float(None)`'s unguided `TypeError`).
    """
    missing = [key for key in _REQUIRED_KEYS if state.features.get(key) is None]
    if missing:
        raise ValueError(
            f"F1TrendFilter requires state.features{_REQUIRED_KEYS!r}; missing {missing!r} "
            "— populate them upstream (perception layer / LEAN indicators) before running "
            "the chain."
        )
    trend_direction = float(state.features["trend_direction"])  # type: ignore[arg-type]
    trend_strength = float(state.features["trend_strength"])  # type: ignore[arg-type]
    higher_tf_trend_direction = float(
        state.features["higher_tf_trend_direction"]  # type: ignore[arg-type]
    )
    if not 0.0 <= trend_strength <= 100.0:
        raise ValueError(
            f"F1TrendFilter: trend_strength must be in [0, 100] (an ADX-style reading), "
            f"got {trend_strength!r} — check the upstream indicator computation"
        )
    return trend_direction, trend_strength, higher_tf_trend_direction


def _conflicts(trend_direction: float, higher_tf_trend_direction: float) -> bool:
    """Both timeframes hold a nonzero, opposite-signed trend direction."""
    return (
        trend_direction != 0.0
        and higher_tf_trend_direction != 0.0
        and (trend_direction > 0.0) != (higher_tf_trend_direction > 0.0)
    )


def _directional_recommendation(trend_direction: float) -> Recommendation:
    """BUY/SELL by the sign of the primary-timeframe slope, NEUTRAL if flat."""
    if trend_direction > 0.0:
        return Recommendation.BUY
    if trend_direction < 0.0:
        return Recommendation.SELL
    return Recommendation.NEUTRAL


class F1TrendFilter:
    """The chain's trend-regime gate: implements `Filter.apply()`."""

    def apply(self, state: ExecutionState) -> FilterResult:
        """Veto on a cross-timeframe direction conflict; otherwise recommend by trend sign."""
        trend_direction, trend_strength, higher_tf_trend_direction = _read_required(state)
        if _conflicts(trend_direction, higher_tf_trend_direction):
            return FilterResult(
                filter_name="F1_trend",
                recommendation=Recommendation.NEUTRAL,
                reason=(
                    f"direction conflict: primary trend_direction={trend_direction} vs. "
                    f"higher_tf_trend_direction={higher_tf_trend_direction}"
                ),
                veto=True,
            )
        recommendation = _directional_recommendation(trend_direction)
        trend_score = trend_direction * trend_strength / 100.0
        return FilterResult(
            filter_name="F1_trend",
            recommendation=recommendation,
            reason=(
                f"trend_direction={trend_direction}, trend_strength={trend_strength}, "
                f"higher_tf_trend_direction={higher_tf_trend_direction}"
            ),
            enrichment={"trend_score": trend_score},
        )
