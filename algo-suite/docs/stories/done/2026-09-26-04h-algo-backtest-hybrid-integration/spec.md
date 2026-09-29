# Spec 04h — algo-backtest: hybrid strategy integration (lane of Spec 04, Wave 4 — final)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §4 step 6, §5, and §7
(Definition of Done) for full context.
**Depends on:** Spec 04a (`OrderExecutor`) and Spec 04g (F7) both landed.
**Blocks:** Spec 06 (Chapter 4 hybrid results).
**Order:** Wave 4 — last lane of Spec 04, start once 04a and 04g both merge.
**Boundary:** wires existing pieces together — `chain/model.py`'s terminal step, new
`strategies/*/config.yaml`, `algos/experiment_zero/` (buyhold/random/perfect_foresight), plus doc
updates.

## Objective

- Wire F7's terminal step to `OrderExecutor` (04a) — the join point between the two halves of the
  parent spec.
- `baseline` (chain without F4)/`hybrid` (full chain) strategy YAML via `extends:` composition
  (`experiments.md` §1).
- Experiment 0 — `buyhold`/`random`/`perfect_foresight` known-answer strategies through the same
  chain + executor; validates every later Sharpe number.
- End-to-end integration test: `algo-backtest run --strategy hybrid --symbol EURUSD` runs through
  the full chain; `decisions.parquet` (04f) joins `trades.parquet` by `trade_id`.
- Mermaid filter-chain diagram per strategy README (`specs.md` §11.3.3).

## Definition of done

Everything in the parent spec's §7 Definition of Done. Update `algo-backtest/SPEC.md`, `00-PLAN.md`
§1, `ch04-deliverables.md` status column, and move the parent `04-algo-backtest-filter-chain-hybrid/`
story (and this lane) to `done/<YYYY-MM-DD>-algo-backtest-filter-chain-hybrid/` per the swarmforge
constitution's story-lifecycle rule, with a `lessons-learned.md`.
