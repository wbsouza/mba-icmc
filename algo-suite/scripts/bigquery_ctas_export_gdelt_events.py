"""Bulk materializer: GDELT Events via BigQuery -- one-time full-table CTAS + per-date query.

Replaces scripts/bigquery_pull_gdelt_events.py's month-by-month pull against the
huge UNPARTITIONED public source (the actual bottleneck: ~2m40s+ and ~349GB billed
for a single month) with:

  1. ONE-TIME full materialization: `CREATE TABLE {project}.{dataset}.events AS SELECT *
     FROM gdelt-bq.gdeltv2.events WHERE ...`, PARTITION BY event_date, scans the huge
     public source exactly once for the whole requested window (`_ensure_full_table`).
     If that table already exists, it's reused unconditionally -- the public source is
     never re-scanned or re-billed on any later run, retry, or resume, no matter how
     many times this script is invoked. Paid for specifically so every later read is a
     cheap, partition-pruned query, not another full scan.
  2. Per DAY, on demand: a partition-pruned `SELECT * FROM {project}.{dataset}.events
     WHERE event_date = ...` (`_query_month_by_date`) against that already-materialized,
     already-partitioned table -- reads OUR OWN small table, never the public one again,
     cheap regardless of how wide the overall window is. Every date prints a progress
     line the moment its query returns -- no month/year batch can hide which date is in
     flight.
  3. Per-month write into the exact canonical layout `algo-transform run --source gdelt`
     already produces (reuses `GdeltEvent`, `gdelt.event_path()`, `ParquetRepository` --
     same schema/location as the other GDELT scripts, so `algo-score` reads it unchanged
     regardless of path). A month only counts as done once its `.done` marker is
     written, right after the Parquet write succeeds -- `serde.write_table` has no
     atomic tmp-then-rename, so a kill mid-write must never be silently trusted via raw
     file existence alone.

Scope: Events table ONLY (same reasoning as bigquery_pull_gdelt_events.py -- this
codebase has no Mentions/GKG decoder wired into algo-transform). GKG is a separate
script, bigquery_ctas_export_gdelt_gkg.py, deliberately non-canonical (see its docstring).

Prerequisites beyond bigquery_pull_gdelt_events.py's (project, billing, key file): the
`gdelt-pull` service account additionally needs BigQuery Data Editor (CTAS creates a
table).

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/mba-ai-gdelt-key.json
  uv run --with google-cloud-bigquery python scripts/bigquery_ctas_export_gdelt_events.py \
      --project mba-ai-509708 --from 2015-02 --to 2024-12

`{project}.{dataset}.events` (the one-time full materialization) is left in place
always -- it IS the durable, reusable copy of the whole window.

Resilience: the window's missing months are processed one at a time, each queried day
by day before its Parquet write. A kill mid-run only loses the *current month's*
in-progress day queries (never the one-time full materialization, since that already
happened) -- `_missing_months` resumes from the first still-missing month next run. See
docs/stories/in-progress/08-news-event-data-materialization/spec.md's 2026-09-26
amendment for why this replaced the earlier month-batch + GCS export design.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

from algo_core import layout
from algo_core.logging import configure_logging, get_logger
from algo_core.repository.parquet import ParquetRepository
from algo_transform.events import GdeltEvent
from algo_transform.readers import gdelt

_SOURCE_TABLE = "gdelt-bq.gdeltv2.events"
_log = get_logger("bigquery_ctas_export")

_SELECT_COLUMNS = "*"  # every Events column -- see _ensure_full_table's docstring


def main() -> None:
    """CLI entry point: ensure full table -> per-date query -> accumulate -> write per month."""
    configure_logging()
    args = _parse_args()
    data_root = Path(args.data_root) if args.data_root else layout.data_root()
    _log.info(
        "start",
        data_root=str(data_root),
        project=args.project,
        dataset=args.dataset,
        window=f"{args.from_month}..{args.to_month}",
    )

    from google.cloud import bigquery  # deferred: only imported when actually run

    bq_client = bigquery.Client(project=args.project)
    start_time = time.monotonic()

    missing = _missing_months(data_root, args.from_month, args.to_month, args.rebuild)
    if not missing:
        _log.info("done", months_written=0, total_elapsed_s=0, reason="all months already materialized")
        return
    _log.info("missing_months", count=len(missing), months=[f"{y:04d}-{m:02d}" for y, m in missing])

    full_table_ref = _ensure_full_table(bq_client, args.project, args.dataset, args.from_month, args.to_month)

    total_written = 0
    for month_num, (year, month) in enumerate(missing, start=1):
        out_path = gdelt.event_path(data_root, year, month)
        marker = _done_marker(data_root, year, month)
        events, quarantined = _query_month_by_date(bq_client, full_table_ref, year, month, out_path)
        if quarantined:
            _log.warning("quarantined_total", month=f"{year:04d}-{month:02d}", rows=quarantined)

        marker.touch()
        total_written += 1
        _log.info(
            "written",
            month=f"{year:04d}-{month:02d}",
            rows=len(events),
            path=str(out_path),
            months_done=month_num,
            of_months=len(missing),
            months_remaining=len(missing) - month_num,
            elapsed_s=round(time.monotonic() - start_time),
        )

    total_elapsed = time.monotonic() - start_time
    _log.info("done", months_written=total_written, total_elapsed_s=round(total_elapsed))


def _query_month_by_date(
    client: "bigquery.Client", full_table_ref: str, year: int, month: int, out_path: Path
) -> tuple[list[GdeltEvent], int]:  # noqa: F821
    """Query one month DAY BY DAY, writing `out_path` after EVERY day -- never a silent wait.

    Each query filters on `event_date` (the partitioning column) for a single calendar
    day, so it prunes to that day's partition only -- cheap, regardless of how wide the
    overall window is. After each day, the accumulated-so-far events are (re)written to
    `out_path`, so a real, inspectable file exists and grows daily -- not only once the
    whole month finishes. This is safe under the existing resume contract: `.done` is
    only touched by the caller once the full month completes, so `_missing_months` never
    mistakes a partial file for a finished one (same reasoning as `_done_marker`'s
    docstring: raw file existence was never the completion signal, `.done` always was).
    """
    events: list[GdeltEvent] = []
    quarantined = 0
    for day in range(1, _last_day_of_month(year, month) + 1):
        target = date(year, month, day)
        query = f"""
            SELECT * FROM `{full_table_ref}`
            WHERE event_date = DATE({year:04d}, {month:02d}, {day:02d})
        """
        job = client.query(query)
        rows = list(job.result())
        for row in rows:
            try:
                events.append(_row_to_event(dict(row.items())))
            except ValueError as exc:
                quarantined += 1
                _log.warning("quarantined_row", date=target.isoformat(), error=str(exc))
        ParquetRepository(GdeltEvent, out_path).put(events)
        _log.info(
            "day_written",
            date=target.isoformat(),
            rows_today=len(rows),
            rows_saved_so_far=len(events),
            path=str(out_path),
        )
    return events, quarantined


def _missing_months(data_root: Path, from_month: str, to_month: str, rebuild: bool) -> list[tuple[int, int]]:
    """Return the (year, month) pairs in the window that aren't already materialized locally."""
    fy, fm = (int(part) for part in from_month.split("-"))
    ty, tm = (int(part) for part in to_month.split("-"))
    all_months: list[tuple[int, int]] = []
    y, m = fy, fm
    while (y, m) <= (ty, tm):
        all_months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    if rebuild:
        return all_months
    return [(y, m) for y, m in all_months if not _done_marker(data_root, y, m).exists()]


