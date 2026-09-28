# Story 19 progress and handoff

Status: planned draft. Updated September 28, 2026. Planning owner: Codex.
Implementation owner: unassigned. No experiment, model fit or engine change has
been started for this story.

## Working tree and ownership

| Agent | Working tree | Branch | Scope |
| --- | --- | --- | --- |
| Codex | /home/wellington/workspace/mba-agents/mba-main | main at 35a0dc9 | Story 19 and parallel coordination documents only |
| Implementation workers | Not created | Not created | Await explicit execution authorization |

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
convention; update both in the same tested task commit. All remain pending.

- [ ] T1: Register the adaptive comparison protocol.
- [ ] T2: Build the incremental data and label-maturity adapter.
- [ ] T3: Implement exact-UTC epoch planning.
- [ ] T4: Implement exponential weights and feasibility checks.
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
