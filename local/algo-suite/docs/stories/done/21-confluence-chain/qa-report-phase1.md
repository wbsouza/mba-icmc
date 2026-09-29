# Story 21 — Phase 1 QA report (T1..T5)

Agent role: QA. Branch `feat/21-confluence-chain`, worktree `/tmp/mba-impl-21`.
Phase 1 baseline: `0c4d612` (hardener close-out). Executed
`qa-procedure-phase1.md` literally through pytest-bdd selections, the Python
REPL and the `algo-backtest` CLI, turned it into `qa-phase1.sh` (deterministic,
exit 0 = pass), and ran it. Script: `qa-phase1.sh`. All 30 checks passed.

## Environment note: shared worktree, concurrent phase-2 lane

A phase-2 coder (T6+, confluence time-exit lifecycle and drift-control votes)
committed twice on this same branch during this QA run (`3bbbbf8`, `b2f8442`,
both after the `0c4d612` baseline), adding files under `chain/` and
`tests/` while this script executed, and left further work untracked
(`confluence_cells.feature`, `confluence_controls.feature`,
`confluence_horizon_units.feature`, `confluence_preflight.feature`). Directory
sweeps in the procedure (Step 1's collection count, Step 13's full suite and
lint/type) initially failed only because they picked up this in-flight,
unrelated phase-2 work (one run even hit a transient `NameError` mid-edit).
Confirmed Phase 1's own modules and step files are byte-identical since
`0c4d612` (`git diff 0c4d612..HEAD` on those exact paths is empty), so this is
a shared-worktree collision, not a Phase 1 regression. `qa-phase1.sh` computes
the set of paths added under `tests/` and `chain/` since `0c4d612` (committed
or still untracked) at run time and excludes them from Steps 1a and 13, so the
script stays deterministic regardless of how far phase-2 has landed. Per the
brief, no production code was touched or fixed.

## Correction to the procedure doc's stale counts

`qa-procedure-phase1.md` records the specifier's pre-cleaner/hardener counts.
The cleaner (coverage/CRAP review) and hardener (mutation testing) stages
added scenarios afterward — per `progress.md`'s "Cleaner phase 1" and
"Hardener phase 1" entries — so several "Expected" counts in the procedure are
stale. Actual current counts (used as source of truth) and not treated as
failures:

