# Story 12 — progress

Wave 1 (parallel worktrees, merged by the lead):
- [x] A — `capital_mgmt` plan keys + `execution` section + parsers + provenance + `strategy-config.yaml` artifact + YAML/README/SPEC
- [x] C — spread slippage + per-lot commission models from `execution`, pure math with BDD
- [x] E — `price_features.atr_period`, ATR indicator + `atr_pips` feature, offline parity
- [x] F — controls and legacy baselines take `cash` (TD-65 resolved), experiment specs
- [x] H — end-of-run broker-style `statement.md` + `equity.png`, `algo-backtest statement --run` for existing runs

Wave 2:
- [ ] B — F6 builds the trade plan (stop, lot, targets, trail, reward:risk veto)
- [ ] D — executor places sized market + stop + target orders, partial close, trail, min hold; `size` dropped

Wave 3 (lead):
- [ ] Consolidation: merge, full `make test`, ruff, mypy, architecture gates
- [ ] Integration scenarios: stop fill, target partial close, trail move, spread cost
- [ ] Rerun 2015-09 baseline + hybrid from $10,000 with A05 values; Oct–Nov confirmation
- [ ] Gauntlet: CRAP, mutation pass, QA script and procedure
- [ ] Docs: SPEC, READMEs, technical-debt (TD-46, TD-51 execution part, TD-65), thesis §3, story 09 follow-up
- [ ] PR
