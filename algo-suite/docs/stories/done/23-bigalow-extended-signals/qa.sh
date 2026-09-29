#!/usr/bin/env bash
# Story 23 QA script. Deterministic: exit 0 = every step passed as expected
# in qa-procedure.md. Run from algo-suite/ (the script cd's there itself).
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." || exit 1

FAIL=0
step() {
  local name="$1"; shift
  echo "--- $name ---"
}

check_output() {
  local name="$1" expected="$2" shift_cmd="$3"
  local out
  out=$(eval "$shift_cmd" 2>&1)
  local status=$?
  if [ $status -ne 0 ]; then
    echo "FAIL ($name): command exited $status"
    echo "$out" | tail -20
    FAIL=1
    return
  fi
  if ! echo "$out" | grep -qF "$expected"; then
    echo "FAIL ($name): expected to find '$expected' in output"
    echo "$out" | tail -20
    FAIL=1
    return
  fi
  echo "PASS ($name): found '$expected'"
}

step "1: full regression suite"
check_output "full-suite" "1994 passed, 53 deselected" \
  "uv run pytest algo-backtest/tests -q -p no:cacheprovider"

step "2: three Story 23 covering-test files together"
check_output "covering-tests" "321 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_catalog.py algo-backtest/tests/steps/test_candle_contract.py algo-backtest/tests/steps/test_candle_context.py -q -p no:cacheprovider"

step "3: Counterattack Line group (BEXT-01,02,04,05,06)"
check_output "counterattack" "16 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q -p no:cacheprovider -k 'counterattack or Counterattack'"

step "4: Methods Rising group (BEXT-01,04,05)"
check_output "methods-rising" "8 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q -p no:cacheprovider -k 'Methods'"

step "5: mutual exclusivity with piercing_line/dark_cloud_cover (BEXT-03)"
check_output "mutual-exclusivity" "30 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q -p no:cacheprovider -k 'dark-cloud or dark_cloud or piercing or midpoint'"

step "6: Fibonacci confluence, context evaluator (BEXT-07..10)"
check_output "fibonacci-context" "12 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_context.py -q -p no:cacheprovider -k 'Fibonacci'"

step "7: FibonacciEvidence contract validation (BEXT-08)"
check_output "fibonacci-contract" "4 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_contract.py -q -p no:cacheprovider -k 'Fibonacci'"

step "8: legacy/default-catalog-unchanged regression (BEXT-06,10)"
check_output "legacy-unchanged" "2 passed" \
  "uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q -p no:cacheprovider -k 'Frozen or default_catalog or extended-signal or extended_signal'"

step "9: REPL construction of CandleCatalog/ContextEvaluator (BEXT-01,04,07,08,09,10)"
uv run python - <<'PYEOF'
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from algo_backtest.perception.candle_contract import (
    CandleConfig, ContextConfig, ClosedBar, READY, WARMUP, UNDEFINED,
)
from algo_backtest.perception.candle_catalog import CandleCatalog
from algo_backtest.perception.candle_context import ContextEvaluator


def hourly(n):
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    return [t0 + timedelta(hours=i) for i in range(n)]


def bar(t, o, h, l, c):
    return ClosedBar(close_time=t, open=o, high=h, low=l, close=c)


# 1: Counterattack Line firing (ledger addendum positive example)
cfg = CandleConfig(enabled_rules=("bearish_counterattack_line",))
cat = CandleCatalog(cfg, "EURUSD")
ts = hourly(2)
cat.update(bar(ts[0], 900, 1010, 890, 1000))
ev = cat.update(bar(ts[1], 1020, 1025, 995, 1002))
assert any(h.id == "bearish_counterattack_line" and h.status == READY and h.polarity == -1
           for h in ev.hits), "Counterattack Line did not fire as expected"

# 2: Methods Rising n=3 (ledger addendum positive example)
cfg = CandleConfig(enabled_rules=("methods_rising",))
cat = CandleCatalog(cfg, "EURUSD")
ts = hourly(4)
bars = [bar(ts[0], 1000, 1025, 995, 1020), bar(ts[1], 1015, 1018, 1002, 1005),
        bar(ts[2], 1008, 1010, 1000, 1003), bar(ts[3], 1010, 1030, 1005, 1025)]
for b in bars[:-1]:
    cat.update(b)
ev = cat.update(bars[-1])
assert any(h.id == "methods_rising" and h.status == READY and h.polarity == 1
           for h in ev.hits), "Methods Rising n=3 did not fire"

