"""Steps for confluence_controls.feature — the constant-direction control filter (story 21, T7).

The direct-vote scenarios hand `ConstantDirectionFilter` a hand-built `ExecutionState`
(and one with no features at all); the veto scenarios run the real `FilterChain` with
the real F5/F6 gates parsed from the feature's YAML, reusing the same real-gate
construction `test_confluence_agreement.py` uses for T1's veto proofs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.constant_direction import ConstantDirectionFilter
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f6_capital_mgmt import CapitalMgmtFilter, parse_capital_mgmt_config
from algo_backtest.chain.model import (
    ChainOutcome,
    Decision,
    ExecutionState,
    Filter,
    FilterChain,
    FilterResult,
)
from algo_backtest.chain.terminal import AgreementTerminalDecision
from algo_backtest.rules.risk_guard import parse_risk_guard_caps
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_controls.feature")

_BAR_TIMESTAMP = datetime(2016, 4, 5, 10, tzinfo=UTC)


@dataclass
class _ControlsCtx:
    """Per-scenario context: the standalone filter, the last result(s), or the real chain."""

    control_filter: ConstantDirectionFilter | None = None
    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    results: list[FilterResult] = field(default_factory=list)
    error: Exception | None = None
    gates: list[Filter] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    terminal: AgreementTerminalDecision | None = None
    outcome: ChainOutcome | None = None


@pytest.fixture
def controls_ctx() -> _ControlsCtx:
    """A fresh per-scenario controls context."""
    return _ControlsCtx()


def _state(features: dict[str, object], *, at: datetime = _BAR_TIMESTAMP) -> ExecutionState:
    return ExecutionState(timestamp=at, pair="EURUSD", features=dict(features))


# --- Standalone filter, direct apply ---


@given(parsers.parse('a constant-direction filter configured for "{direction}"'))
def _build(controls_ctx: _ControlsCtx, direction: str) -> None:
    controls_ctx.control_filter = ConstantDirectionFilter(direction=direction)


@given("a bar whose features are:")
def _bar_features(controls_ctx: _ControlsCtx, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    assert header == ["feature", "value"], header
    controls_ctx.features = {name: yaml.safe_load(value) for name, value in rows}


@given("a bar whose features are empty")
def _bar_no_features(controls_ctx: _ControlsCtx) -> None:
    controls_ctx.features = {}


@when("the constant-direction filter applies")
def _apply(controls_ctx: _ControlsCtx) -> None:
    assert controls_ctx.control_filter is not None
    controls_ctx.result = controls_ctx.control_filter.apply(_state(controls_ctx.features))


@when(parsers.parse('the constant-direction filter applies to a bar at "{time}"'))
def _apply_at(controls_ctx: _ControlsCtx, time: str) -> None:
    assert controls_ctx.control_filter is not None
    at = datetime.fromisoformat(time.replace("Z", "+00:00"))
    controls_ctx.results.append(controls_ctx.control_filter.apply(_state({}, at=at)))


@when(parsers.re(r'a constant-direction filter configured for "(?P<value>.*)" is built and fails'))
def _build_fails(controls_ctx: _ControlsCtx, value: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        ConstantDirectionFilter(direction=value)
    controls_ctx.error = exc_info.value


@then(parsers.parse('the constant-direction result recommends "{direction}"'))
def _recommends(controls_ctx: _ControlsCtx, direction: str) -> None:
    assert controls_ctx.result is not None
    assert controls_ctx.result.recommendation == direction


@then("the constant-direction result does not veto")
def _no_veto(controls_ctx: _ControlsCtx) -> None:
    assert controls_ctx.result is not None
    assert controls_ctx.result.veto is False


@then("the constant-direction result has no enrichment")
def _no_enrichment(controls_ctx: _ControlsCtx) -> None:
    assert controls_ctx.result is not None
    assert controls_ctx.result.enrichment == {}


@then(parsers.parse('both constant-direction results recommend "{direction}"'))
def _both_recommend(controls_ctx: _ControlsCtx, direction: str) -> None:
    assert len(controls_ctx.results) == 2, controls_ctx.results
    assert all(result.recommendation == direction for result in controls_ctx.results)


@then(parsers.parse('the constant-direction failure names "{fragment}"'))
def _failure_names(controls_ctx: _ControlsCtx, fragment: str) -> None:
    assert controls_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(controls_ctx.error), str(controls_ctx.error)


# --- Real chain: F5/F6 vetoes still apply ---


@given("the real F5 and F6 gates parsed from:")
def _real_gates(controls_ctx: _ControlsCtx, docstring: str) -> None:
    """The real gate filters from the feature's YAML, as the production wiring parses them."""
    sections: dict[str, Any] = yaml.safe_load(docstring)
    caps = parse_risk_guard_caps(sections["risk_guard"], strategy="scenario")
    plan = parse_capital_mgmt_config(sections["capital_mgmt"], strategy="scenario")
    controls_ctx.gates = [
        RiskGuardFilter(caps=caps),
        CapitalMgmtFilter(config=plan, spread_pips=0.0, broker_stop_level_pips=0.0),
    ]


@given(
    parsers.parse(
        'a chain of a constant-direction voter "{name}" configured for "{direction}", then '
        "the real F5 and F6 gates"
    )
)
def _chain(controls_ctx: _ControlsCtx, name: str, direction: str) -> None:
    voter = ConstantDirectionFilter(direction=direction)
    assert name == voter.apply(_state({})).filter_name
    controls_ctx.filters = [voter, *controls_ctx.gates]


@given(parsers.parse('the chain is closed by an agreement terminal requiring "{required}"'))
def _closed_by(controls_ctx: _ControlsCtx, required: str) -> None:
    controls_ctx.terminal = AgreementTerminalDecision(
        required_filters=(required,), voter_name_map={required: required}
    )


@when("the constant-direction chain runs")
def _run_chain(controls_ctx: _ControlsCtx) -> None:
    assert controls_ctx.terminal is not None
    chain = FilterChain(filters=controls_ctx.filters, terminal=controls_ctx.terminal)
    controls_ctx.outcome = chain.run(_state(controls_ctx.features))


def _outcome(controls_ctx: _ControlsCtx) -> ChainOutcome:
    assert controls_ctx.outcome is not None
    return controls_ctx.outcome


@then(parsers.parse('the constant-direction chain outcome decision is "{decision}"'))
def _outcome_decision(controls_ctx: _ControlsCtx, decision: str) -> None:
    assert _outcome(controls_ctx).decision == Decision(decision)


@then(parsers.parse('the constant-direction chain was vetoed by "{name}"'))
def _vetoed_by(controls_ctx: _ControlsCtx, name: str) -> None:
    """`none` asserts no filter vetoed; otherwise exactly that filter did."""
    vetoes = [r.filter_name for r in _outcome(controls_ctx).state.filter_results if r.veto]
    assert vetoes == ([] if name == "none" else [name]), vetoes