def _done_marker(data_root: Path, year: int, month: int) -> Path:
    """Completion marker for one month, written only after its Parquet write succeeds.

    `serde.write_table` writes the Parquet file directly (no atomic tmp-then-rename), so
    a kill mid-write can leave a truncated file that still `.exists()`. Gating "done" on
    this marker instead of the raw file -- same idea as prepare-lean-data.sh's sha256
    sidecar -- means an interrupted write is never silently trusted: no marker,
    `_missing_months` redoes the month next run.
    """
    return gdelt.event_path(data_root, year, month).parent / ".done"


def _ensure_full_table(
    client: "bigquery.Client", project: str, dataset: str, from_month: str, to_month: str
) -> str:  # noqa: F821
    """Materialize the FULL requested window into `{project}.{dataset}.events`, once.

    This is the one expensive step: it scans the huge public source table
    (`gdelt-bq.gdeltv2.events`) for the whole window in a single CTAS. If the
    destination table already exists, it's reused unconditionally -- the public source
    is never re-scanned/re-billed on a rerun, resume, or retry. Every day afterward
    reads this small, already-partitioned table on demand instead (see
    `_query_month_by_date`). To force a fresh pull for a changed window, drop the table
    yourself first -- this script never drops or replaces it automatically.
    """
    from google.api_core.exceptions import NotFound

    client.create_dataset(f"{project}.{dataset}", exists_ok=True)
    table_ref = f"{project}.{dataset}.events"
    try:
        client.get_table(table_ref)
        _log.info("full_table_reused", table=table_ref, reason="already exists, not re-scanning source")
        return table_ref
    except NotFound:
        pass

    fy, fm = (int(part) for part in from_month.split("-"))
    ty, tm = (int(part) for part in to_month.split("-"))
    # PARTITION BY event_date (+ CLUSTER BY SQLDATE): the public source (verified this
    # session: gdelt-bq.gdeltv2.events is 396GB, no partitioning, no clustering) can't
    # prune a date-scoped query at all, so scanning it once here is unavoidable
    # regardless of approach -- but without partitioning OUR OWN copy too, every later
    # per-batch WHERE query against it would ALSO scan close to the full table
    # (confirmed live: ~349GB billed for a single month before this fix, when the copy
    # only had CLUSTER BY -- best-effort block skipping wasn't enough at this scale).
    # SQLDATE is INT64 (YYYYMMDD), not BigQuery's native DATE type, so PARTITION BY
    # can't reference it directly -- event_date is a computed DATE column derived from
    # it purely so BigQuery can partition-prune on it. Partition pruning only
    # activates when the WHERE clause filters the partitioning column itself, so
    # `_query_month_by_date` below filters on event_date, not the original SQLDATE.
    query = f"""
        CREATE TABLE `{table_ref}`
        PARTITION BY event_date
        CLUSTER BY SQLDATE
        AS
        SELECT {_SELECT_COLUMNS}, PARSE_DATE('%Y%m%d', CAST(SQLDATE AS STRING)) AS event_date
        FROM `{_SOURCE_TABLE}`
        WHERE SQLDATE BETWEEN {fy:04d}{fm:02d}01 AND {ty:04d}{tm:02d}{_last_day_of_month(ty, tm):02d}
    """
    _log.info("full_table_ctas_running", table=table_ref, window=f"{from_month}..{to_month}")
    job = client.query(query)
    job.result()
    _log.info("full_table_ctas_billed", table=table_ref, bytes_billed=job.total_bytes_billed, job_id=job.job_id)
    return table_ref


