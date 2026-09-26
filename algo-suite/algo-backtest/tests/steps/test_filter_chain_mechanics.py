"""Steps for filter_chain_mechanics.feature — FilterChain.run() mechanics with stub filters.

Stub filters (PASS/VETO/ABSTAIN) stand in for the not-yet-built F1-F7 filters
(specs.md §11.3.2) so the accumulate / veto-short-circuit / abstain-does-not-veto loop
is proven ahead of that Wave-2 work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone

import pytest
from algo_backtest.chain.filters.f1_trend import F1TrendFilter
from algo_backtest.chain.filters.f2_indicator import F2IndicatorFilter
from algo_backtest.chain.filters.f3_pattern import F3PatternFilter
from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter,
    NewsContextConfig,
    NewsContextIndex,
)
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f6_capital_mgmt import CapitalMgmtFilter
from algo_backtest.chain.filters.f7_meta_learner import F7Config, F7MetaLearnerFilter
from algo_backtest.chain.model import (
    ChainOutcome,
    Decision,
    ExecutionState,
    Filter,
    FilterChain,
    FilterResult,
    Recommendation,
    TerminalDecision,
)
from algo_backtest.chain.terminal import F7TerminalDecision, decision_to_order_action
from algo_backtest.rules.risk_guard import RiskGuardCaps
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/filter_chain_mechanics.feature")

_BAR_TIMESTAMP = datetime(2024, 1, 1, tzinfo=UTC)


@dataclass
class _StubMetaLearnerPredictor:
    """A `TrainedMetaLearner`-shaped double with a fixed p_hat, for real-chain integration."""

    p_hat: float

    def predict(self, features: object) -> float:
        return self.p_hat


@dataclass
class _StubFilter:
    """A filter stub with a fixed recommendation/veto, recording every call it receives."""

    name: str
    recommendation: Recommendation
    call_log: list[str]
    veto: bool = False
    enrichment: dict[str, object] = field(default_factory=dict)
    received: list[ExecutionState] = field(default_factory=list, init=False)

    def apply(self, state: ExecutionState) -> FilterResult:
        """Record the call and the exact `state` object received, then return the fixed result."""
        self.call_log.append(self.name)
        self.received.append(state)
        return FilterResult(
            filter_name=self.name,
            recommendation=self.recommendation,
            reason=f"stub {self.recommendation.value}",
            veto=self.veto,
            enrichment=dict(self.enrichment),
        )


@dataclass
class _StubTerminal:
    """A terminal decision-maker that always reports a fixed `Decision`.

    Reads `state.features` on every call (mirroring the real `TerminalDecision` contract
    of "interpret the accumulated state") and records what it saw, so tests can verify it
    was handed the actual running state rather than a stand-in.
    """

    decision: Decision
    received_features: dict[str, object] | None = field(default=None, init=False)

    def decide(self, state: ExecutionState) -> Decision:
        """Record the observed `state.features`, then return the pre-configured decision."""
        self.received_features = dict(state.features)
        return self.decision


@dataclass
class _ChainCtx:
    """Per-scenario fixture context: the chain-under-construction plus its call log."""

    call_log: list[str] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    terminal: TerminalDecision | None = None
    outcome: ChainOutcome | None = None
    state: ExecutionState | None = None
    error: Exception | None = None
    real_features: dict[str, object] = field(default_factory=dict)
    risk_guard_caps: RiskGuardCaps = field(
        default_factory=lambda: RiskGuardCaps(
            portfolio_at_risk_cap=0.1,
            daily_drawdown_limit=-0.05,
            weekly_drawdown_limit=-0.1,
            max_concurrent_trades_per_account=5,
            max_leverage=10.0,
        )
    )
    news_index: NewsContextIndex | None = None
    real_meta_learner_p_hat: float = 0.8
    use_staged_filters: bool = False
    real_terminal: TerminalDecision | None = None
    real_outcome: ChainOutcome | None = None
    real_error: Exception | None = None
    order_action: str | None = None


def _pass_filter(ctx: _ChainCtx, name: str) -> _StubFilter:
    """A stub filter that recommends BUY, no veto, enriching one feature named after itself."""
    return _StubFilter(
        name=name,
        recommendation=Recommendation.BUY,
        call_log=ctx.call_log,
        enrichment={f"{name}_value": True},
    )


@pytest.fixture
def chain_ctx() -> _ChainCtx:
    """A fresh per-scenario chain-building context."""
    return _ChainCtx()


@given(
    parsers.parse(
        'a chain of PASS filters "{first}" and "{second}" each enriching a distinct feature'
    )
)
def _two_pass_filters(chain_ctx: _ChainCtx, first: str, second: str) -> None:
    """Two non-veto, non-abstain filters, each enriching a distinct feature key."""
    chain_ctx.filters = [_pass_filter(chain_ctx, first), _pass_filter(chain_ctx, second)]


@given(
    parsers.parse(
        'a chain of a PASS filter "{first}", a VETO filter "{veto_name}" that also enriches, '
        'and a PASS filter "{last}"'
    )
)
def _pass_veto_pass(chain_ctx: _ChainCtx, first: str, veto_name: str, last: str) -> None:
    """PASS, then a hard VETO that carries its own enrichment, then a PASS never reached."""
    chain_ctx.filters = [
        _pass_filter(chain_ctx, first),
        _StubFilter(
            name=veto_name,
            recommendation=Recommendation.HOLD,
            call_log=chain_ctx.call_log,
            veto=True,
            enrichment={f"{veto_name}_value": True},
        ),
        _pass_filter(chain_ctx, last),
    ]


@given(
    parsers.parse(
        'a chain of a PASS filter "{first}", an ABSTAIN filter "{abstain_name}", '
        'and a PASS filter "{last}"'
    )
)
def _pass_abstain_pass(chain_ctx: _ChainCtx, first: str, abstain_name: str, last: str) -> None:
    """PASS, then a no-veto ABSTAIN, then a PASS that must still run."""
    chain_ctx.filters = [
        _pass_filter(chain_ctx, first),
        _StubFilter(
            name=abstain_name,
            recommendation=Recommendation.ABSTAIN,
            call_log=chain_ctx.call_log,
        ),
        _pass_filter(chain_ctx, last),
    ]


@given(parsers.parse('a terminal decision-maker that reports "{decision}"'))
def _terminal(chain_ctx: _ChainCtx, decision: str) -> None:
    """A stub terminal collaborator fixed to report the given `Decision`."""
    chain_ctx.terminal = _StubTerminal(decision=Decision(decision))


@when("the chain runs")
def _run_chain(chain_ctx: _ChainCtx) -> None:
    """Build the chain from the staged filters/terminal and run it on a fresh state."""
    assert chain_ctx.terminal is not None
    chain = FilterChain(filters=chain_ctx.filters, terminal=chain_ctx.terminal)
    state = ExecutionState(timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features={})
    chain_ctx.state = state
    chain_ctx.outcome = chain.run(state)


@then("both filters ran in order")
def _both_ran_in_order(chain_ctx: _ChainCtx) -> None:
    """Both configured filters were called, in the order they were declared."""
    expected = [f.name for f in chain_ctx.filters if isinstance(f, _StubFilter)]
    assert chain_ctx.call_log == expected


@then("state.features holds both filters' enrichment")
def _features_enriched(chain_ctx: _ChainCtx) -> None:
    """Every filter's enrichment key made it into the final `state.features`."""
    assert chain_ctx.outcome is not None
    features = chain_ctx.outcome.state.features
    for chain_filter in chain_ctx.filters:
        assert isinstance(chain_filter, _StubFilter)
        for key in chain_filter.enrichment:
            assert key in features


