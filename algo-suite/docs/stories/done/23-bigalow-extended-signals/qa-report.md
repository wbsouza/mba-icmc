# Story 23 — QA report

QA pass, 2026-09-28, worktree `/tmp/mba-impl-23`, branch
`feat/23-bigalow-extended-signals` (HEAD `d071149` at QA start). Executed
`qa.sh` (deterministic, `exit 0` = pass) implementing every step of
`qa-procedure.md`, itself written by QA from `spec.md`'s BEXT-01..10
acceptance criteria and `tasks.md`'s Done-when boxes (no specifier stage
ran for this story). Full log:
`docs/stories/in-progress/23-bigalow-extended-signals/qa.sh`'s stdout,
reproduced per step below. Cross-checked against `mutation-report.md`'s and
`progress.md`'s recorded final counts (1994 passed/53 deselected full
suite, 321 covering-test scenarios) — both matched exactly, no drift since
the hardener's pass.

| # | Step | Command (abbrev.) | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Full regression suite | `pytest algo-backtest/tests -q` | 0 | `1994 passed, 53 deselected` | same | PASS |
| 2 | 3 covering-test files together | `pytest .../test_candle_{catalog,contract,context}.py -q` | 0 | `321 passed` | same | PASS |
| 3 | Counterattack Line group (BEXT-01,02,04,05,06) | `-k "counterattack or Counterattack"` | 0 | `16 passed` | same | PASS |
| 4 | Methods Rising group (BEXT-01,04,05) | `-k "Methods"` | 0 | `8 passed` | same | PASS |
| 5 | Mutual exclusivity w/ piercing_line/dark_cloud_cover (BEXT-03) | `-k "dark-cloud or dark_cloud or piercing or midpoint"` | 0 | `30 passed` | same | PASS |
| 6 | Fibonacci confluence, context (BEXT-07..10) | `-k "Fibonacci"` on `test_candle_context.py` | 0 | `12 passed` | same | PASS |
| 7 | `FibonacciEvidence` contract validation (BEXT-08) | `-k "Fibonacci"` on `test_candle_contract.py` | 0 | `4 passed` | same | PASS |
| 8 | Legacy/default-catalog-unchanged regression (BEXT-06,10) | `-k "Frozen or default_catalog or extended-signal..."` | 0 | `2 passed` | same | PASS |
| 9 | REPL: direct `CandleCatalog`/`ContextEvaluator` construction (8 assertions) | inline `uv run python` | 0 | `REPL_OK`, all 8 asserts held | same | PASS |
| 10 | Code-quality gates | `ruff check`, `mypy --strict`, `make check-perception-architecture` | 0 | all clean/PASS | same | PASS |

## Step 9 detail (real interfaces, real numbers, no fixture reuse)

1. **Counterattack Line fires**: bullish prior `(900,1010,890,1000)` then
   `(1020,1025,995,1002)` — `bearish_counterattack_line` READY, polarity -1.
2. **Methods Rising n=3 fires**: signal `(1000,1025,995,1020)` + 3
   pullbacks (`1005`/`1003`/`1025` closes) — READY, polarity 1.
3. **Methods Rising n=2 rejected**: signal + 2 pullback bars (3 bars total,
   below the lookback of 4) — WARMUP, polarity 0, never a false fire.
4. **Methods Rising n=6 boundary**: signal + 6 pullback bars (7 total, the
   maximum window) — READY, polarity 1.
5. **Fibonacci real levels**: 5-bar window, swing low `900`, swing high
   `1000`, close `962` — computed 38.2% level `961.8`
   (`1000 - 0.382*100`), within the 0.10-of-range tolerance (`3` on a
   `30`-range bar) — `status=READY`, `level=0.382`.
6. **Fibonacci WARMUP**: 3 bars against a 5-bar lookback — `status=WARMUP`,
   `level=None`.
7. **Fibonacci degenerate**: 5 flat bars (`1000` OHLC) — `status=UNDEFINED`,
   `level=None`, no `ZeroDivisionError`.
8. **Legacy-unchanged**: the same 5-bar window through a default
   `CandleConfig()` (`fibonacci_enabled=False`) — `context.fibonacci is
   None`.

## Blockers

None. No Docker/LEAN (`-m integration`) step was required by this story's
scope (pure perception-layer modules, no integration marks).

## Outcome

All 10 steps PASS. No production code was touched or needs fixing; no real
failure found. Story 23's BEXT-01..10 acceptance criteria are demonstrated
through real interfaces, matching `spec.md`'s traceability table
(`Implemented`) and the hardener's final gate counts.
