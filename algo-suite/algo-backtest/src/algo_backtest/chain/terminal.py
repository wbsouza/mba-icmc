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

`AgreementTerminalDecision` (story 21, the confluence chain) is the third rule: a
nonempty set of *required* voters, named by their canonical lower-case YAML ids and mapped
to their runtime `FilterResult.filter_name` through an explicit `voter_name_map`, must all
have voted the same BUY or SELL; any other directional voter must agree; an explicit HOLD
from any voter blocks; optional ABSTAIN/NEUTRAL votes are ignored; anything else is HOLD.
It never vetoes — F5/F6 veto through `FilterChain.run` before it is consulted.

`decision_to_order_action` is the second half of the join point: `engine.order_executor`
defines its own `Decision` StrEnum (same four string values, but a separate type — that
module is importable outside the LEAN container and has no dependency on `chain.model`)
plus a `SizingContext`. This module never imports `engine.order_executor` at module scope
(that package's `OrderExecutor` itself only runs meaningfully inside the LEAN container,
per its own docstring) — callers inside a LEAN algorithm import both and use
`decision_to_order_action` to convert.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from algo_backtest.chain.model import Decision, ExecutionState, FilterResult, Recommendation

_F7_FILTER_NAME = "f7_meta_learner"
_AGREEMENT = "AgreementTerminalDecision"
# The chain's gates: they emit no direction (always ABSTAIN, veto or not), so they can
# never be required voters — a config naming one is a misconfiguration to fail fast on.
_GATE_NAMES = frozenset({"f5_risk_guard", "f6_capital_mgmt", "volume_strength"})
_DIRECTIONAL = frozenset({Recommendation.BUY, Recommendation.SELL})

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


@dataclass(frozen=True)
class AgreementTerminalDecision:
    """`TerminalDecision` for the confluence chain: named required voters must agree.

    - ``required_filters``: canonical lower-case YAML ids (`f1_trend`, `f4_news_context`,
      ...), nonempty, no duplicates, every one a key of ``voter_name_map`` and none of
      them a gate.
    - ``voter_name_map``: the closed canonical → runtime `FilterResult.filter_name` map
      (`f1_trend` → `F1_trend`, `f2_indicator` → `F2_indicator`, ...). Nothing is
      lower-cased or guessed: a name absent from the map is unknown.

    Raises:
        ValueError: at construction, naming the offending entry and the fix.
    """

    required_filters: tuple[str, ...]
    voter_name_map: Mapping[str, str]

    def __post_init__(self) -> None:
        """Fail fast on an empty map, an empty/duplicated list, a gate or an unknown name."""
        if not self.voter_name_map:
            raise ValueError(
                f"{_AGREEMENT}: voter_name_map is empty — pass the canonical → runtime voter "
                "names (e.g. {'f1_trend': 'F1_trend'}) so required_filters can be resolved"
            )
        known = sorted(self.voter_name_map)
        if not self.required_filters:
            raise ValueError(
                f"{_AGREEMENT}: required_filters is empty — name at least one direction-emitting "
                f"filter (known voters: {known})"
            )
        seen: set[str] = set()
        for name in self.required_filters:
            if name in seen:
                raise ValueError(
                    f"{_AGREEMENT}: required_filters names {name!r} more than once — list each "
                    "voter once"
                )
            seen.add(name)
            self._check_known(name, known)

    @staticmethod
    def _check_known(name: str, known: list[str]) -> None:
        """One required name is a mapped voter, not a gate and not an unknown spelling."""
        if name in _GATE_NAMES:
            raise ValueError(
                f"{_AGREEMENT}: required_filters entry {name!r} is a gate, not a "
                f"direction-emitting voter — gates veto through FilterChain.run; remove it "
                f"(known voters: {known})"
            )
        if name not in known:
            raise ValueError(
                f"{_AGREEMENT}: required_filters entry {name!r} is not a known voter; known "
                f"voters: {known} — use the canonical lower-case name from voter_name_map"
            )

    def decide(self, state: ExecutionState) -> Decision:
        """The agreed BUY/SELL of every required voter, unless anything blocks it: HOLD.

        Raises:
            ValueError: a required voter has no result or more than one result in
                `state.filter_results` — a chain misconfiguration, never a HOLD.
        """
        votes = [self._required_vote(name, state.filter_results) for name in self.required_filters]
        if len(set(votes)) != 1 or votes[0] not in _DIRECTIONAL:
            return Decision.HOLD
        direction = votes[0]
        required_runtime = {self.voter_name_map[name] for name in self.required_filters}
        others = [r for r in state.filter_results if r.filter_name not in required_runtime]
        if any(_blocks(result, direction) for result in others):
            return Decision.HOLD
        return _RECOMMENDATION_TO_DECISION[direction]

    def _required_vote(self, name: str, results: list[FilterResult]) -> Recommendation:
        """The single result of the required voter `name`, by its runtime name."""
        runtime = self.voter_name_map[name]
        matches = [r for r in results if r.filter_name == runtime]
        if len(matches) == 1:
            return matches[0].recommendation
        ran = [r.filter_name for r in results]
        problem = "did not run" if not matches else f"ran {len(matches)} times"
        raise ValueError(
            f"{_AGREEMENT}: required voter {name!r} (runtime name {runtime!r}) {problem} "
            f"(filters that ran: {ran}) — check config.yaml's filters: every required voter "
            "must run exactly once before the terminal is consulted"
        )


def _blocks(result: FilterResult, direction: Recommendation) -> bool:
    """An optional voter blocks with an explicit HOLD or a directional vote against `direction`."""
    vote = result.recommendation
    return vote is Recommendation.HOLD or (vote in _DIRECTIONAL and vote is not direction)


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
