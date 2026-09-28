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
- [x] T2 Add F1 momentum context
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

### 2026-09-28 — T2: Add F1 momentum context (CC-06..CC-08, CC-20, CC-28)

- What: `chain/filters/f1_trend.py` gains the selectable variant beside the untouched
  `F1TrendFilter`: `MomentumContextConfig` / `parse_momentum_context_config` /
  `momentum_context_mapping` (section `momentum_context`, key `lookback_bars` = L, a
  positive integer; bool/float/string/null/unknown keys rejected), `MomentumHistory(L)`
  (pure bounded buffer of the last L+1 completed closes; `push(close_time, close)` needs
  aware-UTC strictly increasing times and finite positive closes; a rejected push leaves
  it unchanged) and `F1MomentumContextFilter(config, history)` (filter_name `F1_trend`;
  BUY/SELL/NEUTRAL by the sign of `close[t]/close[t-L]-1`; ABSTAIN with reason
  `WARMUP: n of L+1 closes` until then; never vetoes; reads no `state.features`).
  Whether an *expected* close is missing is the feed's coverage contract (T9/T13), as
  the module docstring records.
- Scenario correction (structural, no outcome changed): `confluence_momentum.feature`
  had two `Scenario Outline: <case>` with identical titles; pytest-bdd named both
  `test_case` and the second silently replaced the first, dropping the six CC-06 vote
  rows (32 collected instead of 38). Retitled them `with L+1 closes, <case>` and
  `short of L+1 closes, <case>`; 38 now collect. The other four features have no
  duplicate titles (checked).
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_confluence_momentum.py -q -p no:cacheprovider`
  → 38 collected, 38 passed; with `test_f1_trend.py` → 51 passed;
  `uv run ruff check algo-backtest` clean; `ruff format --check` clean on the two files
  of this task; `uv run mypy --strict algo-backtest` → no issues.
- Status updates: tasks.md T2 both boxes; spec.md CC-06, CC-07, CC-08, CC-28 →
  `Implemented (T2)`; CC-20 → `Implemented (T1, T2)`.
- Next: T3.
