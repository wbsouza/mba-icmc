# Story 19 progress and handoff

Status: in progress, Phase 1 (T1 through T5). Updated September 28, 2026.
Planning owner: Codex. Implementation owner for Phase 1: Claude coder, Lane A.
No experiment run has been started; the frozen protocol is
[method-design.md](method-design.md).

## Working tree and ownership

| Agent | Working tree | Branch | Scope |
| --- | --- | --- | --- |
| Codex | /home/wellington/workspace/mba-agents/mba-main | main at 35a0dc9 | Story 19 and parallel coordination documents only |
| Claude coder, Lane A | /tmp/mba-impl-19 | feat/19-adaptive-retraining, base ef0111d | Phase 1 T1 through T5: `algo-backtest/src/algo_backtest/retraining/`, the F7 family-weights patch, their feature/step files, this story's docs |

The earlier 199a4df planning baseline is now merged; session 2 is done Story 20.
Planning began at 6568120; main advanced to 35a0dc9 when the supervised Story 21
documentation update merged as PR 87. The existing move into in-progress is preserved;
it does not imply implementation has begun. See the
[parallel plan](../../parallel-19-21-22.md) for future branches/worktrees and all
planning-helper ownership. No implementation worktrees/workers were created.
The [review disposition](review-disposition.md) records decisions required at T1.

Intended planning publication branch: `docs/parallel-19-21-22-plan`.
Creation failed: local Git metadata is read-only; Forgejo requires approval
unavailable in this session. No new branch, commit, push or PR is claimed for
this amendment. Existing merged planning commits are not affected.

## What changed and why

The user refined sliding-window retraining into a complete adaptive cycle:
consume new data, track outcome availability, train, validate, publish and load
on demand for future transactions. The design now includes that lifecycle, not
just observation weights. A host coordinator and an optional LEAN provider
preserve the current separation between training and execution.

tlc-spec-driven supplied requirement traceability, atomic task gates and the
review-before-execution boundary. Experimental-design guided matched controls
and avoidance of false independent replications; docs-writer guided source and
handoff clarity. Five controls isolate threshold refresh, history truncation
and exponential weighting without changing entry/risk filters.

## Implementation checklist

The canonical task definitions and dependencies are in
[tasks.md](../../../../../.specs/features/recency-weighted-retraining/tasks.md).
This checklist mirrors those IDs for the repository's per-story progress
convention; update both in the same tested task commit.

- [x] T1: Register the adaptive comparison protocol.
- [x] T2: Build the incremental data and label-maturity adapter.
- [x] T3: Implement exact-UTC epoch planning.
- [x] T4: Implement exponential weights and feasibility checks.
- [x] T5: Pass weights through family-model fitting.
- [x] T6: Pass independent weights through combiner fitting.
- [x] T7: Publish immutable epoch bundles.
- [ ] T8: Implement separate-span threshold calibration.
- [ ] T9: Orchestrate one epoch's weighted training.
- [ ] T10: Implement the full adaptive-cycle coordinator.
- [ ] T11: Implement the on-demand epoch provider.
- [ ] T12: Integrate adaptive cycles into continuous LEAN replay.
- [ ] T13: Record current and entry model identities.
- [ ] T14: Package schedules and lifecycle metadata in runs.
- [ ] T15: Expose adaptive preparation and replay orchestration.
- [ ] T16: Report paired policy results and time diagnostics.
- [ ] T17: Document the adaptive methodology in Chapter 3.
- [ ] T18: Execute and archive the registered five-policy study.
- [ ] T19: Write verified findings into Chapter 4.

## Implementation log

### 2026-09-28 T1: Register the adaptive comparison protocol (Claude coder, Lane A)

What changed and why: wrote [method-design.md](method-design.md), the frozen
protocol (five policies, temporal contract, weighting, support minima, seed,
baseline identity with sha256, data inventory with partition checksums,
analysis plan with the analyzer feasibility check, attempt budget, measured
resource cap, native-coordination gate, approval of disposition items 1 to 10,
and the seven pinned readings the specifier fixed). The T0 pre-check and D60
trial (commits `ca76847`, `0d66abf`) are recorded as prior evidence outside the
frozen matrix because the parallel-plan commit `ef0111d` dropped those
amendment sections from this story's `review.md` and the canonical plan never
absorbed them; a D60 arm needs a separate amendment.

