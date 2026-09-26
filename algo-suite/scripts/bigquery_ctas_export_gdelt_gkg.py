"""Bulk materializer: GDELT GKG (quotes/themes/tone) via BigQuery CTAS + native Parquet export.

Standalone exploratory artifact -- NOT wired into the canonical algo-transform/algo-score
pipeline. No GdeltGkg model or path convention exists in algo-transform, and adding one would
be new library code requiring Gherkin/BDD coverage per this repo's CLAUDE.md ("EVERY test is
described in Gherkin -- NON-NEGOTIABLE"), out of scope for a time-boxed pull. Output lands at
`<data_root>/gdelt_gkg/year=Y/month=M/data.parquet` -- deliberately separate from the canonical
`parquet/events/gdelt/...` tree, so it's obviously supplementary context (real GDELT-extracted
quotes, page titles via Extras, themes, a richer tone breakdown) for manual/exploratory review
alongside the Events-derived AvgTone/GoldsteinScale signal, not a tested pipeline input.

Same resilience contract as bigquery_ctas_export_gdelt_events.py:
  1. ONE-TIME full materialization: `CREATE TABLE {project}.{dataset}.gkg AS SELECT ...` scans
     the public `gdelt-bq.gdeltv2.gkg` for the whole window exactly once. If that table already
     exists, it's reused unconditionally -- never re-scanned/re-billed on any later run.
  2. Per batch, on demand: a cheap `CREATE OR REPLACE TABLE ... AS SELECT * FROM
     {project}.{dataset}.gkg WHERE ...` slices the batch's months from OUR OWN small table,
     never the public one again.
  3. Native export (`client.extract_table()`) to GCS, batch-scoped prefix, self-cleaned before
     each export so a retried batch never mixes stale shards from a killed attempt.
  4. Bulk download + local repartition by (year, month), one Parquet file per month, written
     only after a full successful read -- a `.done` marker (written right after) is the source
     of truth for "already materialized", not raw file existence, so a kill mid-write is never
     silently trusted as complete.

GKG's `DATE` column is `YYYYMMDDHHMMSS` (14 digits) -- different shape from Events' `SQLDATE`
(8-digit YYYYMMDD); verified directly against a live query before writing this, not assumed.

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/mba-ai-gdelt-key.json
  uv run --with google-cloud-bigquery --with google-cloud-storage --with pyarrow \
      python scripts/bigquery_ctas_export_gdelt_gkg.py \
      --project mba-ai-509708 --from 2015-02 --to 2024-12

Overrides: --dataset, --bucket, --batch-months (default 12), --rebuild, --keep-gcs, --data-root.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from algo_core import layout
from algo_core.logging import configure_logging, get_logger

_SOURCE_TABLE = "gdelt-bq.gdeltv2.gkg"
_log = get_logger("bigquery_ctas_export_gkg")

_SELECT_COLUMNS = "*"  # every GKG column -- deliberately unfiltered, see module docstring


def main() -> None:
    """CLI entry point: ensure full table -> per-batch extract -> export -> download -> repartition."""
    configure_logging()
    args = _parse_args()
    data_root = Path(args.data_root) if args.data_root else layout.data_root()
    bucket_name = args.bucket or f"{args.project}-gdelt-gkg-export"
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
        prefix = f"gdelt-gkg-{batch[0][0]:04d}{batch[0][1]:02d}-{batch[-1][0]:04d}{batch[-1][1]:02d}"

        stale = _list_export_shards(bq_client, bucket_name, prefix)
        if stale:
            _log.info("stale_shards_found", batch=batch_num, prefix=prefix, count=len(stale))
            _delete_blobs(bucket, stale)

        blob_paths = _export_to_gcs(bq_client, table_ref, bucket_name, prefix)
        _log.info("batch_export_done", batch=batch_num, shards=len(blob_paths))

        with tempfile.TemporaryDirectory(prefix="gdelt-gkg-export-") as tmpdir:
            local_files = _download_shards(bucket, blob_paths, Path(tmpdir))
            written = _repartition_to_local(local_files, data_root, args.rebuild)
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


def _local_path(data_root: Path, year: int, month: int) -> Path:
    """Non-canonical local path for one month's GKG Parquet (deliberately outside `parquet/`)."""
    return data_root / "gdelt_gkg" / f"year={year:04d}" / f"month={month:02d}" / "data.parquet"


def _done_marker(data_root: Path, year: int, month: int) -> Path:
    """Completion marker written only after a month's Parquet write succeeds (see module docstring)."""
    return _local_path(data_root, year, month).parent / ".done"


def _missing_months(data_root: Path, from_month: str, to_month: str, rebuild: bool) -> list[tuple[int, int]]:
    """Return the (year, month) pairs in the window not already materialized locally."""
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


