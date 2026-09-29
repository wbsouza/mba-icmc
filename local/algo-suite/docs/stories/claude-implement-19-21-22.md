# Claude implementation handoff — Stories 19, 21 and 22

Copy the prompt below into Claude Code. This document is an execution handoff,
not evidence that implementation, tests, experiments or publication have occurred.

---

Take ownership of implementing Stories 19, 21 and 22 in
`/home/wellington/workspace/mba-agents/mba-main`. Follow their task plans, run the
registered experiments when their gates are met, update the monograph with actual
results, commit and push the changes, and open one integration PR against `main`.
Do not merge it or deploy to a live account. Laya is excluded.

## 1. Establish the handoff before editing

Read `AGENTS.md`, `algo-suite/CLAUDE.md`, `.specs/STATE.md`, and
`algo-suite/docs/stories/parallel-19-21-22.md`. Read each story's spec, design,
context, tasks and progress:

| Story | Story directory under `algo-suite/docs/stories/in-progress/` | Canonical plan under `.specs/features/` |
| --- | --- | --- |
| 19 | `19-adaptive-recency-retraining/` | `recency-weighted-retraining/` |
| 21 | `21-confluence-chain/` (including `task-plan.md`) | `confluence-chain/` |
| 22 | `22-candlestick-context-extension/` | `candlestick-context/` |

Read Story 19's `review.md` and `review-disposition.md`. Story 21's supervised
Claude spec, progress and evidence at merged PR #87 (`35a0dc9`) were preserved;
the new task plan is a companion, not an approved replacement. Resolve its D1–D11
proposals with me before dependent implementation, particularly exit timing,
reversal/hold policy and data availability. Resolve Story 19's open dispositions
and other material draft assumptions too. Ask a compact batch of questions;
continue independent approved work while an affected task is blocked. Do not
treat this execution request as approval of every proposed default.

Inspect actual Git HEAD, status, remotes, worktrees, running jobs and existing
PRs before writing. The planning handoff was left on `main` with uncommitted
documentation because Codex could not write `.git` or create a Forgejo branch.
Do not assume it has been published. Preserve all existing work; explicitly
reconcile the Story 19/22 directory moves and the planned Story 22 spec changed
by PR #87. Exclude unrelated Story 06/07 moves from the planning commit. Do not
reset, stash away, overwrite, or indiscriminately stage another agent's changes.
If Git/network permissions still block publication, report the blocker; do not
bypass it. Otherwise make a scoped planning commit on a new branch before
creating implementation worktrees from that common reviewed commit.

## 2. Required skills and parallel ownership

Load and fully read **tlc-spec-driven**, **python-cucumber**, and
**uncle-bob-agent-gauntlet**, plus the applicable references, before affected work.
Codex found the gauntlet at
`/home/wellington/.agents/skills/uncle-bob-agent-gauntlet/SKILL.md`, but could not
locate `python-cucumber`; locate it in your installed skill catalog. If a required
skill is unavailable, report its exact name and ask for its location or approval
of a specific fallback. Do not claim it was applied or install an arbitrary
replacement. User instructions, repository rules and approved contracts prevail
where generic skill advice conflicts, including this repository's Gherkin-first
test convention. Use CodeGraph first where indexed.

Use three implementation lanes/subagents in separate worktrees, with the branch
and path assignments proposed in the shared plan after checking availability.
One coordinator owns integration. Execute tasks in dependency order within each
lane; parallelize independent lanes, not edits to shared files. Story 19's F7
weight support precedes Story 22's encoder change. Serialize engine, wiring,
config, recorder/schema, shared test fixtures and manuscript changes using the
documented file leases. Story 21 executes T15 before T14 and T20 before T19.
Do not integrate branches by taking one agent's entire version of a shared file.

For each bounded feature batch, run fresh, separate gauntlet stages:
specifier → coder → cleaner → hardener → QA. Reuse the approved plans; the
specifier supplies executable Gherkin criteria and a human-oriented QA procedure,
not a replacement architecture. Tests ship with each task. Cleaner enforces the
repository's complexity/coverage/CRAP and dependency gates. Hardener records the
mutation scope and operators, kills surviving non-equivalent mutants, and
independently justifies any equivalent exclusions. Keep timeouts/errors distinct
from kills and include a negative control proving the harness detects faults.
QA executes the procedure through real supported interfaces, including native
LEAN scenarios where required. Run tlc-spec-driven's fresh independent final
Verifier and isolated fault sensor as well. Never mutate the working source or
historical experiment artifacts to run fault tests.

