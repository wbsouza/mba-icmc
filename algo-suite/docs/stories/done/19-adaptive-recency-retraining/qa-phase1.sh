#!/usr/bin/env bash
# Story 19 Phase 1 QA script. Deterministic re-run of qa-procedure-phase1.md
# through the real interfaces it names. Exit 0 = every step passed.
set -uo pipefail

export TMPDIR="${TMPDIR:-/home/wellington/.cache/claude-tmp}"
mkdir -p "$TMPDIR"

SUITE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
STORY_REL="docs/stories/in-progress/19-adaptive-recency-retraining"
SPECS="$SUITE/../.specs/features/recency-weighted-retraining"
SKILL="/home/wellington/.claude/skills/tlc-spec-driven/scripts"
LEDGER_DIR="$TMPDIR/qa19-ledger"

fail=0
step() { echo "== $1 =="; }
check() { if [ "$1" -ne 0 ]; then echo "FAIL: $2"; fail=1; else echo "PASS: $2"; fi; }

cd "$SUITE"

step "Step 0: Phase 1 surface"
OUT0A=$(uv run python -c "import algo_backtest.retraining as r, algo_backtest.retraining.ingestion as i, algo_backtest.retraining.schedule as s, algo_backtest.retraining.weights as w; print(sorted(n for n in dir(i)+dir(s)+dir(w) if not n.startswith('_')))")
E0A=$?
echo "$OUT0A"
for name in consume monthly_epochs stage_spans select_rows exponential_weights normalize_mean_one effective_n uniform_weights check_support; do
  echo "$OUT0A" | grep -q "'$name'" || E0A=1
done
OUT0B=$(uv run python -c "import inspect; from algo_backtest.chain.filters.f7_meta_learner import train_meta_learner as t; print(inspect.signature(t))")
E0B=$?
echo "$OUT0B"
echo "$OUT0B" | grep -q "family_weights" || E0B=1
echo "$OUT0B" | grep -q "random_state" || E0B=1
check $((E0A + E0B)) "Step 0 surface + signature"

step "Step 1: T1 documentation checklist"
F="$STORY_REL/method-design.md"
E1=0
test -s "$F" || E1=1
(cd "$SUITE/.." && git diff --check) || E1=1
python3 "$SKILL/validate_spec.py" "$SPECS/spec.md" --strict || E1=1
python3 "$SKILL/validate_tasks.py" "$SPECS/tasks.md" --strict || E1=1
[ "$(grep -c "" "$F")" -gt 0 ] || E1=1
[ "$(grep -c -E '^\| (F|Q|R|U|E) \|' "$F")" -eq 5 ] || E1=1
grep -q "2015-03-02T00:00:00Z" "$F" || E1=1
grep -q "2016-02-29" "$F" || E1=1
grep -q "2015-07-04" "$F" || E1=1
grep -q "2015-12-31" "$F" || E1=1
grep -q "2\^(-age_days / 60)" "$F" || E1=1
grep -q "n_eff = sum(w)\^2 / sum(w\^2)" "$F" || E1=1
grep -q ">= 1000" "$F" || E1=1
grep -q "random_state=42" "$F" || E1=1
grep -q -i "sha256" "$F" || E1=1
grep -q "ALGO_DATA_ROOT" "$F" || E1=1
grep -q "primary block length 4" "$F" || E1=1
grep -q "sensitivity block length 2" "$F" || E1=1
grep -q "9999 resamples" "$F" || E1=1
grep -q "30 minutes" "$F" || E1=1
grep -q -i "measured by the coordinator" "$F" || E1=1
grep -q -i "exploratory" "$F" || E1=1
grep -q -i "disposition" "$F" || E1=1
# NDA check is absence, not presence: the doc need not discuss the two earlier
# systems at all. We only verify it stays within the three allowed euphemisms
# wherever it *does* refer to prior trading-system work (manually reviewed;
# no literal forbidden name can be grepped for here without naming it).
grep -q "\[x\] T1" "$STORY_REL/progress.md" || E1=1
grep -q -E "RWT-18 .*Implemented \(T1\)" "$SPECS/spec.md" || E1=1
grep -q -E "RWT-21 .*Implemented \(T1\)" "$SPECS/spec.md" || E1=1
grep -q -E "RWT-29 .*Implemented \(T1\)" "$SPECS/spec.md" || E1=1
check $E1 "Step 1 T1 checklist"