def _ensure_full_table(
    client: "bigquery.Client", project: str, dataset: str, from_month: str, to_month: str
) -> str:  # noqa: F821
    """Materialize the FULL requested window into `{project}.{dataset}.gkg`, once.

    Reused unconditionally if it already exists -- the public source is never re-scanned on a
    rerun/resume/retry. See `bigquery_ctas_export_gdelt_events.py`'s `_ensure_full_table` for the
    identical reasoning; kept as a local copy here rather than a shared import to keep this
    script's blast radius (and review surface) self-contained.
    """
    from google.api_core.exceptions import NotFound

    client.create_dataset(f"{project}.{dataset}", exists_ok=True)
    table_ref = f"{project}.{dataset}.gkg"
    try:
        client.get_table(table_ref)
        _log.info("full_table_reused", table=table_ref, reason="already exists, not re-scanning source")
        return table_ref
    except NotFound:
        pass

    fy, fm = (int(part) for part in from_month.split("-"))
    ty, tm = (int(part) for part in to_month.split("-"))
    # PARTITION BY gkg_date (+ CLUSTER BY `DATE`): the public source (verified this
    # session: gdelt-bq.gdeltv2.gkg is 22TB, no partitioning, no clustering) can't
    # prune a date-scoped query at all, so scanning it once here is unavoidable
    # regardless of approach -- but without partitioning OUR OWN copy too, every later
    # per-batch WHERE query against it would ALSO scan close to the full 22TB
    # (confirmed live: ~19.5TB billed for a single month before this fix, when the
    # copy only had CLUSTER BY -- best-effort block skipping wasn't enough at this
    # scale, plus a 1500-shard export matching the full table's shard count).
    # GKG's DATE is INT64 (YYYYMMDDHHMMSS), not BigQuery's native DATE type, so
    # PARTITION BY can't reference it directly -- gkg_date is a computed DATE column
    # derived from its first 8 digits purely so BigQuery can partition-prune on it.
    # Partition pruning only activates when the WHERE clause filters the
    # partitioning column itself, so `_extract_batch_table` below filters on
    # gkg_date, not the original DATE. `DATE` is also a reserved word in BigQuery
    # SQL, hence the backticks around the source column.
    query = f"""
        CREATE TABLE `{table_ref}`
        PARTITION BY gkg_date
        CLUSTER BY `DATE`
        AS
        SELECT {_SELECT_COLUMNS}, PARSE_DATE('%Y%m%d', SUBSTR(CAST(`DATE` AS STRING), 1, 8)) AS gkg_date
        FROM `{_SOURCE_TABLE}`
        WHERE DATE BETWEEN {fy:04d}{fm:02d}01000000 AND {ty:04d}{tm:02d}{_last_day_of_month(ty, tm):02d}235959
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

    Filters on `gkg_date` (the partitioning column), not the original DATE, so
    BigQuery's partition pruning actually triggers -- see `_ensure_full_table`.
    """
    table_ref = f"{project}.{dataset}.gkg_batch"
    ranges = " OR ".join(
        f"gkg_date BETWEEN DATE({y:04d}, {m:02d}, 1) AND DATE({y:04d}, {m:02d}, {_last_day_of_month(y, m)})"
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
    """Export the batch table to Parquet in GCS (bulk, server-side); return the blob paths."""
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
    """Delete GCS export shards."""
    for blob_path in blob_paths:
        blob = bucket.blob(blob_path)
        if blob.exists():
            blob.delete()


def _repartition_to_local(local_files: list[Path], data_root: Path, rebuild: bool) -> int:
    """Read downloaded shard(s), group rows by (year, month) from DATE, write + mark done.

    Rows are written as-is (no model validation -- this is a raw exploratory artifact, not a
    canonical typed repository). A row whose DATE can't be parsed is quarantined individually,
    same reasoning as the Events script: don't lose an entire batch's rows for one bad record.
    """
    total_rows = sum(pq.read_metadata(p).num_rows for p in local_files)
    _log.info("repartition_start", shards=len(local_files), rows=total_rows)
    by_month: dict[tuple[int, int], list[dict]] = {}
    quarantined = 0
    processed = 0
    start_time = time.monotonic()
    last_date = ""
    logged_day = ""
    for path in local_files:
        table = pq.read_table(path)
        for row in table.to_pylist():
            processed += 1
            try:
                raw_date = str(row["DATE"])
                year, month = int(raw_date[0:4]), int(raw_date[4:6])
            except (KeyError, TypeError, ValueError) as exc:
                quarantined += 1
                _log.warning("quarantined_row", error=str(exc))
                continue
            by_month.setdefault((year, month), []).append(row)
            last_date = raw_date
            day = raw_date[0:8]  # DATE is YYYYMMDDHHMMSS; compare the day part, not the full timestamp
            # At least one line per distinct day seen (see the Events
            # script's identical reasoning), plus the row-count threshold as
            # a safety net for a single very dense day.
            if day != logged_day or processed % 250_000 == 0 or processed == total_rows:
                logged_day = day
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
    for (year, month), rows in sorted(by_month.items()):
        marker = _done_marker(data_root, year, month)
        if marker.exists() and not rebuild:
            _log.info("skipped", month=f"{year:04d}-{month:02d}", reason="already done")
            continue
        out_path = _local_path(data_root, year, month)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows), out_path)
        marker.touch()
        _log.info("written", month=f"{year:04d}-{month:02d}", rows=len(rows), path=str(out_path))
        written += 1
    return written


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
    parser.add_argument("--bucket", default=None, help="GCS bucket name (default: <project>-gdelt-gkg-export)")
    parser.add_argument("--data-root", default=None, help="Override ALGO_DATA_ROOT convention resolution")
    parser.add_argument("--rebuild", action="store_true", help="Re-write months that already exist")
    parser.add_argument("--keep-gcs", action="store_true", help="Don't delete the GCS export shards afterward")
    parser.add_argument(
        "--batch-months",
        type=int,
        default=12,
        help="Months per extract/export/download/repartition batch (resume granularity on a kill)",
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