Baseline recorded before any Phase 1 change (cwd `/tmp/mba-impl-19/algo-suite`):

- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider | tail -1`:
  `1598/1651 tests collected (53 deselected)`, exit 0.
- `uv run pytest algo-backtest/tests/steps/test_f7_meta_learner.py
  algo-backtest/tests/steps/test_f7_model_io.py
  algo-backtest/tests/steps/test_training_family_contract.py -q`: 86 passed, exit 0.
- `uv run ruff check algo-backtest`: clean, exit 0. `uv run mypy --strict
  algo-backtest`: clean (63 source files), exit 0. `uv run ruff format --check
  algo-backtest`: 66 pre-existing files would be reformatted (exit 1), none in
  this lane's scope; Phase 1 gates format only on touched files.

Docs gate (cwd `/tmp/mba-impl-19`):

- `git diff --check`: no output, exit 0.
- `python3 /home/wellington/.claude/skills/tlc-spec-driven/scripts/validate_spec.py
  .specs/features/recency-weighted-retraining/spec.md --strict`: 0 errors,
  0 warnings, exit 0.
- `python3 /home/wellington/.claude/skills/tlc-spec-driven/scripts/validate_tasks.py
  .specs/features/recency-weighted-retraining/tasks.md --strict`: 0 errors,
  0 warnings, exit 0.

Data root access: read-only listing and `sha256sum` on
`/home/wellington/workspace/mba-agents/mba-main/algo-suite/data`; nothing
written there. Commit `cc0e10a`, pushed to `origin/feat/19-adaptive-retraining`.
Next: T2.

### 2026-09-28 T2: Build the incremental data and label-maturity adapter (Claude coder, Lane A)

What changed and why: new `algo_backtest.retraining` package with
`ingestion.py`: `SourceRow`, `Batch`, `PartitionRecord`, `validate_batch`,
`Ledger` (`open`, `consume`, `watermark`, `row_count`, `partitions`,
`maturity`, `visible_keys`, `mature_keys`), the module-level `consume(directory,
batch)`, `read_partition(path, partition=...)` and `file_sha256`. The ledger is
one `ledger.json` per directory, written atomically (temp file plus rename) and
only when a batch adds rows, so identical retries leave the bytes untouched.
Maturity is inclusive (`label_time <= cutoff`, pinned reading 2); as-of
visibility is inclusive on availability; new rows may not precede the
watermark; a re-delivered key with different content or a re-identified
partition with a different sha256 is a conflict; nothing is persisted from a
rejected batch. Steps in `tests/steps/test_retraining_ingestion.py`.

Scenario changes (feature is the spec; recorded per the brief):

- Corrected "The persisted ledger reopens with the same watermark and row
  state": it asserted `bar-003` pending after the watermark reached its
  `label_time` (14:00), contradicting pinned reading 2 and the sibling scenario
  "A pending label matures when a later batch carries the watermark to its
  label_time (label_time <= cutoff)". Now asserts `bar-003` mature and
  `bar-005` pending.
- Added "An as-of query with a naive cutoff is refused rather than read as
  local time (RWT-02)" and "The same partition path with different bytes but
  identical rows is still a conflict" (spec.md retry/idempotency: same identity
  with different bytes rejected) so every branch of the adapter has a covering
  scenario. Two unrequested branches (ledger schema-version check, unknown-key
  message) were removed instead of tested.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_ingestion.py -q
  -p no:cacheprovider`: 22 passed (18 scenarios plus 4 Examples rows),
  0 failed, 0 skipped.
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on
  the three touched Python files: clean. `uv run mypy --strict algo-backtest`:
  clean, 65 source files.

Adequacy: RWT-23 covered by the two-batch watermark, regression, and
mid-batch-failure scenarios (watermark asserted from a reopened ledger);
RWT-24 by late outcome, maturation, as-of cutoff and `label_time None`
rejection; RWT-02 by the timestamp outline, duplicate key, ordering and
declared-count scenarios. Every scenario maps to one of those or to the
retry/idempotency and prefix-invariance dimensions of spec.md. Commit
`3fbf939`, pushed. Next: T3.

### 2026-09-28 T3: Implement exact-UTC epoch planning (Claude coder, Lane A)

