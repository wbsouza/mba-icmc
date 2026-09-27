# Spec 04 — algo-backtest: order-execution engine (LEAN integration) + filter chain (F1–F7) + hybrid strategy

**Tool:** `algo-suite/algo-backtest/` · **Status:** Done (2026-09-26) — all
lanes (04a-04h) landed; `baseline`/`hybrid` both run against the real pinned
LEAN container producing a `decisions.parquet`↔`trades.json` `trade_id` join.
Still a wiring smoke test, not a methodology result — see
`docs/technical-debt.md` TD-51.
**Blocks:** Spec 06 (Ch.4 hybrid results); partially blocks the tail of Spec 05
(ablation needs real hybrid runs, though Spec 05's machinery is built against
existing price-only runs first).
**Depends on:** Spec 03 landed — real per-pair sentiment/event Parquet on disk.
**Governing contracts:** [`algo-suite/algo-backtest/SPEC.md`](../../../../algo-backtest/SPEC.md) (engine integration,
`FilterResult`/`ExecutionState`/`Decision`/`FilterChain` model, `filters/`
package layout, §4.1 sequence diagram, §"Feature: Deterministic filter chain"
Gherkin) **and** [`specs.md`](../../../../specs.md) §6 (execution-engine choice: LEAN, Apache 2.0,
official OANDA broker adapter, Python algorithms) and §11 (the full
architectural rationale — agentic perception vs. deterministic execution, the
F1–F7 filter table §11.3.2, the per-strategy Mermaid-diagram convention
§11.3.3, the audit-trail format §11.3.4, the fx-manager port map §14 for the
risk/capital-management filters' formulas).

**User directive this spec exists to satisfy explicitly:** "one of the first
big chunk is to create the engine to execute the orders integrated with the
open source engine that does the real order execution, including the tests
scenarios in cucumber (gherkin language)." That is §3 below — read it first;
it is the highest-priority sub-deliverable of this spec, not an afterthought.

## 1. Objective

Three deliverables, in this order:

1. **The order-execution engine** (§3) — the integration point where this
   codebase's decisions become real orders inside **LEAN**, the open-source
   engine (Apache 2.0, QuantConnect) chosen specifically because it does *real*
   order execution against a broker adapter (`Lean.Brokerages.Oanda`), not a
   toy fill simulator — [`specs.md`](../../../../specs.md) §6.2. This is buildable and testable now,
   independent of Spec 03, using the strategies that already exist
   (`baseline_ma`/`baseline_meanrev`) as the proving ground, then reused by
   the filter chain in §4.
2. **The filter chain engine** (§4) — `FilterResult`, `ExecutionState`,
   `Decision`, `FilterChain`, and the F1–F7 filters as pluggable classes,
   config-driven (YAML, per [`specs.md`](../../../../specs.md) §14.9), with the audit trail persisted
   as `decisions.parquet` (§11.3.4).
3. **Strategy A05 / "hybrid"** (§5) — the concrete filter-chain wiring
   described in [`specs.md`](../../../../specs.md) §11.3.2/§11.3.3, terminating in the order-execution
   engine from §3.

## 2. Why order execution comes first inside this spec

The filter chain's terminal step — the "order executor" — is not a new
abstraction to invent; it is the existing LEAN integration, generalized from
the two hardcoded price-only strategies to a config-driven chain output. Per
[`specs.md`](../../../../specs.md) §11.3.1.1: "The order executor is itself just the terminal filter…
its `apply()` always emits one of the four final decisions… and the executor's
job is to interpret the accumulated context and either place an order, manage
an existing position, or stand aside." Building and testing that
LEAN-order-execution integration in isolation first — before the filter chain
exists to drive it — means it can be verified against LEAN's real
(containerized, pinned-image) execution semantics without also debugging F1–F7
at the same time.

## 3. Order-execution engine — LEAN integration (build and test this first)

### 3.1 What "real order execution" means here

LEAN is chosen ([`specs.md`](../../../../specs.md) §6.2) specifically because it has an **official
OANDA broker adapter** and a real event-driven order lifecycle — not because
it's merely a data replay loop. The order-execution engine is the code path
that:

1. Takes a `Decision` (`BUY` / `SELL` / `HOLD` / `NO_TRADE`, per
   [`specs.md`](../../../../specs.md) §11.3.1.1) plus the sizing/risk context accumulated in
   `ExecutionState.features`.
2. Calls LEAN's real order primitives — `self.MarketOrder(...)` (or the
   appropriate order type once F6 capital-management/stop-loss sizing is
   wired, §14.5) — inside the `QCAlgorithm` subclass.
