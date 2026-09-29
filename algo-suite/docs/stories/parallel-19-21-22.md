# Parallel delivery plan: Stories 19, 21 and 22

Status: draft for approval, September 28, 2026. Planning only. No implementation,
training, market replay or live trading is authorized by this document.
The user requested parallel delivery planning and explicitly deferred Laya.

## Canonical task plans

| Lane | Scope | Canonical plan | Independent research question |
| --- | --- | --- | --- |
| A: Story 19 | Causal rolling/exponential retraining and on-demand epoch loading | [19 tasks](../../../.specs/features/recency-weighted-retraining/tasks.md) | Does recency weighting improve the same frozen-feature strategy relative to uniform expanding training? |
| B: Story 21 | Agreement terminal, momentum context, causal intensity quantiles and horizon exit | [Confluence tasks](../../../.specs/features/confluence-chain/tasks.md) | Does registered confluence improve its matched trigger-only and drift controls? |
| C: Story 22 | Expanded deterministic geometry, context, confirmation and evidence UI | [Rules-only tasks](../../../.specs/features/candlestick-context/tasks.md) | Does context add anything beyond the existing six patterns or expanded geometry alone? |

Parallel means independent components advance concurrently. It does not mean
three agents edit the same engine file, nor that all new filters enter all
experiments. Local tasks execute sequentially within each lane. The user's
cross-story parallelism changes the scheduling across lanes, not the
tlc-spec-driven per-task tests, atomic commits or independent verifier gates.

## Repository state and future worktrees

Initial checkout: `/home/wellington/workspace/mba-agents/mba-main`, `main`,
commit `6568120`. It advanced to `35a0dc9` during planning when PR 87 merged
Claude's supervised Story 21 update. The Story 21 move is now committed;
the other pre-existing story moves must be preserved, not reset or restaged
blindly. Leave unrelated 06/07 changes outside this publication.

| Agent / role | Branch | Worktree | State |
| --- | --- | --- | --- |
| Codex planning coordinator | main | /home/wellington/workspace/mba-agents/mba-main | Current checkout; shared plan and Story 19 docs only |
| Peirce planning helper | main | Same checkout | Planning complete: Story 21 companion docs only; no implementation |
| Erdos planning helper | main | Same checkout | Planning complete: Story 22 docs only; no implementation |
| Future A worker | feat/19-adaptive-retraining | /tmp/mba-impl-19 | Proposed, not created |
| Future B worker | feat/21-confluence-chain | /tmp/mba-impl-21 | Proposed, not created |
| Future C worker | feat/22-candlestick-rules | /tmp/mba-impl-22 | Proposed, not created |
| Future integration owner | feat/integrate-19-21-22 | /tmp/mba-impl-integration | Proposed, not created |

All future worktrees must start from the same approved planning commit. Check
branch/path availability before creation; never reuse or reset an old agent's
worktree. The existing `/tmp/mba-story21` belongs to earlier work and is not this
implementation lane. Each story's progress file records the actual agent ID,
branch, worktree, base SHA and task before any worker is launched.

Existing planning is already on main: Story 19 through PR 81, Story 21 through
PR 82, and Story 22's split through PR 86 (original candlestick plan in PR 76).
This amendment needs a new planning PR; do not reopen or duplicate those changes.

### Supervised Story 21 update: preservation boundary

PR 87 adds the calibration-month analysis and moves Story 21 to in-progress.
The user explicitly requires preserving Claude's work. The existing Story 21
`spec.md`, `progress.md` and `evidence/signal-horizon-check.md` remain unchanged
from main at `35a0dc9`. The new task plan lives separately in
`.specs/features/confluence-chain/` and the story's `task-plan.md` entry point.
Any different timing or evidence interpretation is a proposed clarification for
approval, not an overwrite of the supervised story or historical evidence.

## Launch checkpoint: required before implementation

1. Approve the three task plans and Story 19's [review disposition](in-progress/19-adaptive-recency-retraining/review-disposition.md).
   All unresolved source/timing/data assumptions must become frozen decisions
   or explicit exclusions, not guessed implementations.
2. Confirm tools: propose CodeGraph first, shell, apply_patch, Gherkin/Cucumber,
   tlc-spec-driven and documentation checks. Missing capabilities are blockers
   for affected gates, not permission to claim they passed.
3. Record the starting regression counts, locked dependencies, source/config
   identities and available Docker/data/resources without launching studies.
4. Assign one integration owner and a file lease for every shared path below.
   Identify schema fields, defaults, availability timestamps and compatibility
   rules in the three design docs. No default strategy changes.
5. Freeze each experiment separately before inspecting new comparative outcomes.
   The inspected 2016–2017 year remains exploratory, including November–February.

## Execution waves and joins