What changed and why: `retraining/schedule.py` with `Span` (half-open UTC
interval, validated on construction), `Epoch` (deployment month plus the
schedule's first D), `StageSpans`, `POLICIES`, `EXPANDING_START`,
`monthly_epochs(start, end)`, `epoch_starting(epochs, D)`,
`stage_spans(epoch, policy)` and `select_rows(rows, span)`. F and Q anchor
their family/combiner spans on the schedule's initial epoch; only Q's threshold
span moves with D (pinned reading 5). `select_rows` takes ingestion's
`SourceRow`, so bucket-start timestamps and trade context cannot reach the
selector (RWT-09); a `None` label_time is rejected (RWT-24); an empty
selection is returned, feasibility being `check_support`'s job (pinned
reading 4). The UTC helpers moved from `ingestion.py` into
`retraining/utc.py` so both modules share one public check; ingestion's
behaviour is unchanged (its 22 scenarios still pass). `walk_forward_split`
is untouched; the feature's regression scenario runs it on the same rows.
Steps in `tests/steps/test_retraining_schedule.py`. No scenario was changed.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_schedule.py -q
  -p no:cacheprovider`: 41 passed (11 scenarios plus 30 Examples rows).
- `uv run pytest` on `test_retraining_ingestion.py`, `test_f7_meta_learner.py`,
  `test_f7_model_io.py`, `test_training_family_contract.py`: 108 passed
  (22 + 86, the F7 baseline count unchanged).
- `uv run ruff check algo-backtest`: clean after one import-order fix.
  `uv run ruff format --check` on the retraining package and the two
  retraining step files: clean. `uv run mypy --strict algo-backtest`: clean,
  67 source files.

Adequacy: RWT-03 by the twelve-epoch coverage, contiguity/union and the
month/year/leap outline; RWT-02 by the invalid-span outlines for planning and
selection and the unregistered epoch/policy outline; RWT-01 by the half-open
availability, bucket-start, leaking-label and missing-history scenarios plus
the legacy day-end contrast; RWT-09 by the trade-context scenario; the
per-policy stage-span outlines pin the temporal contract's exact instants.
Commit `bbcc598`, pushed. Next: T4.

### 2026-09-28 T4: Implement exponential weights and feasibility checks (Claude coder, Lane A)

What changed and why: `retraining/weights.py` with `age_days(available_at,
cutoff)`, `exponential_weights(available_at, cutoff, half_life_days)` (absolute
`2 ** (-age / h)`, pinned reading 1: partial underflow gives exact zeros, total
underflow is rejected as zero total weight), `normalize_mean_one`,
`effective_n`, `uniform_weights`, `SupportMinima`, `REGISTERED_MINIMA` (the
protocol's family/combiner/threshold minima) and `check_support(labels,
weights, minima, stage=...)`, which reports every violated minimum as
"measured X, required Y" in one failure. Per-class minima count raw rows; only
the effective N carries the weights (pinned reading 6). Steps in
`tests/steps/test_retraining_weights.py`.

Scenario change (feature is the spec; recorded per the brief): corrected the
rows of "The spec's analytic fixture: ages 0, h and 2h at half-life 60 days".
It placed rows at 2015-12-31 and 2015-11-01 against the 2016-03-01 cutoff and
expected ages 60 and 120, but 2016 is a leap year and those instants are 61 and
121 elapsed UTC days old, contradicting RWT-04 (age in elapsed UTC days). The
rows now sit at 2016-01-01 and 2015-11-02, exactly 60 and 120 days before the
cutoff; the expected ages and weights are unchanged.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_weights.py -q
  -p no:cacheprovider`: 49 passed (14 scenarios plus 35 Examples rows).
- `uv run ruff check algo-backtest`: clean (after splitting `check_support`'s
  violation builders to stay under complexity 8). `uv run ruff format --check`
  on the retraining package and the weights step file: clean.
  `uv run mypy --strict algo-backtest`: clean, 68 source files.

Adequacy: RWT-04 by the analytic fixture and the fractional/leap/year-end age
outline; RWT-05 by the 12/7-6/7-3/7 fixture, the ratio-preserving case and the
per-stage independence scenario; RWT-06 by the twelve boundary rows of the
minima outline, the all-violations message and the length mismatch; RWT-02 by
the half-life, future-row, naive/non-UTC, empty-stage and invalid-weight
outlines; the extreme-scale rule by the 2^-20 ratio, partial-underflow and
total-underflow scenarios. Commit `f784dca`, pushed. Next: T5.

### 2026-09-28 T5: Pass weights through family-model fitting (Claude coder, Lane A)