@then("state.filter_results holds both filters' results in order")
def _results_in_order(chain_ctx: _ChainCtx) -> None:
    """`filter_results` lists both filters, in call order."""
    assert chain_ctx.outcome is not None
    names = [r.filter_name for r in chain_ctx.outcome.state.filter_results]
    expected = [f.name for f in chain_ctx.filters if isinstance(f, _StubFilter)]
    assert names == expected


@then(parsers.parse('the chain outcome decision is "{decision}"'))
def _outcome_decision(chain_ctx: _ChainCtx, decision: str) -> None:
    """The chain's final decision matches the expected `Decision`."""
    assert chain_ctx.outcome is not None
    assert chain_ctx.outcome.decision == Decision(decision)


def _observed_filter_names(chain_ctx: _ChainCtx) -> list[str]:
    """Every filter name actually invoked so far — stub call log, or the real chain's audit
    trail (`state.filter_results`, which preserves call order same as the stub log does)."""
    observed = list(chain_ctx.call_log)
    if chain_ctx.real_outcome is not None:
        observed += [r.filter_name for r in chain_ctx.real_outcome.state.filter_results]
    return observed


@then(parsers.parse('the filter "{name}" was never called'))
def _never_called(chain_ctx: _ChainCtx, name: str) -> None:
    """The named filter is absent from the call log (the veto short-circuited before it)."""
    assert name not in _observed_filter_names(chain_ctx)


