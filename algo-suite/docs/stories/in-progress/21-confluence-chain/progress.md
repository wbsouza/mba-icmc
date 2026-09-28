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
- [x] T3 Calculate immutable monthly intensity snapshots
- [x] T4 Add F4 relative intensity mode
- [x] T5 Define the optional F6 bar-count plan
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

### 2026-09-28 — T3: Calculate immutable monthly intensity snapshots (CC-09, CC-10, CC-13, CC-14, CC-31)

- What: new pure module `chain/intensity_history.py`: `calibration_window(t)` (fixed UTC
  month start M and M-30d), `IntensityObservation` (aware-UTC `bar_closed_at` and
  `available_at`, finite intensity, non-empty `source_id`; null availability or an empty
  source is refused), `IntensityHistory(clock_minutes, collection_started_at)` with
  `declare_closure(start, end)` (documented closures as an explicit input, coordinator
  decision 4), `record(observation)` (clock-grid and strict chronological order; a
  rejected row leaves the history unchanged) and `snapshot_for(decision_time)` (cached
  per cutoff, so the month is frozen and a mid-month start rebuilds the same one).
  Sample = one observation per completed bar with close in `[M-30d, M)` and
  `available_at < M`; a row available at/after M satisfies coverage but leaves the
  sample (coordinator decision 1). Coverage of every grid close (closures exempt) is
  checked only when the declared collection reaches `window_start`; otherwise the
  snapshot is `WARMUP` with null quantiles. Linear quantiles at `(n-1)q` in pure Python
  (numpy `linear` semantics, cross-checked). `IntensitySnapshot` carries the 12
  provenance fields (status READY/WARMUP, quantile_method "linear", schema_version 1,
  coordinator decision 3) and round-trips via `as_mapping`/`from_mapping`.
- Scenario correction: `confluence_history.feature`, scenario "a gap inside a documented
  market closure is not a missing bar": the expected `q_high` 1.37 contradicted the
  spec's own quantile definition. Removing the 2016-03-18 row drops the value 1.40; the
  29-value sample interpolates index 25.2 between 1.30 and 1.35 → 1.31 (numpy
  `quantile(..., 0.9, method="linear")` agrees: 1.31). Cell changed to 1.31; `q_low`
  0.19 was already right.
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_confluence_history.py -q -p no:cacheprovider`
  → 32 collected, 32 passed; `uv run ruff check algo-backtest` clean (C901 included);
  `ruff format --check` clean on the two new files; `uv run mypy --strict algo-backtest`
  → 64 source files, no issues.
- Status updates: tasks.md T3 both boxes; spec.md CC-09, CC-10, CC-13, CC-14, CC-31 →
  `Implemented (T3)`.
- Next: T4.

### 2026-09-28 — T4: Add F4 relative intensity mode (CC-09..CC-12, CC-14, CC-20, CC-31)

- What: `chain/filters/f4_news_context.py` gains `direction_source: intensity_relative`.
  `F4NewsContextFilter` takes two injected sources, `snapshots` (cutoff →
  `IntensitySnapshot`) and `availability` (decision minute → `available_at`), both
  required in relative mode and refused at construction when absent (snapshots checked
  first; coordinator decision 7). Vote after the veto: unswapped sign 1 is I >= q90 →
  BUY, I <= q10 → SELL (decision 6); the registered sign -1 swaps it; strictly between
  → NEUTRAL; q10 == q90 → HOLD ("degenerate snapshot"); WARMUP → HOLD with no static
  fallback; an intensity available after the decision minute, a minute without an
  availability record, or a month without a snapshot raises. The static thresholds are
  refused under any non-`intensity` source. Metadata carries the six snapshot
  provenance fields beside `sentiment_source_present`; the static and sentiment
  branches are unchanged (the shared band helper reproduces the story-14 rule exactly).
- Legacy feature extension (coordinator decision 5): `f4_news_context.feature`'s
  "unknown source" example now expects the choices list
  `['intensity', 'intensity_relative', 'sentiment']` — the only diff in that file.
- Scenario correction: `confluence_relative_intensity.feature`, outline "WARMUP holds
  at intensity <intensity>": the example `an extreme low intensity | -3.0` sits below
  the scenario's own veto threshold -0.5, so the veto fires first (the feature's
  preamble and the design keep the veto ahead of every direction source) and the row
  could never be a non-veto HOLD. Replaced by `a low intensity above the veto | -0.4`;
  the WARMUP-holds outcome is unchanged.
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_confluence_relative_intensity.py -q -p no:cacheprovider`
  → 40 collected, 40 passed; with `test_f4_news_context.py` and
  `test_filter_chain_mechanics.py` → 118 passed; `uv run ruff check algo-backtest`
  clean; `ruff format --check` clean on the new step file (`f4_news_context.py` was
  already on the pre-existing would-reformat list; not reformatted wholesale);
  `uv run mypy --strict algo-backtest` → no issues.