3. Handles the **asynchronous order-event callback**, `OnOrderEvent`, which is
   how LEAN reports fills/rejections back to the algorithm — this collapses
   the legacy `fx-manager` state machine's "waiting for MT4 reply" states
   ([`specs.md`](../../../../specs.md) §14.6: `ORDER_SEND_REQUESTED`/`ORDER_INFO_REQUESTED` →
   collapsed into `self.MarketOrder(...)` + `OnOrderEvent`; `WAITING_FEEDBACK`
   → gone, LEAN events are synchronous from the strategy's point of view).
4. Persists the resulting fill (price, timestamp, order id) into the trade
   ledger (`trades.parquet`, already the contract `algo-analyze` Spec 05
   reads).

### 3.2 Scope for this sub-deliverable

- Confirm what the existing `baseline_ma`/`baseline_meanrev` algos
  (`algo_backtest/algos/*/main.py`) already do for order placement — they are
  presumably already calling `MarketOrder`/handling fills, since price-only
  backtests already produced real numbers ([`first-baseline-results.md`](../../../first-baseline-results.md)). If
  so, this sub-deliverable is **extracting** that into a reusable
  `OrderExecutor` component both the existing algos and the future filter
  chain (§5) call, not writing order execution from scratch. Read those two
  files before writing anything; do not duplicate working code.
- If order handling is currently inlined per-algo, factor it into a shared
  module (e.g. `algo_backtest/execution/order_executor.py`) with a narrow
  interface: given a `Decision` + sizing context, place the order, await/handle
  `OnOrderEvent`, return a normalized fill record. This is what the filter
  chain's terminal `apply()` calls in §5.
- Do not invent new order types beyond what the strategy needs at this stage
  (market orders with a stop-loss/take-profit per the capital-management
  filter's sizing, §14.5) — LEAN supports more order types than this project
  needs; scope to what F6/F7 actually require.
- OANDA live/paper brokerage (`Lean.Brokerages.Oanda`) itself is **Phase 6,
  out of scope for this spec** ([`PRD.md`](../../../../PRD.md) §6: "Phase 6 is a stretch goal, off
  the TCC freeze critical path"). This spec's order-execution engine targets
  the **backtest** order path (LEAN's simulated brokerage in backtest mode),
  which is the same `MarketOrder`/`OnOrderEvent` API surface OANDA live mode
  would use later — so building it correctly now costs nothing extra and
  keeps Phase 6 a config/brokerage swap, not a rewrite, per [`specs.md`](../../../../specs.md) §11.5.

### 3.3 Gherkin test scenarios (explicit deliverable — cucumber/pytest-bdd)

Add `tests/features/order_execution.feature` (or extend the existing
integration-test suite under `algo-backtest/tests/integration/` if that's
where LEAN-container tests already live — check first, do not create a
parallel test location). These scenarios exercise the **real, pinned LEAN
container** (`quantconnect/lean:17748`, per the testcontainers pattern already
proven for the Parquet→lean-data path, [`technical-debt.md`](../../../technical-debt.md) TD-19), not a mock
of LEAN — the whole point is proving integration with the actual open-source
execution engine:

```gherkin
Feature: Order execution through the LEAN engine
  Background:
    Given a pinned LEAN engine container running the backtest brokerage
    And a materialized lean-data store for EURUSD covering one trading day

  Scenario: A BUY decision places a real market order and the fill is recorded
    Given a strategy that emits one BUY decision at a known bar
    When the backtest runs through the order-execution engine
    Then LEAN places a market order for that bar
    And an OnOrderEvent fill is received
    And the fill (price, timestamp, order id) is written to trades.parquet

  Scenario: A SELL decision places a real market order in the opposite direction
    Given a strategy that emits one SELL decision at a known bar
    When the backtest runs through the order-execution engine
    Then LEAN places a sell-side market order
    And the resulting trade record shows a short position opened

  Scenario: HOLD manages an existing position without opening a new order
    Given an open position from a prior BUY
    And a strategy that emits HOLD at the current bar
    When the backtest runs through the order-execution engine
    Then no new order is placed
    And the existing position's stop/trail state is evaluated per the capital-management filter

  Scenario: NO_TRADE places no order
    Given no open position
    And a strategy that emits NO_TRADE at the current bar
    When the backtest runs through the order-execution engine
    Then no order is placed
    And no trade record is created for that bar

  Scenario: An order rejection is handled, not silently dropped
    Given LEAN rejects an order (e.g. insufficient margin)
    When the order-execution engine receives the OnOrderEvent rejection
    Then the rejection is recorded in the run's audit trail
    And the backtest continues to the next bar rather than crashing

  Scenario Outline: Stop-loss and take-profit levels are attached at order placement
    Given a strategy that emits <decision> with a capital-management-filter-computed stop distance
    When the order-execution engine places the order
    Then the order carries a stop-loss at the computed level
    And the fill record's risk parameters match the capital-management filter's output

    Examples:
      | decision |
      | BUY      |
      | SELL     |
```

Prune/adapt per the project's own Gherkin discipline (CLAUDE.md: every test is
Gherkin, no plain `def test_…()`); these scenarios are a starting draft, not a
frozen spec — the implementing agent should validate them against what LEAN's
`OnOrderEvent` payload actually contains before finalizing assertions.

## 4. The filter chain engine (F1–F7)

Once §3's order-execution engine exists and is proven, build the filter chain
around it:

1. **Chain mechanics first, filters as stubs.** `FilterResult`,
   `ExecutionState`, `FilterChain.run()` per the dataclasses already given
   verbatim in `specs.md` §11.3.1 — copy that shape, it's already designed.
   Prove accumulation, veto short-circuit, and abstain-does-not-veto with
   trivial stub filters before wiring real ones.
2. **F1–F3 (price-derived: trend, indicator, pattern).** Consume TA features
   LEAN computes natively. No new external data dependency — buildable and
   testable immediately.
3. **F5/F6 (risk guard, capital management).** Port from `fx-manager` per
   `specs.md` §14.5–§14.8 (lot-size formula, trail-stop math, the `RiskGuard`
   gap-closing parameters — `risk=0.03`, `STOP_LEVEL_FACTOR=1.2`, etc., all
   given verbatim). A regression test should verify the Python port reproduces
   the legacy decisions on identical synthetic input (§14.3's stated
   discipline). Independent of news data — buildable in parallel with step 2.
4. **F4 (news-context filter).** Consumes Spec 03's per-pair sentiment + event
   features; vetoes on active high-risk events (`specs.md` §11.3.2).
5. **F7 (threshold-rule filter / meta-learner).** LightGBM sub-models per
   feature family + logistic meta-learner combining them into `p̂ₜ`
   (`PRD.md` §1). Train on the walk-forward split (`PRD.md` §4).
6. **Wire the terminal filter to §3's `OrderExecutor`.** F7 (or an explicit
   order-executor step after it, per `specs.md` §11.3.1.1) calls the
   order-execution engine built in §3 — this is the join point between the
   two halves of this spec.

## 5. Strategy configs: baseline vs hybrid

`baseline` (chain without F4, or F4 forced ABSTAIN) and `hybrid` (full chain)
as YAML, via `extends:` composition (`experiments.md` §1: "hybrid extends
baseline adding F4"). Note `technical-debt.md` TD-8 — general `extends:` cycle
detection is out of MVP scope; a flat, non-cyclic two-level `extends` does not
need that machinery.

Also build **Experiment 0** (`experiments.md` table row 0) —
`buyhold`/`random`/`perfect_foresight` known-answer strategies through the
same chain and the same order-execution engine. Build these early: they're
cheap and they're what makes every later Sharpe number trustworthy.

## 6. Test requirements (beyond §3.3)

- `specs.md` §11.3.1's dataclasses and `FilterChain.run()` loop are given —
  use them as-is or justify a deviation in the tool SPEC.md.
- `algo-backtest/SPEC.md` §"Feature: Deterministic filter chain" already has
  Gherkin scenarios (chain-with-F1..F7, F1-enriches-state-with-trend_score);
  extend that file rather than starting a new one.
- VETO vs ABSTAIN is a named test dimension per filter — every filter that can
  veto needs a scenario proving it does; every filter that can abstain needs a
  scenario proving abstain doesn't short-circuit the chain.
- The audit trail (`decisions.parquet`, §11.3.4 columns) is a tested,
  cross-tool contract — Spec 05 (`algo-analyze`) joins on `trade_id` from it.

## 7. Definition of done

- The order-execution engine (§3) runs against the real pinned LEAN container,
  all §3.3 Gherkin scenarios green, and both existing price-only algos are
  migrated to call it (no duplicated order-placement code left inline).
- `algo-backtest run --strategy baseline --symbol EURUSD` and
  `--strategy hybrid --symbol EURUSD` both run through the same chain engine
  with different configs (`experiments.md` Experiment 1/2 commands).
- Engine sanity checks (Experiment 0) land where expected before any hybrid
  number is trusted.
- `decisions.parquet` audit trail persisted per run, joinable to
  `trades.parquet` by `trade_id`.
- Every strategy directory has the Mermaid filter-chain diagram convention
  (`specs.md` §11.3.3) in its own README.
- `make check`, `make audit` green.
- Tool SPEC.md updated to describe the order-execution engine and filter chain
  as built (not just planned); `00-PLAN.md` §1 and `ch04-deliverables.md`
  status column updated for §4.4 Hybrid.
