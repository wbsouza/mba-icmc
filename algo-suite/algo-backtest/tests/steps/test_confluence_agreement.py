"""Steps for confluence_agreement.feature — the named agreement terminal (story 21, T1).

The vote scenarios hand `AgreementTerminalDecision` a hand-built `ExecutionState`; the
veto scenarios run the real `FilterChain` with the real F5/F6 gates parsed from the
feature's YAML and count how often the terminal is consulted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtFilter,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.model import (
    ChainOutcome,
    Decision,
    ExecutionState,
    Filter,
    FilterChain,
    FilterResult,
    Recommendation,
)
from algo_backtest.chain.terminal import (
    AgreementTerminalDecision,
    F7TerminalDecision,
    LastFilterTerminalDecision,
    decision_to_order_action,
)
from algo_backtest.rules.risk_guard import parse_risk_guard_caps
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_agreement.feature")

_BAR_TIMESTAMP = datetime(2016, 4, 5, 10, tzinfo=UTC)


@dataclass
class _FixedVoter:
    """A direction-emitting filter stub with a fixed vote and no veto."""

    name: str
    recommendation: Recommendation

    def apply(self, state: ExecutionState) -> FilterResult:
        """The fixed vote, named after this voter."""
        return FilterResult(
            filter_name=self.name, recommendation=self.recommendation, reason="fixed vote"
        )


@dataclass
class _CountingTerminal:
    """The real agreement terminal, wrapped only to count how often the chain consults it."""

    inner: AgreementTerminalDecision
    consulted: int = 0

    def decide(self, state: ExecutionState) -> Decision:
        """Count the call, then delegate to the real terminal."""
        self.consulted += 1
        return self.inner.decide(state)


@dataclass
class _AgreementCtx:
    """Per-scenario context: the voter map, terminal, chain state and outcome or error."""

    voter_name_map: dict[str, str] = field(default_factory=dict)
    terminal: AgreementTerminalDecision | None = None
    results: list[FilterResult] = field(default_factory=list)
    decision: Decision | None = None
    error: Exception | None = None
    gates: list[Filter] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    counting: _CountingTerminal | None = None
    features: dict[str, object] = field(default_factory=dict)
    outcome: ChainOutcome | None = None


@pytest.fixture
def agreement_ctx() -> _AgreementCtx:
    """A fresh per-scenario agreement context."""
    return _AgreementCtx()


def _names(required: str) -> tuple[str, ...]:
    """The comma-separated required voters of a step, as a tuple (empty for an empty cell)."""
    return tuple(name.strip() for name in required.split(",") if name.strip())


def _state(agreement_ctx: _AgreementCtx) -> ExecutionState:
    """An `ExecutionState` carrying the scenario's staged filter results."""
    state = ExecutionState(timestamp=_BAR_TIMESTAMP, pair="EURUSD", features={})
    state.filter_results = list(agreement_ctx.results)
    return state


