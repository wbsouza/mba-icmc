"""Candlestick bars around each entry, aggregated from the M1 bid/ask Parquet.

The M1 partitions (`<bars-root>/parquet/forex/<SYMBOL>/m1/year=YYYY/month=MM/data.parquet`,
`algo_core.layout.price_path`) hold bid and ask OHLC per minute; the mid of each field
is aggregated into the run's `bar_minutes` buckets with the same rule as the engine's
`ClosedBarClock` (UTC day-anchored buckets, only complete buckets emitted). Offset 0 is
the decision bar — the last bar closed at or before the entry time; negative offsets
precede it and positive ones follow it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from algo_backtest.months import months_between
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for

_DAY_MINUTES = 1440
_FIELDS = ("open", "high", "low", "close")


@dataclass(frozen=True)
class Bar:
    """One aggregated mid-price bar (time = bucket start, UTC)."""

    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class EntryBar:
    """One `entry_bars` row: a bar at `offset` from the decision bar."""

    offset: int
    bar: Bar


def _mid_table(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """(minute-of-epoch int64, mid OHLC float64[n, 4]) of one M1 partition."""
    columns = ["timestamp", *(f"{side}_{f}" for side in ("bid", "ask") for f in _FIELDS)]
    table = pq.read_table(path, columns=columns)  # type: ignore[no-untyped-call]
    stamps = table.column("timestamp").to_numpy().astype("datetime64[m]").astype(np.int64)
    mids = [
        (table.column(f"bid_{f}").to_numpy() + table.column(f"ask_{f}").to_numpy()) / 2.0
        for f in _FIELDS
    ]
    return stamps, np.column_stack(mids)


def aggregate(minutes: np.ndarray, mid: np.ndarray, bar_minutes: int) -> list[Bar]:
    """Complete `bar_minutes` buckets of sorted, unique minute rows (partial ones dropped)."""
    if minutes.size == 0:
        return []
    order = np.argsort(minutes, kind="stable")
    minutes, mid = minutes[order], mid[order]
    bucket = minutes // bar_minutes
    starts = np.flatnonzero(np.r_[True, bucket[1:] != bucket[:-1]])
    ends = np.r_[starts[1:], minutes.size]
    bars: list[Bar] = []
    for first, last in zip(starts, ends, strict=True):
        final_minute = bucket[first] * bar_minutes + bar_minutes - 1
        if last - first != bar_minutes or minutes[last - 1] != final_minute:
            continue
        start = datetime.fromtimestamp(int(bucket[first]) * bar_minutes * 60, UTC)
        bars.append(Bar(
            time=start, open=float(mid[first, 0]), high=float(mid[first:last, 1].max()),
            low=float(mid[first:last, 2].min()), close=float(mid[last - 1, 3]),
        ))
    return bars


def window(
    bars: Sequence[Bar], entry: datetime, bar_minutes: int, before: int, after: int
) -> list[EntryBar]:
    """The bars at offsets -before..after around the decision bar of `entry` (see module doc).

    Raises:
        ValueError: no bar closed at or before `entry` (the partitions do not cover it).
    """
    closes = [bar.time.timestamp() + bar_minutes * 60 for bar in bars]
    index = int(np.searchsorted(np.array(closes), entry.timestamp(), side="right")) - 1
    if index < 0:
        raise ValueError(
            f"no {bar_minutes}-minute bar closes at or before {entry.isoformat()}; the M1 "
            "partitions under --bars-root do not cover the entry"
        )
    first, last = max(0, index - before), min(len(bars), index + after + 1)
    return [EntryBar(offset=i - index, bar=bars[i]) for i in range(first, last)]


class BarStore:
    """Loads and aggregates M1 partitions once per (symbol, bar size, month) across runs."""

    def __init__(self, data_root: Path, before: int, after: int) -> None:
        if before < 0 or after < 0:
            raise ValueError("--bars-before and --bars-after must be >= 0")
        self._root = data_root
        self._before, self._after = before, after
        self._cache: dict[tuple[str, int, int, int], list[Bar]] = {}

    def _month(self, symbol: str, bar_minutes: int, year: int, month: int) -> list[Bar]:
        """The aggregated bars of one month partition (cached; fail fast when absent)."""
        key = (symbol, bar_minutes, year, month)
        if key not in self._cache:
            path = price_path_for(self._root, build_instrument(symbol), "m1", year, month)
            if not path.is_file():
                raise FileNotFoundError(
                    f"M1 partition {path} is missing; --bars-root must hold the run's "
                    "months (download/transform them first) or drop --bars-root"
                )
            self._cache[key] = aggregate(*_mid_table(path), bar_minutes)
        return self._cache[key]

    def around(
        self, symbol: str, bar_minutes: int, entry: datetime, run_start: date, run_end: date
    ) -> list[EntryBar]:
        """The entry-window bars for one trade.

        Only months inside the run's own window are read (the run itself proves they
        exist), so an entry near the window's edge gets fewer neighbours, never a guess.
        """
        span = self._after * bar_minutes + self._before * bar_minutes
        days = max(2, span // _DAY_MINUTES * 2 + 3)  # weekends widen the calendar span
        start = max((entry - timedelta(days=days)).date(), run_start)
        end = min((entry + timedelta(days=days)).date(), run_end)
        bars: list[Bar] = []
        for year, month in months_between(start, end):
            bars.extend(self._month(symbol, bar_minutes, year, month))
        return window(bars, entry, bar_minutes, self._before, self._after)

