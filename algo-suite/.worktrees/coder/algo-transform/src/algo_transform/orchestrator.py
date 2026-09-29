"""Transform one month of raw Dukascopy ticks into a minute QuoteBar partition.

Thin: read ticks (reader), resample (pure), write (Repository). The completeness
gate is what keeps the incremental hourly download consistent with the monthly
Parquet: a month is written **only when complete**, so a half-downloaded month is
never frozen as a partial partition, and an existing partition (always written
from a complete month) is skipped unless ``rebuild``.
"""

from __future__ import annotations

from pathlib import Path

from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import Instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository

from algo_transform.decoders.bi5 import DecodeError
from algo_transform.events import GdeltEvent, GprEvent
from algo_transform.readers import gdelt, gpr
from algo_transform.readers.dukascopy import is_month_complete, load_ticks
from algo_transform.resample import resample
from algo_transform.result import TransformReport, TransformStatus


def transform_month(
    data_root: Path,
    instrument: Instrument,
    year: int,
    month: int,
    *,
    timeframe: Timeframe = Timeframe.M1,
    rebuild: bool = False,
) -> TransformReport:
    """Decode, resample to ``timeframe`` and write one month; gated by completeness."""
    repo: ParquetRepository[QuoteBar] = ParquetRepository(
        QuoteBar, price_path_for(data_root, instrument, timeframe.value, year, month)
    )

    def report(
        status: TransformStatus, paths: tuple[str, ...] = (), **counts: int
    ) -> TransformReport:
        return TransformReport(
            symbol=instrument.symbol, year=year, month=month, status=status, paths=paths, **counts
        )

    if repo.exists() and not rebuild:
        return report(TransformStatus.SKIPPED)
    if not is_month_complete(data_root, instrument.symbol, year, month):
        return report(TransformStatus.INCOMPLETE)
    loaded = load_ticks(data_root, instrument, year, month)
    if loaded.quarantined:
        # A corrupt raw hour would truncate the month silently; refuse to write it.
        # Re-download the quarantined files (logged by the reader) and re-run.
        return report(
            TransformStatus.CORRUPT,
            quarantined=len(loaded.quarantined),
            paths=tuple(str(path) for path in loaded.quarantined),
        )
    bars = resample(loaded.ticks, timeframe)
    repo.put(bars)
    return report(TransformStatus.WRITTEN, ticks=len(loaded.ticks), bars=len(bars))


def transform_gdelt_month(
    data_root: Path, year: int, month: int, *, rebuild: bool = False
) -> TransformReport:
    """Decode and write one complete GDELT Events month."""
    repo: ParquetRepository[GdeltEvent] = ParquetRepository(
        GdeltEvent, gdelt.event_path(data_root, year, month)
    )

    def report(
        status: TransformStatus, paths: tuple[str, ...] = (), **counts: int
    ) -> TransformReport:
        return TransformReport(
            symbol="gdelt", year=year, month=month, status=status, paths=paths, **counts
        )

    if repo.exists() and not rebuild:
        return report(TransformStatus.SKIPPED)
    if not gdelt.is_month_complete(data_root, year, month):
        return report(TransformStatus.INCOMPLETE)
    loaded = gdelt.load_events(data_root, year, month)
    if loaded.quarantined:
        return report(
            TransformStatus.CORRUPT,
            quarantined=len(loaded.quarantined),
            paths=tuple(str(path) for path in loaded.quarantined),
        )
    repo.put(loaded.events)
    return report(TransformStatus.WRITTEN, events=len(loaded.events))


def transform_gpr(data_root: Path, *, rebuild: bool = False) -> TransformReport:
    """Decode and write the whole-window GPR event dataset."""
    repo: ParquetRepository[GprEvent] = ParquetRepository(GprEvent, gpr.event_path(data_root))
    if not gpr.raw_path(data_root).exists():
        return TransformReport(symbol="gpr", year=0, month=0, status=TransformStatus.MISSING)
    if repo.exists() and not rebuild:
        return TransformReport(symbol="gpr", year=0, month=0, status=TransformStatus.SKIPPED)
    try:
        loaded = gpr.load_events(data_root)
    except DecodeError:
        return TransformReport(symbol="gpr", year=0, month=0, status=TransformStatus.CORRUPT)
    repo.put(loaded.rows)
    return TransformReport(
        symbol="gpr", year=0, month=0, status=TransformStatus.WRITTEN, events=len(loaded.rows)
    )