step "Step 2: T2 ingestion pytest"
uv run pytest algo-backtest/tests/steps/test_retraining_ingestion.py -q -p no:cacheprovider
check $? "Step 2 ingestion pytest (baseline was 22 passed at T2; hardener added 3 survivor scenarios -> 25 passed is expected now, see qa-report note)"

step "Step 3: T2 ledger by hand"
rm -rf "$LEDGER_DIR" && mkdir -p "$LEDGER_DIR"
uv run python - <<PYEOF
import sys, hashlib
from datetime import datetime
from pathlib import Path
import algo_backtest.retraining.ingestion as ing

ledger_dir = Path("$LEDGER_DIR")
T = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))

def row(key, avail, label_time, label):
    return ing.SourceRow(key=key, available_at=T(avail), label_time=(T(label_time) if label_time else None), label=label)

ok = True
def expect(cond, msg):
    global ok
    if not cond:
        ok = False
        print("MISMATCH:", msg)

batch_a = ing.Batch(partition="eurusd/h1/2016-01", rows=(
    row("bar-001", "2016-01-04T09:00:00Z", "2016-01-04T10:00:00Z", 1),
    row("bar-002", "2016-01-04T10:00:00Z", "2016-01-04T11:00:00Z", 0),
    row("bar-003", "2016-01-04T11:00:00Z", "2016-01-04T14:00:00Z", 1),
))
batch_b = ing.Batch(partition="eurusd/h1/2016-01", rows=(
    row("bar-004", "2016-01-04T12:00:00Z", "2016-01-04T13:00:00Z", 0),
    row("bar-005", "2016-01-04T14:00:00Z", "2016-01-04T15:00:00Z", 1),
))

l1 = ing.consume(ledger_dir, batch_a)
expect(str(l1.watermark) == "2016-01-04 11:00:00+00:00", "1) watermark")
expect(l1.row_count == 3, "1) row_count")
expect(l1.maturity("bar-001") == "mature" and l1.maturity("bar-002") == "mature" and l1.maturity("bar-003") == "pending", "1) maturity")

files = list(ledger_dir.iterdir())
expect(len(files) == 1, "2) exactly one ledger file")
sha_before = hashlib.sha256((ledger_dir / "ledger.json").read_bytes()).hexdigest()

l2 = ing.consume(ledger_dir, batch_a)
sha_retry = hashlib.sha256((ledger_dir / "ledger.json").read_bytes()).hexdigest()
expect(sha_before == sha_retry, "3) sha unchanged on identical retry")

l3 = ing.consume(ledger_dir, batch_b)
expect(str(l3.watermark) == "2016-01-04 14:00:00+00:00", "4) watermark")
expect(l3.row_count == 5, "4) row_count")
expect(l3.maturity("bar-003") == "mature" and l3.maturity("bar-005") == "pending", "4) maturity")
sha_after_b = hashlib.sha256((ledger_dir / "ledger.json").read_bytes()).hexdigest()

l4 = ing.consume(ledger_dir, batch_a)
sha_after_5 = hashlib.sha256((ledger_dir / "ledger.json").read_bytes()).hexdigest()
expect(sha_after_5 == sha_after_b, "5) idempotent after B")

bad_conflict = ing.Batch(partition="eurusd/h1/2016-01", rows=(
    row("bar-003", "2016-01-04T11:00:00Z", "2016-01-04T14:00:00Z", 0),
))
try:
    ing.consume(ledger_dir, bad_conflict)
    expect(False, "6) expected ValueError")
