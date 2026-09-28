# Story 21 — progress

- [x] 2026-09-28 — planned from the signal-horizon check (`evidence/signal-horizon-check.md`): chain
  contract, thresholds by rule, engine additions, 14 registered cells, endpoints. No code, no run.
- [x] 2026-09-28 — January-2016 level shift checked: coverage uniform, the month is an outlier in the
  event mix; table and consequences in `evidence/signal-horizon-check.md`.
- [ ] Engine: agreement terminal, momentum context, relative intensity thresholds, bar-count exit.
- [ ] Registration, runs, inference, Chapter 4/5.

## Working tree and ownership (implementation, 2026-09-28)

- Agent: Claude coder, Lane B (Story 21), gauntlet CODER stage; the Gherkin was written by
  the SPECIFIER stage and treated as the spec.
- Worktree: `/tmp/mba-impl-21`; branch `feat/21-confluence-chain`; base SHA `ef0111d`
  (planning docs on top of merged PR #88).
- Plan of record: `.specs/features/confluence-chain/{spec,design,tasks}.md` (T1..T22).
- Baseline before Phase 1, `cd algo-suite && uv run pytest algo-backtest/tests -q --co -p no:cacheprovider`:
  1598 collected / 53 deselected (exit 0).
- Pre-existing: `uv run ruff format --check algo-backtest` fails on 66 files at the base
  SHA (among them `f4_news_context.py`, `f6_capital_mgmt.py` and their step files). New
  files are format-clean; touched legacy files are not reformatted wholesale (surgical
  diffs), so the package-wide format check stays a pre-existing failure until a separate
  chore commit.

## Task checklist (mirrors `.specs/features/confluence-chain/tasks.md`)

- [x] T1 Add the named agreement terminal
- [ ] T2 Add F1 momentum context
- [ ] T3 Calculate immutable monthly intensity snapshots
- [ ] T4 Add F4 relative intensity mode
- [ ] T5 Define the optional F6 bar-count plan
- [ ] T6 Model causal expiry as a pure lifecycle
- [ ] T7 Provide explicit drift-control votes
- [ ] T8 Build a separate evidence-unit re-derivation tool
- [ ] T9 Gate data population and point-in-time availability
- [ ] T10 Generate the fixed fourteen-cell manifest
- [ ] T11 Register configuration and provenance contracts (integration lane)
- [ ] T12 Wire approved collaborators and runtime voter names (integration lane)
- [ ] T13 Integrate closed history and actual-event expiry (integration lane)
- [ ] T14 Record expiry evidence against the closing trade (integration lane)
- [ ] T15 Define the additive exit-audit schema (integration lane)
- [ ] T16 Freeze the review-approved registration README
- [ ] T17 Build a bounded fourteen-cell launch harness
- [ ] T18 Implement the registered comparison report
- [ ] T19 Produce the fourteen-cell evidence report
- [ ] T20 Place the registered Chapter 4 protocol (manuscript lane)
- [ ] T21 Write the qualified Chapter 5 conclusion (manuscript lane)
- [ ] T22 Document the accepted public tool contract (integration lane)

## Implementation log

### 2026-09-28 — T1: Add the named agreement terminal (CC-01..CC-05, CC-20)

- What: `AgreementTerminalDecision(required_filters, voter_name_map)` added to
  `algo-backtest/src/algo_backtest/chain/terminal.py` beside the two legacy terminals.
  Construction rejects an empty map, an empty/duplicated required list, a gate name
  (`f5_risk_guard`, `f6_capital_mgmt`, `volume_strength`) and any name absent from the
  closed canonical→runtime map (listing the known voters). `decide` raises when a
  required voter ran zero or several times; HOLD unless every required voter cast the
  same BUY/SELL and no other voter holds or votes against it. It never vetoes.
- Tests: `tests/features/confluence_agreement.feature` (specifier) +
  `tests/steps/test_confluence_agreement.py` (new). No scenario corrected. The CC-05 rows
  run the real `FilterChain` with the real `RiskGuardFilter`/`CapitalMgmtFilter` parsed
  from the feature's YAML and count terminal consultations (0 after a veto).
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py -q -p no:cacheprovider`
  → 45 collected, 45 passed; plus `test_filter_chain_mechanics.py` → 74 passed together;
  `uv run ruff check algo-backtest` clean; `uv run ruff format --check` clean on the two
  files of this task; `uv run mypy --strict algo-backtest` → 63 source files, no issues.
- Status updates: tasks.md T1 both boxes; spec.md CC-01..CC-05 and CC-20 → `Implemented (T1)`.
- Next: T2.
