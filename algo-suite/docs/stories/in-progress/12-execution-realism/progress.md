# Story 12 — progress

Wave 1 (parallel worktrees, merged by the lead):
- [x] A — `capital_mgmt` plan keys + `execution` section + parsers + provenance + `strategy-config.yaml` artifact + YAML/README/SPEC
- [x] C — spread slippage + per-lot commission models from `execution`, pure math with BDD
- [x] E — `price_features.atr_period`, ATR indicator + `atr_pips` feature, offline parity
- [x] F — controls and legacy baselines take `cash` (TD-65 resolved), experiment specs
- [x] H — end-of-run broker-style `statement.md` + `equity.png`, `algo-backtest statement --run` for existing runs
- [x] H2 — `report.html` performance dashboard (KPI cards, SVG equity curve, tabs) beside the statement
- [x] H3 — `equity.csv` per run; `algo-analyze equity-curves` consolidates several runs (chained per strategy) into `equity-consolidated.{csv,png,html}`

Wave 2:
- [x] B — F6 builds the trade plan (stop, lot, targets, trail, reward:risk veto)
- [x] D — executor places sized market + stop + target orders, partial close, trail, min hold; `size` dropped

Wave 3 (lead):
- [x] Consolidation: merge, full `make test`, ruff, mypy, architecture gates (1,536 offline scenarios + 9 LEAN scenarios green, 2026-09-27)
- [x] Integration scenarios: stop fill, target partial close, trail move, spread cost (nine LEAN scenarios green 2026-09-27; `close_on_veto` defaults to false so planned exits govern the trade)
- [x] Cleaner: CRAP > 8 functions split, uncovered branches covered (wave3/cleaner)
- [ ] Rerun 2015-09 baseline + hybrid from $10,000 with A05 values; Oct–Nov confirmation
- [ ] Gauntlet: CRAP, mutation pass, QA script and procedure
- [x] Docs: SPEC, READMEs, architecture, PRD, debt ledger, story 09 follow-up (TD-46 and TD-65 rows deleted as resolved; the debt ledger had no TD-51 row and the dangling TD-51 references were replaced; TD-66..68 added; story 09 stays in progress — its progress file has no checklist, its follow-up bullets are open)
- [ ] Thesis §3 wording (handled outside the docs-sync stage)
- [ ] PR
