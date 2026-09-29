"""Horizon unit re-derivation — normalized returns versus true price pips (story 21, T8).

Read-only re-derivation tool for the frozen session-2 H1 decision archive
(`docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md`,
spec CC-25, CC-26). That archive's forward-return statistic is a *normalized*
return, `(close[t+k]/close[t]-1)/1e-4`, not an EUR/USD price change in pips. This
tool joins archived per-decision rows against independently, timestamp-matched
source close prices (exact UTC minute) and reports both units side by side —
the normalized-return pips and the true price pips, `(close[t+k]-close[t])/0.0001`
— so a reader can no longer conflate them.

It never edits, truncates, reorders or reruns the archive (CC-26) and does not
redo the PR #87 outlier analysis; it only checks the archive is still there. It
writes only to a new, caller-specified output path — never the archive's own.

**Input contract** for a real run: `--decisions` is a Parquet file of columns
`decision_time` (UTC timestamp) and `archived_close` (float) — the frozen
per-decision rows already in the archive; `--source` is a Parquet file of
columns `close_time` (UTC timestamp) and `close` (float) — an independently
sourced close series covering (at least) every decision's own bar and its
horizon bar. Both are required for a real run; this tool never fabricates a
result from a partial or missing source.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_PIP = 0.0001
_TOOL = "rederive_horizon"
OK, MISSING_FUTURE_HORIZON, MISSING_PRICE = "ok", "missing_future_horizon", "missing_price"


def _require_utc(value: datetime, *, what: str) -> None:
    """Fail fast on a naive or non-UTC datetime, naming which time it was."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{_TOOL}: {what} must be timezone-aware UTC, got {value!r}")


def _clock_label(clock_minutes: int) -> str:
    """A human label for a signal-bar clock: "H1" for 60, "H4" for 240, else minutes."""
    return {60: "H1", 240: "H4"}.get(clock_minutes, f"{clock_minutes}-minute")


@dataclass(frozen=True)
class ArchivedDecision:
    """One frozen archive row: the decision's own timestamp and its recorded close."""

    decision_time: datetime
    archived_close: float


@dataclass(frozen=True)
class SourceCloseSeries:
    """An independently sourced close series, sparse and with a known coverage boundary.

    A lookup beyond ``series_end`` is a future-horizon overrun (the source series ends
    before that bar); a lookup at or before ``series_end`` but absent from ``closes`` is
    a gap inside the covered range. These are deliberately distinct outcomes (CC-25).
    """

    closes: Mapping[datetime, float]
    series_end: datetime

    def get(self, at: datetime) -> tuple[float | None, str | None]:
        """The close at `at`, or `(None, status)` naming why it is unavailable."""
        if at in self.closes:
            return self.closes[at], None
        if at > self.series_end:
            return None, MISSING_FUTURE_HORIZON
        return None, MISSING_PRICE


@dataclass(frozen=True)
class RederivedRow:
    """One re-derived row: both pip units side by side, or an explicit unavailable status."""

    decision_time: datetime
    archived_close: float
    normalized_return_pips: float | None
    price_pips: float | None
    unit_status: str

    def as_mapping(self) -> dict[str, Any]:
        """The row as plain JSON-safe values."""
        return {
            "decision_time": self.decision_time.isoformat(),
            "archived_close": self.archived_close,
            "normalized_return_pips": self.normalized_return_pips,
            "price_pips": self.price_pips,
            "unit_status": self.unit_status,
        }


def _check_no_ambiguous_duplicates(decisions: Sequence[ArchivedDecision]) -> None:
    """Fail fast when the same decision timestamp carries two different archived closes."""
    seen: dict[datetime, float] = {}
    for decision in decisions:
        prior = seen.get(decision.decision_time)
        if prior is not None and prior != decision.archived_close:
            raise ValueError(
                f"{_TOOL}: duplicate decision timestamp {decision.decision_time.isoformat()} "
                "with different archived closes"
            )
        seen[decision.decision_time] = decision.archived_close