What changed and why: `chain/filters/f7_meta_learner.py` gains one optional
keyword on `train_meta_learner`, `family_weights: Sequence[float] | None =
None`, validated by the new `_validated_family_weights` (length equal to
`split.train`, every value finite and non-negative, failures naming
`family_weights`, both counts or the offending position) before any family is
fitted, and forwarded to `_fit_family(..., sample_weights=...)`, which passes
`sample_weight=` to `LGBMClassifier.fit` only when weights are given; with
`None` the fit call is the legacy call unchanged (RWT-17). The combiner is
untouched (T6). Steps in `tests/steps/test_f7_family_weights.py`, which observe
the fits through a recording `LGBMClassifier` subclass monkeypatched into the
module. No scenario was changed. No shared file outside the F7 module was
touched. One incidental change rides along: `ruff format` on the touched F7
module split a pre-existing three-argument `F7Config(...)` call onto three
lines (whitespace only), which is what makes `ruff format --check` pass on
that file.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_f7_family_weights.py -q
  -p no:cacheprovider`: 13 passed (4 scenarios plus 9 Examples rows).
- `uv run pytest` on `test_f7_meta_learner.py`, `test_f7_model_io.py`,
  `test_training_family_contract.py`: 86 passed, the baseline count.
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on
  the F7 module and the new step file: clean. `uv run mypy --strict
  algo-backtest`: clean, 68 source files.

Adequacy: RWT-17 by the legacy-versus-omitted and legacy-versus-uniform
parity scenarios (equal p_hat on a held-out row and equal trend P(up) on every
train row, exact equality); RWT-07 by the observed fits receiving the ramp
weights in order and the 40 train rows in order, and by the balanced
identical-feature outline where the unweighted trend P(up) is exactly 0.5 and
weighting one class to ~0 moves it above 0.99 or below 0.01; RWT-02 by the
length and negative/non-finite outlines with zero fits observed; RWT-05 in
this task is the forwarding contract only (normalization is T4's).

### 2026-09-28 Phase 1 closure (Build gate, Claude coder, Lane A)

Commands from `/tmp/mba-impl-19/algo-suite`:

- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider | tail -1`:
  `1723/1776 tests collected (53 deselected)`; baseline `1598/1651`, so
  Phase 1 added exactly its 125 scenarios (22 + 41 + 49 + 13), none removed.
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1723 passed,
  53 deselected, 0 failed, 0 skipped, exit 0 (71.6 s).
- `uv run ruff check algo-backtest`, `uv run mypy --strict algo-backtest`:
  clean, exit 0. `uv run ruff format --check` on every Phase 1 file: clean.
- `make lint`: exit 2, 195 errors; `make type`: exit 2, 107 errors in 9 files.
  Every failing file is outside this lane and pre-existing at `ef0111d`:
  `docs/stories/done/20-session-2-clean-rerun/scripts/*.py`,
  `scripts/bigquery_*.py`, `tools/mutation_harness.py`,
  `docs/stories/done/13-pattern-volume-experiments/evidence/render_intermediate_figures.py`,
  `algo-viewer/tests/fixtures/build_fixture.py`. The coordinator's separate
  chore commit on the integration branch owns that fix; recorded here as a
  pre-existing failure, not a Phase 1 pass.
- `make audit`: exit 0, no known vulnerabilities (the six workspace members
  are skipped as editable, as always).
- Debt review: `docs/technical-debt.md` has no trigger met by Phase 1; TD-71
  stays open and the protocol treats affected runs as failed candidates.

Integration handoff: none needed in Phase 1. No file under `engine/`,
`wiring.py`, `strategies.py`, `decision_recorder.py`, `run.py`, `cli.py`,
`training.py`, `market_signals.py`, `tools/`, the Makefiles or the shared
conftests was touched.

### 2026-09-28 Cleaner phase 1 (Claude cleaner, Lane A)

Baseline `cc0e10a..c5fa0cf` on `feat/19-adaptive-retraining`, cwd
`/tmp/mba-impl-19/algo-suite`. Complexity from `uv run python -m radon cc -s`
(radon is importable); coverage from the five step files
(`test_retraining_{ingestion,schedule,weights}.py`, `test_f7_family_weights.py`,
`test_f7_meta_learner.py`) with `--cov-branch`; CRAP = cc^2 * (1 - cov)^3 + cc
per function. Before cleaning `schedule.py` was 98 % lines (two uncovered,
undocumented `__str__` methods, CRAP 2); everything else was already 100 %.

