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
- [x] Rerun 2015-09 baseline + hybrid from $10,000 with reference values; September and October 2015 confirmation reruns under the execution model (Chapter 4 `sec:confirmation-results`, job `2026-09-27-execution-realism`); November was superseded by the one-year protocol below
- [x] One-year protocol run (spec.md): family models 2015-03-02..2015-12-31, calibration 2016-01, held-out 2016-02, simulation 2016-03-01..2016-10-31 (window extended to October 2016 on 2026-09-27 before the first bar was simulated); baseline and hybrid simulate in parallel (finished 2026-09-27 18:09 PT: baseline −88.41 %, hybrid −87.50 %, 1,029 trades each; story-13 evidence `predecessor-final-20260928T013528Z.md`)
- [x] Gauntlet: CRAP split (wave3/cleaner), mutation-hardening pass (commits 7d4a930 and 3d8b169 merged via integrate/story-12-13), QA script `evidence/qa_check.py` (39 scenarios) and `evidence/qa-procedure.md`
- [x] Docs: SPEC, READMEs, architecture, PRD, debt ledger, story 09 follow-up (TD-46 and TD-65 rows deleted as resolved; the debt ledger had no TD-51 row and the dangling TD-51 references were replaced; TD-66..68 added; story 09 stays in progress — its progress file has no checklist, its follow-up bullets are open)
- [x] Thesis §3 wording: execution model (spread, commission, plan, protective orders) in Chapter 3 `subsec:deterministic-execution` and Chapter 4 `subsec:execution-model` (PR #52, #66)
- [x] PR: #53, #54, #66 merged; story closed 2026-09-28 (lessons-learned.md)

## QA

- `evidence/qa-procedure.md` — the operator-point-of-view system test (explain-strategy,
  a `--param cash=10000` run with the bootstrap provenance print, run-directory inspection,
  report.html, `statement --run` regeneration, `algo-analyze equity-curves` over two runs,
  each step with its command, what to look at and its pass criterion) and
  `evidence/qa_check.py` — the deterministic gate (`uv run python
  docs/stories/done/12-execution-realism/evidence/qa_check.py <run_dir> [<run_dir>...]`,
  exit 0/1, one PASS/FAIL line per check; proven by
  `algo-backtest/tests/features/qa_check_story12.feature`, 39 scenarios, 2026-09-27).
