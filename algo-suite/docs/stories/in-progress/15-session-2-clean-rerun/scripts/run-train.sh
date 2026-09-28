#!/usr/bin/env bash
# Session 2, stage 1: train the twelve models under clean names, calibrate, write the cells.
set -euo pipefail
SUITE=${SUITE:-/tmp/mba-session2/algo-suite}
T=/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training
JOB=$T/2026-09-28-session-2
export ALGO_DATA_ROOT=$T/2026-09-28-broad-window-h4/data
export PYTHONUNBUFFERED=1 ALGO_BROKER__ADAPTER=oanda OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 LOKY_MAX_CPU_COUNT=4
cd "$SUITE"
exec 9>"$JOB/run-train.lock"; flock -n 9 || exit 1
trap 'code=$?; printf "exit_code=%s finished=%s\n" "$code" "$(date -Iseconds)" > "$JOB/exit-status-train.txt"' EXIT
stage() { printf '%s %s\n' "$(date -Iseconds)" "$1" | tee "$JOB/status.txt"; }
git -C "$SUITE" rev-parse HEAD > "$JOB/git-revision-train.txt"
SPLIT="--symbol EURUSD --from 2015-03-02 --train-end 2015-12-31 --validation-end 2016-01-31 --test-end 2016-02-29"
train_one() { m=$1; s=$(python3 -c "import json,sys; print(json.load(open('$JOB/train-map.json'))[sys.argv[1]])" "$m"); script=train_baseline_meta_learner.py; case "$m" in *hybrid*|news-only*) script=train_hybrid_meta_learner.py;; esac; uv run python "algo-backtest/scripts/$script" --strategy "$s" --strategies-dir "$JOB/strategies" $SPLIT --out "$JOB/models/$m.json" > "$JOB/logs/train-$m.log" 2>&1; echo "$m exit=$?" >> "$JOB/logs/train-exit.txt"; }
export -f train_one; export JOB SPLIT
stage train-12-models
python3 -c "import json; print('\n'.join(json.load(open('$JOB/train-map.json'))))" | xargs -P 6 -I{} bash -c 'train_one {}'
sha256sum "$JOB"/models/*.json > "$JOB/model-hashes.txt"
stage calibrate-january-2016
CALIB_JOB="$JOB" uv run python "$JOB/calibrate.py" "$JOB/calibration.json" > "$JOB/logs/calibration.log" 2>&1
CALIB_JOB="$JOB" uv run python "$JOB/calibrate_intensity.py" "$JOB/intensity-calibration.json" >> "$JOB/logs/calibration.log" 2>&1
python3 "$JOB/make_variants.py" "$JOB" >> "$JOB/logs/calibration.log"
while read -r v; do uv run algo-backtest explain-strategy "$v" --strategies-dir "$JOB/strategies" > "$JOB/logs/$v-parameters.txt" 2>&1 || echo "explain $v failed" >> "$JOB/logs/calibration.log"; done < "$JOB/variants.txt"
stage train-complete
