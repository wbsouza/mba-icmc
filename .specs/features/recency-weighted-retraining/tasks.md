# Adaptive recency-weighted retraining tasks

Status: draft; 19 pending tasks. Planning only. No task below is authorized for
execution by the current request. [Design](design.md), [requirements](spec.md).

## Execution Protocol

Activate **tlc-spec-driven** by name before future implementation and follow its
Execute flow. If unavailable, STOP and tell the user. Obtain plan approval and a
separate execution go-ahead; confirm tool preferences and offer sequential
whole-phase worker batches before dispatch. No implementation agents are launched now.

Use CodeGraph before code discovery, apply_patch for edits, Gherkin/pytest-bdd for
all tests, and actual project gates. Use docs-writer for documents. Tests and
minimal component wiring belong in the same atomic task, never a later test task.
After a green gate, update task status and spec traceability in the same
Conventional Commit. Record actual commands, counts, exit codes and hashes in
story progress. No bulk completion, hidden skips or weakened tests.

Run the skill's fresh independent Verifier automatically after the final task:
spec-anchored outcomes, isolated behavior-level fault injection (no stash),
file:line evidence and validation.md PASS/FAIL. Surviving faults become fixes;
bound fix/reverification to three rounds before escalation. Run validate_state
before declaring implementation complete. No completion report exists now.

## Test Coverage Matrix

Generated from algo-suite/CLAUDE.md, Makefile, pyproject.toml and sampled
f7_meta_learner, f7_model_io, training_family_contract, signal_configuration,
closed_signal_parity and minute_pnl_anchors features plus existing F7 steps.
Confirm before Execute. Every code test remains Gherkin-first.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain | BDD unit | Every AC branch and boundary; numeric oracles plus legacy equality | algo-backtest/tests/features + tests/steps | Quick |
| Integration | BDD integration | Happy, corrupt, partial, duplicate, recovery and failure paths; actual model fits alongside doubles | algo-backtest/tests/features + tests/steps | Host |
| Native | BDD container integration | State continuity, protection order, timing, bounded coordination and native parity | algo-backtest/tests/features + tests/steps | Native |
| Analysis | BDD unit/integration | Known numeric results, alignment and unavailable/error distinctions | algo-analyze/tests/features + tests/steps | Analysis |
| Documentation | Document checks | Formula, source, link, status and evidence reconciliation | story and monograph | Docs/Monograph |
| Evidence | Artifact reconciliation | All registered attempts, cycles, failures and settings included | story evidence | Evidence |

Each task's scenario count is a proposed minimum, not a claimed result. Collect
the current baseline before changing tests; preserve it and add the new cases.
Record collected/passed totals to detect deletions. Numerical fixture data
proves mechanics only. Real-market findings require real archived input data.
All new branches need coverage, Ruff complexity <=8 and strict mypy.

## Gate Check Commands

Run Python commands from algo-suite; monograph commands from monografia.
New proposed test files must be selected explicitly after creation and collect
nonzero tests. No-tests exit handling in make test is not a successful task gate.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Pure/trainer component | `uv run pytest algo-backtest/tests`; `make lint type`; explicit new step-file selection |
| Host | IO/coordinator/CLI | Quick plus real host/subprocess BDD cases in the owning test suite |
| Native | LEAN wiring | `make check`; `uv run pytest algo-backtest/tests/steps/test_closed_signal_parity.py algo-backtest/tests/steps/test_minute_pnl_anchors.py -m integration`; explicitly selected new native steps with `-m integration` |
| Analysis | Reporting | `uv run pytest algo-analyze/tests`; `make lint type`; `make -C algo-analyze check-inference` |
| Docs | Story/protocol | `git diff --check`; strict spec/tasks validators below; link and requirement checks |
| Monograph | Thesis edits | Docs plus `make verify` from monografia |
| Evidence | Real study | All prior gates, exact registered run commands, manifest/report reconciliation, input hashes unchanged |
| Build | Phase closure | `make check`; `uv run ruff format --check` on touched Python files; native/analysis gates where applicable; `make audit` and debt review |

No dependencies need installation for this plan. Before later tasks, record
unavailable Docker/data/network/wheels as blocked gates, not passed checks.

```sh
python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/recency-weighted-retraining/spec.md --strict
python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/recency-weighted-retraining/tasks.md --strict
```

Resolve the skill's installed directory if working in another environment.

## Execution Plan

