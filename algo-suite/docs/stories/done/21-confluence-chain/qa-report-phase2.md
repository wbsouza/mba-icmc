# Story 21 — Phase 2 (T6..T10) QA report

QA of `qa-procedure-phase2.md` against HEAD `f6c464a` (branch
`feat/21-confluence-chain`), executed through the real interfaces (pytest
selections, Python REPL, CLI scripts). Turned into a deterministic script,
`qa-phase2.sh` (exit 0 = pass); the run below is that script's actual output.
No production code was changed. Result: **PASS, 0 failures**.

The procedure doc's literal expected counts (133 collected, `47/16/14/21/35`
per task) are from before the hardener stage; the hardener added 5 net new
Gherkin scenarios closing test gaps, so the current, correct counts are 138
collected (`50/16/15/22/35`). Confirmed against `progress.md`'s "Hardener
phase 2" entry ("five Phase-2 step files now collect 138 scenarios") and by
direct `pytest --co`. The script asserts the current counts, not the stale
133.

## Per-step results

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | `pytest algo-backtest/tests -q --co -m 'not integration'` | 0 | `1937/1990 tests collected (53 deselected)` | baseline prints | PASS |
| 1 | 5-file `--co` selection | 0 | `138 tests collected` | 138 (procedure said 133, stale) | PASS |
| 2 | `test_confluence_time_exit.py -q` | 0 | 50 passed | 50/50 (procedure said 47) | PASS |
| 3 | T6 REPL | 0 | `DUE 2016-03-01 14:00:00+00:00`; one `ClosureRequest(trade_id='T1', quantity=-1000.0, at=2016-03-01T14:00:00+00:00)`; final state `DUE` | procedure says final state `PENDING` | **PASS, with a doc gap** — see Finding 1 |
| 4 | `test_confluence_controls.py -q` | 0 | 16 passed | 16/16 | PASS |
| 5 | T7 REPL | 0 | `SELL False {}`; then `rejected: direction must be 'BUY' or 'SELL', got 'HOLD'` | procedure says `Recommendation.SELL False {}` | **PASS, with a doc gap** — see Finding 2 |
| 6 | `test_confluence_horizon_units.py -q` | 0 | 15 passed | 15/15 (procedure said 14) | PASS |
| 7 | archive sha256 before/after `rederive_horizon.py` (no `--decisions`/`--source`) | 1 (script), 0 (check) | hash unchanged (`6c6544a7...5ff7f8f6`); script raised `ValueError: ... no source close data configured — pass --decisions <path> and --source <path> ...` | archive untouched; explicit BLOCKED message | PASS |
| 8 | `test_confluence_preflight.py -q` | 0 | 22 passed | 22/22 (procedure said 21) | PASS |
| 9 | T9 REPL | 0 | `720 218 502`; reconciliation assertion holds | procedure's import path/signature don't exist | **PASS, with a doc gap** — see Finding 3 |
| 10 | `test_confluence_cells.py -q` | 0 | 35 passed | 35/35 | PASS |
| 11 | `make_cells.py` manifest CLI, twice | 0 | 14 `config.yaml` files; 14 manifest rows; 14 distinct `config_hash`; re-run identical cell IDs/hashes | 14/14/14, deterministic | PASS |
| 12 | shared-file diff, Phase-2-scoped | 0 | empty diff over `0c4d612..f6c464a` | nothing prints | **PASS, with a doc gap** — see Finding 4 |
| 13 | ruff, ruff C901, mypy --strict (x2), full offline suite | 0 | ruff/mypy clean; `1937 passed, 53 deselected, 0 failed` | clean; baseline+133 (stale) | PASS |

## Findings (all in the QA procedure document, not in production code)

1. **Step 3 (T6 REPL) — "PENDING" is unreachable via the literal steps given.**
   `TimeExitLifecycle.tradable_event()` only *requests* a closure; it leaves
   the trade `DUE` (blocked from a second request only for that exact
   timestamp via `last_requested_at`). The transition to `PENDING` requires a
   separate `order_submitted(trade_id, order_id, at)` call, confirmed by
   `confluence_time_exit.feature:69` and the `PENDING` example row at line 87,
   both of which stage an explicit "close order submitted" step before
   asserting `PENDING`. The procedure's REPL script omits that call, so its
   documented final state is wrong for the sequence as written. Not a defect:
   production code matches the feature file exactly (all 50 T6 scenarios
   pass); the gap is in the procedure doc's REPL transcript.
2. **Step 5 (T7 REPL) — `Recommendation` is a `StrEnum`.** `print(result.recommendation, ...)`
   prints the bare value `SELL`, not `Recommendation.SELL`; `chain/model.py`
   defines `class Recommendation(StrEnum)`. Cosmetic doc-precision gap only.
3. **Step 9 (T9 REPL) — stale import path and signature.** The procedure's
   `from algo_backtest.experiments.confluence_chain.preflight import
   compute_population_ledger` module does not exist (raises
   `ModuleNotFoundError`); `preflight.py` is a standalone script under
   `experiments/confluence-chain/`, outside the `algo_backtest` package,
   loaded by file path — the same pattern T8 uses and exactly what
   `test_confluence_preflight.py` does. The real `compute_population_ledger`
   also takes `window_start`/`window_end` (UTC `datetime`), not `start`/`end`
   (`date`); a `date`-only January window is 31 days / 744 hours, but a
   `window_start=2016-01-01T00:00Z, window_end=2016-01-31T00:00Z` datetime
   window is 30 days / 720 hours, so the procedure's literal expected numbers
   (`744 240 504`) do not apply either. Loaded the real way with the real
   kwargs, the call returns `720 218 502` and the stated reconciliation
   invariant (`calendar_expanded_count == market_closure_count +
   expected_valid_count`) holds, which is what the step actually needs to
   prove. The procedure doc itself anticipated this ("adjust the import to
   the real path... report the discrepancy either way").
4. **Step 12 — `git diff --stat main -- <paths>` is never empty on this
   branch.** Five of the ten listed paths (`chain/terminal.py`,
   `chain/filters/f1_trend.py`, `chain/filters/f4_news_context.py`,
   `chain/filters/f6_capital_mgmt.py`, `chain/intensity_history.py`) were
   legitimately created/extended by Phase 1 (T1–T5), which sits on this same
   branch since `main`. Diffing against `main` therefore always shows those
   five files changed, regardless of what Phase 2 did. The check that matches
   the step's actual intent — did *Phase 2* touch an integration-owned or
   Phase-1 file — is scoped to the Phase 2 commit range,
   `0c4d612` (Phase 1 hardener/QA boundary) `..f6c464a` (Phase 2 hardener
   HEAD), which the script uses and which is empty, confirming the real
   invariant holds.

No SPEC_DEVIATION or code defect found. All five Phase 2 tasks (T6 time-exit
lifecycle, T7 drift-control filter, T8 horizon re-derivation, T9
population/availability preflight, T10 fourteen-cell manifest) behave as
`progress.md` and the Gherkin feature files describe.

## Blockers

None. Step 7's `ValueError` for `rederive_horizon.py` run without
`--decisions`/`--source` is the documented, expected BLOCKED behaviour (no
fixture/real Parquet available in this environment), not an unexpected
blocker.

Script: `algo-suite/docs/stories/in-progress/21-confluence-chain/qa-phase2.sh`
(exit 0 on this run).