@then(parsers.parse('the filter "{name}" was called'))
def _was_called(chain_ctx: _ChainCtx, name: str) -> None:
    """The named filter is present in the call log (the chain reached it)."""
    assert name in _observed_filter_names(chain_ctx)


@then(
    parsers.parse('state.filter_results holds a result with recommendation "{reco}" and no veto')
)
def _abstain_result_present(chain_ctx: _ChainCtx, reco: str) -> None:
    """An ABSTAIN result is present in the audit trail, and it carries no veto."""
    assert chain_ctx.outcome is not None
    wanted = Recommendation(reco)
    matches = [r for r in chain_ctx.outcome.state.filter_results if r.recommendation == wanted]
    assert matches, f"no filter_results entry with recommendation {reco}"
    assert all(not r.veto for r in matches)


@then("every filter received the running state")
def _every_filter_received_running_state(chain_ctx: _ChainCtx) -> None:
    """Each filter's `apply()` was called with the actual running `ExecutionState` object."""
    assert chain_ctx.state is not None
    for chain_filter in chain_ctx.filters:
        assert isinstance(chain_filter, _StubFilter)
        assert chain_filter.received, f"filter {chain_filter.name} was never called"
        assert chain_filter.received[-1] is chain_ctx.state


@then("the terminal decision-maker observed the accumulated state")
def _terminal_observed_state(chain_ctx: _ChainCtx) -> None:
    """The terminal collaborator was handed the real, accumulated state, not a stand-in."""
    assert chain_ctx.outcome is not None
    assert isinstance(chain_ctx.terminal, _StubTerminal)
    assert chain_ctx.terminal.received_features == chain_ctx.outcome.state.features


@then("state.features holds the enrichment from filters that ran")
def _features_from_called_filters(chain_ctx: _ChainCtx) -> None:
    """Every filter that actually ran has its enrichment merged into `state.features`,
    even when a later filter vetoes."""
    assert chain_ctx.outcome is not None
    features = chain_ctx.outcome.state.features
    for chain_filter in chain_ctx.filters:
        if isinstance(chain_filter, _StubFilter) and chain_filter.name in chain_ctx.call_log:
            for key in chain_filter.enrichment:
                assert key in features


@then("state.filter_results holds results for filters that ran")
def _filter_results_for_called(chain_ctx: _ChainCtx) -> None:
    """`state.filter_results` lists exactly the filters that were actually called, in order —
    proof the real accumulated state (not a stand-in) survives past a veto."""
    assert chain_ctx.outcome is not None
    names = [r.filter_name for r in chain_ctx.outcome.state.filter_results]
    assert names == list(chain_ctx.call_log)


@then("state.features holds the vetoing filter's own enrichment")
def _vetoing_filter_enrichment_survives(chain_ctx: _ChainCtx) -> None:
    """The chain merges a filter's enrichment before checking its veto flag (`chain/model.py`'s
    `run()`), so even the filter that stops the chain still contributes its own enrichment."""
    assert chain_ctx.outcome is not None
    vetoing = next(
        f for f in chain_ctx.filters if isinstance(f, _StubFilter) and f.veto
    )
    for key in vetoing.enrichment:
        assert key in chain_ctx.outcome.state.features


@when(parsers.parse("a FilterResult is built with confidence {confidence:g}"))
def _build_filter_result_with_confidence(chain_ctx: _ChainCtx, confidence: float) -> None:
    """Attempt to construct a `FilterResult` with the given confidence, capturing any error."""
    try:
        FilterResult(
            filter_name="probe", recommendation=Recommendation.HOLD, reason="probe",
            confidence=confidence,
        )
    except ValueError as exc:
        chain_ctx.error = exc


@when("a FilterResult is built with confidence absent")
def _build_filter_result_without_confidence(chain_ctx: _ChainCtx) -> None:
    """Construct a `FilterResult` with no confidence at all (the default `None`)."""
    try:
        FilterResult(filter_name="probe", recommendation=Recommendation.HOLD, reason="probe")
    except ValueError as exc:
        chain_ctx.error = exc


@then("it is rejected for an out-of-range confidence")
def _confidence_rejected(chain_ctx: _ChainCtx) -> None:
    """Construction raised, and the message names the bad value."""
    assert isinstance(chain_ctx.error, ValueError)
    assert "confidence" in str(chain_ctx.error)


