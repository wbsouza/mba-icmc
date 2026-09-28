"""One-off migration: backfill ``date_added`` onto existing local GDELT event Parquet.

Context: existing local GDELT event partitions (written before ``GdeltEvent`` gained
``date_added``, see algo_transform/events.py) are missing that column. The already-
materialized BigQuery table (``{project}.{dataset}.events``, from
``bigquery_ctas_export_gdelt_events.py``) has every raw column, DATEADDED included --
so this script only needs to pull (GLOBALEVENTID, DATEADDED) per month and join it onto
the EXISTING local rows by GLOBALEVENTID. This is far cheaper than re-running the full
per-day export: it reads two small columns instead of re-deriving every field.

For each month in the requested window:
  1. Query BigQuery for (GLOBALEVENTID, DATEADDED), scoped to that month's event_date
     range, against the already-materialized table (never the huge public source).
  2. Read the existing local Parquet partition (read-only; the source file is never
     modified).
  3. Join DATEADDED onto each local row by global_event_id. A local row with no
     matching BigQuery id is a real data problem -- this raises immediately rather
     than silently dropping or defaulting the row (fail-fast, per repo convention).
  4. Validate every joined row as a complete ``GdeltEvent`` (now requiring
     ``date_added``) and write it to a NEW path mirroring the source layout under
     ``--output-root`` -- the real data root is never written to by this script.

This script never overwrites the source. Inspect/diff the output, then swap it into
the real data root yourself (manual step, deliberately not automated here).

Prerequisites: same as bigquery_ctas_export_gdelt_events.py -- a service-account key
with BigQuery Data Viewer/Job User on the project, exported as
``GOOGLE_APPLICATION_CREDENTIALS``, and the one-time full table already materialized
(``{project}.{dataset}.events``).

Usage (2016-03 through 2017-02, reading the real local data, writing to a scratch
output root for inspection before any manual swap):
  export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/mba-ai-gdelt-key.json
  uv run --with google-cloud-bigquery python scripts/backfill_gdelt_available_at.py \
      --project mba-ai-509708 --from 2016-03 --to 2017-02 \
      --data-root algo-suite/data \
      --output-root /tmp/gdelt-available-at-backfill

Output layout mirrors the source:
``<output-root>/parquet/events/gdelt/year=Y/month=M/data.parquet``.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from algo_core.logging import configure_logging, get_logger
from algo_core.repository.parquet import ParquetRepository
from algo_transform.events import GdeltEvent
from algo_transform.readers.gdelt import event_path

if TYPE_CHECKING:
    from google.cloud import bigquery

_log = get_logger("backfill_gdelt_available_at")
_QUERY_RETRIES = 5
_QUERY_BACKOFF_S = 5.0


def main() -> None:
    """CLI entry point: per month, query DATEADDED, join onto existing rows, write anew."""
    configure_logging()
    args = _parse_args()
    data_root = Path(args.data_root)
    output_root = Path(args.output_root)
    _log.info(
        "start",
        data_root=str(data_root),
        output_root=str(output_root),
        project=args.project,
        window=f"{args.from_month}..{args.to_month}",
    )

    from google.cloud import bigquery  # deferred: only imported when actually run

    client = bigquery.Client(project=args.project)
    for year, month in _months(args.from_month, args.to_month):
        _backfill_month(client, args.project, args.dataset, data_root, output_root, year, month)
    _log.info("done")


def _backfill_month(
    client: bigquery.Client,
    project: str,
    dataset: str,
    data_root: Path,
    output_root: Path,
    year: int,
    month: int,
) -> None:
    """Join one month's DATEADDED onto its existing local rows and write the result anew."""
    source_path = event_path(data_root, year, month)
    if not source_path.exists():
        raise ValueError(f"missing local partition: {source_path} -- nothing to backfill")

    import pyarrow.parquet as pq

    table = pq.read_table(source_path)  # type: ignore[no-untyped-call]
    rows: list[dict[str, object]] = table.to_pylist()

    date_added_by_id = _query_date_added(client, project, dataset, year, month)

    unmatched = [
        row["global_event_id"] for row in rows if row["global_event_id"] not in date_added_by_id
    ]
    matched = len(rows) - len(unmatched)
    out_path = event_path(output_root, year, month)
    _log.info(
        "month_joined",
        month=f"{year:04d}-{month:02d}",
        rows_read=len(rows),
        rows_matched=matched,
        rows_unmatched=len(unmatched),
        output_path=str(out_path),
    )
    if unmatched:
        raise RuntimeError(
            f"{year:04d}-{month:02d}: {len(unmatched)} local row(s) have no matching "
            f"GLOBALEVENTID in BigQuery (e.g. {unmatched[:5]}) -- real data problem, "
            "not backfilling with a guess."
        )

    events = [
        GdeltEvent(**row, date_added=date_added_by_id[int(row["global_event_id"])])  # type: ignore[call-overload]
        for row in rows
    ]
    ParquetRepository(GdeltEvent, out_path).put(events)
    _log.info(
        "month_written", month=f"{year:04d}-{month:02d}", rows=len(events), path=str(out_path)
    )


