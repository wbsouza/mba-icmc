#!/usr/bin/env bash
# Session 2, stage 1b: retrain the two news-only models from the snapshotted packaged configs, then calibrate and write the cells.
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
git -C "$SUITE" rev-parse HEAD > "$JOB/git-revision-train-fix.txt"
for s in baseline hybrid news-only news-only-h4 news-rule news-rule-h4; do cp -r "$SUITE/algo-backtest/src/algo_backtest/strategies/$s" "$JOB/strategies/"; done
SPLIT="--symbol EURUSD --from 2015-03-02 --train-end 2015-12-31 --validation-end 2016-01-31 --test-end 2016-02-29"
stage retrain-news-only-models
for m in news-only-h1 news-only-h4; do
  s=$(python3 -c "import json,sys; print(json.load(open('$JOB/train-map.json'))[sys.argv[1]])" "$m")
  uv run python algo-backtest/scripts/train_hybrid_meta_learner.py --strategy "$s" --strategies-dir "$JOB/strategies" $SPLIT --out "$JOB/models/$m.json" > "$JOB/logs/train-$m.log" 2>&1 &
done
wait
for m in news-only-h1 news-only-h4; do
  if [ -s "$JOB/models/$m.json" ]; then echo "$m exit=0 (retrained)" >> "$JOB/logs/train-exit.txt"; else echo "$m exit=1 (retrain failed)" >> "$JOB/logs/train-exit.txt"; exit 1; fi
done
sha256sum "$JOB"/models/*.json > "$JOB/model-hashes.txt"
stage calibrate-january-2016
CALIB_JOB="$JOB" uv run python "$JOB/calibrate.py" "$JOB/calibration.json" > "$JOB/logs/calibration.log" 2>&1
CALIB_JOB="$JOB" uv run python "$JOB/calibrate_intensity.py" "$JOB/intensity-calibration.json" >> "$JOB/logs/calibration.log" 2>&1
python3 "$JOB/make_variants.py" "$JOB" >> "$JOB/logs/calibration.log"
while read -r v; do
  uv run algo-backtest explain-strategy "$v" --strategies-dir "$JOB/strategies" > "$JOB/logs/$v-parameters.txt" 2>&1 || echo "explain $v failed" >> "$JOB/logs/calibration.log"
done < "$JOB/variants.txt"
stage train-complete
