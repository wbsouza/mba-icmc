#!/usr/bin/env bash
# Bulk-download Dukascopy tick prices — resumable + convergent.
# Default window: 2015-01 .. today (EUR/USD + USD/JPY). The thesis-fixed
# bulk pull (10 full calendar years 2015-01-01 .. 2024-12-31) is recovered
# with `TO=2024-12 scripts/download-prices.sh`.
#
# Idempotent: every hour already on disk (real data OR a 0-byte "no-data" marker for
# weekends/holidays) is skipped, so you can Ctrl-C and re-run freely; each run only fetches
# what is still missing. Long for the full 10y x 2 pairs (~175k hours, ~10-18h).
#
#   Incremental nightly pull:    scripts/download-prices.sh
#   Thesis-fixed bulk pull:      TO=2024-12 scripts/download-prices.sh
#   Keep going until complete:   LOOP=1 scripts/download-prices.sh
#   Detached (survives logout):  nohup LOOP=1 scripts/download-prices.sh > prices-10y.log 2>&1 &
#                                # or: tmux new -s prices  ->  LOOP=1 scripts/download-prices.sh
#   NAS cron (00:00 nightly):    0 0 * * * cd /path/to/algo-suite && scripts/download-prices.sh
#                                # uv + PATH must be present in the cron environment.
#
# Live progress: one line per DAY logs "downloading <source> <SYMBOL YYYY-MM-DD 00h>" to
# stderr as the day starts (per-hour would be too noisy; already-present units skip
# silently, so a resume is quiet until new work). Per-pair summary on stdout.
#
# Status line per pair: written=new  skipped=already-present  missing=empty-at-source
# (weekend/holiday, markered so it is not re-requested)  failed=transient (retried next pass).
# Convergence = a pass with written=0 and failed=0.
#
# Override via env: SYMBOLS, FROM, TO, ALGO_DUKASCOPY_MIN_INTERVAL (throttle s), ALGO_DATA_ROOT,
#                   LOOP (1=repeat), LOOP_SLEEP (seconds between passes).
# FROM / TO accept YYYY-MM or the literal "today" (resolves to the current YYYY-MM).
#
# Nightly cron pattern: TO=today scripts/download-prices.sh
# Dukascopy publishes hourly, so each night this picks up the previous day's new
# hours. To make that work safely, before pass 1 the script wipes 0-byte MISSING
# markers in the CURRENT and PREVIOUS month so any hours that 404'd last night
# (because they had not been published yet) get refetched. Past complete months
# are never touched — their 0-byte markers are real weekend/holiday gaps and
# must stay so they are not re-requested. See `wipe_partial_month_markers`.
set -euo pipefail

# Fixed thesis price interval: full calendar years 2015-01-01 .. 2024-12-31 (Dukascopy is
# month-granular, so 2015-01 starts on Jan 1 2015 and 2024-12 runs through Dec 31 2024).
# Env overrides extend the window (TO=today) for incremental nightly pulls or
# scope a single-month transform/test — they should not shrink the thesis bulk pull.
SYMBOLS=${SYMBOLS:-"EURUSD USDJPY"}
FROM=${FROM:-2015-01}
TO=${TO:-today}

_resolve_month() {
  # Map "today" -> the current YYYY-MM. Anything else passes through unchanged
  # so an explicit YYYY-MM still wins.
  case "$1" in
    today) date +%Y-%m ;;
    *) printf '%s\n' "$1" ;;
  esac
}
FROM=$(_resolve_month "$FROM")
TO=$(_resolve_month "$TO")
export ALGO_DUKASCOPY_MIN_INTERVAL=${ALGO_DUKASCOPY_MIN_INTERVAL:-0.15}
LOOP=${LOOP:-0}
LOOP_SLEEP=${LOOP_SLEEP:-30}

# This script lives in algo-suite/scripts/ ; run from the workspace root (algo-suite/).
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$HERE"
export ALGO_DATA_ROOT=${ALGO_DATA_ROOT:-"$HERE/data"}

PASS_WRITTEN=0
PASS_FAILED=0

wipe_partial_month_markers() {
  # Wipe 0-byte MISSING markers in the in-progress month so hours that 404'd
  # on a prior nightly run (because the provider had not yet published them)
  # get refetched. Also wipe the previous month, which covers the midnight
  # rollover edge case: yesterday's tail hours land in last month's directory.
  #
  # Only acts when the requested window actually reaches the current month —
  # the thesis-fixed `TO=2024-12` mode is left untouched. Past complete months
  # are never touched: their 0-byte markers are real weekend/holiday gaps.
  local now_y now_m now_ym prev_y prev_m wiped=0 dir
  now_y=$(date +%Y); now_m=$(date +%m); now_ym="$now_y-$now_m"
  [[ "$TO" < "$now_ym" ]] && return 0
  prev_y=$(date -d "$now_ym-01 -1 month" +%Y)
  prev_m=$(date -d "$now_ym-01 -1 month" +%m)
  for sym in $SYMBOLS; do
    for ym in "$now_y/$now_m" "$prev_y/$prev_m"; do
      dir="$ALGO_DATA_ROOT/raw/dukascopy/$sym/$ym"
      [ -d "$dir" ] || continue
      while IFS= read -r _f; do wiped=$((wiped + 1)); done < <(
        find "$dir" -name '*.bi5' -size 0 -print -delete 2>/dev/null
      )
    done
  done
  echo "wiped $wiped 0-byte markers in current+previous month (TO=$TO covers current month)"
}

run_pass() {
  PASS_WRITTEN=0
  PASS_FAILED=0
  for sym in $SYMBOLS; do
    # Tolerate a non-zero exit (partial failures): retried on the next pass.
    out=$(uv run algo-download run --source dukascopy --symbol "$sym" --from "$FROM" --to "$TO") || true
    echo "[$sym] $out"
    w=$(printf '%s' "$out" | sed -n 's/.*written=\([0-9]*\).*/\1/p'); w=${w:-0}
    f=$(printf '%s' "$out" | sed -n 's/.*failed=\([0-9]*\).*/\1/p'); f=${f:-0}
    PASS_WRITTEN=$((PASS_WRITTEN + w))
    PASS_FAILED=$((PASS_FAILED + f))
  done
}

echo "download-prices: symbols=[$SYMBOLS] window=$FROM..$TO throttle=${ALGO_DUKASCOPY_MIN_INTERVAL}s loop=$LOOP"
echo "data_root=$ALGO_DATA_ROOT"
echo "start: $(date -Is)"

# One-time wipe of the partial current+previous month's 0-byte markers, so
# hours not yet published by Dukascopy on the prior run get refetched. Past
# complete months are untouched.
wipe_partial_month_markers

pass=0
while :; do
  pass=$((pass + 1))
  echo "=== pass $pass ($(date -Is)) ==="
  run_pass
  echo "pass $pass total: written=$PASS_WRITTEN failed=$PASS_FAILED"
  [ "$LOOP" = "1" ] || break
  if [ "$PASS_WRITTEN" -eq 0 ] && [ "$PASS_FAILED" -eq 0 ]; then
    echo "converged: nothing left to fetch."
    break
  fi
  echo "re-running (LOOP=1) in ${LOOP_SLEEP}s..."
  sleep "$LOOP_SLEEP"
done

echo "done: $(date -Is)"
echo "raw bi5 on disk: $(find "$ALGO_DATA_ROOT/raw/dukascopy" -name '*.bi5' 2>/dev/null | wc -l)"
