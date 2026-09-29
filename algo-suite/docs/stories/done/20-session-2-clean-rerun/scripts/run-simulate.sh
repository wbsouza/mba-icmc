#!/usr/bin/env bash
# Session 2, stage 2: one trading year per cell, BUY and SELL in the same run, then tables and the reproduction check.
set -euo pipefail
SUITE=${SUITE:-/tmp/mba-session2/algo-suite}
T=/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training
JOB=$T/2026-09-28-session-2
export ALGO_DATA_ROOT=$T/2026-09-28-broad-window-h4/data
export PYTHONUNBUFFERED=1 ALGO_BROKER__ADAPTER=oanda OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 LOKY_MAX_CPU_COUNT=4
export LEAN_MAX_CONCURRENT=6 LEAN_CONTAINER_MEM_LIMIT=8g LEAN_CONTAINER_CPUS=4
cd "$SUITE"
exec 9>"$JOB/run-simulate.lock"; flock -n 9 || exit 1
trap 'code=$?; printf "exit_code=%s finished=%s\n" "$code" "$(date -Iseconds)" > "$JOB/exit-status-simulate.txt"' EXIT
stage() { printf '%s %s\n' "$(date -Iseconds)" "$1" | tee "$JOB/status.txt"; }
git -C "$SUITE" rev-parse HEAD > "$JOB/git-revision-simulate.txt"
model_for() { python3 -c "import json,sys; print(json.load(open('$JOB/model-map.json'))[sys.argv[1]])" "$1"; }
run_one() { v=$1; m=$(model_for "$v"); MODEL=""; [ -n "$m" ] && MODEL="--model $JOB/models/$m.json"; uv run algo-backtest run --strategy "$v" --strategies-dir "$JOB/strategies" --symbol EURUSD --from 2016-03-01 --to 2017-02-28 --param cash=10000 $MODEL --timeout 43200 > "$JOB/logs/$v-run.log" 2>&1; echo "$v exit=$?" >> "$JOB/logs/runs-exit.txt"; }
export -f run_one model_for; export JOB
stage "simulate-$(wc -l < "$JOB/variants.txt")-cells-2016-03-01..2017-02-28 (6 slots)"
xargs -P 6 -I{} bash -c 'run_one {}' < "$JOB/variants.txt"
stage tables
{ echo "# Session 2: trading year 2016-03-01..2017-02-28, one \$10,000 account per cell, BUY and SELL in the same run"; echo; echo "Untouched months: Nov 2016–Feb 2017. Win% = closed trades with positive P/L."; echo; python3 "$JOB/monthly_table.py" "$ALGO_DATA_ROOT/runs" $(tr '\n' ' ' < "$JOB/variants.txt"); } > "$JOB/results.md"
python3 "$JOB/compare.py" "$JOB" > "$JOB/reproduction.md" 2> "$JOB/logs/compare.log" || true
stage complete
