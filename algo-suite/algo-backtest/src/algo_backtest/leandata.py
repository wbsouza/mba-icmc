"""Materialize canonical UTC QuoteBars into LEAN-native minute day-zips.

The canonical layer (Parquet, features, analysis) is UTC end to end. The materializer
is the single boundary that writes the LEAN-native encoding, so the files are
byte-compatible with real LEAN/OANDA data:

  <root>/lean-data/forex/<market>/minute/<symbol>/<YYYYMMDD>_quote.zip
    -> <YYYYMMDD>_<symbol>_minute_quote.csv  (comma, no header)
       cols: ms_since_midnight, bidO,bidH,bidL,bidC, bidVol, askO,askH,askL,askC, askVol

Encoding contract (START-indexing, **empirically confirmed** against the pinned LEAN
container in tests/integration/test_timezone_roundtrip.py):
  * ms = milliseconds from midnight to the bar's **START**, in the data timezone;
  * the file-day is the bar START's date in the data timezone
    (a full UTC day of forex data therefore runs ms 0 .. 86_340_000 = 00:00 .. 23:59).

LEAN stores forex (OANDA) minute data in **UTC** and delivers each bar to the
algorithm at its EndTime (= start + 1 min), so with the algorithm timezone set to UTC
`self.UtcTime` at delivery equals the bar's UTC end and the round-trip is exact. (The
spike's earlier "END-indexed / America/New_York" inference was wrong on both counts:
NY is LEAN's default *algorithm/exchange* timezone, not the forex *data* timezone, and
QuoteBar.Time/.EndTime inside on_data are exchange-tz-stamped, which is what misled it.)

The data timezone is **injected** (resolved from config per market, never hard-coded
here); for OANDA forex the configured value is UTC, so the conversion is the identity.
"""

from __future__ import annotations

import os
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from algo_core.bars import QuoteBar
from algo_core.instrument import Instrument
from algo_core.layout import lean_data_dir_for


def _check_minute_aligned(bar: QuoteBar) -> None:
    """Reject a bar whose start is not on a whole minute — malformed for minute data.

    Raises:
        ValueError: if the timestamp carries seconds/microseconds (fix upstream
            resampling; emitting it would bake a wrong `ms` into the lean-data file).
    """
    ts = bar.timestamp
    if ts.second or ts.microsecond:
        raise ValueError(
            f"bar {ts.isoformat()} is not minute-aligned (second/microsecond must be 0); "
            f"fix the upstream resampling before materializing lean-data"
        )


def _start_in_tz(bar: QuoteBar, data_tz: ZoneInfo) -> datetime:
    """The bar's START instant (its UTC timestamp) as wall-clock in the data timezone."""
    return bar.timestamp.astimezone(data_tz)


def _ms_since_midnight(start: datetime) -> int:
    """Milliseconds from the data-tz midnight to the bar START (its lean-data `ms`)."""
    midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return int((start - midnight).total_seconds() * 1000)


def _row(bar: QuoteBar, ms: int, digits: int) -> str:
    """One LEAN minute-CSV row: ms-since-data-tz-midnight + bid/ask OHLC + zero volumes."""
    return (
        f"{ms},{bar.bid_open:.{digits}f},{bar.bid_high:.{digits}f},"
        f"{bar.bid_low:.{digits}f},{bar.bid_close:.{digits}f},0,"
        f"{bar.ask_open:.{digits}f},{bar.ask_high:.{digits}f},"
        f"{bar.ask_low:.{digits}f},{bar.ask_close:.{digits}f},0"
    )


def lean_minute_rows(
    bars: list[QuoteBar], data_tz: ZoneInfo, digits: int
) -> dict[date, list[str]]:
    """Group UTC QuoteBars into LEAN minute-CSV rows keyed by file-day (START date, data tz).

    De-duplicates on the **output slot** `(file_day, ms)`, not the input instant, so it
    fails fast on both an exact duplicate minute and the subtler case where a non-UTC
    `data_tz` maps two distinct UTC instants to the same wall-clock slot (the autumn
    DST fall-back hour). For OANDA (`data_tz` = UTC) the slot is never ambiguous.

    Args:
        data_tz: the market's data timezone (config-resolved; UTC for OANDA forex). Bar
            STARTs are expressed as wall-clock in this zone, DST-aware.
        digits: price decimal places for the instrument (formats OHLC).
    """
    by_day: dict[date, list[str]] = defaultdict(list)
    seen: set[tuple[date, int]] = set()
    for bar in sorted(bars, key=lambda b: b.timestamp):
        _check_minute_aligned(bar)
        start = _start_in_tz(bar, data_tz)
        slot = (start.date(), _ms_since_midnight(start))
        if slot in seen:
            raise ValueError(
                f"duplicate lean-data slot day={slot[0].isoformat()} ms={slot[1]} at bar "
                f"{bar.timestamp.isoformat()}; lean-data requires one bar per minute. "
                f"De-duplicate upstream; in a non-UTC data_tz this also flags the DST "
                f"fall-back hour (two UTC instants collapsing to one wall-clock minute)."
            )
        seen.add(slot)
        by_day[slot[0]].append(_row(bar, slot[1], digits))
    return dict(by_day)


def write_lean_minute(
    data_root: Path, instrument: Instrument, bars: list[QuoteBar], data_tz: ZoneInfo
) -> list[Path]:
    """Write minute bars to LEAN-native per-day zips under the instrument's lean-data dir.

    Returns the written zip paths (one per data-tz day with bars).
    """
    out_dir = lean_data_dir_for(data_root, instrument, "minute")
    out_dir.mkdir(parents=True, exist_ok=True)
    symbol = instrument.symbol.lower()

    written: list[Path] = []
    for day, lines in sorted(lean_minute_rows(bars, data_tz, instrument.digits).items()):
        stamp = day.strftime("%Y%m%d")
        zip_path = out_dir / f"{stamp}_quote.zip"
        body = "\n".join(lines) + "\n"
        # Write to a temp file then atomically rename, so a present zip is always
        # complete — an interrupted run never leaves a truncated zip that a later
        # idempotent skip would mistake for a finished day. The tmp name is
        # PID-scoped so two processes racing on the same day (whatever
        # invoked them — two script runs, a direct CLI call, a retry) never
        # share a tmp file: each writes and renames its own, the loser's
        # `.replace()` just overwrites the winner's identical output instead
        # of raising FileNotFoundError on a tmp file the other process
        # already consumed.
        tmp_path = out_dir / f"{stamp}_quote.zip.{os.getpid()}.tmp"
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{stamp}_{symbol}_minute_quote.csv", body)
        tmp_path.replace(zip_path)
        written.append(zip_path)
    return written
