# Progress — Spec 04h (hybrid strategy integration, final)

- [ ] Wire F7 terminal step to `OrderExecutor` (04a)
- [ ] `baseline`/`hybrid` strategy YAML via `extends:` composition
- [ ] Experiment 0 — buyhold/random/perfect_foresight known-answer strategies
- [ ] End-to-end integration test: `algo-backtest run --strategy hybrid --symbol EURUSD`
- [ ] `decisions.parquet` joins `trades.parquet` by `trade_id` (end-to-end check)
- [ ] Mermaid filter-chain diagram per strategy README
- [ ] Update `algo-backtest/SPEC.md`, `00-PLAN.md` §1, `ch04-deliverables.md`
- [ ] Move `04-algo-backtest-filter-chain-hybrid/` (+ lanes) to `done/`, add `lessons-learned.md`
- [ ] `make check` + `make audit` green
