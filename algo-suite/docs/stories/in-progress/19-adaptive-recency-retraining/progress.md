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
- [ ] T5: Pass weights through family-model fitting.
- [ ] T6: Pass independent weights through combiner fitting.
- [ ] T7: Publish immutable epoch bundles.
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
total-underflow scenarios. Next: T5.

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