## 3. Implementation and verification contract

Retain legacy defaults and behavior when new capabilities are disabled. Prove
causal closed-bar processing, label maturity, future-data exclusion, model/feature
identity, monthly rollover and open-position continuity. Prove stop-versus-expiry
ordering, no duplicate closure, veto precedence and old/new artifact compatibility.
Assert the exact error/unavailable outcome for invalid-input cases; do not accept
either outcome indiscriminately. Preserve Claude's original Story 21 evidence;
put unit corrections, re-derivations and population/availability checks in new
artifacts with provenance, never rewrite the historical evidence as if it always
contained the correction.

Run the actual gates in each task plan and the shared integration plan, including
nonzero explicit BDD collections, Ruff, strict mypy, applicable architecture and
CRAP/coverage checks, mutation testing, CLI/system QA, native LEAN integration,
inference and viewer checks when affected, dependency audit and thesis verification.
Discover actual commands from the checkout; do not invent commands or reuse old
pass counts. A skipped test, no-tests-collected exit, missing data or unavailable
Docker/network is not a pass. Do not weaken thresholds or suppress failures to
finish. Necessary dependencies may be added through the owning project manifest
and lockfile, with a reason and verification.

## 4. Experiments and monograph

Freeze each study's approved protocol, parameters, source/data/model hashes,
seeds, dates, costs, attempt budget and feasible statistical settings before
viewing new comparative results. Keep the three research questions separate:

- Story 19: five retraining policies with the original frozen feature/filter
  contract; no new confluence exits or extended candle rules.
- Story 21: fourteen registered confluence/control cells; no adaptive model or
  extra candlestick arm. Verify point-in-time news availability before launch.
- Story 22: legacy geometry, expanded geometry, and geometry-plus-context;
  deterministic rules only, no Laya. Keep other filters fixed.

Combined-feature fixtures prove compatibility; a combined trading study needs a
separate protocol and approval. Do not add a hidden arm or select settings after
seeing outcomes. Already-inspected dates remain exploratory. Report failed,
zero-trade, unavailable and negative outcomes alongside successes.

For **every backtest**, show its run ID and complete resolved filter parameters
beside its results, including disabled filters, clock, threshold/window settings,
training/calibration spans, model identity, stop/target/trail/hold settings, risk
caps, execution costs and resource limits. Include parameter provenance and
commands so another agent can reproduce the run. Use immutable inputs and unique
output directories. A single coordinator caps total CPU, RAM and LEAN jobs across
all agents; measure resources first and do not assume GPU acceleration applies.

Assign one monograph editor. Document the registered methodology before the
corresponding runs, then update Chapter 4 with verified intermediate and final
results and Chapter 5 with qualified conclusions. Include source artifact/run
identities, parameter tables, uncertainty, limitations and unfavorable outcomes.
Build and verify the manuscript; do not fabricate pending results or infer live
readiness from backtests. Preserve unrelated work on Stories 06/07.

## 5. Progress, commits and PR

Update each story's `progress.md` and the shared coordinator handoff after every
tested task: what changed and why, agent ID/role, branch/worktree/base SHA, current
task and file leases, exact commands/cwd/exit status/counts, artifacts, blockers
and next steps. Update the existing Story 21 progress additively once executing;
retain Claude's completed work and historical entries. Do not mark planned work
as implemented or tests as passed without recorded execution.

Commit scoped, tested changes frequently using atomic Conventional Commits and
push the branches. Consolidate through the integration owner and rerun gates on
the exact integrated commit. Open the final integration PR through Forgejo MCP,
linking all three stories, experiment evidence and monograph changes. Include a
gate table with commands and actual results, all blockers, mutation survivors or
exclusions, behavior/schema changes and remaining risks. If a genuine external
blocker prevents completion, open a clearly labeled draft PR with partial status
instead of claiming readiness. Leave the PR unmerged and provide its URL, branch,
commit, worktrees and remaining work.

No method can guarantee absence of hidden bugs. The required outcome is
auditable behavioral and independent fault-detection evidence, not a claim of
bug-free software or guaranteed trading profit.
