"""Bulk materializer: GDELT Events via BigQuery -- one-time full-table CTAS + cheap per-batch export.

Replaces scripts/bigquery_pull_gdelt_events.py's month-by-month Python row
streaming (the actual bottleneck: ~2m40s+ for a single month via
`job.result()`'s row-by-row iterator) with:

  1. ONE-TIME full materialization: `CREATE TABLE {project}.{dataset}.events AS SELECT *
     FROM gdelt-bq.gdeltv2.events WHERE ...` scans the huge public source exactly once
     for the whole requested window (`_ensure_full_table`). If that table already
     exists, it's reused unconditionally -- the public source is never re-scanned or
     re-billed on any later run, retry, or resume, no matter how many times this
     script is invoked.
  2. Per batch, on demand: a cheap `CREATE OR REPLACE TABLE ... AS SELECT * FROM
     {project}.{dataset}.events WHERE ...` (`_extract_batch_table`) slices the batch's
     months out of that already-materialized table -- reads OUR OWN small table, never
     the public one again.
  3. Native export (`client.extract_table()`) to GCS in Parquet, batch-scoped prefix,
     self-cleaned before each export so a retried batch never mixes stale shards from a
     killed attempt with fresh ones into duplicated rows.
  4. Bulk download + local repartition by (year, month) into the exact canonical layout
     `algo-transform run --source gdelt` already produces (reuses `GdeltEvent`,
     `gdelt.event_path()`, `ParquetRepository` -- same schema/location as the other
     GDELT scripts, so `algo-score` reads it unchanged regardless of path). A month
     only counts as done once its `.done` marker is written, right after the Parquet
     write succeeds -- `serde.write_table` has no atomic tmp-then-rename, so a kill
     mid-write must never be silently trusted via raw file existence alone.

Scope: Events table ONLY (same reasoning as bigquery_pull_gdelt_events.py -- this
codebase has no Mentions/GKG decoder wired into algo-transform). GKG is a separate
script, bigquery_ctas_export_gdelt_gkg.py, deliberately non-canonical (see its docstring).

Prerequisites beyond bigquery_pull_gdelt_events.py's (project, billing, key file): the
`gdelt-pull` service account additionally needs BigQuery Data Editor (CTAS creates a
table) and Storage Admin (creates/writes the export bucket).

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/mba-ai-gdelt-key.json
  uv run --with google-cloud-bigquery --with google-cloud-storage --with pyarrow \
      python scripts/bigquery_ctas_export_gdelt_events.py \
      --project mba-ai-509708 --from 2015-02 --to 2024-12

By default the GCS export files are deleted after the local download (they're
redundant with the local Parquet output); pass --keep-gcs to retain them.
`{project}.{dataset}.events` (the one-time full materialization) is left in place
always -- it IS the durable, reusable copy of the whole window. The per-batch scratch
table (`{dataset}.events_batch`) is overwritten every batch and holds no lasting
meaning between batches.

Resilience: the window's missing months are processed in batches (--batch-months,
default 12) of extract -> export -> download -> repartition -> cleanup, each batch
writing its months to local canonical Parquet (and deleting its own GCS shards) before
the next batch starts. A kill mid-run only loses the *current batch's* cheap extract
and GCS export/download (never the one-time full materialization, since that already
happened) -- `_missing_months` resumes from the first still-missing month next run.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from algo_core import layout
from algo_core.logging import configure_logging, get_logger
from algo_core.repository.parquet import ParquetRepository
from algo_transform.events import GdeltEvent
from algo_transform.readers import gdelt

_SOURCE_TABLE = "gdelt-bq.gdeltv2.events"
_log = get_logger("bigquery_ctas_export")

_SELECT_COLUMNS = "*"  # every Events column -- see _ensure_full_table's docstring


def main() -> None:
    """CLI entry point: ensure full table -> per-batch extract -> export -> download -> repartition."""
    configure_logging()
    args = _parse_args()
    data_root = Path(args.data_root) if args.data_root else layout.data_root()
    bucket_name = args.bucket or f"{args.project}-gdelt-export"
    _log.info(
        "start",
        data_root=str(data_root),
        project=args.project,
        dataset=args.dataset,
        bucket=bucket_name,
        window=f"{args.from_month}..{args.to_month}",
    )

    from google.cloud import bigquery, storage  # deferred: only imported when actually run

    bq_client = bigquery.Client(project=args.project)
    gcs_client = storage.Client(project=args.project)
    start_time = time.monotonic()

    missing = _missing_months(data_root, args.from_month, args.to_month, args.rebuild)
    if not missing:
        _log.info("done", months_written=0, total_elapsed_s=0, reason="all months already materialized")
        return
    _log.info("missing_months", count=len(missing), months=[f"{y:04d}-{m:02d}" for y, m in missing])

    bucket = _ensure_bucket(gcs_client, bucket_name)
    full_table_ref = _ensure_full_table(bq_client, args.project, args.dataset, args.from_month, args.to_month)

    batches = [missing[i : i + args.batch_months] for i in range(0, len(missing), args.batch_months)]
    total_written = 0
    for batch_num, batch in enumerate(batches, start=1):
        batch_label = f"{batch[0][0]:04d}-{batch[0][1]:02d}..{batch[-1][0]:04d}-{batch[-1][1]:02d}"
        _log.info("batch_start", batch=batch_num, of_batches=len(batches), months=batch_label)

        table_ref = _extract_batch_table(bq_client, args.project, args.dataset, full_table_ref, batch)
        prefix = f"gdelt-events-{batch[0][0]:04d}{batch[0][1]:02d}-{batch[-1][0]:04d}{batch[-1][1]:02d}"

        # Self-clean before exporting: a batch prefix is deterministic (same months ->
        # same prefix), so a retry of a batch a previous run was killed mid-way through
        # reuses this exact prefix. Deleting first makes the export idempotent per batch
        # regardless of how the previous attempt on this prefix ended.
        stale = _list_export_shards(bq_client, bucket_name, prefix)
        if stale:
            _log.info("stale_shards_found", batch=batch_num, prefix=prefix, count=len(stale))
            _delete_blobs(bucket, stale)

        blob_paths = _export_to_gcs(bq_client, table_ref, bucket_name, prefix)
        _log.info("batch_export_done", batch=batch_num, shards=len(blob_paths))

        with tempfile.TemporaryDirectory(prefix="gdelt-ctas-export-") as tmpdir:
            local_files = _download_shards(bucket, blob_paths, Path(tmpdir))
            written = _repartition_to_canonical(local_files, data_root, args.rebuild)
            total_written += written

        if not args.keep_gcs:
            _delete_blobs(bucket, blob_paths)

        months_done = sum(len(b) for b in batches[:batch_num])
        _log.info(
            "batch_done",
            batch=batch_num,
            of_batches=len(batches),
            months_written=written,
            months_done=months_done,
            months_remaining=len(missing) - months_done,
            elapsed_s=round(time.monotonic() - start_time),
        )

    total_elapsed = time.monotonic() - start_time
    _log.info("done", months_written=total_written, total_elapsed_s=round(total_elapsed))


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
    is never re-scanned/re-billed on a rerun, resume, or retry. Every batch afterward
    reads this small, already-materialized table on demand instead (see
    `_extract_batch_table`). To force a fresh pull for a changed window, drop the table
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
    # `_extract_batch_table` below filters on event_date, not the original SQLDATE.
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


def _extract_batch_table(
    client: "bigquery.Client", project: str, dataset: str, full_table_ref: str, months: list[tuple[int, int]]
) -> str:  # noqa: F821
    """Slice one batch's months out of the already-materialized full table (cheap, our own table).

    Filters on `event_date` (the partitioning column), not the original SQLDATE, so
    BigQuery's partition pruning actually triggers -- see `_ensure_full_table`.
    """
    table_ref = f"{project}.{dataset}.events_batch"
    ranges = " OR ".join(
        f"event_date BETWEEN DATE({y:04d}, {m:02d}, 1) AND DATE({y:04d}, {m:02d}, {_last_day_of_month(y, m)})"
        for y, m in months
    )
    query = f"""
        CREATE OR REPLACE TABLE `{table_ref}` AS
        SELECT * FROM `{full_table_ref}`
        WHERE {ranges}
    """
    _log.info("batch_extract_running", table=table_ref, months=len(months))
    job = client.query(query)
    job.result()
    _log.info("batch_extract_billed", table=table_ref, bytes_billed=job.total_bytes_billed, job_id=job.job_id)
    return table_ref


def _ensure_bucket(client: "storage.Client", name: str) -> "storage.Bucket":  # noqa: F821
    """Return the export bucket, creating it if it doesn't exist yet."""
    bucket = client.bucket(name)
    if not bucket.exists():
        _log.info("creating_bucket", bucket=name)
        bucket = client.create_bucket(name)
    return bucket


