"""Join GDELT Events + GKG (one query per day) into local Parquet, day-partitioned.

Both `{project}.{dataset}.events` and `{project}.{dataset}.gkg` are the one-time-materialized
BigQuery tables from bigquery_ctas_export_gdelt_events.py / _gkg.py -- our own small tables, no
public-source re-scan. This script queries them by DAY (not month/batch): a single day's join
against these already-small tables is cheap and fast, finer granularity than the earlier
month-batching, affordable specifically because the expensive one-time pull already happened.

Join key: events.SOURCEURL = gkg.DocumentIdentifier -- empirically verified this session (no
numeric FK exists between GLOBALEVENTID and GKGRECORDID). Many events can join to the same GKG
row (several event rows can share one source article's URL).

Output layout: <data_root>/gdelt_joined/year=Y/month=M/<YYYY-MM-DD>.parquet -- one file per
calendar day, directories created as needed. Deliberately outside the canonical `parquet/`
tree (same reasoning as the GKG puller): no model/path convention exists for this in
algo-transform, and adding one is new library code needing Gherkin coverage, out of scope here.

Idempotency: a single control file, <data_root>/gdelt_joined/.processed_dates (one ISO date per
line), is the source of truth for "already done". Read once at startup to skip completed days;
a date is appended (and fsync'd) only after that day's write fully succeeds -- a day is never
marked done until its data is safely on disk, mirroring the .done-marker pattern in the sibling
scripts but as one ledger file instead of per-directory markers, per this session's request.

Concurrency guard: an exclusive flock on <data_root>/gdelt_joined/.lock, held for the whole run.
Two instances of this script (or a stray retry) racing on the same control file or the same
day's Parquet file is exactly the class of bug this session spent hours chasing in
prepare-lean-data.sh -- this script refuses to repeat it. Non-blocking probe first (clear log
message naming what's holding it), then blocks.

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/mba-ai-gdelt-key.json
  uv run --with google-cloud-bigquery python scripts/bigquery_join_gdelt_events_gkg.py \
      --project mba-ai-509708 --from 2015-02-19 --to 2024-12-31

Overrides: --dataset, --data-root, --rebuild (re-query and overwrite days already in the
control file).
"""

from __future__ import annotations

import argparse
import fcntl
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from algo_core import layout
from algo_core.logging import configure_logging, get_logger

_log = get_logger("bigquery_join_gdelt")


def main() -> None:
    """CLI entry point: lock -> load ledger -> per-day join -> write -> record, one day at a time."""
    configure_logging()
    args = _parse_args()
    data_root = Path(args.data_root) if args.data_root else layout.data_root()
    out_root = data_root / "gdelt_joined"
    out_root.mkdir(parents=True, exist_ok=True)

    lock_path = out_root / ".lock"
    with open(lock_path, "a+") as lock_file:
        _acquire_lock(lock_file, lock_path)

        control_path = out_root / ".processed_dates"
        from_day = date.fromisoformat(args.from_date)
        to_day = date.fromisoformat(args.to_date)
        if from_day > to_day:
            print(f"error: --from {from_day} is after --to {to_day}", file=sys.stderr)
            raise SystemExit(2)

        processed = set() if args.rebuild else _read_processed_dates(control_path)
        all_days = _day_range(from_day, to_day)
        missing_days = [d for d in all_days if d not in processed]
        _log.info(
            "start",
            data_root=str(data_root),
            project=args.project,
            dataset=args.dataset,
            window=f"{from_day}..{to_day}",
            total_days=len(all_days),
            missing_days=len(missing_days),
        )
        if not missing_days:
            _log.info("done", days_written=0, reason="all days already processed")
            return

        from google.cloud import bigquery  # deferred: only imported when actually run

        client = bigquery.Client(project=args.project)
        start_time = time.monotonic()
        written = 0
        empty = 0
        for i, day in enumerate(missing_days, start=1):
            rows = _query_day(client, args.project, args.dataset, day)
            if rows:
                out_path = _day_path(out_root, day)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                pq.write_table(pa.Table.from_pylist(rows), out_path)
                written += 1
                _log.info("written", date=day.isoformat(), rows=len(rows), path=str(out_path))
            else:
                empty += 1
                _log.info("empty", date=day.isoformat(), reason="no joined rows for this day")

            _append_processed_date(control_path, day)

            if i % 30 == 0 or i == len(missing_days):
                _log.info(
                    "progress",
                    days_done=i,
                    of_days=len(missing_days),
                    days_remaining=len(missing_days) - i,
                    elapsed_s=round(time.monotonic() - start_time),
                )

        total_elapsed = time.monotonic() - start_time
        _log.info("done", days_written=written, days_empty=empty, total_elapsed_s=round(total_elapsed))


def _acquire_lock(lock_file, lock_path: Path) -> None:
    """Exclusive, non-blocking probe first (clear log), then block -- see module docstring."""
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        _log.info(
            "waiting_for_lock",
            lock_path=str(lock_path),
            reason="another instance holds it -- waiting for it to finish",
        )
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _day_range(from_day: date, to_day: date) -> list[date]:
    """Inclusive list of every calendar day from `from_day` to `to_day`."""
    days = []
    d = from_day
    while d <= to_day:
        days.append(d)
        d += timedelta(days=1)
    return days


def _day_path(out_root: Path, day: date) -> Path:
    """Local output path for one day's joined Parquet."""
    return out_root / f"year={day.year:04d}" / f"month={day.month:02d}" / f"{day.isoformat()}.parquet"


def _read_processed_dates(control_path: Path) -> set[date]:
    """Read the control file's ledger of already-processed days (empty set if it doesn't exist yet)."""
    if not control_path.exists():
        return set()
    lines = control_path.read_text().splitlines()
    return {date.fromisoformat(line.strip()) for line in lines if line.strip()}


def _append_processed_date(control_path: Path, day: date) -> None:
    """Append one date to the control file, fsync'd -- a day counts as done only after this."""
    with open(control_path, "a") as f:
        f.write(f"{day.isoformat()}\n")
        f.flush()
        os.fsync(f.fileno())


def _query_day(client: "bigquery.Client", project: str, dataset: str, day: date) -> list[dict]:  # noqa: F821
    """Run the events-join-gkg query for one calendar day; return plain dict rows."""
    stamp = int(day.strftime("%Y%m%d"))
    query = f"""
        SELECT e.*, g.*
        FROM `{project}.{dataset}.events` e
        JOIN `{project}.{dataset}.gkg` g
          ON e.SOURCEURL = g.DocumentIdentifier
        WHERE e.SQLDATE = {stamp}
    """
    job = client.query(query)
    return [dict(row.items()) for row in job.result()]


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP project ID (billing target)")
    parser.add_argument("--from", dest="from_date", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--to", dest="to_date", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--dataset", default="gdelt", help="BigQuery dataset holding events/gkg")
    parser.add_argument("--data-root", default=None, help="Override ALGO_DATA_ROOT convention resolution")
    parser.add_argument(
        "--rebuild", action="store_true", help="Ignore the control file and re-query/overwrite every day"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