- Status updates: tasks.md T4 both boxes; spec.md CC-11, CC-12 → `Implemented (T4)`;
  CC-09, CC-10, CC-14, CC-31 → `Implemented (T3, T4)`; CC-20 → `Implemented (T1, T2, T4)`.
- Next: T5.

### 2026-09-28 — T5: Define the optional F6 bar-count plan (CC-20, CC-21, CC-22)

- What: `chain/filters/f6_capital_mgmt.py` gains `CapitalMgmtConfig.exit_after_bars:
  int | None = None` (N). Absent or `null` → None and the legacy plan byte for byte:
  `capital_mgmt_mapping` and the `trade_plan` enrichment carry the key ONLY when set
  (coordinator decision 10), so legacy resolved-config sidecars are unchanged. A bool,
  float (even whole), zero, negative, string or list is rejected with the full
  remediation ("... must be a positive integer (completed signal bars to hold; the exit
  is submitted at the open of bar t+N) or null to disable, got X — fix
  strategies/<name>/config.yaml"). N may coexist with targets at parse time (decision
  9); the time arms use `targets: []`/`trail_stops: []`, so no target and no
  reward:risk veto, while the ATR stop, shrink, floors, spread, lot and margin veto
  still apply. The accepted D5 bar-open timing contract is recorded in the module
  docstring (item 5) next to the field; the lifecycle itself is T6.