| File | Complexity max | Lines / branches after | CRAP max | Actions |
| --- | --- | --- | --- | --- |
| `retraining/__init__.py` | n/a | 100 % / 100 % | n/a | none |
| `retraining/ingestion.py` | 6 (`Ledger._keys_where`) | 100 % / 100 % | 6 | new `require_label_time` (shared RWT-24 check) replaces the inline None check and both `assert`s; `_new_rows` builds the delivered record once; partition row-count update made explicit |
| `retraining/schedule.py` | 4 | 100 % / 100 % | 4 | removed dead `Span.__str__`/`Epoch.__str__`; `select_rows` reuses `require_label_time` (duplicate check removed); `_is_month_start` simplified to one comparison |
| `retraining/weights.py` | 5 (`_validated_total`) | 100 % / 100 % | 5 | none |
| `retraining/utc.py` | 3 | 100 % / 100 % | 3 | none |
| `chain/filters/f7_meta_learner.py` (Phase 1 diff) | 6 (`_validated_family_weights`) | 100 % / 100 % | 6 | none; its finite/non-negative loop intentionally mirrors `weights._validated_total` so `chain.filters` stays independent of `retraining` (F7 only validates and forwards, RWT-17) |

No function exceeds complexity 8 or CRAP 8. Every function has a docstring;
no silent default was found (the empty-ledger open and the first-partition
count of 0 are initial states, not error hiding). Names match the design
component table (`ingestion`, `schedule`, `weights`); `utc.py` is a shared
helper the table does not list. No test assertion changed; the two rejected
`label_time None` scenarios still see "label_time" and the row key.

Observation left for the hardener (behaviour change, not cleaning):
`weights._class_counts` tallies any integer label, so a non-binary label only
surfaces when a per-class minimum is registered.

Gates after the refactor: the five step files 186 passed, exit 0, 100 % lines
and branches on all six modules; `uv run ruff check algo-backtest` exit 0;
`uv run ruff format --check` on the ten Phase 1 files exit 0 (the tree-wide
check still lists 65 files outside this lane, pre-existing at `ef0111d`);
`uv run mypy --strict algo-backtest` exit 0 (68 files);
`make check-perception-architecture check-inference-architecture` PASS.

## Earlier planning verification (before this amendment)

- Strict skill spec validator: exit 0, zero errors/warnings.
- Strict skill tasks validator: exit 0, zero errors/warnings.
- Git whitespace check and checks across eight planning/index files passed:
  40 local links resolve, all 28 requirements map to the correct task bodies,
  and all 19 implementation tasks remain unchecked.
- No runtime gate or empirical trial was run for this documentation-only story.
- Earlier dependency audit in this session was blocked by uncached TA-Lib and
  disabled network; no clean audit result is claimed and no dependency changed.

The parallel amendment adds RWT-29/30 for registered prediction metrics and
semantic repeatability, retaining the 19 task IDs. Current checks are recorded
in the shared parallel plan after all three document sets are reconciled.

## Takeover procedure

1. Read the story entry, canonical requirements, context, design and tasks.
2. Reconcile Git and PR heads; choose an isolated implementation worktree when
   permitted. Use Story 19; Story 18 is the separate market-context plan.
3. Obtain plan approval and execution authorization. Confirm tools and the
   parallel plan's worktree ownership; execute whole-phase batches sequentially
   within this lane and serialize shared-file integration across lanes.
4. Freeze T1 protocol and verify source/config/data identities. The half-life,
   window, cadence and support minima are proposed, not optimized settings.
5. Complete each task with its Gherkin tests and actual gate evidence. Record
   command, cwd, collected/passed counts, exit code, commit and artifact paths.
6. Prove bounded native/host coordination and open-position continuity. If that
   integration is infeasible, stop for design review, not precomputed-only
   substitution or account-reset stitching.
7. Execute the study only at T18 after all gates and explicit authorization.
   Report all five policies and all failures with full parameter tables.
8. Update the monograph from verified artifacts, then run the independent
   Verifier and discrimination sensor required by tlc-spec-driven.

## Known limitations

The existing trading-year plots are already inspected; any comparison on those
dates is exploratory. No unexamined confirmation dataset or live readiness is
claimed. TD-71 execution failures remain failures and cannot be patched away in
the report. Historical replay can pause simulated time during a bounded model
fit; this is not evidence of meeting a live wall-clock deployment deadline.

