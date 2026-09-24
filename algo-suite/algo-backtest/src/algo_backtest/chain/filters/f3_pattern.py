"""F3 — candlestick pattern filter (specs.md §11.3.2, Spec 04c).

"Recommends BUY/SELL on detected pattern; ABSTAIN if no pattern at current bar." No
upstream perception layer populates `ExecutionState.features` from real TA-Lib `CDL*`
output yet (`engine/algorithm.py` — future 04a/04h integration work; `algo-backtest/
SPEC.md` §3 names TA-Lib as the intended candlestick-recognition source), so this
filter defines and documents its own minimal feature-key contract, proven here with
synthetic `ExecutionState` fixtures (`tests/features/f3_pattern.feature`).

**Feature-key contract** (read from `state.features`):

- ``candlestick_pattern`` (str | None): `None`/absent means no pattern was detected
  this bar. A present value must be one of the recognized pattern names below —
  TA-Lib-style `CDL*` names, lower-cased and without the `CDL` prefix, for this
  filter's own closed vocabulary. An unrecognized name is a data-contract violation
  (upstream produced something this filter's key catalogue doesn't cover) and raises,
  per the workspace's fail-fast policy.

ABSTAIN means "no opinion this bar" — F3 never vetoes.
"""

from __future__ import annotations

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation

_BULLISH_PATTERNS = frozenset({"bullish_engulfing", "hammer", "morning_star"})
_BEARISH_PATTERNS = frozenset({"bearish_engulfing", "shooting_star", "evening_star"})
_KNOWN_PATTERNS = _BULLISH_PATTERNS | _BEARISH_PATTERNS


class F3PatternFilter:
    """The chain's candlestick-pattern gate: implements `Filter.apply()`."""

    def apply(self, state: ExecutionState) -> FilterResult:
        """ABSTAIN with no pattern this bar; otherwise recommend by pattern polarity."""
        pattern = state.features.get("candlestick_pattern")
        if pattern is None:
            return FilterResult(
                filter_name="F3_pattern",
                recommendation=Recommendation.ABSTAIN,
                reason="no pattern detected this bar",
            )
        if pattern not in _KNOWN_PATTERNS:
            raise ValueError(
                f"F3PatternFilter does not recognize candlestick_pattern={pattern!r}; "
                f"known patterns are {sorted(_KNOWN_PATTERNS)!r} — extend this filter's "
                "vocabulary if the upstream detector added a new pattern name."
            )
        recommendation = Recommendation.BUY if pattern in _BULLISH_PATTERNS else Recommendation.SELL
        return FilterResult(
            filter_name="F3_pattern",
            recommendation=recommendation,
            reason=f"detected candlestick pattern {pattern!r}",
        )
