#!/usr/bin/env bash
# One-shot pipeline: raw Dukascopy ticks -> canonical Parquet -> LEAN-native
# day-zips, ready for a `run_lean` backtest. Two stages, both idempotent AND
# integrity-checked: run this 100 times and it produces the same files,
# touching only what is missing or has drifted from its checksum.
#
#   Stage 1  algo-transform run --source dukascopy   raw .bi5  -> parquet/forex/<SYM>/m1/year=Y/month=M/data.parquet
#   Stage 2  algo-backtest materialize                parquet   -> lean-data/forex/oanda/minute/<sym>/*.zip
#
# Idempotency has two layers:
#   1. Both underlying CLIs already skip a month/day whose output file exists
#      (atomic write-then-rename at the Python layer, so a file is never
#      partially written on disk).
#   2. This script adds a sha256 sidecar (`<file>.sha256`, sha256sum format)
#      next to every produced file. Before trusting an existing file as
#      "already done" it is verified against its sidecar; a mismatch (NAS
#      bitrot, an interrupted copy, manual edit) deletes the file + sidecar
#      so the underlying CLI regenerates it on this same run, rather than
#      silently trusting stale/corrupt bytes.
#
# Default window: 2015-01 .. today (EUR/USD + USD/JPY), matching
# scripts/download-prices.sh's default raw-pull window.
#
#   Full overnight run:          nohup scripts/prepare-lean-data.sh > prepare-lean-data.log 2>&1 &
#   Thesis-fixed 10y window:     TO=2024-12 scripts/prepare-lean-data.sh
#   Single pair:                 SYMBOLS=EURUSD scripts/prepare-lean-data.sh
#   Verify only, no writes:      VERIFY_ONLY=1 scripts/prepare-lean-data.sh
#
# Overrides: SYMBOLS, FROM, TO (YYYY-MM or "today"), ALGO_DATA_ROOT, VERIFY_ONLY.
set -euo pipefail

SYMBOLS=${SYMBOLS:-"EURUSD USDJPY"}
FROM=${FROM:-2015-01}
TO=${TO:-today}
VERIFY_ONLY=${VERIFY_ONLY:-0}

_resolve_month() {
  case "$1" in
    today) date +%Y-%m ;;
    *) printf '%s\n' "$1" ;;
  esac
}
FROM=$(_resolve_month "$FROM")
TO=$(_resolve_month "$TO")

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$HERE"
export ALGO_DATA_ROOT=${ALGO_DATA_ROOT:-"$HERE/data"}

CHECKSUMMED=0
CORRUPT=0

# verify_or_checksum FILE
#   - absent: no-op, returns 1 (nothing to verify/skip)
#   - present + sidecar matches: returns 0 (verified good, safe to skip)
#   - present + no sidecar yet: writes one now (first time seeing this file,
#     the underlying CLI's atomic write is trusted as the source of truth),
#     returns 0
#   - present + sidecar mismatches: deletes file + sidecar (so the
#     underlying CLI treats it as missing and regenerates it), returns 1
verify_or_checksum() {
  local f="$1" sidecar="$1.sha256" expected actual
  [ -f "$f" ] || return 1
  if [ -f "$sidecar" ]; then
    expected=$(awk '{print $1}' "$sidecar")
    actual=$(sha256sum "$f" | awk '{print $1}')
    if [ "$expected" != "$actual" ]; then
      echo "CORRUPT: $f (sha256 mismatch, on-disk sidecar says $expected, actual is $actual) — removing for regeneration"
      rm -f "$f" "$sidecar"
      CORRUPT=$((CORRUPT + 1))
      return 1
    fi
    return 0
  fi
  sha256sum "$f" | awk '{print $1, "'"$(basename "$f")"'"}' > "$sidecar"
  CHECKSUMMED=$((CHECKSUMMED + 1))
  return 0
}

echo "prepare-lean-data: symbols=[$SYMBOLS] window=$FROM..$TO verify_only=$VERIFY_ONLY"
echo "data_root=$ALGO_DATA_ROOT"
echo "start: $(date -Is)"

STAGE1_WRITTEN=0
STAGE1_SKIPPED=0
STAGE1_FAILED=0
STAGE2_WRITTEN=0
STAGE2_SKIPPED=0
STAGE2_FAILED=0