| Selection | Doc says | Actual |
| --- | --- | --- |
| 5 confluence step files, collected | 180 | 201 (+19 cleaner, +2 hardener) |
| `test_confluence_agreement.py` | 45 | 45 (unchanged) |
| `test_confluence_momentum.py` | 38 | 43 |
| `test_confluence_history.py` | 32 | 46 (44→46 per hardener's IH-4/IH-5 boundary scenarios) |
| `test_confluence_relative_intensity.py` | 40 | 42 |
| `test_confluence_capital_plan.py` | 25 | 25 (unchanged) |
| Full offline `algo-backtest` suite | baseline 1598 + 180 = 1778 | 1799 (matches hardener's recorded close-out count) |

Also cosmetic: Steps 3/5's expected lines say `Decision.SELL` /
`Recommendation.ABSTAIN`; the enums print their bare member name (`SELL`,
`ABSTAIN`) when interpolated with `print()`, not the `Class.MEMBER` form —
values are otherwise exactly as specified.

## Step-by-step results

| Step | Component | Command(s) | Exit | Observed vs expected |
| --- | --- | --- | --- | --- |
| 1a | baseline collection | `pytest --co -m 'not integration'` | 0 | `1799/1852 tests collected (53 deselected)` — matches current suite (phase-2 WIP excluded) |
| 1b | 5 confluence step files, collected | `pytest --co` on the 5 files | 0 | `201 tests collected` (see correction table) |
| 2 | T1 pytest | `test_confluence_agreement.py` | 0 | 45 passed, 0 failed; F5/F6 veto rows and the gates-pass row present in `-v` output |
| 3 | T1 REPL | `AgreementTerminalDecision` scenarios | 0 | `SELL, HOLD, HOLD, HOLD`, then `rejected: ...'f5_risk_guard' is a gate...` and `rejected: ...required voter 'f4_news_context'...did not run...filters that ran: ['F1_trend']` — exact match |
| 4 | T2 pytest | `test_confluence_momentum.py`, `test_f1_trend.py` | 0 | 43 passed / 13 passed, both 0 failed; `f1_trend.feature` unchanged vs `main` |
| 5 | T2 REPL | `F1MomentumContextFilter` warmup/vote/reject | 0 | `ABSTAIN WARMUP momentum_context WARMUP: 480 of 481 closes collected...`; `BUY False 0.0049999...`; `rejected: ...is not after the last close` — exact match |
| 6 | T3 pytest | `test_confluence_history.py` | 0 | 46 passed (see correction table); named cases (`q10_0195_and_q90_1355`, `rows_that_arrive_after_the_snapshot_froze`, `a_gap_inside_a_documented_market_closure`, `a_collection_that_started_inside_the_window_reports_warmup`) present |
| 7 | T3 REPL | hand-checked quantiles | 0 | `READY 2016-04-01 ... 30 0.195000...0003 1.355000...0002`, agrees with `numpy.quantile` to 1e-12; `frozen: True 64`; provenance JSON present — exact match |
| 8 | T4 pytest | `test_confluence_relative_intensity.py`, `test_f4_news_context.py` | 0 | 42 passed / 49 passed, 0 failed; `f4_news_context.feature` diff is exactly the documented `unknown source` choices-list line, nothing else |
| 9 | T4 REPL | `F4NewsContextFilter` sign/boundary/veto cases | 0 | `('SELL', False) ('BUY', False) ('NEUTRAL', False)`; `('HOLD', False) ('HOLD', False)`; `('HOLD', False)`; `('ABSTAIN', True)` — exact match |
| 10 | T5 pytest | `test_confluence_capital_plan.py`, `test_f6_capital_mgmt.py` | 0 | 25 passed / 107 passed, 0 failed; `f6_capital_mgmt.feature` unchanged vs `main` |
| 11 | T5 REPL | `parse_capital_mgmt_config` legacy/timed/rejects | 0 | `legacy: None [{'at_level_ratio': 2.0, 'close_fraction': 1.0}]`; `timed: 4 () () None`; 5× `rejected: ...capital_mgmt.exit_after_bars must be a positive integer...`; `True True` — exact match |
| 12 | legacy CLI/wiring untouched | `explain-strategy news-rule`/`hybrid`, regression selection, `diff --stat` | 0 | `news-rule` shows `direction_source = "intensity"` with no new keys; `hybrid` resolves `capital_mgmt` (14 lines); regression selection 242 passed; `diff --stat` on `strategies.py`/`chain/wiring.py`/`engine/` empty |
| 13 | quality gates | ruff (+C901), mypy --strict, `make lint type`, full offline suite | 0 | ruff/mypy clean on `chain`+`tests/steps` (phase-2 WIP excluded); `make lint type`: 195/107 findings, all outside `algo-backtest` (pre-existing, BLOCKED per `progress.md`), 0 inside; full suite 1799 passed, 53 deselected, 0 failed |

## Checklist (from the procedure)

All five tasks' pass criteria (T1 agreement terminal, T2 momentum context, T3
intensity snapshots, T4 relative F4, T5 bar-count exit plan) and the
legacy/lint/type criteria are met — see the step table above for the specific
evidence per criterion.

## Blockers

None. No step required Docker/LEAN (Phase 1 has no `-m integration` scope, per
the procedure doc).

## Spec-precision gaps

None newly found beyond what the specifier/cleaner/hardener already recorded
in `progress.md` and `mutation-phase1.md`.

Script: `qa-phase1.sh` (same directory). Run log confirms `QA PHASE 1: ALL
STEPS PASSED`, exit 0.
