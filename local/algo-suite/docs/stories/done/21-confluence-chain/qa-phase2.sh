#!/usr/bin/env bash
# Story 21 — Phase 2 (T6..T10) QA script. Executes qa-procedure-phase2.md's
# steps through the real interfaces (pytest, REPL, CLI). Exit 0 = pass.
#
# Expected counts below are the actual, currently-collected counts (verified
# by direct run against HEAD), not qa-procedure-phase2.md's original figures:
# the hardener stage added 5 net new Gherkin scenarios across the five
# Phase-2 feature files after that procedure was written (133 -> 138
# collected; see qa-report-phase2.md for the per-file breakdown and the
# other procedure-precision gaps this script had to route around).
set -u
export TMPDIR="${TMPDIR:-/home/wellington/.cache/claude-tmp}"
mkdir -p "$TMPDIR"
cd "$(dirname "$0")/../../../.." || exit 1   # -> algo-suite/

FAIL=0
step() { echo "== $1 =="; }
check() {
  # check "<label>" <actual> <expected>
  if [ "$2" = "$3" ]; then
    echo "PASS: $1 ($2)"
  else
    echo "FAIL: $1 (got [$2], expected [$3])"
    FAIL=1
  fi
}

# --- Step 1: baseline + five-file collection ---------------------------------
step "Step 1 - baseline and collection sanity"
BASELINE=$(uv run pytest algo-backtest/tests -q --co -m 'not integration' 2>&1 | tail -1)
echo "baseline: $BASELINE"
SEL_COUNT=$(uv run pytest algo-backtest/tests/steps/test_confluence_time_exit.py \
  algo-backtest/tests/steps/test_confluence_controls.py \
  algo-backtest/tests/steps/test_confluence_horizon_units.py \
  algo-backtest/tests/steps/test_confluence_preflight.py \
  algo-backtest/tests/steps/test_confluence_cells.py -q --co 2>&1 | tail -1 | awk '{print $1}')
check "five-file selection collects 138" "$SEL_COUNT" "138"

# --- Steps 2/4/6/8/10: per-task pytest runs -----------------------------------
step "Step 2 - T6 time_exit pytest"
OUT=$(uv run pytest algo-backtest/tests/steps/test_confluence_time_exit.py -q 2>&1 | tail -1)
check "T6 passes 50/50" "$OUT" "50 passed in ${OUT#*in }"

step "Step 4 - T7 controls pytest"
OUT=$(uv run pytest algo-backtest/tests/steps/test_confluence_controls.py -q 2>&1 | tail -1)
check "T7 passes 16/16" "$OUT" "16 passed in ${OUT#*in }"

step "Step 6 - T8 horizon_units pytest"
OUT=$(uv run pytest algo-backtest/tests/steps/test_confluence_horizon_units.py -q 2>&1 | tail -1)
check "T8 passes 15/15" "$OUT" "15 passed in ${OUT#*in }"

step "Step 8 - T9 preflight pytest"
OUT=$(uv run pytest algo-backtest/tests/steps/test_confluence_preflight.py -q 2>&1 | tail -1)
check "T9 passes 22/22" "$OUT" "22 passed in ${OUT#*in }"

step "Step 10 - T10 cells pytest"
OUT=$(uv run pytest algo-backtest/tests/steps/test_confluence_cells.py -q 2>&1 | tail -1)
check "T10 passes 35/35" "$OUT" "35 passed in ${OUT#*in }"

# --- Step 3: T6 REPL -----------------------------------------------------------
step "Step 3 - T6 time-exit lifecycle REPL"
REPL3=$(uv run python - <<'PYEOF'
from datetime import UTC, datetime
from algo_backtest.chain.time_exit import TimeExitLifecycle

lc = TimeExitLifecycle(clock_minutes=60, exit_after_bars=4)
lc.entry_filled("T1", datetime(2016, 3, 1, 10, 0, 30, tzinfo=UTC), quantity=1000)
for h in range(10, 14):
    lc.completed_candle(datetime(2016, 3, 1, h, tzinfo=UTC), datetime(2016, 3, 1, h + 1, tzinfo=UTC))
print(lc.state("T1"), lc.due_at("T1"))
closures = lc.tradable_event(datetime(2016, 3, 1, 14, 0, tzinfo=UTC))
print(closures)
print(lc.state("T1"))
PYEOF
)
echo "$REPL3"
L1=$(echo "$REPL3" | sed -n '1p')
L3=$(echo "$REPL3" | sed -n '3p')
check "state/due_at line" "$L1" "DUE 2016-03-01 14:00:00+00:00"
# qa-procedure-phase2.md expects L3=PENDING, but tradable_event() only ever
# *requests* a closure; the trade only becomes PENDING once the engine
# separately confirms the order via order_submitted(), per
# confluence_time_exit.feature:69 and its Background. Without that call the
# trade correctly stays DUE. Procedure-precision gap, not a code defect.
check "post-request state stays DUE (procedure doc says PENDING; see qa-report)" "$L3" "DUE"