# 3: Methods Rising n=2 rejected -> WARMUP
cfg = CandleConfig(enabled_rules=("methods_rising",))
cat = CandleCatalog(cfg, "EURUSD")
ts = hourly(3)
bars2 = [bar(ts[0], 1000, 1025, 995, 1020), bar(ts[1], 1015, 1018, 1002, 1005),
         bar(ts[2], 1008, 1010, 1000, 1010)]
for b in bars2[:-1]:
    cat.update(b)
ev = cat.update(bars2[-1])
assert any(h.id == "methods_rising" and h.status == WARMUP and h.polarity == 0
           for h in ev.hits), "Methods Rising n=2 unexpectedly fired or was not WARMUP"

# 4: Methods Rising n=6 boundary
cfg = CandleConfig(enabled_rules=("methods_rising",))
cat = CandleCatalog(cfg, "EURUSD")
ts = hourly(7)
bars6 = [bar(ts[0], 1000, 1025, 995, 1020), bar(ts[1], 1015, 1018, 1002, 1010),
         bar(ts[2], 1008, 1010, 1000, 1005), bar(ts[3], 1006, 1012, 1000, 1008),
         bar(ts[4], 1007, 1015, 1000, 1009), bar(ts[5], 1008, 1013, 1000, 1006),
         bar(ts[6], 1010, 1030, 1005, 1025)]
for b in bars6[:-1]:
    cat.update(b)
ev = cat.update(bars6[-1])
assert any(h.id == "methods_rising" and h.status == READY and h.polarity == 1
           for h in ev.hits), "Methods Rising n=6 did not fire"

# 5: Fibonacci real levels (38.2% retracement within tolerance)
cfg = CandleConfig(context=ContextConfig(fibonacci_enabled=True, fibonacci_lookback_bars=5))
ctx = ContextEvaluator(cfg)
ts = hourly(5)
bars_fib = [bar(ts[0], 950, 960, 900, 950), bar(ts[1], 950, 970, 940, 960),
            bar(ts[2], 960, 980, 950, 970), bar(ts[3], 970, 1000, 960, 990),
            bar(ts[4], 985, 990, 960, 962)]
for b in bars_fib[:-1]:
    ctx.update(b)
ev = ctx.update(bars_fib[-1])
assert ev.fibonacci.status == READY
assert ev.fibonacci.swing_high.value == 1000
assert ev.fibonacci.swing_low.value == 900
assert ev.fibonacci.level == 0.382, f"expected 0.382, got {ev.fibonacci.level}"

# 6: Fibonacci WARMUP before lookback
cfg = CandleConfig(context=ContextConfig(fibonacci_enabled=True, fibonacci_lookback_bars=5))
ctx = ContextEvaluator(cfg)
ts = hourly(3)
for b in [bar(ts[0], 950, 960, 940, 955), bar(ts[1], 955, 965, 945, 960),
          bar(ts[2], 960, 970, 950, 965)]:
    ev = ctx.update(b)
assert ev.fibonacci.status == WARMUP
assert ev.fibonacci.level is None

# 7: Fibonacci degenerate zero-range swing
cfg = CandleConfig(context=ContextConfig(fibonacci_enabled=True, fibonacci_lookback_bars=5))
ctx = ContextEvaluator(cfg)
ts = hourly(5)
for b in [bar(t, 1000, 1000, 1000, 1000) for t in ts]:
    ev = ctx.update(b)
assert ev.fibonacci.status == UNDEFINED
assert ev.fibonacci.level is None

# 8: legacy fields unchanged when Fibonacci disabled
cfg_off = CandleConfig()
ctx_off = ContextEvaluator(cfg_off)
ev_off = None
for b in bars_fib:
    ev_off = ctx_off.update(b)
assert ev_off.fibonacci is None

print("REPL_OK")
PYEOF
if [ $? -eq 0 ]; then
  echo "PASS (repl-construction): all 8 assertions held"
else
  echo "FAIL (repl-construction): see traceback above"
  FAIL=1
fi

step "10: code-quality gates"
check_output "ruff" "All checks passed" "uv run ruff check algo-backtest"
rm -rf algo-suite/.mypy_cache .mypy_cache 2>/dev/null
check_output "mypy" "Success: no issues found in 67 source files" "uv run mypy --strict algo-backtest"
check_output "architecture" "PASS" "make check-perception-architecture"

echo "==="
if [ "$FAIL" -eq 0 ]; then
  echo "QA RESULT: PASS"
  exit 0
else
  echo "QA RESULT: FAIL"
  exit 1
fi
