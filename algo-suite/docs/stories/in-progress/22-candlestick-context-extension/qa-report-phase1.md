# Story 22 — Phase 1 (T1–T6) QA report

QA executed `qa-procedure-phase1.md` literally through the real interfaces (pytest
selections, Python REPL, docs gates) in `/tmp/mba-impl-22`, branch
`feat/22-candlestick-rules`, HEAD `ebac509`. Turned into `qa-phase1.sh` (exit 0 =
PASS), which was then run to produce this report. Expected counts use
`progress.md`'s actual final numbers where the hardener added scenarios after
`qa-procedure-phase1.md` was written (T2 112→119, T4 52→53, T5 20→22; T3 and T6
unchanged). Full run log: `/home/wellington/.cache/claude-tmp/qa-phase1-run2.log`.

**Result: PASS. 0 failures, 0 blockers.**

## 0. Baseline

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 0.1 | commit trail check (T1 ledger `05bbdad` + T2–T6 `071d1d0..ef6450e`) | 0 | all present, trailers valid (`Claude Fable 5.1` or `Claude Sonnet 5`) | commits present with valid trailers | PASS — the doc's exact "-8 window" is stale: 3 extra docs/cleaner/hardener commits (`d20f152`, `33d466c`, `ebac509`) landed after T6 |
| 0.2 | `pytest test_candlestick_detector.py test_f3_pattern.py -q` | 0 | 110 passed | 110 passed, unchanged | PASS |
| 0.3 | `git diff main...HEAD --stat` on legacy detector/feature files | 0 | empty | empty | PASS |

## 1. T1 — source-rule ledger

| Check | Observed | Result |
| --- | --- | --- |
| Source checksums (`sha256sum` on all 4 reachable paths) | book, both presentation copies, transcript all match the ledger's recorded SHA-256 | PASS |
| All 19 admitted rules have ledger rows | all present | PASS |
| Deferred list (J-hook, fry-pan, dumpling, cradle, scoop, belt-hold) | present | PASS |
| Preserved ambiguities (23:38, 48:36, 26:26) | present | PASS |
| NDA (no earlier-system name) | clean | PASS |
| `git diff --check` | clean | PASS |
| `validate_spec.py --strict` | 0 errors, 0 warnings | PASS |
| `validate_tasks.py --strict` | 0 errors, 0 warnings | PASS |

Not independently re-derived by script (prose-quality items, reviewed by reading
the ledger directly during QA): exact formula wording, confirmation-rule text, the
hanging-man OCR dispute note, and the "no speaker performance claims" check — all
read correct by inspection; no automatable signal distinguishes them from prose.

## 2. T2 — contract

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 2.1 | `pytest test_candle_contract.py -q` | 0 | 119 passed | >=100 (progress.md final: 119, hardener added 6) | PASS |
| 2.2 | REPL defaults | — | `1 256 legacy 19` | same | PASS |
| 2.3 | `max_history=257` | — | `ValueError` naming `max_history`, 256 | same | PASS |
| 2.4 | `max_history=199` | — | `ValueError` naming the 200-bar bound | same | PASS |
| 2.5 | mutate frozen field | — | `FrozenInstanceError` | same | PASS |
| 2.6 | `low > high` bar via `CandleHistory.offer` | — | `ValueError` ("ordering"/"repair"); count unchanged then accepts next | same | PASS |
| 2.7 | duplicate `close_time` | — | `ValueError` ("duplicate"); count unchanged | same | PASS |
| 2.8 | misaligned `close_time` | — | `ValueError` ("aligned"); count unchanged | same | PASS |
| 2.9 | `ruff check` + `mypy --strict` on `candle_contract.py` | 0 | clean | exit 0 | PASS |

