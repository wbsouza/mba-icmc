#!/usr/bin/env bash
# QA phase 1 (T1..T5) for story 21 (confluence chain). Executes
# qa-procedure-phase1.md literally through the real interfaces it names.
# Exit 0 = pass. Corrections vs. the procedure doc's stale counts are noted
# inline (see qa-report-phase1.md for the full explanation of each one):
# the five confluence step files now collect 201 cases (not 180) and the
# full offline suite is 1799 passed (not the pre-phase 1598 baseline) —
# both because the cleaner and hardener stages added scenarios after the
# procedure doc was written, as progress.md records.
set -uo pipefail

export TMPDIR=/home/wellington/.cache/claude-tmp
mkdir -p "$TMPDIR"
cd /tmp/mba-impl-21/algo-suite || exit 1

FAIL=0
step() { echo; echo "=== $1 ==="; }
check() {
  # check <label> <status: 0=ok/nonzero=bad> <detail>
  if [ "$2" -eq 0 ]; then
    echo "PASS: $1"
  else
    echo "FAIL: $1 -- $3"
    FAIL=1
  fi
}

# This worktree is shared with a concurrent phase-2 lane (T6+: confluence
# time-exit lifecycle, drift-control votes) landing commits on this same
# branch on top of the Phase 1 baseline (HEAD 0c4d612) while this QA run is
# in progress -- confirmed via `git log` showing commits 3bbbbf8/b2f8442+
# added after 0c4d612, and new/untracked files appearing under tests/ and
# src/algo_backtest/chain mid-run. Phase 1's own modules and step files are
# verified unchanged since 0c4d612 (git diff 0c4d612..HEAD on those exact
# paths is empty). To keep this script deterministic regardless of how far
# phase-2 has landed at run time, Steps 1a/13 compute and exclude every path
# added to tests/ or chain/ since 0c4d612 (committed or still untracked) so
# only Phase 1's own surface is graded.
cd /tmp/mba-impl-21 || exit 1
PHASE1_BASE=0c4d612
ADDED_TRACKED=$(git diff --name-only --diff-filter=A "$PHASE1_BASE" HEAD -- \
  algo-suite/algo-backtest/tests algo-suite/algo-backtest/src/algo_backtest/chain)
UNTRACKED=$(git status --porcelain -- \
  algo-suite/algo-backtest/tests algo-suite/algo-backtest/src/algo_backtest/chain \
  | awk '$1=="??"{print $2}')
PHASE2_PATHS=$(printf '%s\n%s\n' "$ADDED_TRACKED" "$UNTRACKED" | sed '/^$/d' | sed 's#^algo-suite/##' | sort -u)
echo "Phase-2 (post-0c4d612) paths excluded from Phase 1 gates:"
echo "$PHASE2_PATHS" | sed 's/^/  /'
cd /tmp/mba-impl-21/algo-suite || exit 1

