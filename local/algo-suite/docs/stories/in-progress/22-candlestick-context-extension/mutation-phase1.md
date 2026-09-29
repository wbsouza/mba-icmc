# Story 22, Phase 1 — mutation testing report

Hardener pass over Phase 1's new/modified production modules. Manual behaviour-level
mutation testing (no `mutmut` in the workspace): one mutation applied in place at a
time to `/tmp/mba-impl-22`, the full covering test set run, then the module restored
from a backup and `git status --porcelain` reconfirmed to match the pre-mutation
baseline before the next mutation. Baseline HEAD: `33d466c`.

Scope: `perception/candle_contract.py`, `candle_catalog.py`, `candle_context.py`,
`candle_sequence.py`, and the mode-handling hunks added to
`chain/filters/f3_pattern.py` by `git diff ef0111d..HEAD` (dispatch, `_mode`,
`_candidate_ids`, `_candidates`, `_context_warming`, `_satisfied`, `_evaluate`,
`_apply_evidence`).

Covering tests (run together for every mutation, so a mutation in one module that a
neighbouring module's scenarios happen to catch is still recorded as killed):
`test_candle_contract.py`, `test_candle_catalog.py`, `test_candle_context.py`,
`test_candle_sequence.py`, `test_f3_policy_modes.py`, `test_candlestick_detector.py`,
`test_f3_pattern.py` — 51 mutations, run with
`uv run pytest <the 7 files> -q -p no:cacheprovider -x`.

**Result: 50/51 KILLED, 1 equivalent mutant (CC12), 0 TIMEOUT, 0 ERROR.**

The cleaner flagged four specific coverage gaps as likely survivors:
`candle_contract.py`'s `__post_init__` invariant guards and `CandleHistory.config`
(96%), `candle_context.py`'s `ContextEvaluator.history` getter (99%), and
`candle_sequence.py`'s `ScheduledClosure`/`CalendarPolicy` guards (94%). All of
these were targeted directly (CC2, CC3, CC14, CX10, CS1, CS2, CS3), and two of
them (CC14, CX10) genuinely survived the first pass and needed a new scenario.
Coverage after hardening: `candle_catalog.py` 100%, `candle_context.py` 100%
(was 99%), `candle_sequence.py` 98% (was 97% — the CS2 scenario now exercises the
`end <= start` raise; the two still-uncovered lines, 65 and 84, are the raise
statements inside `ScheduledClosure`'s and `CalendarPolicy`'s type/UTC-awareness
guards — no scenario constructs an actually-invalid `datetime` or a non-
`ScheduledClosure` closure, but CS1 and CS3 already proved both guard conditions
are live and fault-detecting by inverting them and watching every valid-usage
scenario fail), `candle_contract.py` 98% (was 97%).

## Mutation table

| id | file | line(s) | operator | original → mutated | result |
|----|------|---------|----------|---------------------|--------|
| CC1 | candle_contract.py | `_integer` | `<`→`<=` | `value < minimum` → `value <= minimum` | KILLED |
| CC2 | candle_contract.py | `SequenceConfig.__post_init__` | guard inverted (coverage gap) | `if not isinstance(...)` → `if isinstance(...)` | KILLED |
| CC3 | candle_contract.py | `CandleConfig.__post_init__` | guard inverted (coverage gap) | `if not isinstance(ctx,...) or not isinstance(seq,...)` → both `not` dropped | KILLED |
| CC4 | candle_contract.py | `_validate_zones` | boundary `<=`→`<` | `overbought <= oversold` → `overbought < oversold` | KILLED |
| CC5 | candle_contract.py | `_validated_sma_periods` | boundary `>`→`>=` | `max(validated) > MAX_HISTORY` → `>= MAX_HISTORY` | KILLED (after hardening; see below) |
| CC6 | candle_contract.py | `CandleConfig.__post_init__` | boundary `<`→`<=` | `max_history < required` → `<= required` | KILLED |
| CC7 | candle_contract.py | `PatternHit.__post_init__` | branch swapped | `if status == READY else 0` → `if status == WARMUP else 0` | KILLED |
| CC8 | candle_contract.py | `IndicatorValue.__post_init__` | `!=`→`==` | `ready != finite` → `ready == finite` | KILLED |
| CC9 | candle_contract.py | `LevelEvidence.__post_init__` | `!=`→`==` | `(sma READY) != (distance set)` → `==` | KILLED |
| CC10 | candle_contract.py | `SequenceEvidence.__post_init__` | `or`→`and` | contradiction check `or`→`and` | KILLED (after hardening; see below) |
| CC11 | candle_contract.py | `_validated_hits` | `==`→`!=` | duplicate check `current == previous` → `!=` | KILLED |
| CC12 | candle_contract.py | `_validated_hits` | boundary `<`→`<=` | `current < previous` → `current <= previous` | **SURVIVED — equivalent mutant** |
| CC13 | candle_contract.py | `_validate_status` | `and`→`or` | `status == READY and warming` → `or` | KILLED |
| CC14 | candle_contract.py | `CandleHistory.config` | accessor gutted (coverage gap) | `return self._config` → `return None` | KILLED (after hardening; see below) |
| CC15 | candle_contract.py | `CandleHistory.offer` | off-by-one | `... // self._period - 1` → `... // self._period` | KILLED |
| CG1 | candle_catalog.py | `_doji` | boundary `<=`→`<` | `body <= 0.10*range` → `body < 0.10*range` | KILLED |
| CG2 | candle_catalog.py | `_doji_long_legged` | boundary `>=`→`>` | `min(upper,lower) >= 0.30*range` → `>` | KILLED |
| CG3 | candle_catalog.py | `_doji_dragonfly` | boundary `<=`→`<` | `upper <= 0.10*range` → `<` | KILLED |
| CG4 | candle_catalog.py | `_spinning_top` | boundary `<=`→`<` | `body <= 0.30*range` → `body < 0.30*range` | KILLED |
| CG6 | candle_catalog.py | `_bullish_kicker` | boundary `>=`→`>` | `open >= prior.open` → `>` | KILLED |
| CG7 | candle_catalog.py | `_hanging_man` | boundary `>`→`>=` | `net(3) > 0` → `>= 0` | KILLED |
| CG8 | candle_catalog.py | `evaluate_catalog` | off-by-one | readiness `len(bars) >= lookback` → `>` | KILLED |
| CG9 | candle_catalog.py | `legacy_scores` | branch swap | bullish/bearish engulfing `max`/`min` swapped | KILLED |
| CX1 | candle_context.py | `ema_value` | boundary `<`→`<=` | warmup `len(closes) < period` → `<=` | KILLED |
| CX2 | candle_context.py | `_raw_k` | boundary `<`→`<=` | warmup `end+1 < period` → `<=` | KILLED |
| CX3 | candle_context.py | `_raw_k` | `==`→`!=` | zero-range check inverted | KILLED |
| CX4 | candle_context.py | `_smoothed` | boundary `<`→`<=` | warmup `len(values) < length` → `<=` | KILLED |
| CX5 | candle_context.py | `_zone` | boundary `>`→`>=` | OVERBOUGHT `d > 80` → `>= 80` | KILLED |
| CX6 | candle_context.py | `_zone` | boundary `<`→`<=` | OVERSOLD `d < 20` → `<= 20` | KILLED |
| CX7 | candle_context.py | `level_evidence` | boundary `<`→`<=` | warmup `len(closes) < period` → `<=` | KILLED |
| CX8 | candle_context.py | `_t_line_position` | boundary `>`→`>=` | ABOVE `close > ema` → `>=` | KILLED |
| CX9 | candle_context.py | `evaluate_context` | ternary branches swapped | `WARMUP if ... else READY` → swapped | KILLED |
| CX10 | candle_context.py | `ContextEvaluator.history` | accessor gutted (coverage gap) | `return self._history` → `return None` | KILLED (after hardening; see below) |
| CS1 | candle_sequence.py | `ScheduledClosure.__post_init__` | guard inverted (coverage gap) | UTC-aware check `!=`→`==` | KILLED |
| CS2 | candle_sequence.py | `ScheduledClosure.__post_init__` | boundary `<=`→`<` (coverage gap) | `end <= start` → `end < start` | KILLED (after hardening; see below) |
| CS3 | candle_sequence.py | `CalendarPolicy.__post_init__` | guard inverted (coverage gap) | `not isinstance(...)` → `isinstance(...)` | KILLED |
| CS4 | candle_sequence.py | `_is_doji` | `==`→`!=` | status check inverted | KILLED |
| CS5 | candle_sequence.py | `_confirmation_direction` | inclusive edge `<=`→`<` | bullish `open <= low` → `open < low` | KILLED |
| CS6 | candle_sequence.py | `_confirmation_direction` | inclusive edge `<=`→`<` | bearish `close <= low` → `close < low` | KILLED |
| CS7 | candle_sequence.py | `_aligned_strictly_after` | off-by-one | `(periods+1)*period` → `periods*period` | KILLED |
| CS8 | candle_sequence.py | `_expected_next_close` | boundary `<`→`<=` | closure window `continuous < end` → `<= end` | KILLED (after hardening; see below) |
| CS9 | candle_sequence.py | `_resolve` | `!=`→`==` | missing-bar check inverted | KILLED |
| CS10 | candle_sequence.py | `SequenceEvaluator.update` | `==`→`!=` | confirmed-resolution branch inverted | KILLED |
| FP1 | f3_pattern.py | `F3PatternFilter.apply` | `==`→`!=` | mode dispatch inverted | KILLED |
| FP2 | f3_pattern.py | `_mode` | guard inverted | `not in _MODES` → `in _MODES` | KILLED |
| FP3 | f3_pattern.py | `_candidate_ids` | `and`→`or` | READY/non-neutral filter loosened | KILLED |
| FP4 | f3_pattern.py | `_context_warming` | `or`→`and` | none-or-warmup check narrowed | KILLED |
| FP5 | f3_pattern.py | `_satisfied` | branch inverted | bullish zone-exclusion inverted | KILLED |
| FP6 | f3_pattern.py | `_satisfied` | wrong constant | bearish branch reused `"ABOVE"` for `"BELOW"` | KILLED |
| FP7 | f3_pattern.py | `_evaluate` | boundary `>`→`>=` | conflicting-candidates `> 1` → `>= 1` | KILLED |
| FP8 | f3_pattern.py | `_apply_evidence` | branch swapped (CND-12 critical) | `veto = mode == "required_entry"` → `== "advisory"` | KILLED |

Negative control: **CC1** (a plainly-covered boundary exercised by the existing
"one short of ..." Scenario Outline rows) was confirmed KILLED before running the
rest of the catalog, proving the harness detects faults.

## Survivors killed

Six mutations survived the first pass; all six are now killed by new Gherkin
scenarios (feature first, then steps), and re-running each mutation against the
hardened suite confirms KILLED:

- **CC5** (`sma_periods` at the `MAX_HISTORY` upper bound) — added the
  `sma_period exactly at the 256 bound` row to the existing max_history Scenario
  Outline in `candle_contract.feature` (`max_history 256`, `sma_periods "256"`,
  accepts).
- **CC10** (`SequenceEvidence` partial contradiction) — added the
  "Sequence evidence confirmation fields agree with its state" Rule to
  `candle_contract.feature` with a construction-validation Scenario Outline
  covering both partial-contradiction cases (confirmed missing direction/time)
  and both stray-field cases (idle with a direction or time set), plus new
  `given`/`when`/`then` steps in `test_candle_contract.py`.
- **CC14** (`CandleHistory.config` accessor) — added
  "And the candle history's config has max_history 12" to the existing
  "History is bounded by max_history..." scenario, plus a new step asserting
  `history.config.max_history`.
- **CX10** (`ContextEvaluator.history` accessor) — added "The context evaluator
  exposes its bound history" to `candle_context.feature`, plus a new
  `when`/`then` pair in `test_candle_context.py` that keeps the evaluator instance
  and asserts `evaluator.history.history_count`.
- **CS2** (`ScheduledClosure` equal start/end) — added the
  "A scheduled closure's bounds are validated eagerly" Rule to
  `candle_sequence.feature` with a construction-validation scenario, plus a new
  `when`/`then` pair in `test_candle_sequence.py`.
- **CS8** (closure-window boundary at exactly `closure.end`) — added
  "A next expected close exactly at the closure end is not treated as inside the
  closure" to `candle_sequence.feature`, reusing existing steps with a doji
  timed so its continuous next close lands exactly on `closure.end`; proves the
  half-open `[start, end)` interval is respected at its right edge.

## Equivalent mutant

- **CC12** — `_validated_hits` first raises on `current == previous` (the
  duplicate-id branch) before ever reaching the ascending-order check on the same
  pair; by the time the order check runs, `current != previous` is already an
  established precondition. Widening that check from `current < previous` to
  `current <= previous` therefore never changes behaviour on any input: no test
  can distinguish original from mutant because control flow never reaches the
  differing branch with an equal pair. No new scenario added.

## Restoration and cleanliness

Every mutation was applied to a single module, backed up first, and restored
immediately after its test run (or after a timeout/error) before the next
mutation started. `git -C /tmp/mba-impl-22 status --porcelain` was captured before
mutation 1 and re-checked after every restore and after the full 51-mutation pass
(and again after the six re-runs against the hardened suite): identical each time,
matching the phase-2-specifier baseline of untracked feature files this lane does
not own. No `.mutbak` files were left behind.
