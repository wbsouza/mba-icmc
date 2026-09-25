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
#   Skip checksum sidecars:      CHECKSUM=0 scripts/prepare-lean-data.sh
#
# Overrides: SYMBOLS, FROM, TO (YYYY-MM or "today"), ALGO_DATA_ROOT, VERIFY_ONLY,
# CHECKSUM (1 by default -- sha256-verifies every already-done file every run,
# same integrity contract as the original design; set CHECKSUM=0 to skip it
# when you specifically want a fast pass, e.g. a quick pilot-month check).
set -euo pipefail

SYMBOLS=${SYMBOLS:-"EURUSD USDJPY"}
FROM=${FROM:-2015-01}
TO=${TO:-today}
VERIFY_ONLY=${VERIFY_ONLY:-0}
CHECKSUM=${CHECKSUM:-1}

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

# Serialize on data_root: two concurrent runs against the same ALGO_DATA_ROOT
# race on the tmp-file-then-rename in algo_backtest.leandata.write_lean_minute
# — the loser's tmp file has already been consumed by the winner's rename,
# raising an unhandled FileNotFoundError and failing that whole month.
#
# Scope of this guarantee: flock() reliably coordinates processes on the
# same host always. Cross-host (two different machines both mounting
# ALGO_DATA_ROOT from the same NAS) depends entirely on the mount's
# transport and options: verified against this workstation's actual mount
# (//10.1.1.180/homes, CIFS vers=3.0, no `nobrl`) -- without `nobrl`,
# cifs.ko forwards flock() as an SMB2/3 byte-range lock the server
# arbitrates across clients, so cross-host locking DOES work here today.
# It is fragile, not guaranteed: mount with `nobrl`, an older SMB dialect,
# or NFSv3 without lockd, and flock silently degrades to client-local-only
# locking with no error -- the exact race this fix targets would return
# with no warning. The leandata.py PID-scoped tmp filename remains the real
# safety net that holds regardless of mount options (see
# write_lean_minute's docstring); this lock is a second, mount-dependent
# layer on top of it, not a replacement.
# Fail fast if the mount can't actually guarantee locking, rather than
# silently trusting a lock that might not exclude anything (see the scope
# note above) -- per this repo's own convention (CLAUDE.md: "Fail fast...
# raise immediately with a clear message... how to fix it"). Only checked
# for network filesystems; a local disk has no cross-host concern to begin
# with.
_check_lock_reliable() {
  local path="$1" mnt fstype opts
  mnt=$(df --output=target "$path" 2>/dev/null | tail -1)
  [ -n "$mnt" ] || return 0
  fstype=$(findmnt -no FSTYPE "$mnt" 2>/dev/null) || return 0
  opts=$(findmnt -no OPTIONS "$mnt" 2>/dev/null) || return 0
  case "$fstype" in
    cifs|smb3)
      if printf '%s\n' "$opts" | grep -qw nobrl; then
        echo "prepare-lean-data: ALGO_DATA_ROOT ($path) is mounted with locking disabled (nobrl) — flock() cannot coordinate across hosts on this mount, so the concurrent-write race this lock exists to prevent can reoccur silently. Remount without nobrl, or point ALGO_DATA_ROOT at a mount that supports real byte-range locking." >&2
        exit 1
      fi
      ;;
    nfs|nfs4)
      if printf '%s\n' "$opts" | grep -qwE 'nolock|local_lock'; then
        echo "prepare-lean-data: ALGO_DATA_ROOT ($path) is mounted with NFS locking disabled (nolock/local_lock) — flock() cannot coordinate across hosts on this mount, so the concurrent-write race this lock exists to prevent can reoccur silently. Remount with real NFS locking enabled, or point ALGO_DATA_ROOT at a mount that supports it." >&2
        exit 1
      fi
      ;;
  esac
}