def _export_to_gcs(client: "bigquery.Client", table_ref: str, bucket_name: str, prefix: str) -> list[str]:  # noqa: F821
    """Export the batch table to Parquet in GCS (bulk, server-side); return the blob paths.

    `prefix` is batch-scoped so concurrent/interrupted batches never share shard
    filenames -- a kill mid-batch leaves orphaned shards under that batch's own prefix
    only, never mistaken for another batch's export by `_list_export_shards`.
    """
    from google.cloud import bigquery

    destination_uri = f"gs://{bucket_name}/{prefix}-*.parquet"
    job_config = bigquery.ExtractJobConfig(destination_format=bigquery.DestinationFormat.PARQUET)
    _log.info("export_running", destination=destination_uri)
    job = client.extract_table(table_ref, destination_uri, job_config=job_config)
    job.result()
    return _list_export_shards(client, bucket_name, prefix)


def _list_export_shards(bq_client: "bigquery.Client", bucket_name: str, prefix: str) -> list[str]:  # noqa: F821
    """List the bucket for the export shards matching this batch's prefix."""
    from google.cloud import storage

    storage_client = storage.Client(project=bq_client.project)
    return [blob.name for blob in storage_client.list_blobs(bucket_name, prefix=prefix)]


def _download_shards(bucket: "storage.Bucket", blob_paths: list[str], out_dir: Path) -> list[Path]:  # noqa: F821
    """Bulk-download each export shard once, logging progress every 100 shards."""
    local_files: list[Path] = []
    total = len(blob_paths)
    for i, blob_path in enumerate(blob_paths, start=1):
        blob = bucket.blob(blob_path)
        if not blob.exists():
            continue
        dest = out_dir / Path(blob_path).name
        blob.download_to_filename(str(dest))
        local_files.append(dest)
        if i % 100 == 0 or i == total:
            _log.info("download_progress", shard=i, of_shards=total)
    return local_files


