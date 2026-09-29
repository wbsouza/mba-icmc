"""Constant-direction control filter — the two drift-control votes (story 21, T7).

`ConstantDirectionFilter` is the sole voter behind the always-short and always-long
drift-control arms (spec CC-23, decision D9). Configured once with a fixed direction,
BUY or SELL, it emits that vote on every bar it is asked about, regardless of price,
momentum, relative intensity, news or model state: it never abstains, never explicitly
holds and never vetoes on its own account. It reads no feature from `state.features`
and requires none to be present — the control isolates the confluence chain's trigger
and context logic from its own vote, not from risk management. Both drift-control arms
remain subject to the real F5/F6 vetoes through `FilterChain.run`, exactly like every
other cell (CC-23).

Canonical voter id and runtime `filter_name` are both ``"constant_direction"`` (lower
snake case, like `f4_news_context`, since this is a new addition rather than a legacy
F-numbered filter) — the value the agreement terminal's `voter_name_map` expects.
"""

from __future__ import annotations

from dataclasses import dataclass

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation

FILTER_NAME = "constant_direction"
_DIRECTIONS = {"BUY": Recommendation.BUY, "SELL": Recommendation.SELL}


@dataclass
class ConstantDirectionFilter:
    """A control voter that always recommends the same configured direction.

    Raises:
        ValueError: `direction` is not exactly `"BUY"` or `"SELL"`.
    """

    direction: str

    def __post_init__(self) -> None:
        """Fail fast on anything but the two accepted, upper-case directions."""
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"direction must be 'BUY' or 'SELL', got {self.direction!r}")

    def apply(self, state: ExecutionState) -> FilterResult:
        """The configured direction, unconditionally: no feature is read, no veto is set."""
        del state
        return FilterResult(
            filter_name=FILTER_NAME,
            recommendation=_DIRECTIONS[self.direction],
            reason=f"constant control direction: {self.direction}",
        )