## 3. T3 — catalog

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 3.1 | `pytest test_candle_catalog.py -q` | 0 | 106 passed | >=100 (106, unchanged by hardener) | PASS |
| 3.2 | single bar `(1000,1050,950,1000)` | — | WARMUP; doji + doji_long_legged READY polarity 0; rest WARMUP; ids sorted | same | PASS |
| 3.3 | 20 context bars, dip, recovery | — | `bullish_harami(+1), doji(0), doji_long_legged(0)` all READY, status READY | same | PASS |
| 3.4 | amended hammer/hanging-man fixture | — | `doji, doji_dragonfly, hammer(+1), hanging_man(-1)` READY; `legacy_label == "hammer"` | same (T3's amended fixture) | PASS |
| 3.5 | legacy-corpora prefix equality | — | exercised by `test_candle_catalog.py`'s own scenarios, counted in 3.1 | covered | PASS |
| 3.6 | `grep candle_ tools/perception_quality.py` | — | `candle_contract`/`candle_catalog` registered, no `chain`/`engine` import allowed | same | PASS |
| 3.7 | `perception_quality.py --help` | 0 | runs | exit 0 | PASS |
| 3.8 | coverage `candle_catalog.py` | 0 | 100% | 100% | PASS |

## 4. T4 — context

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 4.1 | `pytest test_candle_context.py -q` | 0 | 53 passed | >=50 (53, hardener +1) | PASS |
| 4.2 | closes 1..10 | — | EMA None x7 then 4.5, 5.5, 6.5; `t_line_position` ABOVE from bar 8 | same | PASS |
| 4.3 | 12 flat bars then 18,12,19.5,13.5 | — | bar12: raw 50, slow WARMUP; bar16: raw 35, slow 50, %D 55, NEUTRAL | same | PASS |
| 4.4 | 16 flat identical bars | — | zone UNDEFINED, values None, no NaN | same | PASS |
| 4.5 | 100 closes at 8 then 100 at 12; 199-bar case | — | distances 20→0.0, 50→0.0, 200→0.2; at 199 bars, level 200 WARMUP and context status WARMUP | same | PASS |
| 4.6 | `ContextConfig(ema_period=0)` | — | `ValueError` naming `ema_period` | same | PASS |
| 4.7 | `ruff check --select C901` | 0 | clean | exit 0 | PASS |

## 5. T5 — sequence

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 5.1 | `pytest test_candle_sequence.py -q` | 0 | 22 passed | 20 collected per doc; progress.md final 22 (hardener +2) | PASS |
| 5.2 | 3-bar confirming sequence | — | IDLE, CANDIDATE, CONFIRMED; direction 1; confirmation 03:00; candidate close 02:00 | same | PASS |
| 5.3 | missing 03:00 bar, continuous policy | — | EXPIRED, `missing_expected_bar` | same | PASS |
| 5.4 | doji then doji | — | bar3 CANDIDATE, `not_engulfing`, candidate_close_time = bar3 close | same | PASS |
| 5.5 | invalid bar after candidate | — | `ValueError`; next valid bar confirms at its own close | same | PASS |

## 6. T6 — F3 policy modes

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 6.1 | `pytest test_f3_policy_modes.py test_f3_pattern.py -q` | 0 | 73 passed | 73 (15 legacy unchanged) | PASS |
| 6.2 | `parse_pattern_config({}, strategy="qa").mode` | — | `"legacy"` | same | PASS |
| 6.3 | invalid mode `"required"` | — | `ValueError` "pattern.mode must be one of legacy, advisory, required_entry" | same | PASS |
| 6.4 | legacy mode, evidence present | — | `BUY`, veto False, reason mentions "hammer"; evidence ignored | same | PASS |
| 6.5 | advisory, conflicting hits | — | `ABSTAIN`, veto False, reason starts "conflicting" | same | PASS |
| 6.6 | required_entry, same evidence | — | `ABSTAIN`, veto True, reason "conflicting"; enrichment has hit ids/mode/reason | same | PASS |
| 6.7 | required_entry, `bullish_engulfing(+1)` READY | — | `BUY`, veto False | same | PASS |
| 6.8 | required_entry, missing `candle_evidence` | — | `ValueError` naming `candle_evidence` and `required_entry` | same | PASS |
| 6.9 | `grep candle_evidence f3_pattern.py` | — | documented in module docstring | same | PASS |

## 7. Phase gate

| Step | Command | Exit | Observed | Expected | Result |
| --- | --- | --- | --- | --- | --- |
| 7.1 | `ruff check` + `mypy --strict` (algo-backtest, tools) | 0 | clean | exit 0 | PASS |
| 7.2 | `pytest algo-backtest/tests -q` | 0 | 1951 passed, 53 deselected | matches hardener's final baseline | PASS |
| 7.3 | `make check-perception-architecture check-inference-architecture` | 0 | both PASS | exit 0 | PASS |
| 7.3b | `make check-perception` (Docker/LEAN, attempted once) | 2 | native/host-coverage line 283 passed; 3 `-m integration` suites 9/8/7 passed; merged-coverage CRAP step fails | native/LEAN lines PASS; CRAP step fails only because `Makefile`'s `check-perception:` target still hardcodes a pre-Story-22 step-file list (never extended to `test_candle_*.py`/`test_f3_policy_modes.py`) | PASS (documented pre-existing gap, not a Story 22 regression — matches progress.md's T6 entry verbatim; not BLOCKED, image was cached and ran) |
| 7.4 | `progress.md` checklist | — | T1–T6 all `[x]` | same | PASS |
| 7.5 | `tasks.md` / `spec.md` | — | both Done-when boxes ticked for T1–T6 (6/6 x2); CND-01–09,11,12 → `Implemented (Tn)`; traceability line still 21 active requirements | same | PASS |
| 7.6 | `git status --short` | — | clean except phase-2 specifier's 10 untracked files (explicitly out of scope, untouched) | clean | PASS |

## Blockers

None. The Docker/LEAN image was cached and ran to completion; no Docker/network
BLOCKED condition was hit.

## Files

- `algo-suite/docs/stories/in-progress/22-candlestick-context-extension/qa-phase1.sh`
- `algo-suite/docs/stories/in-progress/22-candlestick-context-extension/qa-report-phase1.md` (this file)
