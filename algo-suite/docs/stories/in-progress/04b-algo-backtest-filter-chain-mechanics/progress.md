# Progress — Spec 04b (filter-chain mechanics)

Single-file boundary (`chain/model.py` + one new feature file) — tasks run sequentially,
one coder pass then one hardener pass, not parallel workers (avoids same-file races).

- [ ] T1 — `tests/features/filter_chain_mechanics.feature`: 3 stub-filter scenarios
      (accumulation, veto short-circuit, abstain-does-not-veto)
- [ ] T2 — `chain/model.py`: `Recommendation` + `Decision` enums
- [ ] T3 — `chain/model.py`: `FilterResult`, `ExecutionState`, `ChainOutcome` dataclasses
- [ ] T4 — `chain/model.py`: `Filter` + terminal-decision protocols, `FilterChain.run()`
      (accumulate / veto-short-circuit / abstain-does-not-veto), returns `ChainOutcome`
- [ ] T5 — `tests/steps/test_filter_chain_mechanics.py`: step defs + stub filters, scenarios green
- [ ] T6 — sync `algo-backtest/SPEC.md`'s existing "Feature: Deterministic filter chain"
      outline (cross-reference the new stub-mechanics feature file)
- [ ] T7 — gate: `make check` green; mutation pass on `chain/model.py`
      (`uv run python tools/mutation_harness.py algo-backtest --paths src/algo_backtest/chain/model.py`
      or `mutmut`), surviving mutants killed or logged to `technical-debt.md` with rationale
- [ ] `lessons-learned.md` written, story moved to `docs/stories/done/`
