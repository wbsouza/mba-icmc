"""The chain's terminal decision-maker (Spec 04h) — the join point between the F1-F7
filter chain and the order-execution engine (Spec 04a).

`chain/model.py`'s `FilterChain` needs a `TerminalDecision` (`decide(state) -> Decision`)
to close the chain once every filter has run without vetoing. Per specs.md §11.3.2, F7
(the threshold-rule filter, `chain/filters/f7_meta_learner.py`) already *is* that terminal
rule — it runs as the last regular `Filter` in `chain.filters` (so its contribution is
still recorded in `state.filter_results`, feeding the audit trail per §11.3.4) and
`F7TerminalDecision` here just reads its own `FilterResult.recommendation` back out and
maps it onto `chain.model.Decision`.

`LastFilterTerminalDecision` (story 14) is the same rule for a chain that runs no F7: the
strategy's `terminal_filter` key names the last direction-emitting filter, and that
filter's recommendation *is* the decision — BUY/SELL as they are, HOLD/ABSTAIN/NEUTRAL all
HOLD; the gates listed after it (F5, F6) can only veto. The rule-only news strategy
(`news-rule`, F4 → F5 → F6 with `terminal_filter: f4_news_context`) uses it.

`decision_to_order_action` is the second half of the join point: `engine.order_executor`
defines its own `Decision` StrEnum (same four string values, but a separate type — that
module is importable outside the LEAN container and has no dependency on `chain.model`)
plus a `SizingContext`. This module never imports `engine.order_executor` at module scope
(that package's `OrderExecutor` itself only runs meaningfully inside the LEAN container,
per its own docstring) — callers inside a LEAN algorithm import both and use
`decision_to_order_action` to convert.
"""

from __future__ import annotations

from dataclasses import dataclass

from algo_backtest.chain.model import Decision, ExecutionState, Recommendation

_F7_FILTER_NAME = "f7_meta_learner"

# F7's own "otherwise -> HOLD" equation (f7_meta_learner.py) only ever emits BUY/SELL/HOLD,
# never ABSTAIN/NEUTRAL — but `Recommendation` has five members and `FilterResult` gives no
# static guarantee, so every member is mapped explicitly (fail-fast-by-construction: a new
# `Recommendation` member added later would be a KeyError here, not a silently-wrong trade).
_RECOMMENDATION_TO_DECISION: dict[Recommendation, Decision] = {
    Recommendation.BUY: Decision.BUY,
    Recommendation.SELL: Decision.SELL,
    Recommendation.HOLD: Decision.HOLD,
    Recommendation.ABSTAIN: Decision.HOLD,
    Recommendation.NEUTRAL: Decision.HOLD,
}


class F7TerminalDecision:
    """`TerminalDecision` protocol implementation: reads F7's own result as the chain's."""

    def decide(self, state: ExecutionState) -> Decision:
        """Map F7's last `FilterResult.recommendation` onto the chain's final `Decision`.

        Raises:
            ValueError: if `state.filter_results` is empty or its last entry isn't F7's —
                a chain misconfiguration (F7 missing, or another filter placed after it in
                `config.yaml`'s filter order) to fail fast on, not silently decide from the
                wrong filter's vote.
        """
        if not state.filter_results:
            raise ValueError(
                "F7TerminalDecision: state.filter_results is empty — F7 must run as the "
                "last filter in the chain before the terminal decision-maker is consulted"
            )
        last = state.filter_results[-1]
        if last.filter_name != _F7_FILTER_NAME:
            raise ValueError(
                f"F7TerminalDecision: the last filter to run was {last.filter_name!r}, not "
                f"{_F7_FILTER_NAME!r} — check config.yaml's filter order; F7 must be last"
            )
        return _RECOMMENDATION_TO_DECISION[last.recommendation]


@dataclass(frozen=True)
class LastFilterTerminalDecision:
    """`TerminalDecision` for a chain without F7: the named filter's vote is the decision.

    `filter_name` is the strategy's `terminal_filter` (`strategies.py` checks it is the
    last direction-emitting entry of `filters`; only gates may follow it). BUY/SELL map
    as F7's do; HOLD, ABSTAIN and NEUTRAL are all HOLD — a filter with nothing to say
    leaves the position alone, it never opens one.
    """

    filter_name: str

    def decide(self, state: ExecutionState) -> Decision:
        """Map the terminal filter's `FilterResult.recommendation` onto the chain's `Decision`.

        Raises:
            ValueError: no result of the configured terminal filter is in
                `state.filter_results` — a chain misconfiguration to fail fast on.
        """
        results = [r for r in state.filter_results if r.filter_name == self.filter_name]
        if not results:
            ran = [r.filter_name for r in state.filter_results]
            raise ValueError(
                f"LastFilterTerminalDecision: the terminal filter {self.filter_name!r} did not "
                f"run (filters that ran: {ran}) — check config.yaml's filters and terminal_filter"
            )
        return _RECOMMENDATION_TO_DECISION[results[-1].recommendation]


def decision_to_order_action(decision: Decision) -> str:
    """Classify a chain `Decision` into the order action a caller should take.

    Returns one of ``"execute"`` (BUY/SELL — place/flip an order), ``"manage"`` (HOLD —
    leave any open position alone, letting trail-stop/partial-close rules run), or
    ``"stand_aside"`` (NO_TRADE — do nothing this bar). A LEAN algorithm's `on_data()`
    switches on this string to call `self.order_executor.execute(...)` / do nothing,
    rather than re-deriving the same three-way split inline in every strategy's `main.py`.
    """
    if decision in (Decision.BUY, Decision.SELL):
        return "execute"
    if decision is Decision.HOLD:
        return "manage"
    return "stand_aside"
