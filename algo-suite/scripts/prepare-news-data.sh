#!/usr/bin/env bash
# One-shot pipeline: GDELT (via BigQuery) + GPR raw payloads -> canonical event
# Parquet -> event features. Materializes the real event data Spec 04e's
# news-context filter is blocked on (see
# docs/stories/in-progress/08-news-event-data-materialization/spec.md).
#
#   Stage 1  bigquery_ctas_export_gdelt_events.py   BigQuery -> parquet/events/gdelt/.../year=Y/month=M/data.parquet
#            (one-time full-window CREATE TABLE into our own BigQuery schema,
#            reused unconditionally on every rerun; per-batch local Parquet +
#            .done markers -- see the script's own module docstring)
#   Stage 2  bigquery_ctas_export_gdelt_gkg.py       BigQuery -> gdelt_gkg/year=Y/month=M/data.parquet
#            (exploratory, non-canonical -- real per-article quotes/themes,
#            not consumed by algo-score; same one-time-table + .done-marker
#            contract as stage 1)
#   Stage 3  bigquery_join_gdelt_events_gkg.py       BigQuery -> gdelt_joined/year=Y/month=M/<date>.parquet
#            (day-granularity join, events.SOURCEURL = gkg.DocumentIdentifier;
#            exploratory evidence trail for the monograph, not consumed by
#            algo-score; ledgered in gdelt_joined/.processed_dates, its own
#            flock at gdelt_joined/.lock)
#   Stage 4  algo-download / algo-transform --source gpr   raw -> parquet/gpr/.../year=Y/month=M/data.parquet
#   Stage 5  algo-score events --kind {gdelt,gpr}     canonical -> parquet/events/{gdelt,gpr}/...
#
# GDELT's original HTTP-per-15-minute-slot path (algo-download/algo-transform
# --source gdelt, ~19.4h throttle floor) and the LM-lexicon sentiment pass on
# it are BOTH superseded (session of 2026-09-25, see spec.md's Assumptions
# table): the plain `gdelt` adapter's Events data has no article-text field,
# so `algo-score --scorer lm --source gdelt` had nothing real to score. GDELT
# event/sentiment signal now comes from AvgTone/GoldsteinScale (Events,
# BigQuery-sourced) plus real GKG quotes/themes for traceability -- no LM
# scoring stage for GDELT in this script.
#
# Resilience & idempotency -- the actual requirement this script is held to:
# run this 1000 times, it keeps whatever was already correctly processed
# intact and only does the work that's still missing, no matter where a
# prior run was interrupted. It's also *reconstructive*: deleting local
# Parquet output and rerunning rebuilds it identically, because the source
# of truth after the first run is the permanent BigQuery tables
# (`{project}.gdelt.events`/`.gkg`, CREATE TABLE not REPLACE -- never
# re-derived from the public source once they exist), not the local files.
# Delete a local output and rerun: same table, same WHERE-bounded query,
# same rows, same (year, month)/(date) grouping -- deterministic rebuild.
# Only deleting the BigQuery tables too would re-derive from the public
# source, which itself only reproduces identically for historical (not the
# most recent few) days -- see spec.md's Reproducibility section.
#   1. Whole-script concurrency: an flock on ALGO_DATA_ROOT (mirrors
#      prepare-lean-data.sh's fix this session) -- two overlapping runs
#      against the same data_root is the exact bug class that cost hours
#      today; this script refuses to repeat it.
#   2. GDELT stages 1-3: each BigQuery script is independently idempotent by
#      design (built/hardened this session) --
#        - the one-time full-table CTAS is skipped entirely once the table
#          exists (`_ensure_full_table` / the join script's tables already
#          being present), so a rerun never re-scans/re-bills the public
#          source;
#        - each batch/day is only counted done via a `.done` marker or the
#          `.processed_dates` ledger, written only AFTER its Parquet write
#          fully succeeds -- a kill mid-write is never silently trusted;
#        - each batch's GCS export shards are self-cleaned before re-export,
#          so a retried batch can't mix stale shards from a killed attempt
#          with fresh ones into duplicated rows;
#        - the join script holds its own flock independent of this
#          wrapper's, so it's safe even if invoked directly, not just
#          through this script.
#   3. GPR (stage 4) and event features (stage 5): each underlying CLI
#      already skips a unit/month whose output file exists (atomic
#      write-then-rename at the Python layer per each tool's own SPEC.md).
#      No sha256-sidecar layer here (unlike prepare-lean-data.sh): exact raw
#      GPR payload paths were not verified before this script was first
#      written (see spec.md's Assumptions table) -- add one once confirmed
#      against a live run, mirroring prepare-lean-data.sh's
#      verify_or_checksum() pattern.
#
#   Pilot month first:            FROM=2020-01 TO=2020-01 scripts/prepare-news-data.sh
#   Full run, backgrounded:       nohup scripts/prepare-news-data.sh > prepare-news-data.log 2>&1 &
#   GDELT only:                   SOURCES=gdelt scripts/prepare-news-data.sh
#   GPR only:                     SOURCES=gpr scripts/prepare-news-data.sh
#   Tighter/looser GDELT batches: BATCH_MONTHS=6 scripts/prepare-news-data.sh
#
# Overrides: SOURCES ("gdelt gpr" by default), FROM, TO (YYYY-MM or "today"),
# PROJECT (BigQuery project ID, default mba-ai-509708), BATCH_MONTHS (default
# 12), ALGO_DATA_ROOT, GOOGLE_APPLICATION_CREDENTIALS.
set -euo pipefail

SOURCES=${SOURCES:-"gdelt gpr"}
FROM=${FROM:-2015-02}
TO=${TO:-today}
PROJECT=${PROJECT:-mba-ai-509708}
BATCH_MONTHS=${BATCH_MONTHS:-12}
export GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-"$HOME/.config/gcloud/mba-ai-gdelt-key.json"}

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

