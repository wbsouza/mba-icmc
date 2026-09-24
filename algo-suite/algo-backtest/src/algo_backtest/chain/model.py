"""Deterministic filter-chain mechanics (Spec 04b).

Implements the dataclass shapes and `FilterChain.run()` loop from `specs.md` §11.3.1
verbatim: each filter contributes a `FilterResult` (recommendation, reason, optional
veto/enrichment) against the running `ExecutionState`; enrichment merges into
`state.features` for downstream filters to read; a veto short-circuits the chain to
`Decision.NO_TRADE`. The terminal collaborator (the "order executor" in
`algo-backtest/SPEC.md` §4.1's sequence diagram) is modelled as the `TerminalDecision`
protocol so the chain has no dependency on any concrete strategy or the LEAN engine.

Real F1-F7 filters (specs.md §11.3.2) are Wave-2 work; this module is proven here with
trivial stub filters (`tests/features/filter_chain_mechanics.feature`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol


class Recommendation(StrEnum):
    """What a single filter would have the strategy do, based on its own evidence."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NEUTRAL = "NEUTRAL"
    ABSTAIN = "ABSTAIN"


class Decision(StrEnum):
    """The chain's final, per-tick outcome (specs.md §11.3.1.1)."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


@dataclass
class FilterResult:
    """One filter's contribution to a chain run: its vote, reasoning, and any veto/enrichment."""

    filter_name: str
    recommendation: Recommendation
    reason: str
    confidence: float | None = None
    veto: bool = False
    enrichment: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Fail fast on a confidence outside `[0, 1]` (specs.md §11.3.1: 'confidence in [0, 1]')."""
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"FilterResult.confidence must be in [0, 1] or None, got {self.confidence!r} "
                f"from filter {self.filter_name!r}"
            )


@dataclass
class ExecutionState:
    """The running state threaded through the chain, enriched in flight by each filter."""

    timestamp: datetime
    pair: str
    features: dict[str, object]
    filter_results: list[FilterResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Fail fast on a naive or non-UTC timestamp — the future `decisions.parquet` audit
        trail (specs.md §11.3.4) is UTC end-to-end; a naive/local value would corrupt joins."""
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() != timedelta(0):
            raise ValueError(
                f"ExecutionState.timestamp must be timezone-aware UTC, got {self.timestamp!r} "
                "— construct it with tzinfo=UTC (from datetime import UTC)"
            )


@dataclass(frozen=True)
class ChainOutcome:
    """The single return value of `FilterChain.run()`: the final decision and the state it saw."""

    decision: Decision
    state: ExecutionState


class Filter(Protocol):
    """A single chain stage: reads the running state, emits a `FilterResult`."""

    def apply(self, state: ExecutionState) -> FilterResult:
        """Evaluate this filter's evidence against `state` and return its contribution."""
        ...


class TerminalDecision(Protocol):
    """The chain's terminal collaborator: turns the accumulated state into a final `Decision`.

    Never vetoes and never abstains — by the time the state reaches it, every upstream
    gating decision has already passed or vetoed (specs.md §11.3.1.1).
    """

    def decide(self, state: ExecutionState) -> Decision:
        """Interpret the accumulated `state` and emit the final BUY/SELL/HOLD/NO_TRADE."""
        ...


@dataclass
class FilterChain:
    """An ordered sequence of filters plus the terminal decision-maker that closes it."""

    filters: list[Filter]
    terminal: TerminalDecision

    def run(self, state: ExecutionState) -> ChainOutcome:
        """Run every filter in order, short-circuiting to NO_TRADE on the first veto.

        Each filter's result is appended to `state.filter_results` and its enrichment is
        merged into `state.features` before the next filter runs, regardless of the
        filter's recommendation — an ABSTAIN is just another non-veto result, not a
        special case.
        """
        for chain_filter in self.filters:
            result = chain_filter.apply(state)
            state.filter_results.append(result)
            state.features.update(result.enrichment)
            if result.veto:
                return ChainOutcome(decision=Decision.NO_TRADE, state=state)
        return ChainOutcome(decision=self.terminal.decide(state), state=state)