# --- Step 5: T7 REPL -------------------------------------------------------------
step "Step 5 - T7 constant-direction filter REPL"
REPL5=$(uv run python - <<'PYEOF'
from datetime import UTC, datetime
from algo_backtest.chain.model import ExecutionState
from algo_backtest.chain.filters.constant_direction import ConstantDirectionFilter

short = ConstantDirectionFilter(direction="SELL")
state = ExecutionState(timestamp=datetime(2016, 3, 1, 10, tzinfo=UTC), pair="EURUSD", features={})
result = short.apply(state)
print(result.recommendation, result.veto, result.enrichment)
try:
    ConstantDirectionFilter(direction="HOLD")
except ValueError as exc:
    print("rejected:", exc)
PYEOF
)
echo "$REPL5"
# qa-procedure-phase2.md expects "Recommendation.SELL False {}", but
# Recommendation is a StrEnum (chain/model.py), whose str() is the bare value
# "SELL", not "Recommendation.SELL". Procedure-precision gap, not a defect.
check "SELL vote line" "$(echo "$REPL5" | sed -n '1p')" "SELL False {}"
case "$(echo "$REPL5" | sed -n '2p')" in
  "rejected: direction must be 'BUY' or 'SELL', got 'HOLD'") echo "PASS: HOLD rejected" ;;
  *) echo "FAIL: HOLD rejection message mismatch"; FAIL=1 ;;
esac

# --- Step 7: T8 archive integrity -----------------------------------------------
step "Step 7 - T8 horizon re-derivation archive integrity"
ARCHIVE=docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md
sha256sum "$ARCHIVE" > "$TMPDIR/before.sha256"
uv run python experiments/confluence-chain/rederive_horizon.py \
  --archive "$ARCHIVE" --out "$TMPDIR/horizon-units.json" >/tmp/horizon_stderr.$$.txt 2>&1
RC=$?
sha256sum "$ARCHIVE" > "$TMPDIR/after.sha256"
if diff -q "$TMPDIR/before.sha256" "$TMPDIR/after.sha256" >/dev/null; then
  echo "PASS: archive untouched"
else
  echo "FAIL: archive hash changed"; FAIL=1
fi
if [ "$RC" -ne 0 ] && grep -q "no source close data configured" /tmp/horizon_stderr.$$.txt; then
  echo "PASS: BLOCKED as documented (no source Parquet configured, explicit remediation message)"
else
  echo "FAIL: unexpected exit/message from rederive_horizon.py without --decisions/--source"; FAIL=1
fi
rm -f /tmp/horizon_stderr.$$.txt
echo "archive sha256: $(sha256sum "$ARCHIVE" | awk '{print $1}')"

# --- Step 9: T9 REPL (population ledger) -----------------------------------------
step "Step 9 - T9 population ledger REPL"
# qa-procedure-phase2.md's import path (algo_backtest.experiments.confluence_chain
# .preflight) does not exist and its start/end `date` kwargs do not match the
# real signature. preflight.py is a standalone script outside the algo_backtest
# package (same pattern as T8), loaded by file path, exactly as
# test_confluence_preflight.py does; its real kwargs are window_start/window_end
# (UTC datetimes). Reconciliation invariant is what's asserted, not literal counts.
REPL9=$(uv run python - <<'PYEOF'
import importlib.util, sys
from pathlib import Path
from datetime import datetime, timezone

path = Path("experiments/confluence-chain/preflight.py")
spec = importlib.util.spec_from_file_location(path.stem, path)
pf = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pf
spec.loader.exec_module(pf)

ledger = pf.compute_population_ledger(
    pair="EURUSD", clock_minutes=60,
    window_start=datetime(2016, 1, 1, tzinfo=timezone.utc),
    window_end=datetime(2016, 1, 31, tzinfo=timezone.utc),
)
print(ledger.calendar_expanded_count, ledger.market_closure_count, ledger.expected_valid_count)
assert ledger.calendar_expanded_count == ledger.market_closure_count + ledger.expected_valid_count
print("assert OK")
PYEOF
)
echo "$REPL9"
check "reconciliation assertion" "$(echo "$REPL9" | sed -n '2p')" "assert OK"