@then("it is accepted")
def _construction_accepted(chain_ctx: _ChainCtx) -> None:
    """Construction did not raise."""
    assert chain_ctx.error is None


@when("an ExecutionState is built with a naive timestamp")
def _build_state_naive_timestamp(chain_ctx: _ChainCtx) -> None:
    """Attempt to construct an `ExecutionState` with a tzinfo-less timestamp."""
    try:
        ExecutionState(timestamp=datetime(2024, 1, 1), pair="EURUSD", features={})
    except ValueError as exc:
        chain_ctx.error = exc


@when("an ExecutionState is built with a timestamp in a non-UTC timezone")
def _build_state_non_utc_timestamp(chain_ctx: _ChainCtx) -> None:
    """Attempt to construct an `ExecutionState` with a tz-aware but non-UTC timestamp."""
    non_utc = timezone(timedelta(hours=-5))
    try:
        ExecutionState(timestamp=datetime(2024, 1, 1, tzinfo=non_utc), pair="EURUSD", features={})
    except ValueError as exc:
        chain_ctx.error = exc


@then("it is rejected for a non-UTC timestamp")
def _timestamp_rejected(chain_ctx: _ChainCtx) -> None:
    """Construction raised, and the message names the timezone requirement."""
    assert isinstance(chain_ctx.error, ValueError)
    assert "UTC" in str(chain_ctx.error)


# --- Rule: The real F1-F7 chain reaches a decision via F7TerminalDecision (Spec 04h) ---


@given("the real F1..F7 chain terminated by F7TerminalDecision")
def _real_terminal(chain_ctx: _ChainCtx) -> None:
    chain_ctx.real_terminal = F7TerminalDecision()


@given(
    parsers.parse(
        "a chain of a PASS filter \"{name}\" only, terminated by F7TerminalDecision"
    )
)
def _single_pass_filter_real_terminal(chain_ctx: _ChainCtx, name: str) -> None:
    """A deliberately-broken chain: F7TerminalDecision consulted after a non-F7 filter."""
    chain_ctx.filters = [_pass_filter(chain_ctx, name)]
    chain_ctx.use_staged_filters = True
    chain_ctx.real_terminal = F7TerminalDecision()


@given("an empty chain terminated by F7TerminalDecision")
def _empty_chain_real_terminal(chain_ctx: _ChainCtx) -> None:
    """A chain with zero filters: F7TerminalDecision sees an empty `filter_results`."""
    chain_ctx.filters = []
    chain_ctx.use_staged_filters = True
    chain_ctx.real_terminal = F7TerminalDecision()


@given(
    "a bullish bar: F1/F2/F3 aligned bullish, no high-risk news, ample margin, "
    "meta-learner p_hat 0.8"
)
def _bullish_bar(chain_ctx: _ChainCtx) -> None:
    """Populate every real filter's required `state.features` for a clean bullish bar."""
    chain_ctx.real_features = {
        # F1 (trend): aligned uptrend on both timeframes.
        "trend_direction": 0.8,
        "trend_strength": 40.0,
        "higher_tf_trend_direction": 0.3,
        # F2 (indicator): both oscillators bullish.
        "rsi": 70.0,
        "macd_hist": 0.5,
        # F3 (pattern): a real bullish candlestick.
        "candlestick_pattern": "hammer",
        # F5 (risk guard): well within every cap.
        "account_portfolio_at_risk": 0.05,
        "account_daily_pnl_fraction": -0.01,
        "account_weekly_pnl_fraction": -0.02,
        "account_open_trade_count": 1,
        "account_leverage": 5.0,
        # F6 (capital management): ample margin for the proposed lot.
        "account_balance": 10_000.0,
        "pip_value": 1.0,
        "stop_loss_pips": 20.0,
        "margin_per_lot": 50.0,
        "available_margin": 10_000.0,
    }
    chain_ctx.news_index = NewsContextIndex(
        event_intensity={_BAR_TIMESTAMP: 0.5},  # calm day, well above any sane veto threshold
        sentiment_polarity={},
        sentiment_source_present=False,
    )
    chain_ctx.real_meta_learner_p_hat = 0.8


@given("the account portfolio-at-risk breaches its configured cap")
def _breach_portfolio_at_risk(chain_ctx: _ChainCtx) -> None:
    chain_ctx.real_features["account_portfolio_at_risk"] = 0.5  # cap is 0.1