except ValueError as exc:
    msg = str(exc)
    expect("bar-003" in msg and "conflict" in msg, "6) error text")
sha_after_6 = hashlib.sha256((ledger_dir / "ledger.json").read_bytes()).hexdigest()
expect(sha_after_6 == sha_after_b, "6) sha unchanged")

bad_none = ing.Batch(partition="eurusd/h1/2016-01", rows=(
    row("bar-006", "2016-01-04T16:00:00Z", None, 0),
))
try:
    ing.consume(ledger_dir, bad_none)
    expect(False, "7) expected ValueError")
except ValueError as exc:
    expect("label_time" in str(exc), "7) error text")
sha_after_7 = hashlib.sha256((ledger_dir / "ledger.json").read_bytes()).hexdigest()
expect(sha_after_7 == sha_after_b, "7) sha unchanged")

fresh = ing.Ledger.open(ledger_dir)
expect(str(fresh.watermark) == "2016-01-04 14:00:00+00:00" and fresh.row_count == 5, "8) reopen watermark/rows")
expect(fresh.maturity("bar-003") == "mature" and fresh.maturity("bar-005") == "pending", "8) reopen maturity")

if not ok:
    sys.exit(1)
print("LEDGER_FIXTURE_OK")
PYEOF
check $? "Step 3 ledger by-hand fixture"

step "Step 4: T3 schedule/selector pytest"
uv run pytest algo-backtest/tests/steps/test_retraining_schedule.py -q -p no:cacheprovider
E4A=$?
uv run pytest algo-backtest/tests/steps/test_f7_meta_learner.py -q -p no:cacheprovider
E4B=$?
check $((E4A + E4B)) "Step 4 schedule (41 passed expected) + f7_meta_learner (unchanged baseline)"

step "Step 5: T3 temporal contract by hand"
uv run python - <<'PYEOF'
import sys
from datetime import datetime, UTC
from algo_backtest.retraining.schedule import monthly_epochs, stage_spans
D = lambda s: datetime.fromisoformat(s).replace(tzinfo=UTC)
ok = True
def expect(cond, msg):
    global ok
    if not cond:
        ok = False
        print("MISMATCH:", msg)

epochs = list(monthly_epochs(D("2016-03-01"), D("2017-03-01")))
expect(len(epochs) == 12, "epoch count")
expect(epochs[0].start == D("2016-03-01") and epochs[-1].start == D("2017-02-01"), "epoch bounds")

f = stage_spans(epochs[0], "F")
expect(f.family.start == D("2015-03-02") and f.family.end == D("2015-12-31"), "F family span")
expect(f.combiner.start == D("2015-12-31") and f.combiner.end == D("2016-01-30"), "F combiner span")
expect(f.threshold.start == D("2016-01-30") and f.threshold.end == D("2016-02-29"), "F threshold span")

r = stage_spans(epochs[0], "R")
expect(r.family.start == D("2015-07-04") and r.family.end == D("2015-12-31"), "R family span")

r_apr = stage_spans(epochs[1], "R")
expect(r_apr.family.start == D("2015-08-04") and r_apr.family.end == D("2016-01-31"), "R-APR family")
expect(r_apr.combiner.start == D("2016-01-31") and r_apr.combiner.end == D("2016-03-01"), "R-APR combiner")
expect(r_apr.threshold.start == D("2016-03-01") and r_apr.threshold.end == D("2016-03-31"), "R-APR threshold")
expect(r_apr.deployment.start == D("2016-04-01") and r_apr.deployment.end == D("2016-05-01"), "R-APR deploy")

q_apr = stage_spans(epochs[1], "Q")
expect(q_apr.family.start == D("2015-03-02") and q_apr.family.end == D("2015-12-31"), "Q-APR family (frozen)")
expect(q_apr.threshold.start == D("2016-03-01") and q_apr.threshold.end == D("2016-03-31"), "Q-APR threshold (moves)")