Four sequential phases (5, 5, 5 and 4 tasks). Conservative ordering includes
phase-readiness gates, not only direct code dependencies. For delegation, offer
sequential batches of consecutive whole phases using the skill budget; obtain
confirmation before spawning. Never split shared F7 edits between concurrent
workers. A separate implementation worktree is recommended when Git writes are
available. The current worktree holds planning documents only.

Across stories, follow the
[parallel delivery and file-ownership plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).
This lane can run beside Stories 21 and 22 after the contract checkpoint.
Within this lane keep the task order below. T5–T6 own the F7 fitting patch;
Story 22 T9's encoder patch follows those commits under the integration owner's
lease. T12–T15 and the monograph tasks require that same single-writer lease
for shared files. This is a scheduling boundary, not a second implementation
of each task. Do not change the pinned feature contract in this experiment.

```text
T1 -> T2 -> T3 -> T4 -> T5
T5 -> T6 -> T7 -> T8 -> T9 -> T10
T10 -> T11 -> T12 -> T13 -> T14 -> T15
T15 -> T16 -> T17 -> T18 -> T19
```

T1 freezes the design/protocol before fitting. T10–T12 must demonstrate the local
coordination mechanism, not silently substitute precomputed-only replay. If
native coordination cannot satisfy the timing/state contract, stop and revise
the design before completing those tasks. T18 cannot begin without explicit
authorization to execute, complete gates and available inputs.

## Task Breakdown

### Phase 1: Protocol and weighted family fitting

### T1: Register the adaptive comparison protocol

**What**: Freeze exact source/config hashes, five policies, dates, half-life, stage spans, support minima, seed, host timeout and finite attempt budget. Record approval or rejection of every review-disposition item, including lifecycle, initial control and optional H4. Review native host coordination before enabling it; unresolved feasibility blocks replay work.

**Where**: `algo-suite/docs/stories/in-progress/19-adaptive-recency-retraining/method-design.md`
**Depends on**: None
**Requirement**: RWT-18, RWT-21, RWT-29
**Reuses**: Session-2 registration and this design.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: Document checks. Check all protocol fields, baseline identity, E/U equal support, data inventory and exploratory status. No fits or performance inspection in this task.
**Gate**: Docs from Gate Check Commands.
**Done when**:

- [x] The stated outcome and all listed acceptance cases pass the Docs gate; actual test/check counts and evidence are recorded.
- [x] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `docs(retraining): register the adaptive comparison protocol`

### T2: Build the incremental data and label-maturity adapter

**What**: Consume complete local M1 Parquet partitions and the canonical feature cache with explicit close/availability timestamps; persist per-source partition identities, cutoff-visible row watermarks and pending versus mature labels. A completed month on disk does not make its later rows historically available. Price-only scope does not require GDELT; enabling news needs separately registered event-availability and completion-marker contracts.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/ingestion.py`
**Depends on**: T1
**Requirement**: RWT-23, RWT-24
**Reuses**: build_training_rows and TrainingRow.label_time.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 10 BDD cases: ordered batches, identical retry, conflicting duplicate, missing bar, invalid UTC, late outcome, unknown label_time, partial persistence, prefix invariance and matured pending label.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): build the incremental data and label-maturity adapter`

### T3: Implement exact-UTC epoch planning

**What**: Create the monthly schedule and exact half-open stage selectors, independent of trade outcomes. Keep legacy date-based split behavior intact.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/schedule.py`
**Depends on**: T2
**Requirement**: RWT-01, RWT-02, RWT-03, RWT-09
**Reuses**: Existing walk_forward_split semantics, with an explicit new UTC contract.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit. At least 10 BDD cases: month/year/leap boundaries, initial coverage, gap/overlap, missing history, label exactly at cutoff, bucket-start versus close, and vetoed/loss observations retained.
**Gate**: Quick from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Quick gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): implement exact-utc epoch planning`

### T4: Implement exponential weights and feasibility checks

**What**: Calculate row-aligned raw/mean-one weights, n_eff and registered sample/class support checks using explicit stage cutoffs.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/weights.py`
**Depends on**: T3
**Requirement**: RWT-02, RWT-04, RWT-05, RWT-06
**Reuses**: Pure numerical module conventions.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit. At least 12 BDD cases including analytic 1/0.5/0.25 weights, 12/7/6/7/3/7 normalization, n_eff=7/3, uniform mode, invalid half-life, future age, extreme scale, zero mass and each sample-minimum boundary.
**Gate**: Quick from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Quick gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): implement exponential weights and feasibility checks`

### T5: Pass weights through family-model fitting