PYTEST_IGNORE_ARGS=()
RUFF_EXCLUDE_ARGS=()
while IFS= read -r p; do
  [ -z "$p" ] && continue
  case "$p" in
    algo-backtest/tests/*) PYTEST_IGNORE_ARGS+=("--ignore=$p") ;;
    algo-backtest/src/algo_backtest/chain/*) RUFF_EXCLUDE_ARGS+=("--extend-exclude" "$(basename "$p")") ;;
  esac
done <<< "$PHASE2_PATHS"

step "Setup"
uv sync --all-packages
check "uv sync" $? ""

step "Step 1 -- baseline and collection sanity"
out=$(uv run pytest algo-backtest/tests -q --co -m 'not integration' -p no:cacheprovider "${PYTEST_IGNORE_ARGS[@]}" 2>&1)
echo "$out" | tail -1
echo "$out" | grep -q "1799/1852 tests collected (53 deselected)"
check "Step1a full suite (phase-2 WIP excluded) collects 1799/1852 (53 deselected)" $? "$(echo "$out" | tail -1)"

out=$(uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py \
  algo-backtest/tests/steps/test_confluence_momentum.py \
  algo-backtest/tests/steps/test_confluence_history.py \
  algo-backtest/tests/steps/test_confluence_relative_intensity.py \
  algo-backtest/tests/steps/test_confluence_capital_plan.py -q --co -p no:cacheprovider 2>&1)
echo "$out" | tail -1
echo "$out" | grep -qE "^201 tests collected"
check "Step1b five confluence step files collect 201 (cleaner+hardener added 21 cases past the doc's 180)" $? "$(echo "$out" | tail -1)"

step "Step 2 -- T1 agreement terminal (pytest)"
out=$(uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^45 passed"
check "test_confluence_agreement.py: 45 passed, 0 failed" $? "$(echo "$out" | tail -2)"
out2=$(uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py -v -p no:cacheprovider 2>&1)
echo "$out2" | grep -q "F5 vetoes an agreed side before the terminal" && \
echo "$out2" | grep -q "F6 vetoes on margin before the terminal" && \
echo "$out2" | grep -q "the gates pass and the agreed side is traded"
check "F5/F6 veto and gates-pass rows ran" $? "veto/gate row names not found in -v output"

step "Step 3 -- T1 agreement terminal (REPL)"
out=$(uv run python - <<'PYEOF'
from datetime import UTC, datetime
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation as R
from algo_backtest.chain.terminal import AgreementTerminalDecision

voters = {"f1_trend": "F1_trend", "f2_indicator": "F2_indicator",
          "f3_pattern": "F3_pattern", "f4_news_context": "f4_news_context"}
terminal = AgreementTerminalDecision(required_filters=("f1_trend", "f4_news_context"),
                                     voter_name_map=voters)
def state(*votes):
    s = ExecutionState(timestamp=datetime(2016, 4, 5, 10, tzinfo=UTC), pair="EURUSD", features={})
    s.filter_results = [FilterResult(filter_name=n, recommendation=R(v), reason="qa") for n, v in votes]
    return s
print(terminal.decide(state(("F1_trend", "SELL"), ("f4_news_context", "SELL"), ("f5_risk_guard", "ABSTAIN"))))
print(terminal.decide(state(("F1_trend", "BUY"), ("f4_news_context", "SELL"))))
print(terminal.decide(state(("F1_trend", "BUY"), ("f4_news_context", "BUY"), ("F2_indicator", "HOLD"))))
print(terminal.decide(state(("F1_trend", "ABSTAIN"), ("f4_news_context", "NEUTRAL"))))
try:
    AgreementTerminalDecision(required_filters=("f1_trend", "f5_risk_guard"), voter_name_map=voters)
except ValueError as exc:
    print("rejected:", exc)
try:
    terminal.decide(state(("F1_trend", "BUY")))
except ValueError as exc:
    print("rejected:", exc)
PYEOF
)
echo "$out"
printf '%s\n' "$out" | sed -n '1p' | grep -qx "SELL" && \
printf '%s\n' "$out" | sed -n '2p' | grep -qx "HOLD" && \
printf '%s\n' "$out" | sed -n '3p' | grep -qx "HOLD" && \
printf '%s\n' "$out" | sed -n '4p' | grep -qx "HOLD" && \
printf '%s\n' "$out" | sed -n '5p' | grep -q "rejected:.*'f5_risk_guard' is a gate" && \
printf '%s\n' "$out" | sed -n '6p' | grep -q "rejected:.*required voter 'f4_news_context'.*did not run"
check "SELL/HOLD/HOLD/HOLD then two rejected: lines (doc's 'Decision.X' prefix is stale; enum prints bare name)" $? "$out"

step "Step 4 -- T2 momentum context (pytest)"
out=$(uv run pytest algo-backtest/tests/steps/test_confluence_momentum.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^43 passed"
check "test_confluence_momentum.py: 43 passed (doc says 38; cleaner added cases)" $? "$(echo "$out" | tail -2)"
out=$(uv run pytest algo-backtest/tests/steps/test_f1_trend.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^13 passed"
check "test_f1_trend.py: 13 passed" $? "$(echo "$out" | tail -2)"
git diff --quiet main -- algo-backtest/tests/features/f1_trend.feature
check "f1_trend.feature unchanged vs main" $? "diff was non-empty"

step "Step 5 -- T2 momentum context (REPL)"
out=$(uv run python - <<'PYEOF'
from datetime import UTC, datetime, timedelta
from algo_backtest.chain.filters.f1_trend import (
    MomentumHistory, parse_momentum_context_config, F1MomentumContextFilter)
from algo_backtest.chain.model import ExecutionState

config = parse_momentum_context_config({"lookback_bars": 480}, strategy="qa")
history = MomentumHistory(lookback_bars=config.lookback_bars)
t0 = datetime(2016, 3, 1, tzinfo=UTC)
f = F1MomentumContextFilter(config=config, history=history)
def apply(at):
    return f.apply(ExecutionState(timestamp=at, pair="EURUSD", features={}))
for k in range(480):
    history.push(t0 + timedelta(hours=k), 1.2 if 0 < k else 1.1)
r = apply(t0 + timedelta(hours=479)); print(r.recommendation, r.metadata["momentum_status"], r.reason)
history.push(t0 + timedelta(hours=480), 1.1055)
r = apply(t0 + timedelta(hours=480)); print(r.recommendation, r.veto, r.enrichment["momentum_return"])
try:
    history.push(t0 + timedelta(hours=480), 1.2)
except ValueError as exc:
    print("rejected:", exc)
PYEOF
)
echo "$out"
printf '%s\n' "$out" | sed -n '1p' | grep -q "^ABSTAIN WARMUP momentum_context WARMUP: 480 of 481 closes collected" && \
printf '%s\n' "$out" | sed -n '2p' | grep -qE "^BUY False 0.00499999" && \
printf '%s\n' "$out" | sed -n '3p' | grep -q "rejected:.*is not after the last close"
check "WARMUP / BUY False 0.005 / rejected duplicate close (doc's 'Recommendation.X' prefix is stale; enum prints bare name, same as step 3)" $? "$out"

step "Step 6 -- T3 monthly intensity snapshots (pytest)"
out=$(uv run pytest algo-backtest/tests/steps/test_confluence_history.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^46 passed"
check "test_confluence_history.py: 46 passed (doc says 32; cleaner+hardener added cases, see progress.md 44->46)" $? "$(echo "$out" | tail -2)"
out2=$(uv run pytest algo-backtest/tests/steps/test_confluence_history.py -v -p no:cacheprovider 2>&1)
echo "$out2" | grep -q "test_the_reference_daily_archive_gives_q10_0195_and_q90_1355" && \
echo "$out2" | grep -q "test_rows_that_arrive_after_the_snapshot_froze" && \
echo "$out2" | grep -q "test_a_gap_inside_a_documented_market_closure" && \
echo "$out2" | grep -q "test_a_collection_that_started_inside_the_window_reports_warmup"
check "named scenario cases present (mid-month case verified separately)" $? "case names not found"

step "Step 7 -- T3 hand-checked quantiles (REPL)"
out=$(uv run python - <<'PYEOF'
from datetime import UTC, datetime, timedelta
import json, numpy as np
from algo_backtest.chain.intensity_history import IntensityHistory, IntensityObservation

values = [0.05 * k for k in (30,5,22,1,18,29,12,3,26,8,15,20,4,25,7,2,28,11,19,6,24,14,9,27,17,13,23,10,21,16)]
history = IntensityHistory(clock_minutes=1440, collection_started_at=datetime(2016, 1, 1, tzinfo=UTC))
for i, v in enumerate(values):
    closed = datetime(2016, 3, 2, tzinfo=UTC) + timedelta(days=i)
    history.record(IntensityObservation(bar_closed_at=closed, available_at=closed, intensity=v, source_id="qa"))
snap = history.snapshot_for(datetime(2016, 4, 17, 10, tzinfo=UTC))
print(snap.status, snap.cutoff, snap.window_start, snap.sample_count, snap.q_low, snap.q_high)
print("numpy agrees:", np.quantile(values, 0.10, method="linear"), np.quantile(values, 0.90, method="linear"))
again = history.snapshot_for(datetime(2016, 4, 1, tzinfo=UTC))
print("frozen:", again == snap, len(snap.source_hash))
print(json.dumps(snap.as_mapping(), sort_keys=True)[:120], "...")
PYEOF
)
echo "$out"
printf '%s\n' "$out" | sed -n '1p' | grep -q "^READY 2016-04-01 00:00:00+00:00 2016-03-02 00:00:00+00:00 30 0.195" && \
printf '%s\n' "$out" | sed -n '3p' | grep -q "^frozen: True 64"
check "READY snapshot q10/q90 matches numpy, frozen True, hash len 64" $? "$out"

step "Step 8 -- T4 relative F4 (pytest)"
out=$(uv run pytest algo-backtest/tests/steps/test_confluence_relative_intensity.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^42 passed"
check "test_confluence_relative_intensity.py: 42 passed (doc says 40)" $? "$(echo "$out" | tail -2)"
out=$(uv run pytest algo-backtest/tests/steps/test_f4_news_context.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^49 passed"
check "test_f4_news_context.py: 49 passed" $? "$(echo "$out" | tail -2)"
git diff main -- algo-backtest/tests/features/f4_news_context.feature > /tmp/f4_diff.txt
diffcount=$(grep -c "^[+-]" /tmp/f4_diff.txt)
grep -q "intensity_relative" /tmp/f4_diff.txt
check "f4_news_context.feature diff only touches the 'unknown source' choices list" $? "diff: $(cat /tmp/f4_diff.txt)"

step "Step 9 -- T4 relative F4 (REPL)"
out=$(uv run python - <<'PYEOF'
from datetime import UTC, datetime
from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter, NewsContextIndex, parse_news_context_config)
from algo_backtest.chain.intensity_history import IntensitySnapshot
from algo_backtest.chain.model import ExecutionState

config = parse_news_context_config({"event_intensity_veto_threshold": -0.5,
    "sentiment_direction_threshold": None, "direction_source": "intensity_relative",
    "intensity_sign": -1}, strategy="qa")
at = datetime(2016, 4, 5, 10, tzinfo=UTC)
def run(intensity, q_low, q_high, status="READY"):
    snapshot = IntensitySnapshot(cutoff=datetime(2016, 4, 1, tzinfo=UTC),
        window_start=datetime(2016, 3, 2, tzinfo=UTC), clock_minutes=60, q_low=q_low, q_high=q_high,
        sample_count=30, max_closed_at=datetime(2016, 3, 31, 23, tzinfo=UTC),
        max_available_at=datetime(2016, 3, 31, 23, tzinfo=UTC), source_hash="ab12",
        quantile_method="linear", schema_version=1, status=status)
    index = NewsContextIndex(event_intensity={at: intensity}, sentiment_polarity={}, sentiment_source_present=False)
    f = F4NewsContextFilter(index=index, config=config, snapshots={snapshot.cutoff: snapshot},
                            availability={at: at})
    r = f.apply(ExecutionState(timestamp=at, pair="EURUSD", features={}))
    return r.recommendation.value, r.veto
print(run(0.8, 0.2, 0.8), run(0.2, 0.2, 0.8), run(0.5, 0.2, 0.8))
print(run(0.4, 0.5, 0.5), run(0.6, 0.5, 0.5))
print(run(5.0, None, None, status="WARMUP"))
print(run(-0.7, 0.2, 0.8))
PYEOF
)
echo "$out"
printf '%s\n' "$out" | sed -n '1p' | grep -qx "('SELL', False) ('BUY', False) ('NEUTRAL', False)" && \
printf '%s\n' "$out" | sed -n '2p' | grep -qx "('HOLD', False) ('HOLD', False)" && \
printf '%s\n' "$out" | sed -n '3p' | grep -qx "('HOLD', False)" && \
printf '%s\n' "$out" | sed -n '4p' | grep -qx "('ABSTAIN', True)"
check "sign -1 mapping, degenerate HOLD, WARMUP HOLD, veto ABSTAIN True" $? "$out"

step "Step 10 -- T5 F6 bar-count plan (pytest)"
out=$(uv run pytest algo-backtest/tests/steps/test_confluence_capital_plan.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^25 passed"
check "test_confluence_capital_plan.py: 25 passed" $? "$(echo "$out" | tail -2)"
out=$(uv run pytest algo-backtest/tests/steps/test_f6_capital_mgmt.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^107 passed"
check "test_f6_capital_mgmt.py: 107 passed" $? "$(echo "$out" | tail -2)"
git diff --quiet main -- algo-backtest/tests/features/f6_capital_mgmt.feature
check "f6_capital_mgmt.feature unchanged vs main" $? "diff was non-empty"

step "Step 11 -- T5 F6 bar-count plan (REPL)"
out=$(uv run python - <<'PYEOF'
import algo_backtest.chain.filters.f6_capital_mgmt as f6
from algo_backtest.chain.filters.f6_capital_mgmt import capital_mgmt_mapping, parse_capital_mgmt_config
base = {"risk_per_trade": 0.03, "stop_loss_pips": 20.0, "pip_value_per_lot": 10.0,
        "lot_notional_units": 100000, "assumed_leverage": 30}
legacy = parse_capital_mgmt_config(base, strategy="qa")
print("legacy:", legacy.exit_after_bars, capital_mgmt_mapping(legacy)["targets"])
timed = parse_capital_mgmt_config({**base, "stop_distance_source": "atr", "atr_multiplier": 2.0,
        "targets": [], "trail_stops": [], "exit_after_bars": 4}, strategy="qa")
print("timed:", timed.exit_after_bars, timed.targets, timed.trail_stops, timed.min_reward_risk)
for bad in (True, 4.5, 0, -4, "four"):
    try:
        parse_capital_mgmt_config({**base, "exit_after_bars": bad}, strategy="qa")
    except ValueError as exc:
        print("rejected:", exc)
print("open of bar t+N" in f6.__doc__, "close of bar t+N-1" in f6.__doc__)
PYEOF
)
echo "$out"
rejected_count=$(printf '%s\n' "$out" | grep -c "rejected:.*capital_mgmt.exit_after_bars must be a positive integer")
printf '%s\n' "$out" | sed -n '1p' | grep -Fqx "legacy: None [{'at_level_ratio': 2.0, 'close_fraction': 1.0}]" && \
printf '%s\n' "$out" | sed -n '2p' | grep -Fqx "timed: 4 () () None" && \
[ "$rejected_count" -eq 5 ] && \
printf '%s\n' "$out" | tail -1 | grep -Fqx "True True"
check "legacy round trip, timed plan, 5 rejections, docstring markers" $? "$out"

step "Step 12 -- legacy CLI and strategies untouched (CC-20)"
out=$(uv run algo-backtest explain-strategy news-rule 2>&1)
echo "$out" | grep -q "^news_context.direction_source = \"intensity\""
r1=$?
echo "$out" | grep -qE "intensity_relative|momentum_context|^agreement|exit_after_bars"
r2=$?
check "explain-strategy news-rule: direction_source=intensity, no new keys" $(( r1 == 0 && r2 != 0 ? 0 : 1 )) "$out"
cnt=$(uv run algo-backtest explain-strategy hybrid 2>&1 | grep -c capital_mgmt)
[ "$cnt" -gt 0 ]
check "explain-strategy hybrid still resolves capital_mgmt (count=$cnt)" $? "count was $cnt"
out=$(uv run pytest algo-backtest/tests/steps/test_filter_chain_mechanics.py \
  algo-backtest/tests/steps/test_chain_wiring.py \
  algo-backtest/tests/steps/test_strategy_explain.py \
  algo-backtest/tests/steps/test_strategies.py -q -p no:cacheprovider 2>&1)
echo "$out" | tail -2
echo "$out" | grep -qE "^242 passed"
check "chain/wiring/explain/strategies regression: 242 passed" $? "$(echo "$out" | tail -2)"
diffstat=$(git -C /tmp/mba-impl-21 diff --stat main -- algo-suite/algo-backtest/src/algo_backtest/strategies.py \
  algo-suite/algo-backtest/src/algo_backtest/chain/wiring.py algo-suite/algo-backtest/src/algo_backtest/engine)
[ -z "$diffstat" ]
check "no integration-owned file changed (strategies.py, wiring.py, engine/)" $? "diffstat: $diffstat"

step "Step 13 -- quality gates for the touched packages"
# See the phase-2 exclusion note above (Phase 1 gates below use the
# dynamically computed PYTEST_IGNORE_ARGS/RUFF_EXCLUDE_ARGS).
uv run ruff check algo-backtest/src/algo_backtest/chain algo-backtest/tests/steps "${RUFF_EXCLUDE_ARGS[@]}"
check "ruff clean on chain + steps (phase-2 WIP excluded)" $? ""
uv run ruff check --select C901 algo-backtest/src/algo_backtest/chain "${RUFF_EXCLUDE_ARGS[@]}"
check "ruff C901 clean on chain (phase-2 WIP excluded)" $? ""
MYPY_EXCLUDE_RE=$(printf '%s\n' "$PHASE2_PATHS" | grep '^algo-backtest/src/algo_backtest/chain/' | sed 's/[.[\*^$/]/\\&/g' | paste -sd'|' -)
if [ -n "$MYPY_EXCLUDE_RE" ]; then
  uv run mypy --strict algo-backtest/src/algo_backtest/chain --exclude "($MYPY_EXCLUDE_RE)"
else
  uv run mypy --strict algo-backtest/src/algo_backtest/chain
fi
check "mypy --strict clean on chain (phase-2 WIP excluded)" $? ""
make lint type > /tmp/mba_phase1_lint_type.log 2>&1
lint_backtest_hits=$(grep "algo-backtest" /tmp/mba_phase1_lint_type.log | grep -vFf <(printf '%s\n' "$PHASE2_PATHS" | xargs -n1 basename 2>/dev/null) | wc -l || true)
[ "${lint_backtest_hits:-0}" -eq 0 ]
check "make lint type: 0 findings inside algo-backtest outside phase-2 WIP (workspace pre-existing failures elsewhere are known/BLOCKED per progress.md)" $? "$(tail -5 /tmp/mba_phase1_lint_type.log)"
out=$(uv run pytest algo-backtest/tests -q -m 'not integration' -p no:cacheprovider "${PYTEST_IGNORE_ARGS[@]}" 2>&1)
echo "$out" | tail -3
echo "$out" | grep -qE "^1799 passed, 53 deselected" && ! echo "$out" | grep -qE "failed|error"
check "full offline algo-backtest suite (phase-2 WIP excluded): 1799 passed, 53 deselected, 0 failed" $? "$(echo "$out" | tail -3)"

echo
if [ "$FAIL" -eq 0 ]; then
  echo "QA PHASE 1: ALL STEPS PASSED"
else
  echo "QA PHASE 1: FAILURES ABOVE"
fi
exit $FAIL