u_jan = stage_spans(epochs[10], "U")
expect(u_jan.family.start == D("2015-03-02") and u_jan.family.end == D("2016-11-01"), "U-JAN family expanding")
expect(u_jan.deployment.start == D("2017-01-01") and u_jan.deployment.end == D("2017-02-01"), "U-JAN deploy")

try:
    stage_spans(epochs[0], "X")
    expect(False, "expected ValueError for unknown policy")
except ValueError as exc:
    expect("policy" in str(exc), "policy error text")

try:
    monthly_epochs(D("2016-03-02"), D("2017-03-01"))
    expect(False, "expected ValueError for non month-start")
except ValueError as exc:
    expect("month start" in str(exc), "month start error text")

if not ok:
    sys.exit(1)
print("SCHEDULE_FIXTURE_OK")
PYEOF
check $? "Step 5 temporal contract by-hand"

step "Step 6: T4 weights pytest"
uv run pytest algo-backtest/tests/steps/test_retraining_weights.py -q -p no:cacheprovider
check $? "Step 6 weights pytest (49 passed expected)"

step "Step 7: T4 analytic fixture by hand (dates corrected for leap year per progress.md T4)"
uv run python - <<'PYEOF'
import sys
from datetime import datetime, UTC
from algo_backtest.retraining.weights import exponential_weights, normalize_mean_one, effective_n, uniform_weights
D = lambda s: datetime.fromisoformat(s).replace(tzinfo=UTC)
ok = True
def expect(cond, msg):
    global ok
    if not cond:
        ok = False
        print("MISMATCH:", msg)

cutoff = D("2016-03-01")
# NOTE: qa-procedure-phase1.md's Step 7 fixture uses 2015-12-31/2015-11-01, which are
# 61/121 elapsed days before 2016-03-01 (2016 is a leap year), not 60/120. progress.md's
# T4 log records this exact leap-year correction (rows moved to 2016-01-01/2015-11-02).
# We use the corrected dates as source of truth (team-lead direction).
raw = list(exponential_weights([cutoff, D("2016-01-01"), D("2015-11-02")], cutoff, 60))
expect(raw == [1.0, 0.5, 0.25], f"RAW {raw}")
norm = list(normalize_mean_one(raw))
expect(abs(norm[0] - 12/7) < 1e-9 and abs(norm[1] - 6/7) < 1e-9 and abs(norm[2] - 3/7) < 1e-9, f"NORM {norm}")
expect(abs(sum(norm) - 3.0) < 1e-9, "NORM sum 3.0")
expect(abs(effective_n(raw) - 7/3) < 1e-9, f"NEFF {effective_n(raw)}")
u = list(uniform_weights(3))
expect(u == [1.0, 1.0, 1.0] and effective_n(u) == 3.0, "UNIFORM")

try:
    exponential_weights([cutoff], cutoff, 0)
    expect(False, "expected ValueError half_life")
except ValueError as exc:
    expect("half_life_days" in str(exc), "half_life error text")
try:
    exponential_weights([D("2016-03-02")], cutoff, 60)
    expect(False, "expected ValueError future row")
except ValueError as exc:
    expect("after the cutoff" in str(exc), "future row error text")
try:
    normalize_mean_one([0.0, 0.0])
    expect(False, "expected ValueError zero total")
except ValueError as exc:
    expect("zero total" in str(exc), "zero total error text")

if not ok:
    sys.exit(1)
print("WEIGHTS_FIXTURE_OK")
PYEOF
check $? "Step 7 analytic fixture (leap-year-corrected)"

