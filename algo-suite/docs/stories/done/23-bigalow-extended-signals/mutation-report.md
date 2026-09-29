# Story 23 — mutation testing report

Hardener pass, 2026-09-28. Manual behaviour-level mutation testing (no `mutmut`
in the workspace) over the three Story 23 production modules, one mutation at
a time in place, restored after each run (`git checkout -- <file>`), verified
against a clean `git status --porcelain` baseline before and after. Covering
tests: `test_candle_catalog.py`, `test_candle_contract.py`,
`test_candle_context.py` (`-q -p no:cacheprovider -x`), 312 scenarios before
this pass, 321 after.

Note on process: the first pass through all 24 mutations used a runner script
with a path bug (`cd`'d into `algo-suite` while still prefixing test paths
with `algo-suite/`), so every pytest invocation failed with "no tests ran"
and every mutation was misreported KILLED. This was caught before writing
this report by inspecting the raw pytest logs, the script was fixed, and
every mutation below was re-run and its log re-verified to contain a genuine
pass/fail (not a collection error).

## candle_catalog.py (9 mutations)

| id | file:line | operator | original -> mutated | result |
| --- | --- | --- | --- | --- |
| C1 | candle_catalog.py:90 | `<=`->`<` | `_doji`: `body <= DOJI_BODY_RATIO * range` -> `<` | KILLED |
| C2 | candle_catalog.py:96 | `>=`->`>` | `_doji_long_legged`: `min(upper,lower) >= LONG_LEG_RATIO*range` -> `>` | KILLED |
| C3 | candle_catalog.py:146 | `+`->`-` | `_body_midpoint`: `(open+close)/2` -> `(open-close)/2` | KILLED |
| C4 | candle_catalog.py:212-220 | removed guard | `_bearish_counterattack_line`: removed `current.close > _body_midpoint(prior)` (the dark-cloud-cover mutual-exclusivity guard) | KILLED |
| C5 | candle_catalog.py:229 | `<`->`<=` | `_bullish_counterattack_line`: `close < mid(prior)` -> `<=` (piercing-line guard) | **SURVIVED** -> killed by new scenario |
| C6 | candle_catalog.py:237 | off-by-one | `_methods_rising`: `range(MIN, MAX+1)` -> `range(MIN-1, MAX+1)` (tries n=2) | **SURVIVED** -> killed by new scenario |
| C7 | candle_catalog.py:237 | off-by-one | `_methods_rising`: `range(MIN, MAX+1)` -> `range(MIN, MAX+2)` (tries n=7) | KILLED |
| C8 | candle_catalog.py:245 | `>=`->`>` | `_methods_rising` tail floor: `close >= signal.open` -> `>` | KILLED |
| C9 | candle_catalog.py:176 | `>=`->`>` (negative control) | `_bullish_kicker`: `open >= prior.open` -> `>` | KILLED |

## candle_context.py (8 mutations)

| id | file:line | operator | original -> mutated | result |
| --- | --- | --- | --- | --- |
| X1 | candle_context.py:129 | `>=`->`>` | `_swing` tie-break: `high_index >= low_index` -> `>` | **SURVIVED** -> killed by new scenario |
| X2 | candle_context.py:141 | `<=`->`<` | `_nearest_level` tolerance: `distance <= tolerance` -> `<` | KILLED |
| X3 | candle_context.py:141 | `<`->`<=` | `_nearest_level` best-distance tie-break: `distance < best_distance` -> `<=` | **SURVIVED** -> killed by new scenario |
| X4 | candle_context.py:162 | `==`->`!=` | `fibonacci_evidence` zero-range guard: `if high == low` -> `!=` | KILLED |
| X5 | candle_context.py:41 | wrong constant | `FIB_TOLERANCE_RATIO`: `0.10` -> `0.05` | KILLED |
| X6 | candle_context.py:46 | `<`->`<=` | `ema_value` warmup boundary: `len(closes) < period` -> `<=` | KILLED |
| X7 | candle_context.py:103 | `<`->`<=` | `level_evidence` warmup boundary: `len(closes) < period` -> `<=` | KILLED |
| X8 | candle_context.py:113 | `>`->`>=` | `_t_line_position` ABOVE boundary: `close > ema.value` -> `>=` | KILLED |

## candle_contract.py (7 mutations)

| id | file:line | operator | original -> mutated | result |
| --- | --- | --- | --- | --- |
| K1 | candle_contract.py:72-92 | frozen literal -> derived | `DEFAULT_ENABLED_RULES` tuple literal -> `tuple(sorted(rule for rule in CATALOG if rule not in {three new ids}))` | SURVIVED — **equivalent mutant**, see below |
| K2 | candle_contract.py:447-453 | removed validation raise | `FibonacciEvidence._validate_level`: guard replaced with `if False and (...)` | **SURVIVED** -> killed by new scenario |
| K3 | candle_contract.py:97 | `<`->`<=` | `_integer` minimum boundary: `value < minimum` -> `<=` | KILLED |
| K4 | candle_contract.py:346 | `==`->`!=` | `PatternHit.__post_init__`: `expected = ... if status == READY else 0` -> `!= READY` | KILLED |
| K5 | candle_contract.py:295 | `<=`->`<` | `CandleConfig._validate_max_history` upper bound: `value <= MAX_HISTORY` -> `<` | KILLED |
| K6 | candle_contract.py:181 | `<=`->`<` | `ContextConfig._validate_zones`: `overbought <= oversold` -> `<` (equal zones wrongly accepted) | KILLED |
| K7 | candle_contract.py:605 | removed check | `_aligned_utc_close_time`: dropped `minute_of_day % timeframe_minutes` from the rejection condition | KILLED |

