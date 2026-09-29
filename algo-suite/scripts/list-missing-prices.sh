#!/usr/bin/env bash
# List Dukascopy hours whose .bi5 is absent on disk (= truly FAILED, not
# weekend/holiday). Read-only: walks the fixed thesis window
# 2015-01-01..2024-12-31 for EURUSD + USDJPY and stats each expected path.
#
# Why not include 0-byte files: they are provider-confirmed "no data here"
# markers (Dukascopy returns 404 for weekend/holiday hours; the adapter
# persists b"" so a resume skips them). Re-downloading them just produces
# the same 404s. See algo-download/src/.../dukascopy/source.py:106 and
# algo-download/src/.../source.py:30 (is_done = path.exists()).
#
# Default output: $ALGO_DATA_ROOT/runs/dukascopy/missing-<ts>.txt
# Retry: scripts/download-prices.sh already refetches missing-file units on
# every pass (LOOP=1 loops until convergence) — no extra step required.
#
# Overrides: SYMBOLS, FROM (YYYY-MM-DD), TO (YYYY-MM-DD), ALGO_DATA_ROOT, OUT.
set -euo pipefail

SYMBOLS=${SYMBOLS:-"EURUSD USDJPY"}
FROM=${FROM:-2015-01-01}
TO=${TO:-2024-12-31}

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$HERE"
DATA_ROOT=${ALGO_DATA_ROOT:-"$HERE/data"}
OUT=${OUT:-"$DATA_ROOT/runs/dukascopy/missing-$(date +%Y%m%dT%H%M%S).txt"}
mkdir -p "$(dirname "$OUT")"

echo "list-missing-prices: symbols=[$SYMBOLS] window=$FROM..$TO"
echo "data_root=$DATA_ROOT"
echo "out=$OUT"

# Single Python process for the whole scan. Uses one os.scandir() per day-dir
# (1 network roundtrip) instead of 24 os.path.exists() calls (24 roundtrips)
# — important because data_root is typically a NAS mount over CIFS.
python3 - "$FROM" "$TO" "$SYMBOLS" "$DATA_ROOT" "$OUT" <<'PY'
import datetime
import os
import sys

from_, to_, syms, root, out = sys.argv[1:]
start = datetime.date.fromisoformat(from_)
end = datetime.date.fromisoformat(to_)
step = datetime.timedelta(days=1)
expected_hours = {f"{h:02d}h.bi5" for h in range(24)}

grand_total = 0
with open(out, "w") as fh:
    for sym in syms.split():
        count = 0
        cursor = start
        while cursor <= end:
            # On-disk layout owned by algo_core.layout.dukascopy_raw_path:
            # 1-indexed month, file name `<HH>h.bi5`. (The provider URL uses
            # 0-indexed month + `_ticks.bi5` — that is a separate concern.)
            day_dir = (
                f"{root}/raw/dukascopy/{sym}/{cursor.year:04d}/{cursor.month:02d}/{cursor.day:02d}"
            )
            try:
                present = {entry.name for entry in os.scandir(day_dir)}
            except FileNotFoundError:
                present = set()
            missing_here = expected_hours - present
            for fname in sorted(missing_here):
                hour = fname[:2]  # "HHh.bi5" → "HH"
                fh.write(
                    f"{sym} {cursor.year:04d}-{cursor.month:02d}-{cursor.day:02d} {hour}h\n"
                )
            count += len(missing_here)
            cursor += step
        print(f"[{sym}] missing={count}")
        grand_total += count
print(f"total missing (no file on disk) = {grand_total}")
PY

echo "list -> $OUT"
echo
echo "To refetch them, the existing pipeline already does it:"
echo "  LOOP=1 scripts/download-prices.sh    # loops until written=0 failed=0"
echo "Missing-file units are automatically retried; 0-byte markers (weekend/"
echo "holiday) are correctly skipped."