step "Step 8: T5 family weights pytest + F7 suite"
uv run pytest algo-backtest/tests/steps/test_f7_family_weights.py -q -p no:cacheprovider
E8A=$?
uv run pytest algo-backtest/tests/steps/test_f7_meta_learner.py algo-backtest/tests/steps/test_f7_model_io.py algo-backtest/tests/steps/test_training_family_contract.py -q -p no:cacheprovider
E8B=$?
check $((E8A + E8B)) "Step 8 family weights + F7 suite (86 baseline expected for the trio)"

step "Step 9: T5 legacy parity and real effect by hand"
uv run python - <<'PYEOF'
import sys
from datetime import datetime, timedelta, UTC
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily, TrainingRow, WalkForwardSplit, train_meta_learner, family_vector,
)
ok = True
def expect(cond, msg):
    global ok
    if not cond:
        ok = False
        print("MISMATCH:", msg)

def row(i, direction, label):
    return TrainingRow(timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i),
                       features={"trend_direction": direction, "trend_strength": 50.0,
                                 "higher_tf_trend_direction": direction}, label=label)
train = [row(i, 1.0, 1) for i in range(20)] + [row(20 + i, 1.0, 0) for i in range(20)]
val = [row(100, 1.0, 1), row(101, -1.0, 0), row(102, 1.0, 1), row(103, -1.0, 0)]
split = WalkForwardSplit(train=tuple(train), validation=tuple(val), test=())
fams = [FeatureFamily.TREND]
vec = family_vector(FeatureFamily.TREND, train[0].features)
legacy = train_meta_learner(fams, split, random_state=42)
none = train_meta_learner(fams, split, random_state=42, family_weights=None)
ones = train_meta_learner(fams, split, random_state=42, family_weights=[1.0] * 40)
p = lambda m: m.family_models[FeatureFamily.TREND].predict_proba_up(vec)
pl, pn, po = p(legacy), p(none), p(ones)
expect(pl == 0.5 and pn == 0.5 and po == 0.5, f"LEGACY/NONE/ONES {pl},{pn},{po}")

down0 = train_meta_learner(fams, split, random_state=42, family_weights=[1.0] * 20 + [1e-6] * 20)
up0 = train_meta_learner(fams, split, random_state=42, family_weights=[1e-6] * 20 + [1.0] * 20)
expect(p(down0) > 0.99, f"DOWN~0 {p(down0)}")
expect(p(up0) < 0.01, f"UP~0 {p(up0)}")

try:
    train_meta_learner(fams, split, random_state=42, family_weights=[1.0] * 39)
    expect(False, "expected ValueError length mismatch")
except ValueError as exc:
    msg = str(exc)
    expect("family_weights" in msg and "39" in msg and "40" in msg, f"length error text: {msg}")

if not ok:
    sys.exit(1)
print("F7_LEGACY_PARITY_OK")
PYEOF
check $? "Step 9 legacy parity / weighting effect"

step "Step 10: quality gates and no lost tests"
E10=0
uv run ruff check algo-backtest/src/algo_backtest/retraining algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py algo-backtest/tests/steps/test_retraining_ingestion.py algo-backtest/tests/steps/test_retraining_schedule.py algo-backtest/tests/steps/test_retraining_weights.py algo-backtest/tests/steps/test_f7_family_weights.py || E10=1
uv run ruff format --check algo-backtest/src/algo_backtest/retraining algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py || E10=1
uv run mypy --strict algo-backtest/src/algo_backtest/retraining algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py || E10=1
# make lint/type run tree-wide; progress.md's Phase 1 closure documents a fixed
# set of pre-existing, out-of-lane failures (session-2 scripts, bigquery
# scripts, algo-viewer fixture, mutation harness). Only fail Step 10 if a
# Phase 1 path (retraining/ or the F7 diff) shows up in that output.
make lint type > "$TMPDIR/qa19-lint-type.log" 2>&1
LINTTYPE_STATUS=$?
if [ $LINTTYPE_STATUS -ne 0 ]; then
  if grep -qE "retraining/|chain/filters/f7_meta_learner\.py|test_retraining_|test_f7_family_weights" "$TMPDIR/qa19-lint-type.log"; then
    echo "make lint type touches a Phase 1 path (see $TMPDIR/qa19-lint-type.log)"
    E10=1
  else
    echo "make lint type failed (exit $LINTTYPE_STATUS) but only on pre-existing, out-of-lane files (per progress.md Phase 1 closure); not a Phase 1 regression"
  fi