**What**: Extend only the family-fitting component and its call chain with optional validated weights, preserving omitted-weight behavior.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py`
**Depends on**: T4
**Requirement**: RWT-05, RWT-07, RWT-17
**Reuses**: _fit_family and existing F7 BDD fixtures.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit. At least 5 BDD cases for exact fit arguments, ordering, invalid length, real weighted-fit effect and legacy equivalence.
**Gate**: Quick from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Quick gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): pass weights through family-model fitting`

### Phase 2: Complete training and adaptive cycle

### T6: Pass independent weights through combiner fitting

**What**: Extend the logistic-combiner fitting component with separate stage weights and preserve out-of-sample stacking.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py`
**Depends on**: T5
**Requirement**: RWT-05, RWT-08, RWT-17
**Reuses**: train_meta_learner and its validation-only regression.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit. At least 6 BDD cases for stage-specific arguments, train/combiner inversion, one-class failure, future-data independence, real weighted-fit effect and omitted-weight parity.
**Gate**: Quick from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Quick gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): pass independent weights through combiner fitting`

### T7: Publish immutable epoch bundles

**What**: Wrap portable model IO with atomic bundle manifests, complete provenance, checksums and conflict-safe publication.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/bundle.py`
**Depends on**: T6
**Requirement**: RWT-11, RWT-15
**Reuses**: f7_model_io pickle-free artifacts.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 8 BDD cases: round-trip predictions, metadata completeness, identical reuse, collision, corrupt model, interrupted write, unknown schema and incompatible families.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): publish immutable epoch bundles`

### T8: Implement separate-span threshold calibration

**What**: Compute unweighted linear q10 quantiles from the reserved span; do not reuse combiner-fit predictions or time-weight threshold selection.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/thresholds.py`
**Depends on**: T7
**Requirement**: RWT-10
**Reuses**: F7 strict theta_low/theta_high semantics.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit. At least 6 BDD cases: hand-calculated quantiles, exact threshold HOLD behavior, tied thresholds, non-finite scores, insufficient rows and exclusion of later scores.
**Gate**: Quick from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Quick gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): implement separate-span threshold calibration`

### T9: Orchestrate one epoch's weighted training

**What**: Fit one policy epoch from watermark-visible mature rows, then combiner, separate thresholds and bundle; require no future test rows to train.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/trainer.py`
**Depends on**: T8
**Requirement**: RWT-01, RWT-06, RWT-09, RWT-11, RWT-24, RWT-30
**Reuses**: T2–T8 components and existing family-contract validation.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 10 BDD cases: all policies, exact row/weight provenance, insufficient support, pending labels excluded, future-tail mutation invariance, no trade-profit selection, failed fit without publication and repeated-fit equality of semantic model payload hashes. Volatile duration/wall-time metadata is preserved separately, not falsely required to be byte-identical.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): orchestrate one epoch's weighted training`

### T10: Implement the full adaptive-cycle coordinator

**What**: Implement the registered consume/mature/fit/validate/publish state machine and bounded local request/response protocol. Checkpoint successful stages; identical boundary retries must not retrain or republish.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/cycle.py`
**Depends on**: T9
**Requirement**: RWT-23, RWT-25, RWT-26, RWT-27
**Reuses**: T2 ingestion, T9 trainer and T7 atomic registry.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 10 BDD cases: complete cycle, once-per-boundary trigger, pending labels, repeated request, partial-stage recovery, watermark conflict, worker failure, timeout, failed validation and future-only activation metadata.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): implement the full adaptive-cycle coordinator`

### Phase 3: On-demand engine integration

### T11: Implement the on-demand epoch provider

**What**: Select by decision time, deserialize only the eligible bundle, pin the active model, evict inactive objects under cache capacity and switch model/threshold pair atomically.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/retraining/provider.py`
**Depends on**: T10
**Requirement**: RWT-03, RWT-12, RWT-15, RWT-26, RWT-28
**Reuses**: T7 bundles and existing prediction interface.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit. At least 10 BDD cases: exact boundary, no future load, missing epoch, corrupt bundle, family mismatch, paired switch, cache hit, bounded eviction, pinned active model and invalid capacity.
**Gate**: Quick from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Quick gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): implement the on-demand epoch provider`

### T12: Integrate adaptive cycles into continuous LEAN replay

