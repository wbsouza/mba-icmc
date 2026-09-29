# Story 19 — Phase 1 QA report (T1..T5)

QA agent, worktree `/tmp/mba-impl-19`, Phase 1 boundary commit `2d6a63c`
(`test(retraining): harden phase 1 modules against surviving mutants`).
Executed `qa-procedure-phase1.md` literally through pytest selections, the
Python REPL and files on disk, then encoded it as the deterministic
[`qa-phase1.sh`](qa-phase1.sh) (exit 0 = pass). Two full runs: the first
surfaced three script bugs (below), all fixed; the second run is clean.

**Result: `qa-phase1.sh` exits 0. All 13 steps PASS.**

## Corrections to the QA procedure (source of truth = progress.md, per
## team-lead direction)

1. **Step 2 (ingestion pytest) count.** The procedure expects `20 passed`.
   Actual, both at T2 completion and now: `25 passed` — `progress.md` records
   the T2 gate as `22 passed` (18 scenarios + 4 Examples), then the hardener
   pass added 3 new scenarios for surviving mutants ING-1/2/5, giving 25.
   `progress.md` is the correct source; the procedure text predates both the
   original T2 commit and the hardener pass.
2. **Step 7 (weights analytic fixture) dates.** The procedure's REPL snippet
   uses rows at `2015-12-31` and `2015-11-01` against cutoff `2016-03-01`,
   expecting raw weights `[1.0, 0.5, 0.25]`. 2016 is a leap year, so those
   instants are 61/121 elapsed days before the cutoff, not 60/120 — running
   them verbatim gives `[1.0, 0.494257..., 0.247128...]`, not the expected
   table. `progress.md`'s T4 log documents this exact leap-year correction
   (rows moved to `2016-01-01` / `2015-11-02`). Re-running with the corrected
   dates reproduces the expected table exactly (`RAW [1.0, 0.5, 0.25]`, `NORM`
   sum `3.0`, `NEFF 2.333...`). `qa-phase1.sh` uses the corrected dates.
3. **Step 8 (family-weights pytest) count.** The procedure expects
   `13 passed`. Actual: `14 passed` — the hardener added one scenario for
   survivor F7-3. Same pattern as (1).