def _row_to_event(row: dict) -> GdeltEvent:
    """Map one BigQuery row dict (raw Events column names) to GdeltEvent."""
    try:
        return GdeltEvent(
            global_event_id=int(row["GLOBALEVENTID"]),
            event_date=_parse_yyyymmdd(str(row["SQLDATE"])),
            event_code=str(row["EventCode"]),
            goldstein_scale=float(row["GoldsteinScale"]),
            avg_tone=float(row["AvgTone"]),
            actor1_code=str(row["Actor1Code"] or ""),
            actor2_code=str(row["Actor2Code"] or ""),
            num_mentions=int(row["NumMentions"]),
            num_sources=int(row["NumSources"]),
            num_articles=int(row["NumArticles"]),
            source_url=str(row["SOURCEURL"] or ""),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"malformed row (GLOBALEVENTID={row.get('GLOBALEVENTID')}): {exc}") from exc


def _parse_yyyymmdd(value: str) -> date:
    """Parse a GDELT/BigQuery YYYYMMDD date value (matches the HTTP-path decoder)."""
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))


def _last_day_of_month(year: int, month: int) -> int:
    """Return the last calendar day of (year, month), leap-year aware."""
    import calendar

    return calendar.monthrange(year, month)[1]


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP project ID (billing target)")
    parser.add_argument("--from", dest="from_month", required=True, help="YYYY-MM, inclusive")
    parser.add_argument("--to", dest="to_month", required=True, help="YYYY-MM, inclusive")
    parser.add_argument("--dataset", default="gdelt", help="Destination BigQuery dataset name")
    parser.add_argument("--data-root", default=None, help="Override ALGO_DATA_ROOT convention resolution")
    parser.add_argument("--rebuild", action="store_true", help="Re-write months that already exist")
    args = parser.parse_args()
    if len(args.from_month.split("-")) != 2 or len(args.to_month.split("-")) != 2:
        print("error: --from/--to must be YYYY-MM", file=sys.stderr)
        raise SystemExit(2)
    return args


if __name__ == "__main__":
    main()