# Serialize the whole script on data_root -- same reasoning as
# prepare-lean-data.sh's lock (added this session after two overlapping runs
# corrupted output via a tmp-file race): two overlapping invocations of this
# script, or of one of its underlying stages run by hand, must never write
# concurrently into the same ALGO_DATA_ROOT.
mkdir -p "$ALGO_DATA_ROOT"
LOCK_FILE="$ALGO_DATA_ROOT/.prepare-news-data.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "prepare-news-data: another instance holds the lock on $LOCK_FILE (data_root=$ALGO_DATA_ROOT) — waiting for it to finish..."
  flock 9
fi

echo "prepare-news-data: sources=[$SOURCES] window=$FROM..$TO project=$PROJECT batch_months=$BATCH_MONTHS"
echo "data_root=$ALGO_DATA_ROOT"
echo "start: $(date -Is)"

DL_WRITTEN=0; DL_SKIPPED=0; DL_FAILED=0
TR_WRITTEN=0; TR_SKIPPED=0; TR_FAILED=0
EV_WRITTEN=0; EV_SKIPPED=0; EV_FAILED=0

# _run_ranged CLI_ARGS... -- tallies WRITTEN SKIPPED FAILED
#   Streams live via tee (not `out=$(...)`) so a long call shows per-unit
#   progress instead of buffering silently, mirroring prepare-lean-data.sh.
_run_ranged() {
  local tally_written="$1" tally_skipped="$2" tally_failed="$3"; shift 3
  local tmp_out out w s f
  echo "  running: $* ($(date -Is))"
  tmp_out=$(mktemp)
  "$@" 2>&1 | tee "$tmp_out" || true
  out=$(cat "$tmp_out")
  rm -f "$tmp_out"
  w=$(printf '%s\n' "$out" | grep -c ': written ') || true
  s=$(printf '%s\n' "$out" | grep -c ': skipped ') || true
  f=$(printf '%s\n' "$out" | grep -cE ': (missing|incomplete|corrupt|failed) ') || true
  eval "$tally_written=\$(( $tally_written + w ))"
  eval "$tally_skipped=\$(( $tally_skipped + s ))"
  eval "$tally_failed=\$(( $tally_failed + f ))"
}

echo
echo "=== stage 1-3: GDELT via BigQuery (Events, GKG, day-join) ($(date -Is)) ==="
if printf '%s\n' "$SOURCES" | grep -qw gdelt; then
  echo "[gdelt] events: ensure full table + per-date local materialize ($FROM..$TO)"
  uv run --with google-cloud-bigquery \
    python scripts/bigquery_ctas_export_gdelt_events.py \
    --project "$PROJECT" --from "$FROM" --to "$TO"

  echo "[gdelt] gkg: ensure full table + per-batch local materialize ($FROM..$TO)"
  uv run --with google-cloud-bigquery --with google-cloud-storage --with pyarrow \
    python scripts/bigquery_ctas_export_gdelt_gkg.py \
    --project "$PROJECT" --from "$FROM" --to "$TO" --batch-months "$BATCH_MONTHS"

  # The join script is day-granular; expand the month window to its first/last
  # calendar day.
  JOIN_FROM="${FROM}-01"
  JOIN_TO=$(date -d "${TO}-01 +1 month -1 day" +%Y-%m-%d)
  echo "[gdelt] join events+gkg, one query per day ($JOIN_FROM..$JOIN_TO)"
  uv run --with google-cloud-bigquery \
    python scripts/bigquery_join_gdelt_events_gkg.py \
    --project "$PROJECT" --from "$JOIN_FROM" --to "$JOIN_TO"
else
  echo "gdelt not in SOURCES, skipping"
fi

echo
echo "=== stage 4: GPR raw -> canonical Parquet ($(date -Is)) ==="
if printf '%s\n' "$SOURCES" | grep -qw gpr; then
  echo "[gpr] whole-window (no date range)"
  _run_ranged DL_WRITTEN DL_SKIPPED DL_FAILED \
    uv run algo-download run --source gpr
  _run_ranged TR_WRITTEN TR_SKIPPED TR_FAILED \
    uv run algo-transform run --source gpr
else
  echo "gpr not in SOURCES, skipping"
fi
echo "stage 4 total: download written=$DL_WRITTEN skipped=$DL_SKIPPED missing/failed=$DL_FAILED"
echo "stage 4 total: transform written=$TR_WRITTEN skipped=$TR_SKIPPED missing/failed=$TR_FAILED"

echo
echo "=== stage 5: event features ($(date -Is)) ==="
for src in $SOURCES; do
  case "$src" in
    gdelt)
      _run_ranged EV_WRITTEN EV_SKIPPED EV_FAILED \
        uv run algo-score events --kind gdelt --from "$FROM" --to "$TO"
      ;;
    gpr)
      # UNCONFIRMED (see spec.md Assumptions): assuming gpr's events pass
      # rejects a date range the same way its download/transform calls do,
      # by analogy with the whole-window pattern used everywhere else for
      # this source. Verify against `algo-score events --help` before the
      # first real run; if it instead requires --from/--to, add them here.
      _run_ranged EV_WRITTEN EV_SKIPPED EV_FAILED \
        uv run algo-score events --kind gpr
      ;;
    *)
      echo "unknown source '$src' (expected: gdelt gpr)" >&2
      exit 2
      ;;
  esac
done
echo "stage 5 total: written=$EV_WRITTEN skipped=$EV_SKIPPED missing/failed=$EV_FAILED"

echo
echo "done: $(date -Is)"
echo "=== algo-transform coverage ==="
uv run algo-transform coverage || true