@given("an active high-risk news event at this bar")
def _active_high_risk_event(chain_ctx: _ChainCtx) -> None:
    assert chain_ctx.news_index is not None
    chain_ctx.news_index = NewsContextIndex(
        event_intensity={_BAR_TIMESTAMP: -5.0},  # far below any sane veto threshold
        sentiment_polarity={},
        sentiment_source_present=False,
    )


def _build_real_filters(chain_ctx: _ChainCtx) -> list[Filter]:
    """Assemble the real F1-F7 chain from the scenario's staged inputs."""
    assert chain_ctx.news_index is not None
    p_hat = chain_ctx.real_meta_learner_p_hat
    return [
        F1TrendFilter(),
        F2IndicatorFilter(),
        F3PatternFilter(),
        F4NewsContextFilter(
            index=chain_ctx.news_index,
            config=NewsContextConfig(
                event_intensity_veto_threshold=-1.0, sentiment_direction_threshold=0.15
            ),
        ),
        RiskGuardFilter(caps=chain_ctx.risk_guard_caps),
        CapitalMgmtFilter(risk_per_trade=0.03),
        F7MetaLearnerFilter(
            meta_learner=_StubMetaLearnerPredictor(p_hat=p_hat),  # type: ignore[arg-type]
            config=F7Config(theta_high=0.55, theta_low=0.45),
        ),
    ]


def _staged_or_real_filters(chain_ctx: _ChainCtx) -> list[Filter]:
    """The scenario's explicitly-staged filter list (incl. deliberately empty), or the
    real F1-F7 chain built from `real_features`/`news_index` when nothing was staged."""
    if chain_ctx.use_staged_filters:
        return chain_ctx.filters
    return _build_real_filters(chain_ctx)


@when("the real chain runs")
def _run_real_chain(chain_ctx: _ChainCtx) -> None:
    filters = _staged_or_real_filters(chain_ctx)
    assert chain_ctx.real_terminal is not None
    chain = FilterChain(filters=filters, terminal=chain_ctx.real_terminal)
    state = ExecutionState(
        timestamp=_BAR_TIMESTAMP, pair="EURUSD", features=dict(chain_ctx.real_features)
    )
    chain_ctx.real_outcome = chain.run(state)


@when("the real chain runs expecting failure")
def _run_real_chain_expect_failure(chain_ctx: _ChainCtx) -> None:
    filters = _staged_or_real_filters(chain_ctx)
    assert chain_ctx.real_terminal is not None
    chain = FilterChain(filters=filters, terminal=chain_ctx.real_terminal)
    state = ExecutionState(
        timestamp=_BAR_TIMESTAMP, pair="EURUSD", features=dict(chain_ctx.real_features)
    )
    try:
        chain_ctx.real_outcome = chain.run(state)
    except ValueError as exc:
        chain_ctx.real_error = exc


@then(parsers.parse('the real chain outcome decision is "{decision}"'))
def _real_outcome_decision(chain_ctx: _ChainCtx, decision: str) -> None:
    assert chain_ctx.real_outcome is not None
    assert chain_ctx.real_outcome.decision == Decision(decision)


@then(parsers.parse('every real filter ran in order "{names}"'))
def _real_filters_ran_in_order(chain_ctx: _ChainCtx, names: str) -> None:
    assert chain_ctx.real_outcome is not None
    expected = [name.strip() for name in names.split(",")]
    actual = [r.filter_name for r in chain_ctx.real_outcome.state.filter_results]
    assert actual == expected


@then("the real chain did not veto")
def _real_chain_no_veto(chain_ctx: _ChainCtx) -> None:
    assert chain_ctx.real_outcome is not None
    assert not any(r.veto for r in chain_ctx.real_outcome.state.filter_results)


@then(parsers.parse('the real chain fails naming "{fragment}"'))
def _real_chain_fails(chain_ctx: _ChainCtx, fragment: str) -> None:
    assert chain_ctx.real_error is not None
    assert fragment in str(chain_ctx.real_error)


# --- Rule: decision_to_order_action classifies every chain Decision (Spec 04h) ---


@when(parsers.parse('chain Decision "{decision}" is classified'))
def _classify_decision(chain_ctx: _ChainCtx, decision: str) -> None:
    chain_ctx.order_action = decision_to_order_action(Decision(decision))


@then(parsers.parse('the order action is "{action}"'))
def _order_action_is(chain_ctx: _ChainCtx, action: str) -> None:
    assert chain_ctx.order_action == action
