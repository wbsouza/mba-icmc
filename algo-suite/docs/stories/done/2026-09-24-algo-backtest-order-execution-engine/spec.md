# Spec 04a — algo-backtest: order-execution engine (lane of Spec 04, Wave 1)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §3 for full context,
Gherkin draft, and house rules. Task breakdown: `04-algo-backtest-filter-chain-hybrid/tasks.md`,
Track A (T1–T5).
**Depends on:** nothing. **Blocks:** Spec 04h (hybrid integration) only.
**Order:** Wave 1, lane A — start now, in parallel with 04b.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/engine/` (new: `order_executor.py`,
`algorithm.py`, `brokerage/`), plus mechanical edits to `algos/baseline_ma/main.py` and
`algos/baseline_meanrev/main.py` to call the new `OrderExecutor`. Do not touch `chain/*` (04b's lane).

## Objective

Extract `OrderExecutor` from the two existing baseline algos' inline order-placement code, build the
`QCAlgorithm` skeleton (`engine/algorithm.py`) wired to it, and prove the 6 Gherkin scenarios from
the parent spec §3.3 against the real pinned LEAN container. Include the brokerage-adapter port
(`engine/brokerage/`, `BrokerageAdapter` ABC + registry, first concrete adapter `oanda.py` calling
`self.set_brokerage_model(BrokerageName.OANDA, AccountType.MARGIN)`) so the fill/fee/spread model is
config-selected, not hardcoded — mirrors `algo_download`'s `NewsDataSource`/`REGISTRY` pattern.

## Definition of done

- `OrderExecutor`, `engine/algorithm.py`, and the brokerage-adapter registry exist and are used by
  both baseline algos (no duplicated order-placement code left).
- `tests/features/order_execution.feature` green against the real LEAN container (TD-19 pattern).
- `make check` green.