## 2026-09-28 — Hardener phase 1: mutation testing complete

Agent role: hardener, worktree `/tmp/mba-impl-19`, branch
`feat/19-adaptive-retraining`, base SHA `82d3908` (unchanged by this pass).
Manual behaviour-level mutation testing (`mutmut` unavailable) across
`retraining/{ingestion,schedule,weights,utc}.py` and the phase-1
`family_weights` diff of `chain/filters/f7_meta_learner.py`: 35 mutations
(1 negative control, confirmed KILLED), one at a time, backed up/applied/
tested/restored in place in this shared worktree with a `git status
--porcelain` check after every restore. Full table, method and the
cleaner-flagged `_class_counts` check are in
[mutation-phase1.md](mutation-phase1.md).

Result: 31/34 non-control mutations KILLED on first run; 4 SURVIVED
(ING-1, ING-2, ING-5 in `ingestion.py`; F7-3 in the F7 diff), all genuine
boundary-equality gaps (label_time == available_at, equal-availability
ordering, watermark-equality, and a zero `family_weights` value). Added one
new Gherkin scenario per survivor to `retraining_ingestion.feature` and
`f7_family_weights.feature`, reconfirmed all 4 KILLED. 0 equivalent-mutant
justifications needed.

Command: `uv run pytest algo-backtest/tests/steps/test_retraining_ingestion.py
test_retraining_schedule.py test_retraining_weights.py
test_f7_family_weights.py test_f7_meta_learner.py -q -p no:cacheprovider -x`
(cwd `algo-suite/`), plus full-suite/lint/type gates after restore:
`pytest algo-backtest/tests` → 1727 passed, 53 deselected; `ruff check
algo-backtest` → clean; `mypy --strict algo-backtest` → clean (68 files).

No production module was changed — only the two feature files above and
this story's docs. Deviation: mutated in place in the shared worktree
(backup/restore) rather than in an isolated `git worktree add` scratch copy
per `STAGES.md`'s default Hardener recipe, per explicit team-lead direction
for this resumed session, after confirming the concurrent specifier agent
sharing this worktree never touches the mutated tracked files.

### 2026-09-28 T6: Pass independent weights through combiner fitting (Claude coder, Lane A, Phase 2)

