"""Materialize a month of canonical Parquet into the durable lean-data store.

Reads the canonical minute `QuoteBar` Parquet for one (instrument, year, month) via
the same `ParquetRepository` algo-transform writes with, and emits LEAN-native
day-zips through `leandata.write_lean_minute`, in the config-resolved data timezone.

The store is built once and reused: re-running is **idempotent and atomic per day** —
each day-zip is written via a temp file + rename (`write_lean_minute`), so a day is
either fully present or absent; days whose zip already exists are skipped, so only
missing days are written. A missing or empty canonical Parquet source is a hard stop
(fail fast), not a silent no-op.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import Instrument
from algo_core.layout import lean_data_dir_for, price_path_for
from algo_core.repository.parquet import ParquetRepository

from algo_backtest.leandata import write_lean_minute


class MaterializeStatus(StrEnum):
    """Outcome of a month materialization."""

    WRITTEN = "written"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class MaterializeResult:
    """What a `materialize_month` call did: which day-zips it wrote, how many it skipped."""

    status: MaterializeStatus
    written: tuple[Path, ...]
    skipped_days: int


def _file_day_stamp(bar: QuoteBar, data_tz: ZoneInfo) -> str:
    """The lean-data file-day (`YYYYMMDD`) for a bar: its START date in the data tz."""
    return bar.timestamp.astimezone(data_tz).strftime("%Y%m%d")


def materialize_month(
    data_root: Path, instrument: Instrument, year: int, month: int, data_tz: ZoneInfo
) -> MaterializeResult:
    """Materialize one month of canonical minute Parquet into lean-data day-zips.

    Raises:
        FileNotFoundError: if there is no canonical Parquet for the month (run
            algo-transform first) — fail fast rather than write an empty store.
    """
    parquet = price_path_for(data_root, instrument, Timeframe.M1.value, year, month)
    repo: ParquetRepository[QuoteBar] = ParquetRepository(QuoteBar, parquet)
    if not repo.exists():
        raise FileNotFoundError(
            f"no canonical Parquet at {parquet}; run algo-transform for "
            f"{instrument.symbol} {year}-{month:02d} before materializing lean-data"
        )

    bars = repo.read_all()
    if not bars:
        raise ValueError(
            f"canonical Parquet at {parquet} is empty; a month partition with no bars is a "
            f"bad upstream artifact, not 'already materialized' — re-run algo-transform for "
            f"{instrument.symbol} {year}-{month:02d}"
        )
    out_dir = lean_data_dir_for(data_root, instrument, "minute")

    # Probe each distinct day-zip once (not once per bar): a month is ~tens of
    # thousands of bars but only ~22 days.
    days = {_file_day_stamp(b, data_tz) for b in bars}
    present_days = {d for d in days if (out_dir / f"{d}_quote.zip").is_file()}
    missing = [b for b in bars if _file_day_stamp(b, data_tz) not in present_days]
    skipped = len(present_days)

    if not missing:
        return MaterializeResult(MaterializeStatus.SKIPPED, (), skipped)
    written = write_lean_minute(data_root, instrument, missing, data_tz)
    return MaterializeResult(MaterializeStatus.WRITTEN, tuple(written), skipped)