def _query_date_added(
    client: bigquery.Client, project: str, dataset: str, year: int, month: int
) -> dict[int, datetime]:
    """Query {GLOBALEVENTID: DATEADDED} for one month from the already-materialized table."""
    last_day = _last_day_of_month(year, month)
    query = f"""
        SELECT GLOBALEVENTID, DATEADDED
        FROM `{project}.{dataset}.events`
        WHERE event_date BETWEEN DATE({year:04d}, {month:02d}, 1)
            AND DATE({year:04d}, {month:02d}, {last_day:02d})
    """
    rows = _query_with_retries(client, query)
    return {int(row["GLOBALEVENTID"]): _parse_yyyymmddhhmmss(str(row["DATEADDED"])) for row in rows}


def _query_with_retries(
    client: bigquery.Client,
    query: str,
    retries: int = _QUERY_RETRIES,
    backoff: float = _QUERY_BACKOFF_S,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Any]:
    """Run a BigQuery query, retrying on transient API/connection errors (linear backoff).

    Matches bigquery_ctas_export_gdelt_events.py's retry helper -- same reasoning: an
    unattended multi-month run hitting one transient blip must not crash outright.
    """
    from google.api_core.exceptions import GoogleAPICallError

    for attempt in range(retries + 1):
        try:
            return list(client.query(query).result())
        except (GoogleAPICallError, ConnectionError, TimeoutError) as exc:
            if attempt == retries:
                raise
            wait = backoff * (attempt + 1)
            _log.warning(
                "query_retry",
                attempt=attempt + 1,
                of_attempts=retries + 1,
                wait_s=wait,
                error=repr(exc),
            )
            sleep(wait)
    raise RuntimeError("unreachable: retry loop always returns or raises")


def _months(from_month: str, to_month: str) -> list[tuple[int, int]]:
    """Return every (year, month) pair in the inclusive window."""
    fy, fm = (int(part) for part in from_month.split("-"))
    ty, tm = (int(part) for part in to_month.split("-"))
    months: list[tuple[int, int]] = []
    y, m = fy, fm
    while (y, m) <= (ty, tm):
        months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return months


def _parse_yyyymmddhhmmss(value: str) -> datetime:
    """Parse a GDELT DATEADDED YYYYMMDDHHMMSS value as UTC (matches the HTTP-path decoder)."""
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=UTC)


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
    parser.add_argument("--dataset", default="gdelt", help="Source BigQuery dataset name")
    parser.add_argument("--data-root", required=True, help="EXISTING local data root (read-only)")
    parser.add_argument(
        "--output-root", required=True, help="NEW output root for the backfilled Parquet"
    )
    args = parser.parse_args()
    if len(args.from_month.split("-")) != 2 or len(args.to_month.split("-")) != 2:
        print("error: --from/--to must be YYYY-MM", file=sys.stderr)
        raise SystemExit(2)
    if Path(args.data_root).resolve() == Path(args.output_root).resolve():
        print("error: --output-root must differ from --data-root", file=sys.stderr)
        raise SystemExit(2)
    return args


if __name__ == "__main__":
    main()