@given("the canonical voter names map to runtime result names:")
def _voter_map(agreement_ctx: _AgreementCtx, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    assert header == ["canonical", "runtime"], header
    agreement_ctx.voter_name_map = {canonical: runtime for canonical, runtime in rows}


@given("the canonical voter names map to no runtime result names")
def _empty_voter_map(agreement_ctx: _AgreementCtx) -> None:
    agreement_ctx.voter_name_map = {}


@given(parsers.parse('an agreement terminal requiring "{required}"'))
def _terminal(agreement_ctx: _AgreementCtx, required: str) -> None:
    agreement_ctx.terminal = AgreementTerminalDecision(
        required_filters=_names(required), voter_name_map=agreement_ctx.voter_name_map
    )


@given("the chain state holds these filter results:")
def _filter_results(agreement_ctx: _AgreementCtx, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    assert header == ["filter_name", "recommendation"], header
    agreement_ctx.results = [
        FilterResult(filter_name=name, recommendation=Recommendation(vote), reason="staged")
        for name, vote in rows
    ]


@given("the chain state holds no filter results")
def _no_filter_results(agreement_ctx: _AgreementCtx) -> None:
    agreement_ctx.results = []


@when("the agreement terminal decides")
def _decide(agreement_ctx: _AgreementCtx) -> None:
    assert agreement_ctx.terminal is not None
    agreement_ctx.decision = agreement_ctx.terminal.decide(_state(agreement_ctx))


@when("the agreement terminal decides and fails")
def _decide_fails(agreement_ctx: _AgreementCtx) -> None:
    assert agreement_ctx.terminal is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        agreement_ctx.terminal.decide(_state(agreement_ctx))
    agreement_ctx.error = exc_info.value


@when(parsers.re(r'an agreement terminal requiring "(?P<required>.*)" is built and fails'))
def _build_fails(agreement_ctx: _AgreementCtx, required: str) -> None:
    """`parsers.re` so the empty-list example (an empty quoted cell) still matches."""
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        AgreementTerminalDecision(
            required_filters=_names(required), voter_name_map=agreement_ctx.voter_name_map
        )
    agreement_ctx.error = exc_info.value


@then(parsers.parse('the agreement decision is "{decision}"'))
def _decision_is(agreement_ctx: _AgreementCtx, decision: str) -> None:
    assert agreement_ctx.decision == Decision(decision)


@then(parsers.parse('the agreement failure names "{fragment}"'))
def _failure_names(agreement_ctx: _AgreementCtx, fragment: str) -> None:
    assert agreement_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(agreement_ctx.error), str(agreement_ctx.error)


# --- Rule: F5 and F6 vetoes short-circuit the real chain before the terminal (CC-05) ---


@given("the real F5 and F6 gates parsed from:")
def _real_gates(agreement_ctx: _AgreementCtx, docstring: str) -> None:
    """The real gate filters from the feature's YAML, as the production wiring parses them."""
    sections: dict[str, Any] = yaml.safe_load(docstring)
    caps = parse_risk_guard_caps(sections["risk_guard"], strategy="scenario")
    plan = parse_capital_mgmt_config(sections["capital_mgmt"], strategy="scenario")
    agreement_ctx.gates = [
        RiskGuardFilter(caps=caps),
        CapitalMgmtFilter(config=plan, spread_pips=0.0, broker_stop_level_pips=0.0),
    ]


@given(
    parsers.parse(
        'a chain of a "{f1_vote}" voter "{f1_name}", a "{f4_vote}" voter "{f4_name}", then the '
        "real F5 and F6 gates"
    )
)
def _chain(
    agreement_ctx: _AgreementCtx, f1_vote: str, f1_name: str, f4_vote: str, f4_name: str
) -> None:
    voters: list[Filter] = [
        _FixedVoter(f1_name, Recommendation(f1_vote)),
        _FixedVoter(f4_name, Recommendation(f4_vote)),
    ]
    agreement_ctx.filters = voters + agreement_ctx.gates


@given(parsers.parse('the chain is closed by an agreement terminal requiring "{required}"'))
def _closed_by(agreement_ctx: _AgreementCtx, required: str) -> None:
    agreement_ctx.counting = _CountingTerminal(
        AgreementTerminalDecision(
            required_filters=_names(required), voter_name_map=agreement_ctx.voter_name_map
        )
    )


@given("a bar whose features are:")
def _bar_features(agreement_ctx: _AgreementCtx, datatable: list[list[str]]) -> None:
    """The bar's `state.features`, straight from the feature file's table (YAML-typed)."""
    header, *rows = datatable
    assert header == ["feature", "value"], header
    agreement_ctx.features = {name: yaml.safe_load(value) for name, value in rows}


@when("the agreement chain runs")
def _run_chain(agreement_ctx: _AgreementCtx) -> None:
    assert agreement_ctx.counting is not None
    chain = FilterChain(filters=agreement_ctx.filters, terminal=agreement_ctx.counting)
    state = ExecutionState(
        timestamp=_BAR_TIMESTAMP, pair="EURUSD", features=dict(agreement_ctx.features)
    )
    agreement_ctx.outcome = chain.run(state)


def _outcome(agreement_ctx: _AgreementCtx) -> ChainOutcome:
    """The chain outcome, which must exist by the time a Then step reads it."""
    assert agreement_ctx.outcome is not None
    return agreement_ctx.outcome


@then(parsers.parse('the agreement chain outcome decision is "{decision}"'))
def _outcome_decision(agreement_ctx: _AgreementCtx, decision: str) -> None:
    assert _outcome(agreement_ctx).decision == Decision(decision)


@then(parsers.parse('the agreement chain was vetoed by "{name}"'))
def _vetoed_by(agreement_ctx: _AgreementCtx, name: str) -> None:
    """`none` asserts no filter vetoed; otherwise exactly that filter did."""
    vetoes = [r.filter_name for r in _outcome(agreement_ctx).state.filter_results if r.veto]
    assert vetoes == ([] if name == "none" else [name]), vetoes


@then(parsers.parse('every agreement chain filter ran in order "{names}"'))
def _ran_in_order(agreement_ctx: _AgreementCtx, names: str) -> None:
    expected = [name.strip() for name in names.split(",")]
    actual = [r.filter_name for r in _outcome(agreement_ctx).state.filter_results]
    assert actual == expected


@then(parsers.parse("the agreement terminal was consulted {count:d} times"))
def _consulted(agreement_ctx: _AgreementCtx, count: int) -> None:
    assert agreement_ctx.counting is not None
    assert agreement_ctx.counting.consulted == count


# --- Rule: the legacy terminals keep their behaviour beside the new one (CC-20) ---


@when(parsers.parse('LastFilterTerminalDecision for "{name}" decides'))
def _last_filter_decides(agreement_ctx: _AgreementCtx, name: str) -> None:
    agreement_ctx.decision = LastFilterTerminalDecision(name).decide(_state(agreement_ctx))


@when("F7TerminalDecision decides and fails")
def _f7_decides_fails(agreement_ctx: _AgreementCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        F7TerminalDecision().decide(_state(agreement_ctx))
    agreement_ctx.error = exc_info.value


@then(
    parsers.parse(
        'decision_to_order_action maps "{first}" to "{first_action}", "{second}" to '
        '"{second_action}" and "{third}" to "{third_action}"'
    )
)
def _order_actions(
    first: str,
    first_action: str,
    second: str,
    second_action: str,
    third: str,
    third_action: str,
) -> None:
    expected = {first: first_action, second: second_action, third: third_action}
    for decision, action in expected.items():
        assert decision_to_order_action(Decision(decision)) == action