echo
echo "=== stage 1: dukascopy -> canonical parquet ($(date -Is)) ==="
for sym in $SYMBOLS; do
  # Pre-pass: verify every month's data.parquet already on disk against its
  # sidecar; a mismatch deletes the file so the transform call below sees it
  # as missing and regenerates it instead of trusting corrupt bytes.
  cursor="$FROM-01"
  end="$TO-01"
  while [ "$(date -d "$cursor" +%Y%m)" -le "$(date -d "$end" +%Y%m)" ]; do
    y=$(date -d "$cursor" +%Y); m=$(date -d "$cursor" +%m)
    verify_or_checksum "$ALGO_DATA_ROOT/parquet/forex/$sym/m1/year=$y/month=$m/data.parquet" || true
    cursor=$(date -d "$cursor +1 month" +%Y-%m-01)
  done

  if [ "$VERIFY_ONLY" != "1" ]; then
    # Range-native: one call covers the whole window, one line per month,
    # skips any month whose data.parquet still exists (i.e. passed verify above).
    out=$(uv run algo-transform run --source dukascopy --symbol "$sym" --from "$FROM" --to "$TO") || true
    echo "$out"
    w=$(printf '%s\n' "$out" | grep -c ': written ') || true
    s=$(printf '%s\n' "$out" | grep -c ': skipped ') || true
    f=$(printf '%s\n' "$out" | grep -cE ': (missing|incomplete|corrupt) ') || true
    STAGE1_WRITTEN=$((STAGE1_WRITTEN + w))
    STAGE1_SKIPPED=$((STAGE1_SKIPPED + s))
    STAGE1_FAILED=$((STAGE1_FAILED + f))

    # Post-pass: checksum whatever the transform call just wrote (or
    # regenerated after a corrupt-file removal above).
    cursor="$FROM-01"
    while [ "$(date -d "$cursor" +%Y%m)" -le "$(date -d "$end" +%Y%m)" ]; do
      y=$(date -d "$cursor" +%Y); m=$(date -d "$cursor" +%m)
      verify_or_checksum "$ALGO_DATA_ROOT/parquet/forex/$sym/m1/year=$y/month=$m/data.parquet" || true
      cursor=$(date -d "$cursor +1 month" +%Y-%m-01)
    done
  fi
done
echo "stage 1 total: written=$STAGE1_WRITTEN skipped=$STAGE1_SKIPPED missing/incomplete/corrupt=$STAGE1_FAILED"

echo
echo "=== stage 2: canonical parquet -> lean-data day-zips ($(date -Is)) ==="
for sym in $SYMBOLS; do
  sym_lc=$(printf '%s' "$sym" | tr '[:upper:]' '[:lower:]')
  zip_dir="$ALGO_DATA_ROOT/lean-data/forex/oanda/minute/$sym_lc"

  # Pre-pass: verify every day-zip already on disk for this symbol; a
  # mismatch deletes it so materialize below regenerates just that day.
  if [ -d "$zip_dir" ]; then
    while IFS= read -r -d '' zf; do
      verify_or_checksum "$zf" || true
    done < <(find "$zip_dir" -name '*_quote.zip' -print0)
  fi

  if [ "$VERIFY_ONLY" != "1" ]; then
    cursor="$FROM-01"
    end="$TO-01"
    while [ "$(date -d "$cursor" +%Y%m)" -le "$(date -d "$end" +%Y%m)" ]; do
      y=$(date -d "$cursor" +%Y)
      m=$(date -d "$cursor" +%m)
      parquet_dir="$ALGO_DATA_ROOT/parquet/forex/$sym/m1/year=$y/month=$m"
      if [ -d "$parquet_dir" ]; then
        out=$(uv run algo-backtest materialize --symbol "$sym" --year "$y" --month "$m" 2>&1) || {
          echo "[$sym $y-$m] FAILED: $out"
          STAGE2_FAILED=$((STAGE2_FAILED + 1))
          cursor=$(date -d "$cursor +1 month" +%Y-%m-01)
          continue
        }
        echo "[$sym $y-$m] $out"
        case "$out" in
          written:*) STAGE2_WRITTEN=$((STAGE2_WRITTEN + 1)) ;;
          skipped:*) STAGE2_SKIPPED=$((STAGE2_SKIPPED + 1)) ;;
        esac
      else
        echo "[$sym $y-$m] no parquet partition, skipping (stage 1 reported missing/incomplete for this month)"
      fi
      cursor=$(date -d "$cursor +1 month" +%Y-%m-01)
    done

    # Post-pass: checksum whatever materialize just wrote (or regenerated).
    if [ -d "$zip_dir" ]; then
      while IFS= read -r -d '' zf; do
        verify_or_checksum "$zf" || true
      done < <(find "$zip_dir" -name '*_quote.zip' -print0)
    fi
  fi
done
echo "stage 2 total: written=$STAGE2_WRITTEN skipped=$STAGE2_SKIPPED failed=$STAGE2_FAILED"

echo
echo "done: $(date -Is)"
echo "checksums written this run=$CHECKSUMMED corrupt files removed+regenerated=$CORRUPT"
echo "lean-data day-zips on disk:"
find "$ALGO_DATA_ROOT/lean-data" -name '*_quote.zip' 2>/dev/null | sed -E 's#.*/([^/]+)/[0-9]{8}_quote\.zip#\1#' | sort | uniq -c
