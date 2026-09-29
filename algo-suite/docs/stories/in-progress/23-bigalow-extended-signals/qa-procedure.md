# Story 23 — QA procedure

You are a person operating the system: prove each BEXT-01..10 requirement
through real interfaces (pytest selections and direct construction of
`CandleCatalog`/`ContextEvaluator` in a Python REPL), not by reading source.
No specifier stage ran for this story (coder -> cleaner -> hardener direct),
so this procedure is written by QA from `spec.md`'s acceptance criteria and
`tasks.md`'s Done-when boxes, cwd `/tmp/mba-impl-23/algo-suite`.

## Step 1 — full regression suite (all stories, not just 23)

```
uv run pytest algo-backtest/tests -q -p no:cacheprovider
```

Expected: `1994 passed, 53 deselected` (matches `mutation-report.md`'s and
`progress.md`'s recorded final gate — any drift means something regressed
since the hardener's pass).

## Step 2 — the three Story 23 covering-test files together

```
uv run pytest algo-backtest/tests/steps/test_candle_catalog.py \
  algo-backtest/tests/steps/test_candle_contract.py \
  algo-backtest/tests/steps/test_candle_context.py -q -p no:cacheprovider
```

Expected: `321 passed` (matches `mutation-report.md`'s post-hardener count).

## Step 3 — Counterattack Line group (BEXT-01, BEXT-02, BEXT-04, BEXT-05, BEXT-06)

```
uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q \
  -p no:cacheprovider -k "counterattack or Counterattack"
```

Expected: 16 passed (geometry outline, both gap-direction negatives, WARMUP
before 2 bars, the piercing/dark-cloud-zone non-double-classification pair,
and the exact-midpoint outline).

## Step 4 — Methods Rising group (BEXT-01, BEXT-04, BEXT-05)

```
uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q \
  -p no:cacheprovider -k "Methods"
```

Expected: 8 passed — minimum 3, maximum 6, rejected at 2 (WARMUP) and 7,
the equality boundary on criterion 4, the criterion-5 negative, and
prefix-invariance.

## Step 5 — mutual exclusivity with `piercing_line`/`dark_cloud_cover` (BEXT-03)

```
uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q \
  -p no:cacheprovider -k "dark-cloud or dark_cloud or piercing or midpoint"
```

Expected: 30 passed, including the two "stays dark cloud/piercing only"
scenarios and the exact-midpoint-fires-neither outline (the hardener's C5
killing scenario).

## Step 6 — Fibonacci confluence, context evaluator (BEXT-07..10)

```
uv run pytest algo-backtest/tests/steps/test_candle_context.py -q \
  -p no:cacheprovider -k "Fibonacci"
```

Expected: 12 passed — rising leg, falling leg, tolerance boundary, tie-break
(index and nearest-level), WARMUP, the "context status WARMUP while only
Fibonacci warms" case, disabled-is-None (BEXT-10), and prefix-invariance.

## Step 7 — `FibonacciEvidence` contract validation (BEXT-08)

```
uv run pytest algo-backtest/tests/steps/test_candle_contract.py -q \
  -p no:cacheprovider -k "Fibonacci"
```

Expected: 4 passed (the K2-killing outline: level only when READY and from
the registered ratios).

## Step 8 — legacy/default-catalog-unchanged regression (BEXT-06, BEXT-10)

```
uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q \
  -p no:cacheprovider -k "Frozen or default_catalog or extended-signal or extended_signal"
```

Expected: 2 passed ("Frozen legacy equality against the existing detector on
every prefix" and "The default catalog omits the extended-signal ids even
with ample history").

## Step 9 — REPL: construct the objects directly and read the evidence

Run `uv run python`, or the equivalent block in `qa.sh`, importing
`CandleConfig`, `ContextConfig`, `ClosedBar` from `candle_contract`,
`CandleCatalog` from `candle_catalog`, `ContextEvaluator` from
`candle_context`. Bars need a UTC, hour-aligned `close_time`
(`CandleConfig`'s default `timeframe_minutes=60`).

1. **Counterattack Line firing** — bullish prior `(900, 1010, 890, 1000)`
   then `(1020, 1025, 995, 1002)` (the ledger addendum's positive example)
   with `enabled_rules=("bearish_counterattack_line",)`: expect a READY hit,
   polarity -1.
2. **Methods Rising, n=3** — the ledger addendum's positive example
   (signal `(1000,1025,995,1020)` + 3 pullbacks) with
   `enabled_rules=("methods_rising",)`: expect a READY hit, polarity 1.
3. **Methods Rising, n=2 rejected** — signal + only 2 pullback bars (3 bars
   total, below the registered lookback of 4): expect a WARMUP hit,
   polarity 0, never a false fire.
4. **Methods Rising, n=6 boundary** — signal + 6 pullback bars (7 bars
   total, the maximum window): expect a READY hit, polarity 1.
5. **Fibonacci, real levels** — 5-bar window (`fibonacci_lookback_bars=5`),
   swing low 900 at the oldest bar, swing high 1000 three bars later, final
   bar closing at 962 (within 0.10-of-range tolerance of the 38.2%
   retracement `1000 - 0.382*100 = 961.8`): expect `status="READY"`,
   `swing_high.value==1000`, `swing_low.value==900`, `level==0.382`.
6. **Fibonacci, WARMUP** — 3 bars against a 5-bar lookback: expect
   `status="WARMUP"`, `level is None`.
7. **Fibonacci, degenerate** — 5 flat bars (open=high=low=close=1000):
   expect `status="UNDEFINED"`, `level is None`, never a `ZeroDivisionError`.
8. **Legacy fields unchanged when disabled** — the same 5-bar window through
   a default `CandleConfig()` (`fibonacci_enabled=False`): expect
   `context.fibonacci is None`.

## Step 10 — code-quality gates (re-verification, not new evidence)

```
uv run ruff check algo-backtest
rm -rf .mypy_cache && uv run mypy --strict algo-backtest
make check-perception-architecture
```

Expected: all three clean/PASS, matching the hardener's recorded gates.