4. **Step 1 NDA checklist item, as literally written.** "Grep the file for
   any product/codename the repo forbids; only 'the EJB version', 'the Spring
   version', 'the reference strategy' are allowed" reads as a presence check,
   but it's an absence check: `method-design.md` never needs to discuss the
   two earlier systems at all, and in fact doesn't use any of the three
   euphemisms (it only discusses this repo's own session-2 baseline). No
   forbidden name appears (manually reviewed — the actual forbidden strings
   are NDA-redacted from this agent's own memory by design, so they can't be
   grepped for). Treated as compliant; the script doesn't assert presence of
   the euphemisms, only that the doc doesn't need them.

None of these are Phase 1 regressions.

## Worktree contamination note (not a Phase 1 failure)

This worktree is shared: `code-19-p2` (Phase 2, T6 "combiner weights") was
actively editing `algo_backtest/chain/filters/f7_meta_learner.py` and
committed `d1958b0` partway through this QA run, moving HEAD past the
Phase 1 boundary `2d6a63c`. Effects observed and how they were handled:

- Steps 8/9 (T5, `train_meta_learner`) were re-run against the live file both
  mid-edit and after the T6 commit; results were identical and correct in
  both cases (`family_weights` handling is untouched and backward-compatible
  with the new `combiner_weights` kwarg). No Phase 1 defect.
- Step 10's tree-wide `pytest --co` picked up Phase 2's untracked feature
  files (`retraining_bundle.feature`, `retraining_cycle.feature`,
  `retraining_thresholds.feature`, `retraining_trainer.feature`,
  `f7_combiner_weights.feature`), inflating collection to `1746/1799`
  (vs. the hardener's documented `1727` at Phase 1 close). All 1746 collected
  tests pass; the extra collected tests are Phase 2 in-progress work, not a
  Phase 1 count regression.
- Steps 11/12 originally diffed `ef0111d..HEAD`; once HEAD moved to `d1958b0`
  this falsely flagged Phase 2's own new feature file as an "other feature
  changed" and made `git status --short` non-empty. Fixed by pinning both
  checks to the actual Phase 1 boundary `PHASE1_SHA=2d6a63c` instead of
  `HEAD`. Re-verified directly: `git diff --name-only ef0111d..2d6a63c --
  algo-backtest/tests/features` touches only `f7_family_weights.feature`,
  `retraining_ingestion.feature`, `retraining_schedule.feature`,
  `retraining_weights.feature` (all expected); the nine shared-file paths
  Step 12 guards (`engine/`, `wiring.py`, `strategies.py`,
  `decision_recorder.py`, `run.py`, `cli.py`, `training.py`,
  `market_signals.py`, both `conftest.py`, the `Makefile`) show zero diff
  between `ef0111d` and `2d6a63c`.
- `make lint type` fails tree-wide (195 ruff errors, ~107 mypy errors) but
  every offending file matches `progress.md`'s Phase 1 closure list exactly
  (`docs/stories/done/20-session-2-clean-rerun/scripts/*.py`,
  `scripts/bigquery_*.py`, `algo-viewer/tests/fixtures/build_fixture.py`,
  `docs/stories/done/13-pattern-volume-experiments/evidence/
  render_intermediate_figures.py`, `tools/mutation_harness.py`) —
  pre-existing at `ef0111d`, none under `retraining/` or the F7 diff.
  `ruff check` / `ruff format --check` / `mypy --strict` scoped to the five
  Phase 1 paths all pass clean.

## Step-by-step result

| Step | What | Result |
| --- | --- | --- |
| 0 | Phase 1 surface (exports + `train_meta_learner` signature) | PASS |
| 1 | T1 doc checklist (`method-design.md`, validators, traceability) | PASS |
| 2 | T2 ingestion pytest | PASS — 25 passed (see correction 1) |
| 3 | T2 ledger by hand (8-part fixture: consume/idempotency/conflict/reopen) | PASS |
| 4 | T3 schedule pytest + F7 baseline | PASS — 41 passed; F7 unchanged (61, and 86 for the trio) |
| 5 | T3 temporal contract by hand (12 epochs, F/Q/R/U/E spans, 2 rejections) | PASS |
| 6 | T4 weights pytest | PASS — 49 passed |
| 7 | T4 analytic fixture by hand | PASS — with leap-year-corrected dates (correction 2) |
| 8 | T5 family-weights pytest + F7 suite | PASS — 14 passed (correction 3); trio 86 passed (baseline) |
| 9 | T5 legacy parity / weighting effect by hand | PASS — legacy/none/ones bit-identical 0.5; extreme weights >0.99 / <0.01; length-mismatch rejection names 39/40 |
| 10 | Quality gates, no lost tests | PASS — scoped ruff/format/mypy clean; tree-wide `make lint type` failures confined to pre-existing out-of-lane files; full suite 1746 passed, 53 deselected, 0 failed |
| 11 | Bookkeeping in commits | PASS — T1..T5 ticked, traceability rows read `Implemented (Tn)`; pinned to boundary `2d6a63c` (see contamination note) |
| 12 | What must NOT have changed | PASS — zero diff on the 10 shared-file paths and the non-Phase-1 feature files between `ef0111d` and `2d6a63c` |

No BLOCKED steps; nothing in Phase 1 needed Docker/LEAN.

## Artifacts

- Script: `qa-phase1.sh` (this directory), exit 0.
- Full run log (second, clean run) captured interactively; key evidence
  reproduced above. Ledger fixture used `$TMPDIR/qa19-ledger` (ephemeral).

Commit: `docs(retraining): qa report phase 1`.
