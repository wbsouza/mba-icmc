# Spec 04b — algo-backtest: filter-chain mechanics (lane of Spec 04, Wave 1)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §4 step 1 and
`specs.md` §11.3.1 (dataclasses, verbatim) for full context. Task breakdown:
`04-algo-backtest-filter-chain-hybrid/tasks.md`, Track B (T6–T7).
**Depends on:** nothing. **Blocks:** Spec 04c, 04d, 04e, 04f (Wave 2 — all four gate on this).
**Order:** Wave 1, lane B — start now, in parallel with 04a.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/chain/model.py` only, plus
`tests/features/filter_chain_mechanics.feature`. Do not touch `engine/*` (04a's lane) or any
`chain/filters/*.py` (those are Wave 2's lanes).

## Objective

`FilterResult`, `ExecutionState`, `Decision`, `ChainOutcome`, `FilterChain` — copy the dataclass
shapes verbatim from `specs.md` §11.3.1; implement `FilterChain.run()`'s accumulate /
veto-short-circuit / abstain-does-not-veto loop. Prove it with 2–3 trivial stub filters
(constant VETO/ABSTAIN/PASS) before any real F1–F7 filter exists — extend the existing
"Feature: Deterministic filter chain" outline in `algo-backtest/SPEC.md` rather than starting new.

## Definition of done

- `chain/model.py` implements the full dataclass set + `FilterChain.run()`.
- Stub-filter scenarios prove accumulation, veto short-circuit, and abstain-does-not-veto.
- `make check` green.