## Totals

- 24 mutations: 22 genuinely KILLED on first try, 5 initially SURVIVED
  (C5, C6, X1, X3, K2), 1 equivalent mutant (K1).
- One negative control (C9), confirmed KILLED, proving the harness detects
  faults.
- Every SURVIVED mutant now has a killing Gherkin scenario; re-running each
  of the five against the updated feature/step files confirms KILLED
  (verified individually, restoring the source mutation and leaving the new
  scenarios in place each time).

## Equivalent mutant: K1

`DEFAULT_ENABLED_RULES` mutated from a frozen tuple literal to a computed
`tuple(sorted(rule for rule in CATALOG if rule not in {the three Story 23 ids}))`.
For the *current* contents of `CATALOG`, this produces the exact same 19-id
tuple in the exact same order as the literal — every value-level assertion
(`assert_enabled_rules`, `assert_defaults`, BEXT-06's byte-identical
regression) passes identically under both versions, because the two
definitions are extensionally equal today. No Gherkin scenario operating at
the public-API/evidence level can distinguish "frozen literal" from
"currently-equal derivation" without inspecting the source definition
itself, which is outside what BDD scenarios describe.

This is not a false negative in the harness — it is a structural fragility
the brief anticipated ("if not that's a gap"): a *future* rule id added to
`CATALOG` without updating the exclusion set would silently and invisibly
change `DEFAULT_ENABLED_RULES` under the derived form, breaking BEXT-06
(byte-identical Story 22 defaults) at that future point, not now. The
cleaner's 2026-09-28 review already reached the same conclusion by inspection
("Reviewed, not changed: ... this is intentional ... a derived exclusion-set
would silently re-admit any new rule by default"). No behavioural test can
enforce "stay a literal, not a derivation" — that is a code-review/structural
concern, not a mutation-testable one. Recommend keeping this noted in both
the cleaner's review and here rather than adding an ineffective scenario.

## New killing scenarios added

- `candle_catalog.feature`: "A close exactly at the piercing/dark-cloud
  midpoint fires neither pattern" (outline, 2 cases) — kills C5, and closes
  the symmetric equality-boundary gap on `_bearish_counterattack_line` that
  C5's sibling mutation would also have exposed.
- `candle_catalog.feature`: "Methods Rising never considers fewer than three
  pullback bars even with ample history" — kills C6 (the WARMUP-gated
  "only two pullback bars" scenario never actually exercises the internal
  loop's minimum, since the rule's registered lookback is 4 and gates the
  call to `_methods_rising` entirely at 3 bars; this scenario uses 5 bars so
  the function runs and a spurious n=2 window is reachable).
- `candle_context.feature`: "Fibonacci tie-break resolves to the high when
  the swing extremes share a bar" — kills X1 (constructs a window where one
  bar carries both the max high and the min low, a genuine index tie).
- `candle_context.feature`: "Fibonacci nearest-level tie keeps the
  first-checked ratio" — kills X3 (close exactly equidistant between the
  38.2% and 50% levels).
- `candle_contract.feature`: new Rule "Fibonacci evidence carries a level
  only when READY and from the registered ratios" with a
  `FibonacciEvidence` validation outline (4 cases) — kills K2, and adds
  direct-construction coverage for `FibonacciEvidence.__post_init__` that
  was previously untested at the contract level (the cleaner's 2026-09-28
  review already flagged `candle_contract.py`'s 94% coverage as concentrated
  in exactly these untested defensive guards).

## Final gates (worktree `/tmp/mba-impl-23`, branch `feat/23-bigalow-extended-signals`)

| Gate | Command | Result |
| --- | --- | --- |
| Covering tests | `uv run pytest algo-backtest/tests/steps/test_candle_catalog.py algo-backtest/tests/steps/test_candle_contract.py algo-backtest/tests/steps/test_candle_context.py -q -p no:cacheprovider` | 321 passed (was 312) |
| Full suite | `uv run pytest algo-backtest/tests -q -p no:cacheprovider` | 1994 passed, 53 deselected |
| Lint | `uv run ruff check algo-backtest` | All checks passed |
| Types | `uv run mypy --strict algo-backtest` (after `rm -rf .mypy_cache`) | Success: no issues found in 67 source files |
| Architecture | `make check-perception-architecture` | PASS |

No production code was changed; only the three `.feature` files and
`test_candle_contract.py` (new steps for the `FibonacciEvidence` scenario).
