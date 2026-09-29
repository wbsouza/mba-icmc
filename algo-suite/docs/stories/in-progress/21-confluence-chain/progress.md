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
- [x] T16 Freeze the review-approved registration README
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

## 2026-09-28 — Hardener phase 1

Manual mutation testing (no `mutmut` in this workspace) of the five Phase 1
production modules: `chain/terminal.py` (`AgreementTerminalDecision`),
`chain/filters/f1_trend.py` (momentum context), `chain/intensity_history.py`
(whole module), `chain/filters/f4_news_context.py` (`intensity_relative` hunks),
`chain/filters/f6_capital_mgmt.py` (`exit_after_bars` hunks). 41 mutations
injected one at a time in the worktree (backup → mutate → run the nine covering
step files → restore → confirm the file's `git status --porcelain` clean), across
comparison boundaries, `==`/`!=`, sign flips, arithmetic, off-by-one, removed
validation raises and wrong constants, plus one negative control per module (5
total). All 41 KILLED. Two mutations survived on the first pass — `IH-4`
(`IntensityHistory._compute`'s WARMUP boundary, `collection_started_at >
window_start`) and `IH-5` (`declare_closure`'s `end <= start` guard) — both for
the same reason: no existing scenario hit the exact boundary value
(`collection_started_at == window_start`; closure `end == start`). Added two
scenarios to `confluence_history.feature` (44 → 46 scenarios in that file; no
step code changed) that assert the correct boundary behaviour; both mutants then
KILLED. Full table, operators and the two survivor write-ups:
`mutation-phase1.md`. Gates after restoring everything: `uv run pytest
algo-backtest/tests -q -p no:cacheprovider` → 1799 passed, 53 deselected;
`uv run ruff check algo-backtest` → clean; `uv run mypy --strict algo-backtest`
→ clean on 64 files (`.mypy_cache` removed after). One untracked file unrelated
to this lane (`confluence_time_exit.feature`, plus others that appeared from a
concurrent lane mid-campaign: `confluence_cells.feature`,
`confluence_controls.feature`, `confluence_horizon_units.feature`,
`confluence_preflight.feature`) was left untouched throughout, per the shared-
worktree convention. Agent: hardener (Claude Sonnet 5). Branch
`feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, base commit `c622427`.

## 2026-09-28 — Coder phase 2, T6

Implemented `chain/time_exit.py` (`TimeExitLifecycle`, `ClosureRequest`,
`ExitRecord`): the pure, LEAN-free bar-count expiry lifecycle behind
`capital_mgmt.exit_after_bars` (CC-15..CC-19, CC-28, CC-31; D5, D6, D11). Single
open trade at a time; bar t = the completed-candle bucket containing the entry
fill (floor to the clock grid, half-open `[start, end)`); due at the close of
bar t+N-1 (the open of t+N); one closure requested on the first tradable event
at/after that time; stop fills (full/partial) reconcile before any expiry
request; same-side signals never reset age; a filled reversal closes the old
trade with reason "reversal" and starts a new identity from its own bar t; a
live close order blocks a second request; a rejected/canceled order returns the
trade to DUE and the retry waits for a strictly later event (idempotency is
keyed on the last-requested timestamp, so the rejection's own event requests
nothing); the event that carried a request suppresses new entry on that event
only; an unresolved trade at end-of-stream is reported, never assumed closed.

Deviations from the specifier's `confluence_time_exit.feature` (both are
factual corrections of the literal example values against their own stated
inputs, not reinterpretations of D5/D6/D11 — recorded per COMMON-RULES):
- "quantity must be nonzero number" → "quantity must be a nonzero number" (the
  fragment column already read "a nonzero number"; the module message was
  written to match the Rule-heading prose instead of the table — fixed the
  code to match the table, the actual spec-anchored assertion).
- The weekend-gap scenario's elapsed-time assertion said "54 hours 0 minutes 30
  seconds" from entry fill `2016-03-04T19:00:30Z` to closure request
  `2016-03-07T01:00:00Z`; the real difference between those two literal
  timestamps is 53h59m30s (verified independently in Python:
  `datetime(2016,3,7,1,0,tzinfo=UTC) - datetime(2016,3,4,19,0,30,tzinfo=UTC)
  == timedelta(days=2, seconds=21570)`). Corrected the feature file's expected
  value to 53 hours 59 minutes 30 seconds; the scenario's timestamps, due-at
  assertion and closure-request assertion were all left untouched.
Also added the `Given "the following happens: {events}"` step (missing from
the original step file scope; needed by the three end-of-stream Outline rows)
with a two-entry closed vocabulary ("nothing", or one tradable event followed
by a close-order submission) matching exactly the two forms the feature uses.

Gate (cwd `algo-suite`): `uv run pytest
algo-backtest/tests/steps/test_confluence_time_exit.py -q` → 47 passed (47
collected, matches the QA procedure's Phase 2 count); `uv run ruff check` →
clean (fixed via `uv run ruff format`); `uv run ruff format --check` → clean;
`uv run mypy --strict algo-backtest/src/algo_backtest/chain/time_exit.py` →
clean. Regression (`test_filter_chain_mechanics.py test_f1_trend.py
test_f4_news_context.py test_f6_capital_mgmt.py test_chain_wiring.py
test_strategy_explain.py test_decision_recorder.py test_audit.py
test_bar_clock.py test_order_executor.py test_trade_plan.py`) → 458 passed, 0
failed. No existing test was modified beyond the one factual scenario-value
correction above; no test was skipped or deleted.

Files touched: `algo-backtest/src/algo_backtest/chain/time_exit.py` (new),
`algo-backtest/tests/features/confluence_time_exit.feature` (specifier's file,
one line corrected), `algo-backtest/tests/steps/test_confluence_time_exit.py`
(new), `.specs/features/confluence-chain/tasks.md` (T6 checkboxes),
`.specs/features/confluence-chain/spec.md` (CC-15..CC-19, CC-28, CC-31 status).
Not touched: any integration-owned file (`strategies.py`, `chain/wiring.py`,
`engine/*`, `chain/audit.py`, `chain/decision_recorder.py`) or any other
Story-21-private module besides `time_exit.py`.

Next: T7 (`chain/filters/constant_direction.py`, the drift-control filter).
Blockers: none. Agent: coder (Claude Sonnet 5). Branch
`feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, base commit `0c4d612`.

## 2026-09-28 — Coder phase 2, T7

Implemented `chain/filters/constant_direction.py` (`ConstantDirectionFilter`,
`FILTER_NAME = "constant_direction"`): the sole voter behind the always-short
and always-long drift-control arms (CC-23, D9). Constructor parameter
`direction: Literal["BUY", "SELL"]`; any other value (including "HOLD",
"NEUTRAL", "ABSTAIN", lower case, or empty) is refused at construction. `apply`
reads nothing from `state.features` and always returns the same configured
`Recommendation`, no veto, no enrichment. Canonical voter id and runtime
`filter_name` are both `"constant_direction"` (pinned choice from the
specifier's gap list #1, since this is a new addition rather than a legacy
F-numbered filter).

Proved the control is not a risk-management bypass with the real chain: the
real `RiskGuardFilter`/`CapitalMgmtFilter` (parsed the same way
`test_confluence_agreement.py` proves T1's F5/F6 vetoes) plus the real
`AgreementTerminalDecision` requiring `"constant_direction"`, run through the
real `FilterChain.run` — gates pass and the constant vote trades; F5 vetoes on
portfolio-at-risk; F6 vetoes on margin. No deviation from the specifier's
`confluence_controls.feature`; one step (`a constant-direction filter
configured for "" is built and fails`) needed `parsers.re` instead of
`parsers.parse` for the empty-quoted-cell case, matching the same fix already
used in `test_confluence_agreement.py`'s empty-required-filters step (a step-file
parsing detail, not a feature-file or production-code change).

Gate (cwd `algo-suite`): `uv run pytest
algo-backtest/tests/steps/test_confluence_controls.py -q` → 16 passed (16
collected, matches the QA procedure's Phase 2 count); `uv run ruff check` →
clean; `uv run ruff format --check` → clean; `uv run mypy --strict
algo-backtest/src/algo_backtest/chain/filters/constant_direction.py` → clean.
Regression (the eleven Phase-1/legacy step files plus
`test_confluence_time_exit.py` and `test_confluence_controls.py` together) →
521 passed, 0 failed. No existing test was modified, skipped or deleted.

Files touched: `algo-backtest/src/algo_backtest/chain/filters/constant_direction.py`
(new), `algo-backtest/tests/steps/test_confluence_controls.py` (new),
`.specs/features/confluence-chain/tasks.md` (T7 checkboxes),
`.specs/features/confluence-chain/spec.md` (CC-23 status). Not touched:
`confluence_controls.feature` (specifier's file, no deviation needed), any
integration-owned file, or any other Story-21-private module.

Next: T8 (`experiments/confluence-chain/rederive_horizon.py`, the horizon
evidence-unit re-derivation tool). Blockers: none. Agent: coder (Claude Sonnet
5). Branch `feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, base
commit `3bbbbf8`.

## 2026-09-28 — Coder phase 2, T8

Implemented `experiments/confluence-chain/rederive_horizon.py` (CC-25, CC-26):
a standalone, LEAN-free script (`experiments/heikin-ashi-signals/` layout, not
part of the `algo_backtest` package) that re-derives the session-2 H1 decision
archive's normalized-return statistic alongside true EUR/USD price pips from
independently, timestamp-matched source closes — never from the archive's own
recorded value beyond the decision's own bar. Public API: `ArchivedDecision`,
`SourceCloseSeries` (a sparse close map plus a `series_end` coverage boundary,
so a lookup beyond it is `missing_future_horizon` and a gap inside it is
`missing_price` — these are deliberately distinct, per the specifier's gap-list
#2), `RederivedRow`, `rederive_horizon` (pure), `rederive_and_write` (adds the
output-path contract: required, must not equal the archive path), and `main`
(the CLI: `--archive`, `--out`, `--decisions`/`--source` Parquet inputs; absent
`--decisions`/`--source` raises an explicit "no source close data configured"
error rather than fabricating a result — real Parquet loading via
`algo_core.duck` is implemented but untested here, since no fixture Parquet
exists in this environment; this is the QA procedure's documented BLOCKED path,
not a Phase 2 defect).

No SPEC_DEVIATION: the specifier's `confluence_horizon_units.feature` needed no
correction. Verified the two example rows' normalized-return/price-pip pairs
independently in Python before implementing
(`(1.09010/1.08650-1)/1e-4 == 33.1339`, etc.) — all three scenario rows matched
the formulas in the feature's own preamble exactly.

The specifier's step file location (`algo-backtest/tests/steps/`) sits inside
the `algo_backtest` package's test tree while the production script sits
outside it (top-level `experiments/`); the step file loads it by file path via
`importlib.util.spec_from_file_location` rather than a dotted import (there is
no precedent step file for a Phase-1 standalone script to follow, since
`experiments/heikin-ashi-signals/runner.py` has no test file). T9 and T10 will
need the same loading pattern for their own scripts.

Gate (cwd `algo-suite`): `uv run pytest
algo-backtest/tests/steps/test_confluence_horizon_units.py -q` → 14 passed (14
collected, matches the QA procedure's Phase 2 count); `uv run ruff check` →
clean; `uv run ruff format --check` → clean; `uv run mypy --strict
experiments/confluence-chain/rederive_horizon.py` → clean (`.mypy_cache`
removed after). Regression (the eleven Phase-1/legacy step files plus
`test_confluence_time_exit.py` and `test_confluence_controls.py`) → 521
passed, 0 failed. No existing test was modified, skipped or deleted.

Files touched: `experiments/confluence-chain/rederive_horizon.py` (new),
`algo-backtest/tests/steps/test_confluence_horizon_units.py` (new),
`.specs/features/confluence-chain/tasks.md` (T8 checkboxes),
`.specs/features/confluence-chain/spec.md` (CC-25, CC-26 status). Not touched:
`confluence_horizon_units.feature` (specifier's file, no deviation needed), any
integration-owned file, or any other Story-21-private module.

Next: T9 (`experiments/confluence-chain/preflight.py`, the population and
availability preflight). Blockers: none. Agent: coder (Claude Sonnet 5).
Branch `feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, base commit
`b2f8442`.

## 2026-09-28 — Coder phase 2, T9

Implemented `experiments/confluence-chain/preflight.py` (CC-08, CC-09, CC-13,
CC-24, CC-32; D2, D8): two independent, pure functions.

`compute_population_ledger` reconciles, for one (pair, clock, window): the
calendar-expanded slot count, `market_closure_count` (the weekly FX closure,
Friday 22:00 UTC through Sunday 22:00 UTC; an H4 bucket counts as closure if
*any* of its four constituent H1 hours is closed — the specifier's pinned gap
#3), `expected_valid_count`, `warmup_count` and `missing_count` (always 0 on
success; a genuinely missing expected bar hard-fails per D8/CC-24, grouped
into contiguous-run messages), plus `ready_count = expected_valid_count -
warmup_count - missing_count`. Verified the closure math against the
specifier's three worked reconciliations by hand before implementing (January
2016 H1: 744/240/504; the Jan 1-3 weekend H1: 72/48/24 and H4: 18/13/5; the
Jan 4-7 no-weekend window: 0 closures on both clocks) — all three matched on
first run, no iteration needed.

`compute_arm_ledger` implements the specifier's pinned gap #4 (a queryable
`news_availability_required` boolean, true for A/B/T-only, false for
M-only/always-short/always-long) and CC-13/CC-32: an absent
`AvailabilitySidecar` for a news-dependent arm is `status="unavailable"` with
an explicit reason, the arm still returned (never dropped); a present sidecar
with any `available_at >= decision_time` observation hard-fails instead of
silently passing.

Deviation from tasks.md's "Reuses" hint (not a scenario correction — recorded
per COMMON-RULES): the module does not call the existing
`news_coverage_problems` (`chain/filters/f4_news_context.py`) or
`ClosedBarClock` (`perception/bar_clock.py`). Both read real Parquet under a
`data_root`; the specifier's `confluence_preflight.feature` exercises pure
counting/status logic over directly staged missing-bar sets, warmup counts and
sidecar objects (COMMON-RULES: "every Phase 2 module is pure/component";
nothing here touches NAS data). A real T17 launch harness can call
`news_coverage_problems` as its own source of the missing-bar/sidecar inputs
this module's public functions accept — that integration point is unaffected
by this deviation. No test asserts filesystem/Parquet behavior, so nothing here
is faked to pass a check; the module simply does not (yet) have a real-data
front end, matching what was actually tested.

The `ready_count` field name and the `expected_valid_count == warmup_count +
missing_count + ready_count` equation both match the specifier's pinned gap #5
exactly.

Gate (cwd `algo-suite`): `uv run pytest
algo-backtest/tests/steps/test_confluence_preflight.py -q` → 21 passed (21
collected, matches the QA procedure's Phase 2 count); `uv run ruff check` →
clean; `uv run ruff format --check` → clean; `uv run mypy --strict
experiments/confluence-chain/preflight.py` → clean (`.mypy_cache` removed
after). Regression (the eleven Phase-1/legacy step files plus
`test_confluence_time_exit.py`, `test_confluence_controls.py` and
`test_confluence_horizon_units.py`) → 535 passed, 0 failed. No existing test
was modified, skipped or deleted.

Files touched: `experiments/confluence-chain/preflight.py` (new),
`algo-backtest/tests/steps/test_confluence_preflight.py` (new),
`.specs/features/confluence-chain/tasks.md` (T9 checkboxes),
`.specs/features/confluence-chain/spec.md` (CC-08, CC-09, CC-13, CC-24, CC-32
status). Not touched: `confluence_preflight.feature` (specifier's file, no
deviation needed), any integration-owned file, or any other Story-21-private
module.

Next: T10 (`experiments/confluence-chain/make_cells.py`, the fourteen-cell
manifest generator). Blockers: none. Agent: coder (Claude Sonnet 5). Branch
`feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, base commit
`e4959a6`.

## 2026-09-28 — Coder phase 2, T10 (Phase 2 close-out)

Implemented `experiments/confluence-chain/make_cells.py` (CC-21, CC-23, CC-28;
D3, D7, D9, D11): a deterministic generator of the 7 registered arms (A, B,
A-plan, T-only, M-only, always-short, always-long) × 2 clocks (H1=60/L=480,
H4=240/L=120), two closed registries (`ARMS`, `CLOCK_LOOKBACK`) that refuse
anything outside them. Each cell's `filters:` list is exactly its required
voters plus F5/F6 — deliberately never an extra non-required directional
voter, since the agreement terminal's "any other voter that disagrees" rule
(CC-02) would otherwise force HOLD for e.g. T-only if f1_trend also ran
unrequired; `momentum_context.lookback_bars` is still declared on every cell
regardless of arm, since CC-28 registers it as a per-clock protocol parameter,
not a per-arm one — a design decision worth flagging for T11/T12's config-key
validation, not a spec deviation (nothing in spec.md/design.md contradicts it).
Six arms get the shared time-exit plan (empty targets/trail_stops,
`exit_after_bars: 4`, `min_hold_bars: 4`, `risk_per_trade: 0.03`,
`stop_distance_source: atr`, `atr_multiplier: 2.0`); A-plan pins the eight
fields from the specifier's pinned gap #6
(`experiments/heikin-ashi-signals/strategies/heikin-ashi-h4-talib-volume-on/config.yaml`),
carries no `exit_after_bars` key, and keeps `min_hold_bars: 0` (the reference
template's own default, since D11's `min_hold_bars: 4` registration applies to
"time-exit arms" specifically). Every cell shares EUR/USD, USD 10,000,
OANDA costs (`spread_pips: 1.0`, `commission_per_lot: 0.0`,
`broker_stop_level_pips: 0.0` — the same values every existing strategy config
in this repo uses), the F5 caps and the 2016-03-01..2017-02-28 window.
`config_hash` is a SHA-256 over each cell's canonical (sorted-key) JSON,
verified deterministic across two separate job directories. Writes
`<job_dir>/<cell_id>/config.yaml` (following the
`experiments/heikin-ashi-signals/strategies/` layout) and one
`<job_dir>/manifest.json` listing all 14 rows.

Deviation from tasks.md's "Reuses" hint (not a scenario correction — recorded
per COMMON-RULES): does not call any "pinned template resolution" helper from
`experiments/heikin-ashi-signals/runner.py`, because that script has no
importable, reusable resolution function — it is a `main()`-only CLI. The
eight pinned A-plan fields were instead copied directly from the reference
strategy's `config.yaml` (verified by reading the file), matching the
specifier's own pinned gap #6 exactly.

No SPEC_DEVIATION: the specifier's `confluence_cells.feature` needed no
correction — all 35 scenarios passed against the first implementation.

Gate (cwd `algo-suite`): `uv run pytest
algo-backtest/tests/steps/test_confluence_cells.py -q` → 35 passed (35
collected, matches the QA procedure's Phase 2 count); `uv run ruff check` →
clean; `uv run ruff format --check` → clean; `uv run mypy --strict
experiments/confluence-chain/make_cells.py` → clean (`.mypy_cache` removed
after). Regression (the eleven Phase-1/legacy step files plus
`algo-analyze/tests/steps/test_portfolio_inference.py`, exactly the tasks.md
Gate Check Commands "Regression" selection) → 477 passed, 0 failed. Full
offline suite `uv run pytest algo-backtest/tests -q -p no:cacheprovider` →
**1932 passed, 53 deselected** — the Phase 1 hardening baseline (1799) plus
exactly the five Phase 2 features' 133 new scenario/Examples rows (47 + 16 +
14 + 21 + 35), with zero regressions. No existing test was modified, skipped
or deleted anywhere in Phase 2.

Workspace-wide `make lint type` (run once at Phase 2 close-out, all five
touched files plus their step files individually clean per the per-task gates
above): fails on 9 files, all pre-existing debt this lane never touched —
`tools/mutation_harness.py` (missing type annotations), `scripts/bigquery_*.py`
(no `google.cloud`/`google.api_core` stubs installed) and
`docs/stories/done/20-session-2-clean-rerun/scripts/*.py` (a pre-existing
assignment-type error). Confirmed via `uv run ruff check .` /
`uv run mypy` that none of Phase 2's five new files or step files appear in
either error list. Recorded here as BLOCKED pre-existing debt, not claimed as
passed.

Files touched (T10 only): `experiments/confluence-chain/make_cells.py` (new),
`algo-backtest/tests/steps/test_confluence_cells.py` (new),
`.specs/features/confluence-chain/tasks.md` (T10 checkboxes),
`.specs/features/confluence-chain/spec.md` (CC-21, CC-23, CC-28 status). Not
touched: `confluence_cells.feature` (specifier's file, no deviation needed),
any integration-owned file, or any other Story-21-private module.

### Phase 2 summary (T6–T10 complete)

All five Phase 2 tasks (T6 time-exit lifecycle, T7 drift-control filter, T8
horizon unit re-derivation, T9 population/availability preflight, T10
fourteen-cell manifest) are implemented, gated green individually and
together, committed one-task-per-commit, and pushed to
`feat/21-confluence-chain`. New files, all Story-21-private (never touched by
Phase 1 or integration-owned): `chain/time_exit.py`,
`chain/filters/constant_direction.py`,
`experiments/confluence-chain/{rederive_horizon,preflight,make_cells}.py`,
their five `tests/features/confluence_*.feature` files (all authored by the
specifier, none rewritten except the one corrected scenario-value in
`confluence_time_exit.feature`, recorded above under T6) and five matching
`tests/steps/test_confluence_*.py` files.

**Integration handoff notes for Phase 3 (T11–T15)**:
- T8/T9/T10's production scripts live at `algo-suite/experiments/confluence-chain/`
  (outside the `algo_backtest` package, matching design.md's
  `experiments/heikin-ashi-signals/` layout precedent) but their tests live
  inside `algo-backtest/tests/steps/` (as tasks.md specifies); each step file
  loads its script by file path via `importlib.util.spec_from_file_location`
  (no dotted-import path exists for them). If T11/T12 need to import these
  scripts from `algo_backtest` production code, the same loading pattern
  applies, or the scripts should be promoted into the package at that point —
  a decision for the integration lane, not made here.
- `make_cells.py`'s per-cell config's `agreement.required_filters` key is the
  new, generator-invented location for the canonical required-voter list;
  T11/T12 will need to decide whether `strategies.py`/`chain/wiring.py` reads
  this key verbatim or maps it to its own `momentum_context`/`news_context`/
  `capital_mgmt` section convention already used by Phase 1's real strategy
  configs — the shapes match Phase 1's sections field-for-field (verified by
  eye against `chain/filters/f1_trend.py`'s `MOMENTUM_SECTION`/`_MOMENTUM_KEYS`
  and `f4_news_context.py`'s config keys), but wiring one into the other was
  out of this lane's scope.
- `preflight.py`'s `compute_population_ledger`/`compute_arm_ledger` take
  already-known missing-bar sets and `AvailabilitySidecar` objects; a real T17
  launch harness needs its own front end (e.g. calling the existing
  `news_coverage_problems`/`ClosedBarClock`) to produce those inputs from real
  Parquet — see the T9 entry above for the full reasoning.
- `rederive_horizon.py`'s real `--decisions`/`--source` Parquet loading (via
  `algo_core.duck`) is implemented but untested in this environment (no
  fixture Parquet); confirmed only that the CLI raises its explicit
  "no source close data configured" error when those flags are omitted, per
  the QA procedure's documented BLOCKED expectation.

No blockers remain for Phase 2. Phase 3 (T11 config/provenance contracts) is
the next dependency per tasks.md's execution plan (`T10 -> T11 -> T12 -> T13
-> T15 -> T14`) and is integration-owned, outside this lane. Agent: coder
(Claude Sonnet 5). Branch `feat/21-confluence-chain`, worktree
`/tmp/mba-impl-21`, base commit `525f99e`.

## Cleaner phase 2 (2026-09-28)

Baseline: phase-2 diff `git diff 0c4d612..13fcf4c -- algo-backtest/src
experiments`. Per-file review: ruff (`--select C901,PLR0912,PLR0915`), mypy
`--strict`, branch coverage over the five phase-2 step files, CRAP via
`radon cc -s` (installed in the workspace venv), docstrings/fail-fast/dead-code/
naming review, and the `make check-perception-architecture
check-inference-architecture` dependency-boundary gate.

| File | Ruff | Mypy strict | Coverage (before → after) | Max cc / CRAP (before → after) | Actions |
| --- | --- | --- | --- | --- | --- |
| `chain/time_exit.py` | clean | clean | 98% (2 partial branches, 1 uncovered line) → 100% | `completed_candle` cc 10 (CRAP 10) → 2; `order_status_report` cc 8 → 7 | Split `completed_candle` into `_validate_candle_bounds`/`_is_repeat_of_last_candle`/`_count_bar_toward_horizon`; removed two `if self._open_trade_id == trade_id` guards in `stop_filled`/`order_status_report` that were always true (the lifecycle's own invariant — exactly one non-closed trade, always `self._open_trade_id` — makes both branches unreachable; replaced with an explanatory comment and the unconditional assignment); added the missing "unrecognized order status is refused" scenario to `confluence_time_exit.feature` (reuses the existing `_order_status_refused` step, no step code changed) to cover the `order_status_report` `ValueError` branch that had no scenario |
| `chain/filters/constant_direction.py` | clean | clean | 100% → 100% | cc 1 (trivial) | None needed |
| `experiments/confluence-chain/rederive_horizon.py` | clean | clean | not selected for branch coverage (outside `algo_backtest`); reviewed by inspection | max cc 6 (`_row`), all ≤8 | None needed |
| `experiments/confluence-chain/preflight.py` | clean | clean | not selected for branch coverage (outside `algo_backtest`); reviewed by inspection | max cc 7 (`compute_arm_ledger`), all ≤8 | None needed |
| `experiments/confluence-chain/make_cells.py` | clean | clean | not selected for branch coverage (outside `algo_backtest`); reviewed by inspection | max cc 5, all ≤8 | None needed |

Duplication noted, not merged (Phase 2's private-file boundary, matching the
Phase 1 cleaner's disposition): `_require_utc`/`_clock_label` helpers repeat
verbatim across `time_exit.py`, `preflight.py` and `rederive_horizon.py`.

Verification after refactor: the five phase-2 step files (134 passed, 100%
line+branch coverage on `time_exit.py`/`constant_direction.py`); the
tasks.md Regression selection (`test_filter_chain_mechanics.py`,
`test_f1_trend.py`, `test_f4_news_context.py`, `test_f6_capital_mgmt.py`,
`test_chain_wiring.py`, `test_strategy_explain.py`,
`test_decision_recorder.py`, `test_audit.py`, `test_bar_clock.py`,
`test_order_executor.py`, `test_trade_plan.py`,
`algo-analyze/tests/steps/test_portfolio_inference.py`; 477 passed); `uv run
ruff check algo-backtest experiments` clean; `uv run mypy --strict
algo-backtest experiments/confluence-chain` clean (69 source files);
`check-perception-architecture`/`check-inference-architecture` both PASS.
`.mypy_cache` removed after the run.

No behaviour changed: every existing scenario/assertion is untouched; only one
new scenario was added. Agent: cleaner (Claude Sonnet 5). Branch
`feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, phase commits
`3bbbbf8..13fcf4c`.

## Hardener phase 2 (2026-09-28)

Manual mutation testing (no `mutmut` in the workspace) of the five Phase-2 production
modules: `chain/time_exit.py` (11 mutations), `chain/filters/constant_direction.py` (6),
`experiments/confluence-chain/rederive_horizon.py` (7), `.../preflight.py` (6),
`.../make_cells.py` (6) — 36 total, each applied one at a time in place, run against its
covering step file, then restored, with `git status --porcelain` confirmed to match
baseline after every mutation. Full table, traces and killing scenarios in
`mutation-phase2.md`.

Result: 33 KILLED, 3 SURVIVED. All three survivors are on `time_exit.py` and were traced
(not assumed) to be genuine equivalent mutants: the two flagged "removed guard" lines in
`stop_filled`/`order_status_report` (`self._open_trade_id = None`) are unobservable
through every public method and caller path, because the sole reader of
`_open_trade_id`, `_open_trade()`, already filters a closed trade by its own `status`
field, and the only other writers (`entry_filled`, `reversal_filled`) unconditionally
overwrite it on the next open trade regardless — confirmed by a contrast mutation (M8,
removing the *load-bearing* assignment in `entry_filled`) which was cleanly KILLED. The
third (`_is_repeat_of_last_candle`'s `<=`→`<`) is equivalent because
`_validate_candle_bounds` (always called first) forces `end == last_end` to imply
`start == last_start`, so the mutated boundary is never actually reached with a
differing pair.

Six other initial survivors were genuine test gaps, each closed with a new Gherkin
scenario (feature first) rather than an equivalent-mutant claim: a too-long
(120-minute, grid-aligned) candle in `confluence_time_exit.feature`; the
constant-direction filter's reason text in `confluence_controls.feature`; a gap
exactly at the source series boundary in `confluence_horizon_units.feature`; an
`available_at` exactly equal to `decision_time` in `confluence_preflight.feature`; and
the SHA-256 hash format plus exact cell-ID strings in `confluence_cells.feature`. Also
added (documentation, not required to kill any listed mutant): two scenarios proving a
brand new entry is accepted immediately after a trade fully closes via stop-fill or via
order-fill expiry, to lock in the single-open-trade invariant for future refactors.

Negative controls (M11, H7) confirmed KILLED. Harness note: an initial flaky
KILLED/SURVIVED flip on two `time_exit.py` mutations traced to stale `__pycache__`
bytecode reused across rapid same-second rewrites of the same source file; fixed by
wiping `__pycache__` and setting `PYTHONDONTWRITEBYTECODE=1` for the mutation
subprocesses, then re-confirmed stable across three repeat runs.

The five Phase-2 step files now collect 138 scenarios (was 134), all passing. Full
suite: `uv run pytest algo-backtest/tests -q -p no:cacheprovider` — 1937 passed, 53
deselected. `uv run ruff check algo-backtest experiments` clean. `uv run mypy --strict
algo-backtest experiments/confluence-chain` clean (69 source files); `.mypy_cache`
removed after the run. No production code was changed by this pass — only new Gherkin
scenarios and step definitions. Agent: hardener (Claude Sonnet 5). Branch
`feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`, base commit `324a1e0`.

## T16 — Freeze the review-approved registration README (2026-09-28)

Wrote `algo-suite/experiments/confluence-chain/README.md`: accepted D1–D11
(D5 = the source spec's own bar-open timing, not the rejected draft), the 14
registered cell IDs generated by `make_cells.py`, exploratory labels for both
the full year and Nov–Feb (both already inspected — see the source spec and
`evidence/signal-horizon-check.md`), the H1/H4 clock contract (L=480/120,
4-bar horizon = 4/16 scheduled hours), the primary (H1 A vs T-only, Nov–Feb)
and secondary contrasts, the D7 bootstrap settings, no-model-dependency and
the one-attempt policy. Config hashes are not recorded — `config_hash` is
computed by `make_cells.py` at generation time; the README states the
manifest's `{cell_id, arm, clock_minutes, config_hash}` structure instead of
inventing values.

Read the integration branch's Phase 3 log (`feat/integrate-19-21-22` at
`581d1c0`, read-only, not merged) to register against the actually-implemented
contract rather than the design proposal. Recorded both disclosed engine gaps
as constraints, not silent workarounds: `intensity_relative` fails fast at
`initialize()` for lack of GDELT `available_at` provenance, blocking 8 of 14
cells (`A`, `B`, `A-plan`, `T-only` × H1/H4); 6 cells (`M-only`,
`always-short`, `always-long` × H1/H4) need no news input and are launch-ready
today, subject to the price-population gate. The
`exit_after_bars`+`close_on_veto` conflict does not affect this manifest —
verified against `make_cells.py`'s `_execution_for`: all 14 cells set
`close_on_veto: false`.

Also found and disclosed (not fixed, out of this doc-only task's scope): the
standalone `preflight.py`'s `compute_arm_ledger` arm registries
(`_NEWS_REQUIRED_ARMS`, `_NO_NEWS_ARMS`) omit `"A-plan"` from both sets, even
though `A-plan` shares `A`'s required voters and news dependency — calling it
today raises `ValueError: unknown arm`. Confirmed against
`confluence_preflight.feature`, whose arm-ledger rules exercise only `A`, `B`
and `T-only`. Does not change which cells can launch (the engine-level
`initialize()` gate blocks `A-plan` first), but the registry needs correcting
before `A-plan` can be preflighted through this exact script.

Corrected the population source while drafting: EUR/USD price data is
Dukascopy tick data (`algo-suite/PRD.md` §7), aggregated to closed H1/H4 bars;
OANDA is the pinned execution-cost/broker-floor model only
(`make_cells.py`'s `_OANDA_EXECUTION`), never the price source — the two must
not be conflated.

Resource cap: `parallel-19-21-22.md` records the semaphore policy (one
coordinator, explicit cap and timeouts set at registration) but no specific
numbers. The coordinator's communicated values (3 concurrent LEAN containers,
8 threads/host, 30-minute timeout per cell) are recorded in the README as
communicated, explicitly flagged as not yet written into a repository doc, per
the "no invented resource values" constraint.

Marked both T16 "Done when" boxes and added a verification record to
`tasks.md`; set spec.md's CC-23/27/28/29 traceability status to
`Implemented (T16)`.

Gate (Docs): `git diff --check` clean; `validate_tasks.py --strict` on
`.specs/features/confluence-chain/tasks.md` → `0 error(s), 0 warning(s)`;
`check_commit.py --message "docs(confluence): freeze the review-approved
registration readme"` → OK. Reviewed links/parameters against T10's
`make_cells.py` and T9's `preflight.py` for consistency (both cited findings
above came from that review).

One commit `b369822` (`docs(confluence): freeze the review-approved
registration readme`), pushed to `origin/feat/21-confluence-chain`. Agent:
protocol owner (Claude Sonnet 5). Branch `feat/21-confluence-chain`, worktree
`/tmp/mba-impl-21`, base commit `36fcfa4`.

Next: T17 (`experiments/confluence-chain/run_cells.py`, the bounded 14-cell
launch harness), depends on T16.

## T17 — Build the bounded fourteen-cell launch harness (2026-09-28)

Wrote `algo-suite/experiments/confluence-chain/run_cells.py`, the explicit-run-ID
harness (`launch_job(job_dir, ...)` + a thin `main()` CLI). Every invocation
regenerates the full 14-cell registration under the caller-supplied `--job-dir`
via T10's `make_cells.generate_manifest` (deterministic — a no-op on unchanged
inputs) and copies `README.md` into it, then launches only the requested subset
(default: all 14) that both pass the news-availability gate and have no existing
`status.json` (resume never overwrites an attempt; the only sanctioned way to
attempt a cell again is naming it in `--rerun`, never an automatic retry).

Reused T9's `preflight.py` directly (loaded by file path, same pattern as its own
Gherkin steps) for the integration gate: `compute_arm_ledger` with no sidecar
marks every news-dependent arm `"unavailable"` and skips launching it, no
subprocess call made. Handled the disclosed `preflight.py` registry gap
(README, "Known constraints", finding 3 — `compute_arm_ledger("A-plan", ...)`
raises `ValueError: unknown arm`) by aliasing A-plan to A's arm ledger result
before calling it — A-plan shares A's required voters and news dependency, so
this resolves to the same `"unavailable"` outcome without ever touching
`preflight.py` itself (out of this task's scope; T9 is already done) and
without raising. Verified interactively: `a-h1`, `b-h4`, `t-only-h1`, `a-plan-h1`
(and their H4/H1 counterparts) all resolve to `unavailable`; `m-only-*`,
`always-short-*` and `always-long-*` (6 cells) are launch-ready today, matching
the README's launch-ready/blocked table exactly.

Added a real (not fake) price-population gate, `population_gate`: for every
month the registered window touches, checks the source Parquet partition file
exists (`preflight.partition_path`) and calls `compute_population_ledger` with
that real `partition_exists` flag — a missing partition is a hard failure that
aborts the whole invocation before any cell launches (CC-24, "a failed preflight
launches zero cells"). This covers partition presence only; the fuller row-level
reconciliation (`warmup_bars`/`missing_bars`, needing actual per-bar timestamps)
needs real data access this harness does not perform on its own and is left as a
caller responsibility before any separately authorized T19 run — disclosed here,
not silently assumed.

The child backtest is invoked through the current CLI contract (`cli.py`'s `run`
command: `algo-backtest run --strategy <cell_id> --symbol <pair> --from <start>
--to <end> --strategies-dir <job_dir> --timeout <seconds>`), never an old
latest-directory glob, and never with `--model` (no cell in this study needs an
F7 model). The runner is injectable (`Runner` callable); this task's own tests
substitute a fake one and launch no research cells. Each cell's own directory
(`<job_dir>/<cell_id>/`, already holding T10's `config.yaml`) also holds
`command.json` (exact argv + config hash + source revision + code hashes,
written before launch), `run.log` (captured stdout+stderr) and the terminal
`status.json` (`succeeded`/`failed`/`unavailable`, exit code, reason, results
dir parsed from the child's own `results=` output line).

Wrote `tests/features/confluence_run_contract.feature` first (15 scenario/example
cases across 8 Rules: exactly 14 registered ids, distinct output roots, no
`--model`, preflight failure launches zero cells, news-blocked cells never
launch (including the A-plan alias, proven not to raise), a nonzero child exit
persists as a failure record without raising, resume never overwrites an
attempt, an explicit rerun is the only way to attempt again, and every status
carries its config hash and source revision) and
`tests/steps/test_confluence_run_contract.py` (15 passed). Verified by hand
(scratch script, not committed) against real `make_cells`/`preflight` output
before writing the Gherkin: `ALLOWED_CELL_IDS` matches the README's 14 ids
exactly; the arm-ledger alias resolves A-plan without a `ValueError`; the real
`population_gate` raises with the exact missing-partition message when no
partition file exists and passes once the (fake) partition files are present.

Gate: `uv run pytest algo-backtest/tests/steps/test_confluence_run_contract.py
-q -p no:cacheprovider` → 15 passed. Regression (`test_filter_chain_mechanics`,
`test_f1_trend`, `test_f4_news_context`, `test_f6_capital_mgmt`,
`test_chain_wiring`, `test_strategy_explain`, `test_decision_recorder`,
`test_audit`, `test_bar_clock`, `test_order_executor`, `test_trade_plan`,
`algo-analyze`'s `test_portfolio_inference`) → 477 passed. Full suite
`uv run pytest algo-backtest/tests -q -p no:cacheprovider` → 1952 passed, 53
deselected (was 1937 before this task — the 15 new scenarios). `uv run ruff
check algo-backtest experiments` clean; `uv run ruff format --check
algo-backtest/tests/steps/test_confluence_run_contract.py
experiments/confluence-chain/run_cells.py` clean (pre-existing files elsewhere
in the tree were already unformatted under this environment's ruff version —
untouched, out of this task's scope); `uv run mypy --strict
experiments/confluence-chain` clean (4 source files). `validate_tasks.py
--strict` on `tasks.md` → `0 error(s), 0 warning(s)`; `validate_spec.py --strict`
on `spec.md` → `0 error(s), 0 warning(s)`; `git diff --check` clean.

Marked both T17 "Done when" boxes; set spec.md's CC-23/24/32 traceability status
to `Implemented (..., T17)`.

Next: T18 (`experiments/confluence-chain/compare.py`, the registered comparison
report), depends on T17.

## Hardener phase 3 (2026-09-28)

Manual mutation testing (no `mutmut` for `experiments/`) of the work since `f6c464a`: T17's
`experiments/confluence-chain/run_cells.py` (78 mutations), T16's registration `README.md`
(16) and the one production function this pass had to fix, `preflight.py::partition_path`
(6) — 100 total, each applied in place one at a time, run against the covering step files and
restored, `git status --porcelain` matching baseline after every one (0 drift). T18
(`compare.py`) had not landed, so it is out of scope. Full tables and traces in
`mutation-phase3.md`.

Result: 94 KILLED, 6 SURVIVED, all justified, 0 unjustified. Four `run_cells.py` equivalents
(R4 cell-id set is order-free; R9 `compute_arm_ledger` never reads `clock_minutes`; R13/R14
the required partition is clock-independent) and two README prose claims with no executable
counterpart until T18 (D11/D12, bootstrap block length / resamples — T18 must bind the D7
numbers to the README). Negative control R32 KILLED. The first pass killed only 10 of 66 on
`run_cells.py` because T17's tests always injected a permissive gate and fake runner; the 56
survivors were closed with 63 new Gherkin scenarios/examples in
`confluence_run_contract.feature` (15 → 78), none weakening an existing one.

Genuine production finding fixed: `preflight.partition_path` (and so T17's `population_gate`)
targeted a layout `algo_core.layout` never writes (`algo-suite/data/parquet/forex/<pair>/
clock=N/<month>.parquet` joined onto a `data_root` that is already `algo-suite/data`), so the
gate would have hard-failed on real data. It now returns the real M1 store path
(`parquet/forex/<pair>/m1/year=YYYY/month=MM/data.parquet`, data-root-relative), cross-checked
against `algo_core.layout.price_path` by a scenario. Gate scope (file existence only) unchanged.

Gates: full suite `uv run pytest algo-backtest/tests -q -p no:cacheprovider` 2015 passed (was
1952); `uv run ruff check algo-backtest experiments` clean; `uv run mypy --strict
experiments/confluence-chain` clean. Follow-up for the engine-integration hardening pass
(PR #91 comment #7845): the `on_fill`-after-time-exit call order in
`chain_algorithm.py::on_order_event` is load-bearing (8/10 native scenarios fail if reordered).
Agent: hardener (Claude Sonnet 5.5). Branch `feat/21-confluence-chain`, base `00b91fa`.

Next: T18 (`experiments/confluence-chain/compare.py`, the registered comparison report),
depends on T17.
