# Confluence Chain Context

Gathered: 2026-09-28. Status: draft assumptions for review, planning only.
Spec: `.specs/features/confluence-chain/spec.md`.

## Feature Boundary

Story 21 delivers the existing 14 confluence cells plus their validation and data
availability gate. Stories 19 and 22 may be implemented in parallel later; their
cross-story integration plan belongs to the main agent. This document supplies
Story 21's exact handoffs and makes no changes to either neighboring story.

## User Constraints

This turn owns only the four files in this feature directory and a new Story 21
`task-plan.md`. The user-supervised Claude `spec.md`, `progress.md` and evidence
are primary source documents and remain byte-identical to merged `35a0dc9`.
This worker does not own `.specs/STATE.md`, a story index, other story plans,
code, shared schemas or manuscript files. Preserve the user's
existing directory moves. Implementation, fitting models, backtests and deployments
are outside this planning task. Only documentation validators may run here.

The user authorized committing, pushing and opening a PR for the planning docs.
The main agent owns that publication; this Story 21 worker must not publish or
spawn additional helpers. Peirce and Erdos already exist as planning helpers.
Publication is blocked: the main agent's `git switch` failed on read-only `.git`,
and Forgejo branch creation was denied by approval. No successful branch, commit,
push or PR is claimed. No implementation worktree has been created.

The current planning baseline is `main` at `35a0dc9`, following PR #87. The initial
inspection was at `6568120`; the user-supervised merge subsequently added the
outlier findings and moved Story 21. No edits restore the earlier versions.
At the initial inspection STATE still named an older branch/base; the main agent
subsequently updated it to the three-story plan. No new
project architecture decision is approved there. No confirmed lessons store was
present at the root during inspection. CodeGraph CLI was consulted first; its
broad queries included old `.worktrees/QA` entries, so source grounding uses current
`algo-suite/` files, not those indexed copies.

## Companion Qualifications of Preserved Evidence

The whole March 2016–February 2017 year was inspected, including Nov–Feb. Later
registration cannot restore untouched status. The archive computes normalized
returns divided by 1e-4; it does not compute price pips. T8 re-derives the values
from timestamp-matched prices into a new artifact and leaves the archive intact.
No numerical gain claim is carried into this companion as established fact.
The user's source summary remains unchanged.

Archive: `algo-suite/docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md`.
Historical pre-PR #87 SHA-256 at initial inspection of `6568120`:
`6a9dbe8602bda6d114ab60f2d1217178108107b35eea719d99167eeed99307d0`.

Current SHA-256 at `35a0dc9`, the preservation baseline for this plan:
`6c6544a7426b530ef1c0d682f37397fbcb3ba7d82efa4f3c184855fc5ff7f8f6`.
Commit `09abc0a` added the 45-line outlier section; `b860420` moved the story;
`35a0dc9` merged PR #87. Preserve the user's checked coverage/outlier progress
item. T9 consumes this existing analysis rather than repeats it.

The monthly table's January count 744 equals 31 calendar days times 24 hours;
it must not silently become a count of tradable completed H1 decision bars.
T9 reconciles calendar-expanded rows with the actual closed decision grid, source
coverage, warmup and missing-day exclusions before computing any quantile.
Partition sizes and `.done` markers are the reported evidence, but alone do not
prove row-level completeness, publication availability or attribution to named
geopolitical events. These qualifications leave the source report unchanged.

This companion spells out “20 days” as 480 H1 / 120 H4 completed bars. Both describe 480 scheduled
trading hours, not 20 calendar days; gaps can extend elapsed time. Four H1 bars
represent four scheduled hours; four H4 bars represent sixteen. H4 evidence is an
extrapolation and stays secondary. The archive's closing suggestion about adding
support/resistance contradicts this bounded plan and is not adopted.

## Draft Decisions

D1–D11 in this companion spec are all unapproved clarifications or alternatives
to the primary Claude contract. They cover quantile windows and sampling,
availability cutoffs, reversed trigger sign, named-vote agreement, completed-bar
expiry and precedence, analysis hierarchy, completeness/warmup, controls, audit
compatibility and reversal policy. The user authorized documenting these choices
without stopping planning for answers. No skill review checkpoint is interpreted
as requiring an interruption to this documentation-only task.

The source says to close at bar t+N's open. D5 proposes counting N fully held
completed bars after an actual fill and submitting at the next real event.
These are materially different clocks; D5/D6/D11 need explicit disposition before
T5/T6/T13 or any experiment. Documentation approval alone is not implementation
approval. If a proposal is rejected, revise affected criteria/tests before coding.

The proposed architecture extends the existing terminal/F1/F4/F6 contracts. A
standalone strategy engine would duplicate risk and execution behavior. A plugin
registry abstraction would increase scope without helping these 14 cells. Neither
alternative is selected; the extension proposal still needs implementation review.

## Availability Gap

`GdeltFeature` currently exposes `timestamp` and `event_intensity`, and
`NewsContextIndex` stores timestamp/value dictionaries. Neither proves when a daily
aggregate became knowable. T9 must validate source publication/availability
provenance or a separately approved conservative lag before relative calibration
can run. A minute-grid timestamp is not availability evidence. No data roots,
coverage, source release times or Docker readiness were verified by running jobs
in this turn. An unavailable input stops future runs, not document planning.

## Parallel Handoff Boundary

The proposed Story 21 worker owns terminal/F1/F4/F6 extensions and new Story 21
helper/script/test files only after the main agent assigns exclusive path leases.
If another worker needs any of these files, hand the patch contract to integration
instead of editing concurrently. Tests ship with each behavior task; shared
fixtures also require an integration lease. No plan assumes that separate branches
make simultaneous edits to shared code safe.

Integration consumes T11–T15 and T20–T22. It owns strategy registration/provenance,
chain wiring, native event ordering, recorder and schema compatibility, tool docs
and Chapters 4/5. The handoff table in `design.md` supplies exact paths and tests.
No Story 19 model result or Story 22 pattern/location result becomes a prerequisite
or input to a Story 21 cell.

The main agent's [parallel coordinator](../../../algo-suite/docs/stories/parallel-19-21-22.md)
owns global scheduling and publication. This lane records 22 stable task IDs in
four bounded phases; it creates no worktree and dispatches no additional helper.

## Deferred Ideas

Candlestick and support/resistance experiments remain outside these 14 cells.
Adaptive model integration remains outside Story 21. A fresh confirmatory period
requires a separate future protocol. No additional indicator or research author
is introduced by this plan.
