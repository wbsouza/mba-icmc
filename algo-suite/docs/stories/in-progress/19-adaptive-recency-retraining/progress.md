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
- [x] T8: Implement separate-span threshold calibration.
- [x] T9: Orchestrate one epoch's weighted training.
- [x] T10: Implement the full adaptive-cycle coordinator.
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

### 2026-09-28 T8: Implement separate-span threshold calibration (Claude coder, Lane A, Phase 2)

What changed and why: new `retraining/thresholds.py`, a pure module reusing
`schedule.Span`'s half-open bounds and `weights.REGISTERED_MINIMA["threshold"]` for
its default minimum. `select_scored_rows` applies the same admission rule as every
other stage (`start <= available_at < end` and `label_time < end`, RWT-01) to a
`ScoredRow` (key, available_at, label_time, score — no label). `calibrate_thresholds`
rejects insufficient rows (naming measured/required counts), a non-finite admitted
score (naming the row's own key), non-increasing thresholds (a tie) and a threshold
outside strict (0, 1), then returns unweighted `numpy.quantile` linear (type 7) 0.10
and 0.90 scores (RWT-10) plus the admitted row keys and span. Thresholds are never
time-weighted, matching the frozen protocol's "Weighting" section.

Steps in `tests/steps/test_retraining_thresholds.py`, including F7's actual terminal
rule (`F7Config`/`F7MetaLearnerFilter` with a stub predictor) to prove the calibrated
thresholds really produce HOLD exactly at the boundary and BUY/SELL just past it.

Scenario correction (recorded per COMMON-RULES, not a silent change): the "Rows
outside the span..." scenario's fixture admits 12 rows once its "first" boundary row
(score 0.50) is correctly included alongside the base 11 scores — its own stated
method (`numpy`'s linear/type-7 quantile, per the feature's own preamble) gives
`theta_low = 0.11` and `theta_high = 0.89` for that exact 12-value set (sorted:
0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95; q=0.10 sits at
fractional position 1.1, interpolating strictly between 0.10 and 0.20), not the
`0.1`/`0.9` the specifier wrote (which is only correct for the 11-row set without
"first"). Verified independently with `numpy.quantile` before touching the feature
file. Changed the two expected values only; the row-count, inclusion/exclusion and
span assertions were untouched and already correct. Also switched the `theta_low`/
`theta_high` Then-steps from bit-exact `==` to `math.isclose` (rel_tol 1e-9): the
11-row and outline scenarios happen to land on exact quantile-index positions (no
interpolation) so `==` passed by coincidence, but a genuinely interpolated quantile
(this scenario's 12-row case) is not bit-exact in binary floating point regardless of
correct arithmetic — standard float-comparison practice, not a weakened assertion
(the tolerance is far tighter than any value the tests distinguish).

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_thresholds.py -q
  -p no:cacheprovider`: 20 passed (task asked for >=6; the feature's 15 scenarios plus
  outline Examples rows total 20).
- `uv run pytest algo-backtest/tests/steps/test_f7_meta_learner.py
  test_retraining_schedule.py test_retraining_weights.py -q -p no:cacheprovider`:
  151 passed, 0 failed (regression, unaffected by this task).
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on the new
  module and step file: clean. `uv run mypy --strict algo-backtest`: clean, 70 source
  files.
- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider`: `1787/1840 tests
  collected (53 deselected)`, exactly the running total (1767) + T8's 20, none removed.
  `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1787 passed, 53
  deselected, 0 failed (74.0 s).

Adequacy: RWT-10 by the hand-computed 11-row scenario (exact quantile-index positions,
no interpolation, `==`), the two-row interpolation outline (hand-derived fractional
positions) and the order-independence scenario (shuffled input, same result); RWT-01
by the span-admission scenario (before/at-end/after/immature excluded, boundary-start
row included, corrected row count and thresholds); F7's strict-inequality HOLD-at-
threshold behavior by the five-case outline exercising the real `F7MetaLearnerFilter`.
Insufficient-support, non-finite-score and non-increasing/out-of-band rejections each
have their own scenario asserting the specific named fragment. No shared file outside
the new module was touched.

### 2026-09-28 T9: Orchestrate one epoch's weighted training (Claude coder, Lane A, Phase 2)

What changed and why: new `retraining/trainer.py` orchestrates T2 (ingestion) -> T3
(schedule) -> T4 (weights) -> T5/T6 (weighted F7 fit) -> T7 (bundle) -> T8 (thresholds)
into `train_epoch(policy, epoch, ledger, features, registry, settings)`: reads only
rows visible/mature at the epoch's own preparation cutoff `C` (`schedule.stage_spans`'s
own threshold-span end, RWT-01/RWT-24), weights family/combiner stages uniformly or
(policy E) exponentially to each stage's own span end, checks both stages' support
before any fit (RWT-06), fits with `split.test=()` (never a future test span, RWT-30),
scores the threshold span with the freshly fitted model and calibrates, then publishes
one immutable bundle (RWT-11) via T7. `train_epoch` always refits when called; "freezing"
policy F for later months is a scheduling decision the caller (T10) makes by simply not
calling `train_epoch` again — F/Q/U's later-epoch spans are already anchored to the
first `D` by T3's `schedule.stage_spans`, so a repeated call reproduces byte-identical
rows, weights and payload hash without any special-casing here.

Two small, covered extensions to T2's `ingestion.py` this task needed: `Ledger.row`/
`.rows` (full `SourceRow`s by key — T9's stage selectors need more than keys) and
`Ledger.visible_partitions(cutoff)` (partitions with a row visible at or before
`cutoff`; a partition consumed later, whose rows are all after `cutoff`, never
contributed to a fit prepared against it — RWT-30's future-tail independence needs
this for `hashes.data_sha256`, exactly as it already needed a cutoff-scoped
`ledger_watermark`, see below). Both got their own `retraining_ingestion.feature`
scenarios (now 27 scenarios, was 25).

**A real design gap found and fixed while implementing (not a scenario problem):**
the frozen protocol's manifest table marks `ledger_watermark` and (via
`hashes.data_sha256`) the consumed partitions as identity fields, described only as
"the ingestion watermark" / "the consumed partitions' identities" — with no explicit
statement of whether that means the ledger's raw, ever-advancing internal watermark or
one scoped to what a specific epoch's cutoff could actually see. Implementing it as
the ledger's raw `.watermark` (my first attempt) **fails RWT-30's own "future-tail
mutation invariance" requirement**: consuming a later, unrelated batch (rows dated
after the epoch's cutoff `C`) would change the epoch's `bundle_id`, even though no
row it contributed can ever have influenced the fit. Fixed by computing both fields
capped to the epoch's own cutoff — `trainer._watermark_at_cutoff` (max availability
among rows visible at or before `C`, via `Ledger.visible_keys`, not `Ledger.watermark`)
and `Ledger.visible_partitions(cutoff)` for `data_sha256` — verified against every
watermark value the feature file asserts (first-epoch: 2016-02-25; pending-labels:
2016-02-28T20:00, which needs the *visible*, not *mature*, watermark since a pending
row still advances it; later-epoch: 2016-03-26) and against the mutation-invariance
scenario, which only passes with this fix.

**Two scenario corrections (recorded per COMMON-RULES, not silent changes), both
found and verified by hand-computing the real production model's output before
touching the feature file:**

1. The "second epoch" Outline asserted `theta_low`/`theta_high` for policy Q's second
   epoch "differ from F's first-epoch thresholds" unconditionally. Q's second-epoch
   model is byte-identical to F's (same family/combiner spans, already correctly
   asserted via `payload_relation: equals`); scoring it on the March threshold rows
   happens to reproduce the exact same 0.10/0.90 quantiles as F's February rows
   (verified independently with a standalone script: both row sets' `trend_direction`
   pattern maps to the same two p_hat values under this fit, since the tiny fixture's
   other features don't split the tree). U's second epoch (a genuinely different
   model) does differ, confirmed the same way. Added a `threshold_relation` Examples
   column (`equals` for Q, `differs from` for U) instead of the single hard-coded
   "differ" line, so each policy asserts the value that is actually true of it.
2. My own test fixture (not the spec): the "Recent DOWN labels outweigh older UP
   labels" scenario's step for "rows sharing identical features" originally made
   *every* family column identical across the five replaced rows, including the
   indicator columns (rsi/macd_hist). That kills the indicator family's learnable
   variance too (all rows equal on every column the family models ever see), which
   collapses the combiner and threshold stage to a constant output and makes
   `calibrate_thresholds` fail on tied quantiles. Fixed by making only the three
   TREND columns identical (what the scenario's probe actually reads via
   `family_vector(TREND, ...)`) while keeping each row's original indicator values,
   restoring a working, non-degenerate fit. No feature-file change needed for this
   one — it was a step-implementation bug, not a wrong scenario.

Steps in `tests/steps/test_retraining_trainer.py`; the "trend family P(up)" checks
reload the published bundle (`bundle.load`) rather than trusting the in-memory model,
so publish/load fidelity is exercised too.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_trainer.py -q
  -p no:cacheprovider`: 19 passed (task asked for >=10; the feature's 14 scenarios plus
  outline Examples rows total 19).
- `uv run pytest algo-backtest/tests/steps/test_retraining_ingestion.py
  test_retraining_schedule.py test_retraining_weights.py test_retraining_bundle.py
  test_retraining_thresholds.py test_f7_meta_learner.py test_f7_combiner_weights.py
  test_f7_family_weights.py test_f7_model_io.py -q -p no:cacheprovider`: 257 passed,
  0 failed (regression).
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on every
  touched file: clean. `uv run mypy --strict algo-backtest`: clean, 71 source files.
- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider`: `1808/1861 tests
  collected (53 deselected)`, exactly the running total (1787) + T9's 19 + the 2 new
  ingestion scenarios, none removed. `uv run pytest algo-backtest/tests -q
  -p no:cacheprovider`: 1808 passed, 53 deselected, 0 failed (81.7 s).

Adequacy: RWT-01/RWT-24 by every row-key scenario (family/combiner/threshold keys
exactly match hand-derived span membership; pending rows excluded and independently
confirmed pending/mature via the ledger); RWT-06 by the registered-minima rejection
(0 LightGBM fits observed, exact "measured/required" message) and the one-class
combiner-span failure; RWT-09 by the trade-context scenario (flipped vetoed/traded/pnl
fields change nothing); RWT-11 by "a bundle is published" plus reload-based prediction
and threshold-quantile checks against the real published artifact; RWT-30 by the
repeated-fit-into-fresh-registry scenario (same bundle_id/model_sha256/thresholds,
independently varying wall-clock fields) and the future-tail mutation scenario (the
watermark/data-sha256 fix above). No shared file outside the `retraining/` package was
touched; `ingestion.py`'s two additions are backward-compatible pure reads.

### 2026-09-28 T10: Implement the full adaptive-cycle coordinator (Claude coder, Lane A, Phase 2 close)

What changed and why: new `retraining/cycle.py`'s `Coordinator` runs the registered
consume -> mature -> fit -> validate -> publish state machine exactly once per
(policy, activation_boundary) (RWT-25), on disk under `cycles/<cycle_id>/record.json`
(status, attempts, completed stages, bundle_id) plus `checkpoints/<stage>/` per
completed stage. `cycle_id` is the sha256 of the canonical JSON of the request's
identity fields only (policy, protocol_hash, cutoff, activation_boundary,
source_watermark, prior_bundle_id) — never the batches/settings/features, which are
operational, not identity. Handling order: an already-`ok` cycle_id short-circuits
with no stage touched; a different cycle_id already `ok` for the same
(policy, boundary) is a conflict (RWT-25); the activation boundary must be a
registered, future-only UTC month start (RWT-26), checked before any stage; then
stages run in order, each skipped and reloaded from its checkpoint when already
completed. The registered timeout is checked both entering and completing every
stage (pinned reading: both stage-entry and stage-exit), so a mid-stage overrun is
attributed to the stage that was running, never the next one. A failed stage is
recorded with its name and reason before the exception reaches the caller (RWT-27);
nothing a failed stage did not validate is ever published (RWT-23).

Two production refactors this task needed, both behavior-preserving (T7/T9's own
gates re-run unchanged below prove it): `bundle.publish` split into `bundle.stage`
(compute identity, reuse-or-conflict, write+validate the staged files) and
`bundle.finalize` (the atomic rename) so the coordinator can checkpoint "validate" and
"publish" as separate, independently resumable stages; `trainer.train_epoch` split
into `trainer.prepare_epoch` (fit only, no registry write) and the publish call, so
the coordinator's "fit" stage can checkpoint the trained model (`f7_model_io.
dump_model` + a serialized `BundleDescription`) without touching the registry, and a
later "validate" retry reloads it instead of refitting.

**Found and fixed while implementing (not a test-authoring bug — a real gap in the
consume-stage's watermark check):** the naive check ("the ledger's current watermark
must equal `source_watermark`, else fail") breaks the "different policies at the same
boundary are independent cycles" requirement: two policies built against the same
original (e.g. empty-ledger) snapshot and the same batches, run one after the other,
share one ledger — by the time the second policy's cycle runs, the first has already
advanced the ledger's watermark by consuming those exact batches, so a literal
equality check rejects the second as a false "conflict" even though nothing
unexpected happened (ingestion's own `consume` is idempotent for identical content).
Fixed with `cycle._watermark_after`: the check now accepts either the raw
`source_watermark` (the fresh case) or the watermark that consuming exactly
`request.batches` on top of it would produce (the already-consumed-by-a-sibling-
policy case); a genuinely stale watermark (the "stale-U" scenario) still matches
neither and is still rejected. Verified this doesn't weaken the stale-watermark
scenario by re-deriving both cases' arithmetic by hand before changing the code.

Also found: the `_RecordingClassifier`/timeout-advancing test doubles used
composition (`self._inner = LGBMClassifier(...)`) the way earlier scenarios in this
lane never needed to survive a real `f7_model_io.dump_model` call — T6/T7's own
"LightGBM fits are observed" scenarios never reached a successful publish, so the
missing `.booster_` attribute never surfaced. T10's "publish-stage crash, retried"
scenario does reach a real publish while fits are observed, which surfaced it.
Fixed by making the test doubles real `LGBMClassifier` subclasses (T6's proven
pattern) instead of wrappers.

Steps in `tests/steps/test_retraining_cycle.py`; the trainer fixture batches are
duplicated verbatim from T9's `retraining_trainer.feature` Background (same repo
convention every prior task in this lane already follows: each step module is
self-contained).

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_retraining_cycle.py -q
  -p no:cacheprovider`: 19 passed (task asked for >=10; the feature's 16 scenarios
  plus outline Examples rows total 19).
- `uv run pytest algo-backtest/tests/steps/test_retraining_ingestion.py
  test_retraining_schedule.py test_retraining_weights.py test_retraining_bundle.py
  test_retraining_thresholds.py test_retraining_trainer.py test_f7_meta_learner.py
  test_f7_combiner_weights.py test_f7_family_weights.py test_f7_model_io.py -q
  -p no:cacheprovider`: 276 passed, 0 failed (regression; confirms the `bundle.py`/
  `trainer.py` refactors are behavior-preserving).
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check` on every
  file this task touched: clean (the repo-wide check reports pre-existing
  unformatted files elsewhere, outside this lane, unchanged by this task).
  `uv run mypy --strict algo-backtest`: clean, 72 source files.
- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider`: `1827/1880 tests
  collected (53 deselected)`, exactly the running total (1808) + T10's 19, none
  removed. `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1827 passed,
  53 deselected, 0 failed (85.4 s).

Adequacy: RWT-25 by the once-per-boundary scenarios (identical request is a no-op —
0 LightGBM fits, unchanged registry bytes; a fresh `Coordinator` instance on the same
directories agrees; a different request for an already-`ok` boundary is a named
conflict); RWT-23 by the watermark-conflict scenario (rejected at stage "consume",
naming the stale value, ledger left empty) and the "checked only after the
once-per-boundary lookup" scenario (a completed cycle stays repeatable); RWT-26 by
the four-case boundary-validity outline (equal-to-cutoff, before-cutoff, not-a-
month-start, outside-the-registered-schedule) and the second-boundary scenario
(activation strictly future, prior bundle unaffected); RWT-27 by the three
failure-attribution scenarios (fit / timeout / validate, each naming its own stage
and reason) and the two retry-resumption scenarios (publish-crash retried from the
fit+validate checkpoints with zero re-fits; fit-crash retried from the mature
checkpoint with the ledger's bytes byte-for-byte unchanged, proving consume was not
re-run). No shared file outside `retraining/` was touched.

## Phase 2 closure (T6–T10, Build gate)

Commands from `/tmp/mba-impl-19/algo-suite`, run after T10's own commit:

- `uv run pytest algo-backtest/tests -q --co -p no:cacheprovider`: `1827/1880 tests
  collected (53 deselected)`; Phase 1 baseline was `1727/1780`, so Phase 2 added
  exactly 100 scenarios: 19 (T6) + 21 (T7) + 20 (T8) + 19 (T9) + 19 (T10) plus 2 new
  `retraining_ingestion.feature` scenarios for T9's `Ledger.row`/`.rows`/
  `.visible_partitions` additions, none removed.
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1827 passed, 53
  deselected, 0 failed, exit 0 (85.4 s).
- `uv run ruff check algo-backtest`, `uv run mypy --strict algo-backtest`: clean,
  exit 0 (72 source files). `uv run ruff format --check` on every Phase 2 file
  (T6–T10's production modules and step files): clean.

Phase 2 delivers a complete, host-side, in-process consume -> mature -> fit ->
validate -> publish cycle for one epoch: independent combiner-stage weights (T6),
immutable content-addressed bundles (T7), separate-span threshold calibration (T8),
one-epoch orchestration (T9) and the checkpointed, once-per-boundary coordinator
(T10). What remains for Phase 3 (T11 on): the on-demand provider, native LEAN
integration, decision-record epoch identity, run staging, CLI orchestration, the
actual five-policy study, and the monograph writeup — none of which this phase
touches (`engine/`, `wiring.py`, `strategies.py`, `decision_recorder.py`, `run.py`,
`cli.py`, `training.py`, `market_signals.py`, `tools/` and every Makefile are
untouched by T6–T10, per the Lane A brief).

Integration handoff notes for Phase 3:

- T11 (on-demand provider) can call `bundle.load(registry, bundle_id,
  strategy_families=...)` directly; `cycle.Coordinator.eligible_bundle(policy,
  activation_boundary)` already resolves "the bundle eligible at this boundary" from
  the on-disk cycle records, so T11's cache/eviction layer can sit directly on top of
  it without re-deriving eligibility itself.
- T12 (native LEAN integration) is the only task that needs a *host-process*
  transport around `Coordinator.handle`; this task's docstring says so explicitly.
  `CycleRequest` is a plain dataclass (policy/protocol_hash/cutoff/
  activation_boundary/source_watermark/prior_bundle_id/batches/settings/features) —
  T12 needs to decide how the LEAN-side caller supplies `batches` (parquet partition
  reads, presumably via `ingestion.read_partition`) and `features` (the per-key
  feature-lookup source T9/T10 both treat as a caller-supplied dependency, never
  reading it from a file itself).
- T13 (decision-record epoch identity) needs a bundle's `activation_boundary` and
  `bundle_id`, both already on every published manifest and every cycle record;
  no new field is needed from this phase.
- Every stage's checkpoint files are plain JSON under `cycles/<cycle_id>/
  checkpoints/<stage>/`, documented in `cycle.py`'s module docstring; treat that
  layout as part of this module's contract, not an implementation detail, since T10's
  own tests read it directly (matching how T7's tests read bundle manifests).

## Cleaner phase 2 (2026-09-28)

Baseline: `82d3908..c6a5553` (T6-T10) on `feat/19-adaptive-retraining`, worktree
`/tmp/mba-impl-19`. Scope: `bundle.py`, `cycle.py`, `thresholds.py`, `trainer.py`, the
T9 `ingestion.py` additions (`Ledger.row`/`.rows`/`.visible_partitions`), and the T6
`f7_meta_learner.py` diff, plus their six step files.

| File | ruff C901/PLR0912/PLR0915 | mypy --strict | coverage (branch) | CRAP max | Action |
| --- | --- | --- | --- | --- | --- |
| `retraining/bundle.py` | clean | clean | 98% (245, 251, 263 uncovered: two validation-failure raises inside `_validate_staged`, and `_default_clock`) | 9 (`load`, radon CC 9; ruff C901 reports it within the max-8 gate) | none — `load` is a flat sequence of five independent fail-fast checks, each already a self-contained raise; splitting it would add indirection (multi-parameter helpers over `model_bytes`/`identity`/`model`) without reducing real complexity |
| `retraining/cycle.py` | clean | clean | 96% (67, 282, 452-454, 465->462, 504 uncovered: `_default_clock`, `eligible_bundle`'s "no cycle recorded" raise, `_run_publish`'s already-completed-checkpoint read path, and `_records_for`'s no-match branches) | 8 (`_records_for` after refactor) | refactored: extracted `_records_for` to remove duplicate directory-scan/filter logic between `_require_no_boundary_conflict` and `_find_by_policy_boundary` (radon CC 9 before, both call sites now thinner); tightened `_run_fit`/`_run_validate`'s model type from `Any` to `TrainedMetaLearner` (was accepted but unused type-safety loosening — `f7_model_io.load_model` already returns the concrete type) |
| `retraining/thresholds.py` | clean | clean | 100% | 6 | none |
| `retraining/trainer.py` | clean | clean | 98% (119 uncovered: `_watermark_at_cutoff`'s "no row visible" raise) | 6 | none |
| `retraining/ingestion.py` (T9 additions) | clean | clean | 100% | n/a (`row`/`rows`/`visible_partitions` all CC 1-2) | none |
| `chain/filters/f7_meta_learner.py` (T6 diff) | clean | clean | covered by `test_f7_meta_learner.py`/`test_f7_combiner_weights.py` (full suite green, no per-function gap found) | 6 max (`_validated_stage_weights`, `_require_two_combiner_classes`) | none |

Checked the duplication the brief flagged explicitly: `cycle.py`'s `_watermark_after`
(handles a `None` starting watermark across several batches, since `source_watermark`
is `None` for the first epoch) versus `Ledger.consume`'s `self._watermark =
iso_utc(max(row.available_at for row in new_rows))` (never needs `None`-handling,
since `_require_watermark_order` already guarantees every new row is at or after the
existing watermark). Confirmed by hand the two are mathematically equivalent
wherever their preconditions overlap; did not merge them into a shared helper since
their invariants differ enough (one must tolerate an absent watermark, the other
never does) that forcing a shared abstraction would add a parameter and a branch to
the simpler call site for no behavioural gain.

Coverage gaps recorded above were flagged, not closed — per the cleaner's brief, this
role reports uncovered lines and refactors on CRAP/complexity, it does not author new
Gherkin scenarios (that is the hardener's job, or a coder follow-up); none of the
gaps found are logic that ships silently wrong (each is either a fail-fast raise with
an obvious repro, or a real-clock default that tests correctly bypass by injection).

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest algo-backtest/tests/steps/test_f7_combiner_weights.py
  test_retraining_bundle.py test_retraining_thresholds.py test_retraining_trainer.py
  test_retraining_cycle.py test_retraining_ingestion.py test_f7_meta_learner.py
  test_f7_model_io.py -q -p no:cacheprovider --cov=algo_backtest.retraining
  --cov-branch`: 191 passed, 96% branch coverage on `algo_backtest.retraining`.
- `uv run ruff check algo-backtest`: clean. `uv run ruff format --check
  algo-backtest/src/algo_backtest/retraining/cycle.py`: already formatted.
  `uv run mypy --strict algo-backtest`: clean, 72 source files (cache removed after).
- `make check-perception-architecture check-inference-architecture`: both PASS.
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1827 passed, 53
  deselected, 0 failed (79.5 s) — unchanged from the coder's Phase 2 closure count,
  confirming the `cycle.py` refactor is behavior-preserving.

## 2026-09-28 — Hardener phase 2

Manual mutation testing (no scratch worktree — in-place backup/apply/restore
per mutation, per the team lead's brief) over the cleaner's Phase 2 output:
`retraining/{bundle,thresholds,trainer,cycle}.py`, the T6 `combiner_weights`
diff of `chain/filters/f7_meta_learner.py`, and the T9 additions to
`retraining/ingestion.py`. Full table, negative control and design-gap
detail in [mutation-phase2.md](mutation-phase2.md).

56 mutations injected across the six scope areas (bundle 9, cycle 11,
thresholds 8, trainer 8, F7 diff 5, ingestion diff 4) plus 1 negative
control. 48 KILLED on first run; 8 initially SURVIVED, each fixed with a new
or extended Gherkin scenario (never by weakening an existing one) and
reconfirmed KILLED. 0 SURVIVED and 0 equivalent-mutant justifications
remain. Both mutations the team lead specifically flagged as design-gap
regressions — removing the cycle's watermark-conflict tolerance for an
independent policy replaying the same batches (RWT-25), and making
`ledger_watermark`/`hashes.data_sha256` depend on the ledger's raw state
instead of the epoch's own cutoff (RWT-30 future-tail independence) — were
**KILLED on the first run** by existing scenarios, confirming both of the
coder's mid-task production fixes are properly guarded against regression.

New scenarios added (all additive): bundle.py's default-clock bypass
(publishing without an injected clock); cycle.py's default-clock bypass, the
"no cycle ever ran" eligibility lookup, the exact-timeout-boundary case, and
a publish-checkpoint-then-timeout-crash retry that exercises the previously
uncovered checkpoint-resume read path; a threshold fixture row isolating the
`available_at` half-open upper bound from the `label_time` bound; trainer.py's
empty-ledger fail-fast case, a tightened `training_duration_seconds` upper
bound, and an exact `per_class` provenance check; and an F7 scenario proving
`family_weights` is validated before `combiner_weights` when both are
invalid at once.

Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0):

- `uv run pytest` on the 8 covering step files: 199 passed (191 baseline + 8
  new scenarios).
- `uv run ruff check algo-backtest`: clean (fixed 5 new E501s from the
  hardening step defs before this run).
- `uv run mypy --strict algo-backtest`: clean, 72 source files (cache
  removed after).
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1835 passed, 53
  deselected, 0 failed (85 s).
- `git status --porcelain` after every mutation's restore matched the
  session baseline; the branch's only change from this pass is the 8
  feature/step files plus this report — no file under `algo-backtest/src`
  was left modified.

Commit: `test(retraining): harden phase 2 modules against surviving mutants`.

### 2026-09-28 Phase 3 integration, minimum-viable slice (compressed delivery for an
advisor deadline)

Worktree `/tmp/mba-integ19` (`feat/integrate-19-phase3`, merged onto Story 21's
Phase 3 integration HEAD `3a525ef`). Merge of `feat/19-adaptive-retraining`
(Phase 1+2) was clean, no conflicts.

**Explicit scope reduction, not a silent shortcut**: T11 (on-demand provider)
and T12 (native LEAN integration) are only partially implemented today. What
is proven: `ChainAlgorithm` can load its F7 model from a single, published
retraining bundle (`retraining.bundle.load`) instead of a `model_path` JSON
file, through the real engine, in one real LEAN backtest. What is **not**
implemented (remains real, separately gated future work): T11's cache/
eviction layer, boundary-based bundle selection via
`cycle.Coordinator.eligible_bundle`, and T12's mid-replay adaptive-cycle
retraining triggers ("bounded host coordination" — the design doc's own
harder feasibility gate). Neither T11 nor T12's task checkbox is marked done
in tasks.md; both remain open for that remaining work.

Changes:
- `algo_backtest/retraining/provider.py` (new): `load_active(registry,
  bundle_id, strategy_families=...)`, a thin wrapper over `bundle.load`
  documented as the minimum slice (module docstring names exactly what's
  deferred).
- `engine/chain_algorithm.py`: `ChainAlgorithm` gained three optional class
  attributes, `bundle_registry`/`bundle_id`/`strategy_dir`, alongside the
  existing `model_path` (now optional). `initialize()` branches: if
  `bundle_registry`+`bundle_id` are set, the F7 model loads via
  `provider.load_active` (logs `<TAG>_BUNDLE_ID=`/`<TAG>_MODEL_SHA256=` from
  the bundle's own manifest hash); otherwise the existing `load_model(
  self.model_path)` path is unchanged, so every existing strategy (baseline,
  hybrid, all `tests/algos/*`) is untouched. Bundle-sourced runs still take
  `theta_high`/`theta_low` from `config.yaml`, not the bundle's own
  calibrated thresholds — wiring the bundle's thresholds into the terminal
  rule is left for T13 (decision-identity) or a follow-up, not done here.

New native gate scenario (`tests/features/retraining_provider_engine.feature`,
`tests/steps/test_retraining_provider_engine.py`, algo fixture
`tests/algos/bundle_provider_baseline/`): fits one real T9 epoch bundle (policy
U, `schedule.stage_spans`' real spans: family `[2015-03-02, 2015-11-01)`,
combiner `[2015-11-01, 2015-12-01)`, threshold `[2015-12-01, 2015-12-31)`)
from the project's real EUR/USD M1 Parquet (`ALGO_DATA_ROOT`, same
requirement as `scripts/train_baseline_meta_learner.py`; skips cleanly if
unset), publishes it, then runs the baseline chain natively in the pinned
LEAN image over the bundle's real 2016-01 deployment window with real EUR/USD
LEAN minute data, asserting exit 0, the bundle-id/model-sha256 log lines, at
least one `BUNDLEPROVIDER_DECISION|` line and a real LEAN `STATISTICS::`
summary.

Gate evidence (cwd `/tmp/mba-integ19/algo-suite` unless noted; `uv sync
--group dev` was needed first, the venv `uv run python <script>` had built
earlier had no dev group):
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider -m "not
  integration"`: 2210 passed, 64 deselected, 0 failed (87 s).
- `uv run pytest algo-backtest/tests/steps/test_retraining_provider_engine.py
  -m integration`: 1 passed (325 s) — the new native scenario, real fit + real
  LEAN run.
- `uv run pytest algo-backtest/tests/steps/test_closed_signal_parity.py
  algo-backtest/tests/steps/test_minute_pnl_anchors.py -m integration`: 3
  passed, 4 failed. The 4 failures
  (`test_overnight_losses_survive_incomplete_candles_at_calendar_boundaries`
  ×3, `test_a_slice_without_the_subscribed_quote_cannot_reset_risk_anchors`)
  are pre-existing: confirmed by `git stash`-ing every change in this pass
  and re-running the identical command against the merged-but-unmodified
  tree, same 4 failures, same `'Receiver' object has no attribute
  '_advance_time_exit'` error, on code neither Story 19 nor this integration
  touches. Not fixed here (out of today's scope); flagged for a separate fix.
- `uv run ruff check .` (workspace-wide): clean. `uv run ruff format --check`
  on the new/touched files: clean (one file reformatted before commit).
- `uv run mypy --strict algo-backtest`: clean, 76 source files
  (`chain_algorithm.py` is container-only and excluded from strict mypy, per
  its own module docstring, same as before this change).
- `make check-perception-architecture check-inference-architecture`: both
  PASS.

**The real backtest** (baseline chain, EURUSD, 2016-01-04 to 2016-01-08, cash
10000, the bundle above as its only F7 model, real LEAN, real market data):
221 orders, 71 closed trades, net profit -15.311%, win rate 27%, Sharpe
-1.652 (full LEAN `STATISTICS::` block in the test's captured log on
failure/rerun). This is a four-trading-day smoke window chosen for turnaround
time, not a methodology result — same caveat as `run_baseline_chain.feature`'s
existing TD-51 note; it demonstrates the wiring works and produces a real,
un-fabricated number, not a validated trading result.

Commit: `feat(retraining): wire the on-demand provider into the live engine
(minimum viable slice for today's delivery)`.

### 2026-09-28 Phase 3 minimum-viable slice, second entry: real full-year run,
policy F, the registered study window (do not confuse with the smoke-window entry
above — same wiring, different bundle, different window, both kept distinct)

Follow-up requested after the first entry above: rerun the same single-pinned-
bundle wiring, but honestly and over the actual registered study window, not
the 4-day smoke window. Reusing the earlier entry's bundle (fit tagged
policy U, deploying 2016-01) unchanged across a full year would have
misrepresented policy U: per `schedule.stage_spans`, U's model anchor is the
*current* epoch's own start, so a U bundle is only ever meant to represent
one month before the next month's refit — the exact mid-replay retraining
this slice's wiring deliberately does not implement (see the first entry
above). Policy F's anchor is instead the whole registered schedule's first
month (`epoch.schedule_start`), i.e. F is defined to be fit once and reused
unchanged for the entire horizon — precisely what this slice's wiring already
does. So a **new** bundle was fit, honestly labeled F, anchored at the real
registered study's D0.

Registered study window (`.specs/features/recency-weighted-retraining/spec.md`,
"Study dates"): 2016-03-01 through 2017-02-28. Policy F's real spans for this
D0 (`schedule.stage_spans(epochs[0], "F")`, verified by calling the production
function directly rather than hand-derived): family `[2015-03-02, 2015-12-31)`
311,737 rows, combiner `[2015-12-31, 2016-01-30)` 29,825 rows, threshold
`[2016-01-30, 2016-02-29)` 28,801 rows — all far over the registered minima
(1000/100/100). `bundle_id
e9681f4666891b5a704668c5b294b2781f3319763cdc951c7d6dec566d407ecb`.

**The real backtest** (baseline chain, EURUSD, 2016-03-01 to 2017-02-28 — the
full registered window, not a smoke window — cash 10000, this one frozen
bundle as the sole F7 model for the whole year, real LEAN, real market data,
container log confirms `BUNDLEPROVIDER_BUNDLE_ID=e9681f46...` and
`BUNDLEPROVIDER_MODEL_SHA256=5755a6cb...` logged at 2016-03-01 00:00:00):

- Total orders 4964, closed trades 1603.
- Win rate 26%, loss rate 74%, profit/loss ratio 1.97.
- Net profit -97.782% (start equity 10000.00, end equity 221.82).
- Compounding annual return -97.782%, Sharpe -1.499, Sortino -2.541.
- Max drawdown 97.9%.

A near-total account wipeout under this frozen single-bundle wiring across the
full registered year — consistent with the standing finding that every arm
was negative over a full trading year (see the story-12/14 record). Reported
undisguised: not a fabricated number, not softened, not a validated
methodology result either (still the same minimum-viable-slice wiring, no
mid-replay retraining, no bundle-sourced theta override — same caveats as the
first entry above).

Gate evidence: same code path as the first entry (no source changed for this
run, only a second bundle fit and a second backtest); the fit and run scripts,
the fitted bundle's registry, the full 2.3 MB container log and the extracted
`STATISTICS::` block are all under `/tmp/mba-fast19-window-job-1790634718`
(scratch only — nothing written to this worktree or the real data root by the
run itself).

Commit: `docs(retraining): record the real full-year policy-F backtest result`.