# --- Step 11: T10 manifest CLI ---------------------------------------------------
step "Step 11 - T10 manifest generator CLI"
rm -rf "$TMPDIR/confluence-job" "$TMPDIR/confluence-job2"
uv run python experiments/confluence-chain/make_cells.py --job-dir "$TMPDIR/confluence-job" >/dev/null
CFG_COUNT=$(find "$TMPDIR/confluence-job" -name 'config.yaml' | wc -l | tr -d ' ')
check "14 config.yaml files" "$CFG_COUNT" "14"
read -r ROWS HASHES <<EOF
$(python3 -c "
import json, pathlib
manifest = json.loads((pathlib.Path('$TMPDIR/confluence-job') / 'manifest.json').read_text())
rows = manifest if isinstance(manifest, list) else manifest.get('cells', manifest)
print(len(rows), len({row['config_hash'] for row in rows}))
")
EOF
check "manifest has 14 rows" "$ROWS" "14"
check "14 distinct config_hash values" "$HASHES" "14"

uv run python experiments/confluence-chain/make_cells.py --job-dir "$TMPDIR/confluence-job2" >/dev/null
SAME=$(python3 -c "
import json, pathlib
a = json.loads((pathlib.Path('$TMPDIR/confluence-job')/'manifest.json').read_text())
b = json.loads((pathlib.Path('$TMPDIR/confluence-job2')/'manifest.json').read_text())
ra = a if isinstance(a, list) else a.get('cells', a)
rb = b if isinstance(b, list) else b.get('cells', b)
ida = sorted((r.get('cell_id') or r.get('id'), r['config_hash']) for r in ra)
idb = sorted((r.get('cell_id') or r.get('id'), r['config_hash']) for r in rb)
print(ida == idb)
")
check "re-run is deterministic (identical cell IDs and hashes)" "$SAME" "True"

# --- Step 12: no integration-owned/Phase-1 file touched by Phase 2 --------------
step "Step 12 - no integration-owned or Phase-1 file touched by Phase 2"
# qa-procedure-phase2.md diffs against `main`, which also captures Phase 1's
# (T1-T5) legitimate edits to terminal.py/f1_trend.py/f4_news_context.py/
# f6_capital_mgmt.py/intensity_history.py on this same branch, so that
# literal command is never empty on this branch. Scoped to the Phase 2 commit
# range instead (0c4d612 = Phase 1 hardener/QA boundary .. f6c464a = Phase 2
# hardener HEAD), which is what "did Phase 2 touch these files" actually means.
PHASE2_BASE=0c4d612
PHASE2_HEAD=f6c464a
DIFF=$(git -C /tmp/mba-impl-21 diff --stat "$PHASE2_BASE".."$PHASE2_HEAD" -- \
  algo-suite/algo-backtest/src/algo_backtest/strategies.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/wiring.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/audit.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py \
  algo-suite/algo-backtest/src/algo_backtest/engine \
  algo-suite/algo-backtest/src/algo_backtest/chain/terminal.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/filters/f1_trend.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/filters/f4_news_context.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/filters/f6_capital_mgmt.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/intensity_history.py)
check "phase-2-scoped diff on shared paths is empty" "$DIFF" ""

# --- Step 13: quality gates -------------------------------------------------------
step "Step 13 - quality gates"
uv run ruff check algo-backtest/src/algo_backtest/chain/time_exit.py \
  algo-backtest/src/algo_backtest/chain/filters/constant_direction.py \
  algo-backtest/tests/steps/test_confluence_time_exit.py \
  algo-backtest/tests/steps/test_confluence_controls.py \
  algo-backtest/tests/steps/test_confluence_horizon_units.py \
  algo-backtest/tests/steps/test_confluence_preflight.py \
  algo-backtest/tests/steps/test_confluence_cells.py || FAIL=1
uv run ruff check --select C901 algo-backtest/src/algo_backtest/chain/time_exit.py \
  algo-backtest/src/algo_backtest/chain/filters/constant_direction.py || FAIL=1
uv run mypy --strict algo-backtest/src/algo_backtest/chain/time_exit.py \
  algo-backtest/src/algo_backtest/chain/filters/constant_direction.py || FAIL=1
uv run mypy --strict experiments/confluence-chain/rederive_horizon.py \
  experiments/confluence-chain/preflight.py experiments/confluence-chain/make_cells.py || FAIL=1

FULL=$(uv run pytest algo-backtest/tests -q -m 'not integration' 2>&1 | tail -3)
echo "$FULL"
echo "$FULL" | grep -q "1937 passed, 53 deselected" && echo "PASS: full offline suite 1937 passed, 53 deselected, 0 failed" \
  || { echo "FAIL: full offline suite count mismatch"; FAIL=1; }

echo
if [ "$FAIL" -eq 0 ]; then
  echo "=== QA PHASE 2: ALL CHECKS PASSED ==="
  exit 0
else
  echo "=== QA PHASE 2: FAILURES DETECTED ==="
  exit 1
fi