What changed and why: `chain/filters/f7_meta_learner.py`'s `train_meta_learner`
gains a second optional keyword, `combiner_weights: Sequence[float] | None =
None`, one finite non-negative weight per `split.validation` row. The former
`_validated_family_weights` is generalized to `_validated_stage_weights(weights,
row_count, *, name, span)` and called twice — `family_weights` against
`len(split.train)` first, then `combiner_weights` against
`len(split.validation)` — both before any family is fitted, so a request with
both vectors wrong reports the family error first (the specifier's pinned
reading in `qa-procedure-phase2.md`). `combiner_weights` is forwarded as
`sample_weight=` to `LogisticRegression.fit` only when given; `None` keeps the
legacy call (RWT-17). The one-class guard is generalized to
`_require_two_combiner_classes`, which still rejects fewer than two distinct
validation labels unconditionally, and additionally rejects `combiner_weights`
that zero out one class's total weight even though both labels are present
(the "positive weight" scenario). Steps in
`tests/steps/test_f7_combiner_weights.py`: a `_RecordingLogisticRegression`
subclass alongside the existing `_RecordingClassifier` pattern, monkeypatched
into the module, prove each stage's weights reach only its own fit call and
that a weighted combiner really moves p_hat (identical-feature validation
fixture, 20 UP/20 DOWN, ties at 0.5 unweighted). No existing scenario was
changed.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_f7_combiner_weights.py -q
  -p no:cacheprovider`: 19 passed (task asked for >=6; the feature's 12
  scenarios plus outline Examples rows total 19).
- `uv run pytest algo-backtest/tests/steps/test_f7_meta_learner.py
  test_f7_model_io.py test_f7_family_weights.py -q -p no:cacheprovider`:
  80 passed, the baseline count, 0 failed.
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on
  the F7 module and the new step file: clean. `uv run mypy --strict
  algo-backtest`: clean, 68 source files (`tests/` is excluded from the
  project's mypy config; the new step file's recording subclasses only
  type-check standalone against lightgbm/sklearn's real (unstubbed)
  signatures, matching T5's `_RecordingClassifier`).

Adequacy: RWT-08 by the "reach only" scenario (2 LightGBM fits and 1
LogisticRegression fit observed, each stage's own ramp in order, and the
LogisticRegression inputs equal to the families' recomputed P(up) on
`split.validation`); RWT-05 as the forwarding contract for the combiner stage
(normalization remains T4's); RWT-17 by the legacy-versus-omitted and
legacy-versus-uniform-1.0 parity scenarios (equal p_hat and identical
`coef_`/`intercept_`); RWT-02 by the misaligned-vector outline (family checked
first) and the negative/non-finite-position outline, both with 0 fits of
either kind observed; the "zero total weight leaves one class" scenario is a
spec-precision case the specifier flagged, covered by its own scenario and
message-fragment assertions. `split.test` independence reconfirmed by the
differing-test-rows scenario.

### 2026-09-28 T7: Publish immutable epoch bundles (Claude coder, Lane A, Phase 2)

What changed and why: new `retraining/bundle.py` wraps `f7_model_io`'s portable model
document in a content-addressed, atomic registry entry. `publish(model, description,
registry, *, clock, host)` computes the model document's bytes with empty
`f7_model_io` provenance (so `hashes.model_sha256`, the semantic payload hash RWT-30,
depends only on the fitted booster/coefficients, never on policy or thresholds),
builds the identity manifest (schema_version, policy, seed, families, spans, stage
provenance, thresholds, hashes, runtime — every field design.md's "EpochBundle" lists
except the three volatile ones), hashes its canonical sorted-key/no-whitespace JSON
into `bundle_id`, stages both files into `.staging-<bundle_id>-<nonce>`, reloads and
re-checksums the staged model to validate it reproduces the in-memory model's p_hat on
a probe set, then renames the staging directory into `<bundle_id>` in one atomic
`os.replace` (RWT-11). An existing `bundle_id` on disk with matching model bytes is
returned as a reuse (untouched); mismatched bytes are a conflict, left as found,
never repaired (RWT-15). `load(registry, bundle_id, *, strategy_families=None)`
checks `schema_version`, every required field's presence, `model.json`'s sha256, the
manifest's own bundle_id (content-hash self-check), and the manifest's `families`
against the model document's own — each with its own named failure — before an
optional `f7_model_io.require_families` check against a caller's declared strategy.
`list_bundles` lists published (non-staging) bundle ids only. Two private write/rename
seams (`_write_model_file`, `_rename`) exist solely so tests can inject staged
corruption and rename failure without touching the public API — the same pattern
`ingestion.py`'s atomic write already uses implicitly via `os.replace`.

Steps in `tests/steps/test_retraining_bundle.py`, training a small trend+indicator
meta-learner on seeded synthetic rows and exercising every scenario against a real
`tmp_path` registry (no mocks of the filesystem itself).

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_bundle.py -q
  -p no:cacheprovider`: 21 passed (task asked for >=8; the feature's 15 scenarios plus
  outline Examples rows total 21).
- `uv run pytest algo-backtest/tests/steps/test_f7_model_io.py
  test_f7_meta_learner.py test_f7_combiner_weights.py test_f7_family_weights.py -q
  -p no:cacheprovider`: 99 passed, 0 failed (regression, unaffected by this task).
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on the new
  module and step file: clean. `uv run mypy --strict algo-backtest`: clean, 69 source
  files.
- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider`: `1767/1820 tests
  collected (53 deselected)`, exactly baseline 1727 + T6's 19 + T7's 21, none removed.
  `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1767 passed, 53
  deselected, 0 failed (75.6 s).

Adequacy: RWT-11 by the round-trip scenario (identical predictions/thresholds/family
order after reload), the manifest-completeness scenario (every table field present and
non-null, spot-checked values) and the content-addressing scenario (`model_sha256`
recomputed from bytes, `bundle_id` recomputed from the canonical non-volatile
manifest); RWT-15 by the six missing/corrupt/incompatible load-failure scenarios (each
asserting its own named fragment: "missing", "sha256", "bundle_id", "schema_version",
the removed field's own dotted name, "families", "meta_learner.families") plus the two
publish-time failure scenarios (interrupted rename, failed staged validation) proving
no partial artifact is ever listed or loadable. Identical-reuse and conflict are each
their own scenario with byte-level "file bytes (un)changed" assertions. No existing
scenario was changed; no shared file outside the new module was touched.
