# Story 19 progress and handoff

Status: planned draft. Updated September 28, 2026. Planning owner: Codex.
Implementation owner: unassigned. No experiment, model fit or engine change has
been started for this story.

## Working tree and ownership

| Agent | Working tree | Branch | Scope |
| --- | --- | --- | --- |
| Codex | /home/wellington/workspace/mba-agents/mba-main | docs/13-candlestick-context-plan | Story 19 planning documents only |
| Implementation workers | Not created | Not created | Await explicit execution authorization |

Source baseline inspected: 199a4df. PRs 74–77 are now merged on remote main.
Intended publication branch: `docs/19-adaptive-recency-retraining`, from main.
Publication is blocked: local Git metadata is read-only, and the Forgejo branch
creation call requires approval unavailable under this session's policy.
No branch, commit or PR was created for Story 19. The local checkout remains on
its original branch with planning edits retained.
No new local worktree or subagent was created. Story 19 avoids the Story 18
market-context allocation. Preserve other stories and PR work.

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

## Planning verification

- Strict skill spec validator: exit 0, zero errors/warnings.
- Strict skill tasks validator: exit 0, zero errors/warnings.
- Git whitespace check and checks across eight planning/index files passed:
  40 local links resolve, all 28 requirements map to the correct task bodies,
  and all 19 implementation tasks remain unchecked.
- No runtime gate or empirical trial was run for this documentation-only story.
- Earlier dependency audit in this session was blocked by uncached TA-Lib and
  disabled network; no clean audit result is claimed and no dependency changed.

## Takeover procedure

1. Read the story entry, canonical requirements, context, design and tasks.
2. Reconcile Git and PR heads; choose an isolated implementation worktree when
   permitted. Use Story 19; Story 18 is the separate market-context plan.
3. Obtain plan approval and execution authorization. Confirm tools and proposed
   sequential whole-phase delegation before starting any worker.
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

## T0 pre-checks — 2026-09-28

- [x] Monthly refit pre-check (frozen / rolling 3 / rolling 6 / expanding): rolling 3-month refit 0.529 vs frozen 0.502 on the q10 cut bars, log-loss 0.6932 vs 0.6948; table and reading in `review.md`.
- [ ] Daily refit pre-check (15/30/45/60-day windows, thresholds-only and full refit): running; append the table to `review.md`.
- [ ] Fold the policy changes of the amendment (D60 arm, daily bundles loaded on demand, prediction-quality endpoint, calibration-month gate) into `.specs/features/recency-weighted-retraining/` before T1.