**What**: Connect optional host-cycle requests and provider activation without rebuilding the chain's risk/position state. Prove bounded host synchronization feasibility; stop for design amendment if unavailable.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/engine/chain_algorithm.py`
**Depends on**: T11
**Requirement**: RWT-12, RWT-13, RWT-14, RWT-17, RWT-26, RWT-30
**Reuses**: Production on_data, PnlWindows and native minute_pnl_anchors fixture.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 10 native BDD scenarios: month/year boundary, open trade, same-minute protective event, risk veto, continuous equity/indicators, legacy mode, host timeout, adaptive-versus-prepared-cycle parity and identical decision payloads on a second pinned replay (excluding documented volatile telemetry only).
**Gate**: Native from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Native gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): integrate adaptive cycles into continuous lean replay`

### T13: Record current and entry model identities

**What**: Add backward-compatible epoch evidence to decisions and entry lineage, without conflating a held trade's entry model with the currently active one.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py`
**Depends on**: T12
**Requirement**: RWT-16
**Reuses**: DecisionRecorder and existing decision trail.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 5 BDD cases: no position, entry, held position crossing activation, veto before F7 and historical artifact without epoch fields.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): record current and entry model identities`

### T14: Package schedules and lifecycle metadata in runs

**What**: Stage read-only model inputs and run-scoped exchange/output directories, preserve full filter config and hashes, and publish failure manifests. Do not grant writes to archived inputs.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/run.py`
**Depends on**: T13
**Requirement**: RWT-11, RWT-15, RWT-19
**Reuses**: Existing run staging, strategy contracts and artifact manifests.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 7 BDD cases: manifest completeness, conflicting destination, read-only input scope, child failure, missing schedule, legacy run and interruption evidence.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): package schedules and lifecycle metadata in runs`

### T15: Expose adaptive preparation and replay orchestration

**What**: Expose documented bounded CLI operations for cycle preparation, dry-run schedule inspection and replay; own worker cleanup and ledger updates at the CLI boundary.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/cli.py`
**Depends on**: T14
**Requirement**: RWT-18, RWT-19, RWT-25, RWT-27
**Reuses**: Existing Typer CLI, boundary logging and T10 coordinator.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD integration. At least 8 subprocess BDD cases: help, dry run without fit, invalid protocol before IO, one-cycle request, timeout cleanup, worker failure, resume with matching identity and rejection of changed registration.
**Gate**: Host from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Host gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): expose adaptive preparation and replay orchestration`

### Phase 4: Evaluation and monograph

### T16: Report paired policy results and time diagnostics

**What**: Compare E-U daily equity with registered inference settings; publish all policies, failures, monthly/model-age diagnostics and effective filter/training settings. Show E's stage-specific effective N beside R's row counts and actual threshold values per epoch. Report E/U log-loss, Brier and directional accuracy on identical cutoff-valid rows with counts, independently of realized trades; classification metrics do not establish trading profit.

**Where**: `algo-suite/algo-analyze/src/algo_analyze/retraining_report.py`
**Depends on**: T15
**Requirement**: RWT-19, RWT-20, RWT-21, RWT-29
**Reuses**: Existing portfolio alignment, significance_report and report schemas.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: BDD unit/integration. At least 11 BDD cases: known paired returns, shifted grids, mismatched costs, flat/bankrupt equity unavailable, failed candidate, small-n refusal, exact parameters, exploratory labeling, hand-calculated Brier/log-loss, identical-row E/U comparisons and per-epoch threshold/effective-N/count preservation.
**Gate**: Analysis from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Analysis gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `feat(retraining): report paired policy results and time diagnostics`

### T17: Document the adaptive methodology in Chapter 3

**What**: Explain lifecycle, exponential observation weights, independent stage calibration, future-only activation, fixed controls and exploratory status before new runs.

**Where**: `monografia/chapters/03-methodology.tex`
**Depends on**: T16
**Requirement**: RWT-21, RWT-22
**Reuses**: Existing methodology and T1 frozen protocol.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: Document checks. Verify formula/intervals against this approved spec, distinguish planned versus delivered behavior, and build with no unresolved references.
**Gate**: Monograph from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Monograph gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `docs(retraining): document the adaptive methodology in chapter 3`

### T18: Execute and archive the registered five-policy study

**What**: After separate execution authorization and all prior gates, run the frozen matrix and archive real commands, cycle/fit durations, all attempts, artifact hashes and complete parameter/result tables.

**Where**: `algo-suite/docs/stories/in-progress/19-adaptive-recency-retraining/evidence/results.md`
**Depends on**: T17
**Requirement**: RWT-18, RWT-19, RWT-21
**Reuses**: T15 runner, T16 report and T1 protocol.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: Artifact reconciliation. Reconcile every attempt and each epoch with the registry; verify one continuous account per policy and report failed/inconclusive outcomes. This task is not run during planning.
**Gate**: Evidence from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Evidence gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `docs(retraining): execute and archive the registered five-policy study`

### T19: Write verified findings into Chapter 4

**What**: Add verified comparison tables/figures and limitations, with traceable parameters and no unsupported drift, profitability or live-readiness claim.

**Where**: `monografia/chapters/04-experimental-evaluation.tex`
**Depends on**: T18
**Requirement**: RWT-21, RWT-22
**Reuses**: T18 evidence and Chapter 3 methodology.
**Tools**: Execution Protocol tools; no workers dispatched during planning.
**Tests**: Document checks. Check every numeric claim against T18 artifacts, retain negative outcomes and exploratory labeling, and compile the monograph.
**Gate**: Monograph from Gate Check Commands.
**Done when**:

- [ ] The stated outcome and all listed acceptance cases pass the Monograph gate; actual test/check counts and evidence are recorded.
- [ ] Task/spec status and relevant public documentation are updated in the same atomic commit, with no skipped or deleted regression tests.

**Commit**: `docs(retraining): write verified findings into chapter 4`

## Task Granularity Check

Each task owns one component, fitting stage or document; its tests and minimal
wiring ship with it. Split and revalidate if implementation uncovers independent
components, rather than widening a task into an unreviewable rewrite.

| Task | Scope | Status |
| --- | --- | --- |
| T1 | One document/evidence deliverable | Atomic |
| T2 | One component or fitting stage | Atomic |
| T3 | One component or fitting stage | Atomic |
| T4 | One component or fitting stage | Atomic |
| T5 | One component or fitting stage | Atomic |
| T6 | One component or fitting stage | Atomic |
| T7 | One component or fitting stage | Atomic |
| T8 | One component or fitting stage | Atomic |
| T9 | One component or fitting stage | Atomic |
| T10 | One component or fitting stage | Atomic |
| T11 | One component or fitting stage | Atomic |
| T12 | One component or fitting stage | Atomic |
| T13 | One component or fitting stage | Atomic |
| T14 | One component or fitting stage | Atomic |
| T15 | One component or fitting stage | Atomic |
| T16 | One component or fitting stage | Atomic |
| T17 | One document/evidence deliverable | Atomic |
| T18 | One document/evidence deliverable | Atomic |
| T19 | One document/evidence deliverable | Atomic |

## Diagram-Definition Cross-Check

| Task | Depends on | Diagram predecessor | Status |
| --- | --- | --- | --- |
| T1 | None | None | Match |
| T2 | T1 | T1 | Match |
| T3 | T2 | T2 | Match |
| T4 | T3 | T3 | Match |
| T5 | T4 | T4 | Match |
| T6 | T5 | T5 | Match |
| T7 | T6 | T6 | Match |
| T8 | T7 | T7 | Match |
| T9 | T8 | T8 | Match |
| T10 | T9 | T9 | Match |
| T11 | T10 | T10 | Match |
| T12 | T11 | T11 | Match |
| T13 | T12 | T12 | Match |
| T14 | T13 | T13 | Match |
| T15 | T14 | T14 | Match |
| T16 | T15 | T15 | Match |
| T17 | T16 | T16 | Match |
| T18 | T17 | T17 | Match |
| T19 | T18 | T18 | Match |

## Test Co-location Validation

| Task | Layer | Matrix requirement | Task tests | Status |
| --- | --- | --- | --- | --- |
| T1 | Documentation | Document checks | Document checks | Included |
| T2 | Integration | BDD integration | BDD integration | Included |
| T3 | Domain | BDD unit | BDD unit | Included |
| T4 | Domain | BDD unit | BDD unit | Included |
| T5 | Domain | BDD unit | BDD unit | Included |
| T6 | Domain | BDD unit | BDD unit | Included |
| T7 | Integration | BDD integration | BDD integration | Included |
| T8 | Domain | BDD unit | BDD unit | Included |
| T9 | Integration | BDD integration | BDD integration | Included |
| T10 | Integration | BDD integration | BDD integration | Included |
| T11 | Domain | BDD unit | BDD unit | Included |
| T12 | Native | BDD integration | BDD integration | Included |
| T13 | Integration | BDD integration | BDD integration | Included |
| T14 | Integration | BDD integration | BDD integration | Included |
| T15 | Integration | BDD integration | BDD integration | Included |
| T16 | Analysis | BDD unit/integration | BDD unit/integration | Included |
| T17 | Documentation | Document checks | Document checks | Included |
| T18 | Evidence | Artifact reconciliation | Artifact reconciliation | Included |
| T19 | Documentation | Document checks | Document checks | Included |