```text
Approved contracts and common base
  |-- A: retraining components + F7 weight support -- A provider ready --|
  |-- B: confluence rule/config components --------- B exits ready -----|--> serialized integration
  |-- C: rules/context/F3 components --------------- C evidence ready --|      and compatibility gates
                                                                               |
                                            separate registered A/B/C studies + evidence
                                                                               |
                                               single monograph editor --> final QA
```

The first parallel work is Story 19 T1–T11, Story 21's contract/terminal/context/
trigger/exit components, and Story 22 T1–T6. Stage the F7 weighting patch from
Story 19 T5–T6 first. Story 22 T9 applies its encoder patch to that validated
revision, not a stale branch. This narrow ordering does not block Story 22's
pure rule work or Story 21's terminal and trigger work.

The integration owner implements or applies each lane's shared-file task once,
with the lane's own tests/status in its atomic commit. Private-module workers
can keep moving only when their next task's dependencies are green. Do not
duplicate a shared implementation in both an integration task and a lane task.
After every integration batch, synchronize each affected lane to the reviewed
commit and rerun its gates. Never resolve a semantic conflict by taking all of
one branch's file.

## Shared-file ownership and integration order

Paths below are relative to `algo-suite/` unless prefixed `monografia/`.

| File / surface | Integration contract and owner |
| --- | --- |
| `algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py` | Single integration owner: A T5–T6 optional fitting weights first, then C T9 versioned encoder. Freeze old encoding for A's study; test omitted-weight and legacy-schema equality. |
| `algo-backtest/src/algo_backtest/chain/market_signals.py`, `training.py`, `signal_contract.py` | B momentum/ATR state and C pattern evidence must consume the same closed bars. A receives explicit availability plus a pinned feature contract. Serialize signal/training contract patches, reject mismatched hashes. |
| `algo-backtest/src/algo_backtest/engine/chain_algorithm.py` | Integrate B's time-exit/protection ordering, then A T12 model activation. C's entry veto never bypasses position management. Test their interaction before experimental runs. |
| `algo-backtest/src/algo_backtest/chain/wiring.py`, `strategies.py`, `chain/model.py`, `chain/params.py` | Shared schema/config owner registers optional features once; disabled configuration retains existing behavior; unknown/contradictory settings fail before IO. |
| `algo-backtest/src/algo_backtest/chain/decision_recorder.py` | A T13 epoch fields plus B trigger/exit evidence plus C T11 pattern evidence are additive, independently versioned and round-trip tested together. No duplicated field names with different meanings. |
| `algo-backtest/src/algo_backtest/run.py`, `cli.py` | A T14–T15 and B orchestration share packaging/CLI surfaces. Preserve historical commands; unique run roots and explicit protocol identity for each story. |
| `algo-analyze/src/algo_analyze/resultsdb/`, `algo-viewer/` | C owns pattern UI; integration owner reconciles schema migrations with A/B fields. Old datasets remain readable. A's proposed epoch chart remains deferred, not implicitly part of C. |
| `tools/perception_quality.py`, workspace Makefiles, test fixtures, dependency lock | One owner merges additions; do not lose another lane's coverage, architecture or mutation registrations. Never share mutable fixture or build output directories between parallel test jobs. |
| `monografia/chapters/03-methodology.tex`, `04-experimental-evaluation.tex`, `05-conclusion.tex` | One documentation owner incorporates approved methods and verified evidence in order; Stories 06/07 then finalize the integrated manuscript. No concurrent thesis rewrites. |

Private boundaries: A owns `retraining/` and its new test files; B owns new
confluence/exit components and its new tests; C owns new `perception/candle_*`
components, F3 policy and its new tests. Touching any shared path requires a
recorded lease even inside separate worktrees. Release it only after gate
evidence and an integration SHA exist. New shared dependencies must be identified
before widening a worker's assigned files.

## Integration acceptance gate

These are required interactions to include in the responsible lane's Gherkin
tasks, not a license to postpone that lane's unit tests until integration:

- Legacy mode, no schedule, old catalog: identical predictions, decisions and
  resolved risk/execution parameters on the frozen regression fixtures.
- Shared F7: optional weighting and versioned encoding compose without changed
  feature order or accepting an old model with a new feature contract.
- Closed-bar timing: offline/native evidence agrees at UTC day/month boundaries;
  future suffix changes never alter prior training or signal evidence.
- An open position at a month boundary and a due time exit: protective order
  handling remains first, no double close, no account/risk reset from activation.
- A required-pattern veto and agreement terminal cannot bypass F5/F6 or cancel
  protection; an all-abstaining/missing-required-vote chain never opens a trade.
- Old and new records ingest together: epoch, pattern and trigger fields remain
  distinct from final action; missing historical fields are not synthesized.