mkdir -p "$ALGO_DATA_ROOT"
_check_lock_reliable "$ALGO_DATA_ROOT"
LOCK_FILE="$ALGO_DATA_ROOT/.prepare-lean-data.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "prepare-lean-data: another instance holds the lock on $LOCK_FILE (data_root=$ALGO_DATA_ROOT) — waiting for it to finish..."
  flock 9
fi

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

# _checksum_forex_range SYM FROM TO -- verify/checksum every month's data.parquet
# in range. No-op unless CHECKSUM=1 (see header).
_checksum_forex_range() {
  [ "$CHECKSUM" = "1" ] || return 0
  local sym="$1" cursor="$2-01" end="$3-01"
  while [ "$(date -d "$cursor" +%Y%m)" -le "$(date -d "$end" +%Y%m)" ]; do
    local y m; y=$(date -d "$cursor" +%Y); m=$(date -d "$cursor" +%m)
    verify_or_checksum "$ALGO_DATA_ROOT/parquet/forex/$sym/m1/year=$y/month=$m/data.parquet" || true
    cursor=$(date -d "$cursor +1 month" +%Y-%m-01)
  done
}

# _checksum_lean_zips ZIP_DIR -- verify/checksum every day-zip in ZIP_DIR.
# No-op unless CHECKSUM=1 (see header).
_checksum_lean_zips() {
  [ "$CHECKSUM" = "1" ] || return 0
  local dir="$1"
  [ -d "$dir" ] || return 0
  while IFS= read -r -d '' zf; do
    verify_or_checksum "$zf" || true
  done < <(find "$dir" -name '*_quote.zip' -print0)
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
  _checksum_forex_range "$sym" "$FROM" "$TO"

  if [ "$VERIFY_ONLY" != "1" ]; then
    # Range-native: one call covers the whole window, one line per month,
    # skips any month whose data.parquet still exists (i.e. passed verify above).
    # Streamed via tee (not `out=$(...)`) so each month's line is visible live
    # instead of buffering silently for the whole multi-year call.
    echo "[$sym] starting range $FROM..$TO ($(date -Is))"
    tmp_out=$(mktemp)
    uv run algo-transform run --source dukascopy --symbol "$sym" --from "$FROM" --to "$TO" 2>&1 | tee "$tmp_out" || true
    out=$(cat "$tmp_out")
    rm -f "$tmp_out"
    w=$(printf '%s\n' "$out" | grep -c ': written ') || true
    s=$(printf '%s\n' "$out" | grep -c ': skipped ') || true
    f=$(printf '%s\n' "$out" | grep -cE ': (missing|incomplete|corrupt) ') || true
    STAGE1_WRITTEN=$((STAGE1_WRITTEN + w))
    STAGE1_SKIPPED=$((STAGE1_SKIPPED + s))
    STAGE1_FAILED=$((STAGE1_FAILED + f))

    _checksum_forex_range "$sym" "$FROM" "$TO"
  fi
done
echo "stage 1 total: written=$STAGE1_WRITTEN skipped=$STAGE1_SKIPPED missing/incomplete/corrupt=$STAGE1_FAILED"

echo
echo "=== stage 2: canonical parquet -> lean-data day-zips ($(date -Is)) ==="
for sym in $SYMBOLS; do
  sym_lc=$(printf '%s' "$sym" | tr '[:upper:]' '[:lower:]')
  zip_dir="$ALGO_DATA_ROOT/lean-data/forex/oanda/minute/$sym_lc"

  _checksum_lean_zips "$zip_dir"

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

    _checksum_lean_zips "$zip_dir"
  fi
done
echo "stage 2 total: written=$STAGE2_WRITTEN skipped=$STAGE2_SKIPPED failed=$STAGE2_FAILED"

echo
echo "done: $(date -Is)"
echo "checksums written this run=$CHECKSUMMED corrupt files removed+regenerated=$CORRUPT"
echo "lean-data day-zips on disk:"
find "$ALGO_DATA_ROOT/lean-data" -name '*_quote.zip' 2>/dev/null | sed -E 's#.*/([^/]+)/[0-9]{8}_quote\.zip#\1#' | sort | uniq -c