fi
uv run pytest algo-backtest/tests -q --co -p no:cacheprovider | tail -1
uv run pytest algo-backtest/tests -q -p no:cacheprovider | tail -1 || E10=1
check $E10 "Step 10 quality gates"

# Phase 1's frozen boundary commit, pinned explicitly rather than "HEAD": this
# worktree is shared with a concurrent Phase 2 coder (T6+), so HEAD may have
# already moved past Phase 1 by the time this script runs. Steps 11/12 verify
# the Phase 1 slice itself, not whatever else has landed on top of it since.
PHASE1_SHA=2d6a63c

step "Step 11: bookkeeping in the same commits"
cd /tmp/mba-impl-19
E11=0
git log --oneline "ef0111d..$PHASE1_SHA"
grep -n "^- \[x\] T[1-5]" algo-suite/docs/stories/in-progress/19-adaptive-recency-retraining/progress.md || E11=1
grep -n -E "^\| RWT-(01|02|03|04|05|06|07|09|17|18|21|23|24|29) " .specs/features/recency-weighted-retraining/spec.md || E11=1
check $E11 "Step 11 bookkeeping (note: git status --short may be non-empty at run time because this worktree is shared with a concurrent Phase 2 coder; see qa-report)"

step "Step 12: what must NOT have changed (within the Phase 1 boundary $PHASE1_SHA)"
E12=0
git diff --stat "ef0111d..$PHASE1_SHA" -- algo-suite/algo-backtest/src/algo_backtest/engine algo-suite/algo-backtest/src/algo_backtest/wiring.py algo-suite/algo-backtest/src/algo_backtest/strategies.py algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py algo-suite/algo-backtest/src/algo_backtest/run.py algo-suite/algo-backtest/src/algo_backtest/cli.py algo-suite/algo-backtest/src/algo_backtest/training.py algo-suite/algo-backtest/src/algo_backtest/market_signals.py algo-suite/algo-backtest/tests/conftest.py algo-suite/algo-backtest/tests/steps/conftest.py algo-suite/Makefile
SHARED=$(git diff --name-only "ef0111d..$PHASE1_SHA" -- algo-suite/algo-backtest/src/algo_backtest/engine algo-suite/algo-backtest/src/algo_backtest/wiring.py algo-suite/algo-backtest/src/algo_backtest/strategies.py algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py algo-suite/algo-backtest/src/algo_backtest/run.py algo-suite/algo-backtest/src/algo_backtest/cli.py algo-suite/algo-backtest/src/algo_backtest/training.py algo-suite/algo-backtest/src/algo_backtest/market_signals.py algo-suite/algo-backtest/tests/conftest.py algo-suite/algo-backtest/tests/steps/conftest.py algo-suite/Makefile)
[ -z "$SHARED" ] || E12=1
OTHER=$(git diff --name-only "ef0111d..$PHASE1_SHA" -- algo-suite/algo-backtest/tests/features | grep -v -E "retraining_|f7_family_weights")
if [ -n "$OTHER" ]; then echo "$OTHER"; E12=1; else echo "NO OTHER FEATURE CHANGED"; fi
check $E12 "Step 12 no shared file / other feature touched between ef0111d and $PHASE1_SHA"

echo "=================================================="
if [ "$fail" -eq 0 ]; then
  echo "QA PHASE 1: ALL STEPS PASSED"
  exit 0
else
  echo "QA PHASE 1: FAILURES PRESENT"
  exit 1
fi