def _delete_blobs(bucket: "storage.Bucket", blob_paths: list[str]) -> None:  # noqa: F821
    """Delete the GCS export shards -- redundant once the local Parquet is written."""
    for blob_path in blob_paths:
        blob = bucket.blob(blob_path)
        if blob.exists():
            blob.delete()


def _repartition_to_canonical(local_files: list[Path], data_root: Path, rebuild: bool) -> int:
    """Read the downloaded shard(s), validate each row into GdeltEvent, group by month, write.

    A row-level parse failure (e.g. a NULL GoldsteinScale -- real GDELT data: some rarer
    CAMEO event codes have no pre-assigned Goldstein mapping, not corruption) is
    quarantined individually -- logged loudly and counted, not silently dropped --
    rather than aborting the whole multi-hundred-thousand-row batch on one bad record.
    """
    total_rows = sum(pq.read_metadata(p).num_rows for p in local_files)
    _log.info("repartition_start", shards=len(local_files), rows=total_rows)
    by_month: dict[tuple[int, int], list[GdeltEvent]] = {}
    quarantined = 0
    processed = 0
    start_time = time.monotonic()
    last_date = ""
    logged_date = ""
    for path in local_files:
        table = pq.read_table(path)
        for row in table.to_pylist():
            processed += 1
            try:
                event = _row_to_event(row)
            except ValueError as exc:
                quarantined += 1
                _log.warning("quarantined_row", error=str(exc))
                continue
            by_month.setdefault((event.event_date.year, event.event_date.month), []).append(event)
            last_date = event.event_date.isoformat()
            # At least one line per distinct date seen (shards aren't
            # necessarily date-ordered, so this isn't monotonic, but it
            # guarantees visibility isn't gated purely on row-count volume --
            # a sparse day can't go silent just because 250k rows haven't
            # accumulated yet), plus the row-count threshold as a safety net
            # for a single very dense date.
            if last_date != logged_date or processed % 250_000 == 0 or processed == total_rows:
                logged_date = last_date
                _log.info(
                    "repartition_progress",
                    rows=processed,
                    of_rows=total_rows,
                    date=last_date,
                    elapsed_s=round(time.monotonic() - start_time),
                )

    if quarantined:
        _log.warning("quarantined_total", rows=quarantined)

    written = 0
    for (year, month), events in sorted(by_month.items()):
        out_path = gdelt.event_path(data_root, year, month)
        marker = _done_marker(data_root, year, month)
        if marker.exists() and not rebuild:
            _log.info("skipped", month=f"{year:04d}-{month:02d}", reason="already done")
            continue
        ParquetRepository(GdeltEvent, out_path).put(events)
        marker.touch()
        _log.info("written", month=f"{year:04d}-{month:02d}", rows=len(events), path=str(out_path))
        written += 1
    return written


def _row_to_event(row: dict) -> GdeltEvent:
    """Map one downloaded Parquet row (BigQuery's raw Events column names) to GdeltEvent."""
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
    parser.add_argument("--bucket", default=None, help="GCS bucket name (default: <project>-gdelt-export)")
    parser.add_argument("--data-root", default=None, help="Override ALGO_DATA_ROOT convention resolution")
    parser.add_argument("--rebuild", action="store_true", help="Re-write months that already exist")
    parser.add_argument("--keep-gcs", action="store_true", help="Don't delete the GCS export shards afterward")
    parser.add_argument(
        "--batch-months",
        type=int,
        default=12,
        help="Months per CTAS/export/download/repartition batch (resume granularity on a kill)",
    )
    args = parser.parse_args()
    if len(args.from_month.split("-")) != 2 or len(args.to_month.split("-")) != 2:
        print("error: --from/--to must be YYYY-MM", file=sys.stderr)
        raise SystemExit(2)
    if args.batch_months < 1:
        print("error: --batch-months must be >= 1", file=sys.stderr)
        raise SystemExit(2)
    return args


if __name__ == "__main__":
    main()
