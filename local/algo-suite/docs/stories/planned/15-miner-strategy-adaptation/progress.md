# Story 15 progress and handoff

Status: planned; implementation and experiments have not started.
Created: September 28, 2026. See [spec.md](spec.md).

## Location and ownership

- Planning author: Codex; implementation owner: unassigned.
- Planning checkout: `/home/wellington/workspace/mba-agents/mba-main`.
- Observed branch/revision: `main`, `f438156`; initially clean.
- No new worktree or subagent was created for this documentation task.
- No strategy, dependency, simulation, data or monograph change is part of it.
- Before implementation, choose an isolated feature worktree/branch and record
  all agent ownership here. Preserve ongoing work and refresh live Git state.

## Preparation record

Read repository instructions, the story index, Story 14 and relevant debt.
Used CodeGraph before inspecting current filter/terminal/clock code. Confirmed
the supplied PDF is readable, 290 pages, and recorded its SHA-256 in the spec.
Reviewed the contents and printed pages 43–47 and 140–142; full source review
is still pending. The spec separates existing capabilities from proposed work.

The user's follow-up confirmed veto-filter composition: mandatory gates can
block eligibility, but passing them only arms a setup. Entry triggers and open
position protection remain separate responsibilities.

Documentation validation: `git diff --check` passed. No runtime tests were run
for this planning-only change. Attempted dependency audit with offline uv and a
temporary cache; it could not resolve the uncached TA-Lib wheel, so no clean
vulnerability result is claimed. No dependency declarations changed.

Commit/push blocker: this session mounts `.git` read-only. Creating
`docs/15-miner-strategy-adaptation` failed with a ref-lock permission error.
The story and index update remain uncommitted in the original checkout on
`main`; no branch was created or pushed. The next authorized session must
inspect the diff, create the documentation branch and commit/push these files.

## Delivery checklist

- [ ] Read the relevant book chapters/charts and complete `rule-mapping.md`.
- [ ] Independently review compatibility, ambiguity and exact first-slice scope.
- [ ] Record implementation worktree/branch and agent file ownership.
- [ ] Write Gherkin scenarios for temporal momentum, eligibility and direction.
- [ ] Implement synchronized completed-bar momentum using existing seams.
- [ ] Write and implement pending one-bar entries, cancellation and sizing.
- [ ] Verify structural stops and native order lifecycle, including OCO risk.
- [ ] Define/test causal swing structure and price-zone projections.
- [ ] Define/test time projections and their calendar conventions.
- [ ] Implement/test reviewed swing entry and management policies.
- [ ] Preserve legacy defaults and native/offline parity; pass scoped gates.
- [ ] Audit real data and previously inspected windows; freeze `method-design.md`.
- [ ] Register controls and candle/quote-activity ablations with full parameters.
- [ ] Run fresh isolated experiments; archive every success, failure and no-trade.
- [ ] Review statistical availability and report outcomes without overclaiming.
- [ ] Publish QA/takeover commands, artifacts and per-run parameter appendix.
- [ ] Update live documentation and monograph with verified source/evidence.
- [ ] Complete independent review, mutation/dependency checks and debt review.
- [ ] Commit/push delivery, reconcile story index and add lessons learned.

Check items only after the corresponding committed work and verification exist.
First implementation action: refresh repository state, review Chapter 2 against
F1/F2 and the dual-clock requirements, then propose the exact deterministic
momentum and entry subset before coding. Do not start another simulation merely
because this story now exists.