- Scenario correction (per coordinator decision 10): `confluence_capital_plan.feature`,
  scenario "a five-key section resolves exit_after_bars to null ...": the line
  `And the capital-mgmt mapping records exit_after_bars null` became
  `And the capital-mgmt mapping has no key "exit_after_bars"`.
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_confluence_capital_plan.py -q -p no:cacheprovider`
  → 25 collected, 25 passed; with `test_f6_capital_mgmt.py`,
  `test_strategy_config_artifact.py`, `test_strategies.py`, `test_strategy_explain.py`
  → 312 passed; `f6_capital_mgmt.feature` unchanged; `uv run ruff check algo-backtest`
  clean; `ruff format --check` clean on the new step file (`f6_capital_mgmt.py` was on
  the pre-existing would-reformat list; not reformatted wholesale);
  `uv run mypy --strict algo-backtest` → no issues.
- Status updates: tasks.md T5 both boxes; spec.md CC-21, CC-22 → `Implemented (T5)`;
  CC-20 → `Implemented (T1, T2, T4, T5)`.
- Next: Phase 1 close-out (full suite counts), then T6 (Phase 2) in a later lane run.

### 2026-09-28 — Phase 1 close-out (T1..T5)

- Commits on `feat/21-confluence-chain` (pushed to origin): T1 `c760b76`, T2 `97e766a`,
  T3 `8a7b8f0`, T4 `0e3a1b7`, T5 `1ad1adf`.
- Full offline suite, cwd `algo-suite`, `uv run pytest algo-backtest/tests -q -p no:cacheprovider`:
  1778 passed, 53 deselected, 0 failed (exit 0). Collection 1778/1831 = baseline 1598 +
  45 (agreement) + 38 (momentum) + 32 (history) + 40 (relative intensity) + 25 (capital
  plan), exactly the specifier's counts.
- `uv run ruff check algo-backtest` clean; `uv run mypy --strict algo-backtest` → 64
  source files, no issues; `ruff format --check` clean on all 8 files this phase created
  or owns exclusively (`terminal.py`, `f1_trend.py`, `intensity_history.py`, the five
  `test_confluence_*.py`).
- Workspace `make lint` (195 findings) and `make type` (107 errors) fail on pre-existing
  files outside `algo-backtest` only: `docs/stories/done/**` (142 lint / 47 type),
  `scripts/bigquery_ctas_export_gdelt_{gkg,events}.py`, `scripts/bigquery_join_gdelt_events_gkg.py`,
  `tools/mutation_harness.py` (35 type), one `algo-viewer/tests/fixtures` file. None in
  `algo-backtest`. Recorded as BLOCKED-pre-existing for the workspace gate; the
  integration branch's chore commit owns it.
- Legacy CLI unchanged (CC-20): `algo-backtest explain-strategy news-rule` still resolves
  `direction_source = "intensity"` with no `intensity_relative`/`momentum_context`/
  `agreement`/`exit_after_bars` line; `git diff main -- strategies.py chain/wiring.py engine/`
  is empty (no integration-owned file touched).
- QA procedure: `qa-procedure-phase1.md` (specifier) committed with two alignments to the
  built code: Step 5's first expected line carries the actual `momentum_context WARMUP:`
  reason prefix; Step 13 scopes the lint/type expectation to `algo-backtest` and names
  the pre-existing workspace failures.

### 2026-09-28 — Cleaner phase 1 (T1..T5 modules: coverage, complexity, CRAP review)

Agent role: cleaner. Branch `feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`,
reviewed HEAD `7c9f96a` (phase commits `c760b76..7c9f96a`, base `ef0111d`). Tools:
`ruff check --select C901,PLR0912,PLR0915`, `mypy --strict`, `pytest --cov=algo_backtest.chain
--cov-branch` over the five `test_confluence_*.py` step files plus the legacy regressions
(`test_f1_trend.py`, `test_f4_news_context.py`, `test_f6_capital_mgmt.py`,
`test_filter_chain_mechanics.py`), radon 6.0.1 (`python -m radon cc -s`) for per-function
cyclomatic complexity; CRAP = cc² × (1 − coverage)³ + cc per function (coverage of the
function's own lines).

| File | cc max (radon) | Lines / branches (after) | CRAP max | Actions |
| --- | --- | --- | --- | --- |
| `chain/terminal.py` | 6 (`_required_vote`) — was 9 (`decide`) | 98 % / 96 % (only line 84, the legacy F7 terminal, uncovered — outside the phase diff); new code 100 % | 6 | `AgreementTerminalDecision.decide` split into `_agreed_direction` (the one BUY/SELL every required voter cast) and `_optional_blocks` (any non-required result that blocks it); behaviour identical |
| `chain/filters/f1_trend.py` | 7 (`MomentumHistory.push`) | 100 % / 100 % | 7 | Two uncovered raises (invalid `lookback_bars` at `MomentumHistory`, history/config lookback mismatch at `F1MomentumContextFilter`) covered by new scenarios |
| `chain/intensity_history.py` | 7 (`_compute`) | 100 % / 100 % (was 93 %: 7 lines, 7 branches) | 7 | `clock_minutes` check collapsed from two raises with the same message into one; six new scenarios cover the empty-sample quantile, the WARMUP mapping round trip (null times), non-ISO / naive mapping fields, a fully covered window with nothing available before the cutoff, invalid clocks, and a closure whose end is not after its start |
| `chain/filters/f4_news_context.py` | 8 (`load_news_context_index`, legacy) | 85 % / 100 % (uncovered 259–333 are the legacy Parquet index loader, outside every phase hunk); new code 100 % | 8 (legacy) | Two uncovered new raises (construction without an availability source; a decision minute without an availability record) covered by new scenarios; no source change |
| `chain/filters/f6_capital_mgmt.py` | 7 (`_level_entries`, legacy) | 100 % / 100 % | 7 | No change |

Review notes: every new function has a docstring; no dead code; no silent defaults
(every rejection names the value and the fix). Duplication judged and left in place, with
the reason: the positive-integer predicate (`_positive_int` in F1, inline in F6's
`_exit_after_bars` and in `IntensityHistory.__post_init__`) and the UTC check
(`_require_utc` in `intensity_history.py`, inline in `MomentumHistory.push`) would only
consolidate through a shared module (`chain/params.py` or `chain/model.py`); Phase 1
deliberately changed no shared file (see the close-out above), and the repo already keeps
one private UTC helper per module (`algo_core.bars`, `algo_transform.decoders.bi5`,
`algo_score.scorers.models`, `chain/model.py`), so a cross-module helper is the integration
lane's call, not a phase-1 cleanup. `linear_quantile` deliberately re-implements numpy's
`linear` method without numpy (the module docstring and `confluence_history.feature`
state the semantics); nothing else in `algo_backtest.chain` computes quantiles, so there
is no numpy helper to reuse. Names match `design.md` (`AgreementTerminalDecision`,
`voter_name_map`, `exit_after_bars`, snapshot fields).

Gate results (cwd `algo-suite`, all exit 0): the nine step files above → 397 passed
(378 before, 19 new scenario rows); `uv run ruff check algo-backtest` → clean;
`uv run ruff format --check` clean on the five files edited (f4/f6 untouched);
`uv run mypy --strict algo-backtest` → 64 files, no issues; `make
check-perception-architecture check-inference-architecture` → PASS / PASS. No test
assertion was changed; every addition is a new scenario or Examples row.

## Integration handoff (for T11..T15, integration lane)

- `chain/wiring.py` (T12): build `AgreementTerminalDecision(required_filters=<canonical
  names from YAML>, voter_name_map={"f1_trend": "F1_trend", "f2_indicator":
  "F2_indicator", "f3_pattern": "F3_pattern", "f4_news_context": "f4_news_context"})`;
  `F1MomentumContextFilter(config=parse_momentum_context_config(section, strategy=...),
  history=MomentumHistory(lookback_bars=config.lookback_bars))` when `momentum_context`
  is selected; `F4NewsContextFilter(index, config, snapshots={cutoff: IntensitySnapshot},
  availability={decision_minute: available_at})` when `direction_source:
  intensity_relative` (both mandatory; construction raises otherwise).
- `engine/chain_algorithm.py` (T13): feed `MomentumHistory.push(close_time, close)` once
  per completed signal bar from the same `ClosedBarClock` as the decision path; feed
  `IntensityHistory.record(IntensityObservation(...))` per completed bar from the
  provenance-bearing source (T9) and register documented closures via
  `declare_closure(start, end)`; preload enough history that March starts READY; call
  `snapshot_for(decision_time)` and hand the resulting `{cutoff: snapshot}` to F4. The
  trade plan carries `exit_after_bars` only when configured; T6's lifecycle consumes it.
- `strategies.py` (T11): sections `momentum_context` (`lookback_bars`) and
  `capital_mgmt.exit_after_bars`; `news_context.direction_source: intensity_relative`
  refuses `intensity_buy_threshold`/`intensity_sell_threshold`; `capital_mgmt_mapping`
  and `momentum_context_mapping` are the provenance mappings.
- No shared file was changed in Phase 1; no patch is pending for one.
