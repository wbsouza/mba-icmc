"""Spike materializer: our minute QuoteBars -> LEAN-native day zips (Task 3a).

THROWAWAY exploratory code — do NOT copy to production.

Encodes the format (Task 2a) and the **END-indexing** convention (Task 2b):
  <lean-data>/forex/<market>/minute/<symbol-lower>/<YYYYMMDD>_quote.zip
    -> <YYYYMMDD>_<symbol>_minute_quote.csv  (comma, no header)
       cols: ms_since_midnight, bidO,bidH,bidL,bidC, bidVol, askO,askH,askL,askC, askVol

**Confirmed (safe to port):** the CSV `ms` is the bar **END** time (not start),
ms=0 ⇒ bar `[23:59 D-1, 00:00 D)`; a day-D file holds bars **ending** in D, so we
group by the END day. `QuoteBar.timestamp` is the bar START (UTC); END = start+1min.

**NOT resolved (do NOT port):** the timezone mapping. The naive UTC→NY conversion
below did **not** yield UTC 1:1 in LEAN (README Task 3b: −4h/−8h offsets); LEAN's
forex file↔algorithm tz conversion is non-trivial and must be re-proved
empirically (config-driven data tz + winter/summer testcontainers tests) in the
real materializer. The hard-coded `America/New_York` here is exploratory only.

Contract (what this spike code does): END-indexed CSV, grouped by END day, in the
spike data tz. Non-contract (real impl must add): config-driven per-market data tz,
validated DST handling, testcontainers verification.

The path suffix `forex/<market>/minute/<sym>` is the central layout builder's.
"""

from __future__ import annotations

import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from algo_core.bars import QuoteBar
from algo_core.instrument import Instrument
from algo_core.layout import lean_data_dir_for

_ANCHOR = Path("/__leanroot__")
_MINUTE = timedelta(minutes=1)
# FIXME(tz): SPIKE-ONLY hard-code — the real materializer must read the per-market
# data tz from config (never hard-code), and this naive UTC->NY conversion does NOT
# yield UTC 1:1 in LEAN (README Task 3b). DO NOT COPY to production.
_SPIKE_DATA_TZ = ZoneInfo("America/New_York")


def lean_minute_relpath(instrument: Instrument) -> Path:
    """The `forex/<market>/minute/<symbol>` suffix, from the central layout builder."""
    return lean_data_dir_for(_ANCHOR, instrument, "minute").relative_to(_ANCHOR / "lean-data")


def _end(bar: QuoteBar) -> datetime:
    """A minute bar's END time in the spike data tz (END-indexing is the confirmed part).

    The `.astimezone` to the spike data tz is the *unresolved* part — LEAN's forex tz
    handling is more involved (README Task 3b); the real impl re-proves it.
    """
    return (bar.timestamp + _MINUTE).astimezone(_SPIKE_DATA_TZ)


def _row(bar: QuoteBar, digits: int) -> str:
    end = _end(bar)
    midnight = end.replace(hour=0, minute=0, second=0, microsecond=0)
    ms = int((end - midnight).total_seconds() * 1000)
    return (
        f"{ms},{bar.bid_open:.{digits}f},{bar.bid_high:.{digits}f},"
        f"{bar.bid_low:.{digits}f},{bar.bid_close:.{digits}f},0,"
        f"{bar.ask_open:.{digits}f},{bar.ask_high:.{digits}f},"
        f"{bar.ask_low:.{digits}f},{bar.ask_close:.{digits}f},0"
    )


def _validate(bar: QuoteBar) -> None:
    if bar.timestamp.tzinfo is None or bar.timestamp.utcoffset() != timedelta(0):
        raise ValueError(f"bar timestamp must be UTC-aware; got {bar.timestamp!r}")
    if bar.timestamp.second or bar.timestamp.microsecond:
        raise ValueError(f"bar {bar.timestamp} is not minute-aligned")


def write_lean_minute_days(
    lean_data_folder: Path, instrument: Instrument, bars: list[QuoteBar]
) -> list[Path]:
    """Write minute bars to LEAN-native per-day zips, grouped by the bar's END day
    in the spike data tz (NY). END-indexing is the confirmed part; the tz is not
    (README Task 3b)."""
    by_day: dict[date, list[QuoteBar]] = defaultdict(list)
    for bar in sorted(bars, key=lambda b: b.timestamp):
        _validate(bar)
        by_day[_end(bar).date()].append(bar)

    symbol = instrument.symbol.lower()
    out_dir = lean_data_folder / lean_minute_relpath(instrument)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for day, day_bars in sorted(by_day.items()):
        stamp = day.strftime("%Y%m%d")
        zip_path = out_dir / f"{stamp}_quote.zip"
        body = "\n".join(_row(b, instrument.digits) for b in day_bars) + "\n"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{stamp}_{symbol}_minute_quote.csv", body)
        written.append(zip_path)
    return written