def _row(decision: ArchivedDecision, source: SourceCloseSeries, horizon: timedelta) -> RederivedRow:
    """One decision's re-derived row: both closes come from `source`, never the archive."""
    close_t, status_t = source.get(decision.decision_time)
    close_tk, status_tk = source.get(decision.decision_time + horizon)
    status = status_t or status_tk
    if status is not None or close_t is None or close_tk is None:
        return RederivedRow(
            decision_time=decision.decision_time,
            archived_close=decision.archived_close,
            normalized_return_pips=None,
            price_pips=None,
            unit_status=status or MISSING_PRICE,
        )
    return RederivedRow(
        decision_time=decision.decision_time,
        archived_close=decision.archived_close,
        normalized_return_pips=(close_tk / close_t - 1) / 1e-4,
        price_pips=(close_tk - close_t) / _PIP,
        unit_status=OK,
    )


def rederive_horizon(
    decisions: Sequence[ArchivedDecision],
    source: SourceCloseSeries,
    *,
    horizon_bars: int = 4,
    clock_minutes: int = 60,
) -> list[RederivedRow]:
    """Re-derive every decision's normalized-return and price-pip units from `source`.

    Raises:
        ValueError: a decision time is naive, off the clock grid, or a duplicate
            timestamp carries two different archived closes.
    """
    _check_no_ambiguous_duplicates(decisions)
    horizon = timedelta(minutes=clock_minutes * horizon_bars)
    rows: list[RederivedRow] = []
    for decision in decisions:
        _require_utc(decision.decision_time, what="decision time")
        if (decision.decision_time - _EPOCH) % timedelta(minutes=clock_minutes) != timedelta(0):
            raise ValueError(
                f"{_TOOL}: decision at {decision.decision_time.isoformat()} is not on the "
                f"{_clock_label(clock_minutes)} minute grid"
            )
        rows.append(_row(decision, source, horizon))
    return rows


def rederive_and_write(
    *,
    archive_path: Path,
    decisions: Sequence[ArchivedDecision],
    source: SourceCloseSeries,
    output_path: Path | None,
    horizon_bars: int = 4,
    clock_minutes: int = 60,
) -> list[RederivedRow]:
    """`rederive_horizon`, written as JSON to `output_path`; never touches `archive_path`.

    Raises:
        ValueError: `output_path` is absent or equals `archive_path`, or a
            `rederive_horizon` validation fails.
    """
    if output_path is None:
        raise ValueError(f"{_TOOL}: an explicit output path is required — pass --out <path>")
    if output_path.resolve() == archive_path.resolve():
        raise ValueError(
            f"{_TOOL}: output path {output_path} must not overwrite the frozen archive "
            f"{archive_path} — choose a new path"
        )
    rows = rederive_horizon(
        decisions, source, horizon_bars=horizon_bars, clock_minutes=clock_minutes
    )
    output_path.write_text(json.dumps([row.as_mapping() for row in rows], indent=2))
    return rows


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point: `--archive`, `--out`, plus the real-run `--decisions`/`--source`.

    Raises:
        ValueError: `--decisions`/`--source` are absent — this tool only re-derives
            from real, timestamp-matched data, it never fabricates a result.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--decisions", type=Path, default=None, help="Parquet of decision_time/archived_close"
    )
    parser.add_argument("--source", type=Path, default=None, help="Parquet of close_time/close")
    args = parser.parse_args(argv)
    if args.decisions is None or args.source is None:
        raise ValueError(
            f"{_TOOL}: no source close data configured — pass --decisions <path> and "
            "--source <path> to the real archived-decision and independently sourced "
            "close Parquet files; this tool never fabricates a result"
        )
    decisions, source = _load_parquet_inputs(args.decisions, args.source)
    rederive_and_write(
        archive_path=args.archive, decisions=decisions, source=source, output_path=args.out
    )


def _load_parquet_inputs(
    decisions_path: Path, source_path: Path
) -> tuple[list[ArchivedDecision], SourceCloseSeries]:
    """Load the real `--decisions`/`--source` Parquet files per the module's input contract."""
    from algo_core.duck import connect, read_parquet  # local import: optional workspace dep

    connection = connect()
    decision_rows = read_parquet(connection, str(decisions_path)).fetchall()
    decisions = [
        ArchivedDecision(decision_time=row[0], archived_close=float(row[1]))
        for row in decision_rows
    ]
    source_rows = read_parquet(connection, str(source_path)).fetchall()
    closes = {row[0]: float(row[1]) for row in source_rows}
    if not closes:
        raise ValueError(f"{_TOOL}: {source_path} contains no close_time/close rows")
    source = SourceCloseSeries(closes=closes, series_end=max(closes))
    return decisions, source


if __name__ == "__main__":
    main()