- Corrupt model, bad catalog hash or unavailable trigger history produces the
  specified error/unavailable outcome and failed-attempt evidence, not fallback.

Run the actual workspace `make check`, relevant explicitly collected host and
native BDD files, `make check-perception`, `make -C algo-analyze check-inference`
and `make viewer-check` where those surfaces changed. Commands run from
`algo-suite/`. Run `make audit` and review technical debt; blocked network or
Docker is recorded as blocked, not clean. New step selections must collect a
nonzero count. Every feature needs its own fresh independent Verifier and
isolated fault sensor; the integrated regression is an additional gate.

## Experiments: parallel resources, separate attribution

Implementing all capabilities does not enable them all in each experiment:

- A keeps the existing H1 q10 price-only filter/exit contract and compares five
  retraining policies. No new C patterns or B agreement/time exits.
- B keeps its fourteen confluence/control cells; no adaptive model or new
  candlestick-confirmation arm is silently added.
- C compares legacy geometry, expanded geometry and geometry-plus-context with
  other filters fixed. Laya, new exits and adaptive retraining are excluded.

Combined-feature fixtures test software compatibility only. A combined trading
experiment requires a new registered matrix after these controls, not a hidden
15th confluence cell or an undocumented new retraining policy.

Before launching any study, register source spans, exact effective parameters
for every filter (including disabled ones), costs, seeds, sample support, primary
contrast, feasible dependence-aware inference and attempt budget. Save protocol,
code, data, model and configuration hashes with every attempt. Preserve failed,
zero-trade and unavailable outcomes. Existing execution defects such as TD-71
remain blocking failures for affected runs, not post-hoc repaired results.

One coordinator owns a global CPU/memory/LEAN-slot semaphore. No worker assumes
six slots independently. Measure availability, set a total cap and explicit
timeouts at registration; keep unique run/build roots and immutable input mounts.
GPU acceleration is not assumed and no new model download is part of this plan.
Report resource settings and actual durations beside results.

## Handoff and publication

The requested [Claude implementation prompt](claude-implement-19-21-22.md)
hands off all three lanes with tlc-spec-driven, python-cucumber and the
uncle-bob-agent-gauntlet, actual experiment reporting, monograph updates and a
final integration PR. It is a prompt for the next executor, not a record of
implementation performed here. The python-cucumber skill was not found in this
session; Claude must locate it or obtain approval for a named fallback.

Each task commit includes its tests, spec traceability and story progress update.
Use one atomic Conventional Commit per implemented task. Record actual command,
cwd, exit status, collected/passed/failed counts, artifact paths and commit SHA.
Do not mark any task completed while it is only planned or while its gate is
blocked. After each whole-phase batch, publish a compact handoff with remaining
dependencies and the current file leases.

The user's current publication authorization covers these planning documents,
not a code rollout. Intended branch: `docs/parallel-19-21-22-plan`. Branch creation
was attempted and failed because local `.git` is read-only; Forgejo branch
creation also requires approval unavailable in this session. No new branch,
commit, push or PR is claimed. Keep source edits local for an authorized publisher.
Stage only the requested planning changes, this coordination file, the story
index and `.specs/STATE.md`. Story 21's move is already committed; preserve its
three existing files unchanged and add only its new task-plan entry. Reconcile
the pre-existing 19/22 moves explicitly (including the planned Story 22 spec
updated by PR 87); exclude the existing 06/07 moves.

Before publishing from a writable session, reconcile the remote main SHA and
review the staged name-status diff so no experiment outputs or unrelated edits
enter the planning PR. Suggested title: `docs: plan parallel stories 19, 21 and 22
without Laya`. Leave it unmerged for review. No final implementation validation
report is created during planning.

## Planning verification — September 28, 2026

The coordinator independently ran both strict tlc-spec-driven validators for
each feature: six checks, each exit 0 with zero errors and zero warnings.
The commands are recorded in the respective task plans. Additional read-only
checks confirmed:

- 19: 30 active requirements mapped bidirectionally to 19 pending task bodies.
- 21: 32 active requirements mapped bidirectionally to 22 pending task bodies.
- 22: 21 active requirements mapped bidirectionally to 19 pending task bodies;
  five historical Laya tasks remain deferred.
- Dependency references follow the declared execution order; no implementation
  checklist is marked completed. Scoped Markdown file links resolve.
- Story 21's original spec, progress and evidence match HEAD `35a0dc9` exactly,
  checked using `git diff --exit-code HEAD --` those three paths and SHA-256.
- `git diff --check` passed. Unrelated pre-existing directory moves were not
  reset, staged or published by this work.

These are documentation checks only: no software test suite, mutation campaign,
native replay, training or research experiment ran during this amendment.
