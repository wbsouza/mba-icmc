"""`statement.md` -> the positions still open at the end of the run and the account summary.

The statement is the audited account view `algo-backtest statement --run` writes: its
"Open Trades:" table lists every position the run left open (ticket, open time, side, lots,
open price, stop, targets, mark price, floating P/L) and its "A/C Summary:" block carries the
balance (deposit plus closed P/L), the floating P/L and the equity (balance plus floating).
The viewer needs both to reconcile the trades table (realized only) with the equity curve
(mark-to-market). Parsing reads the markdown tables the statement writer renders; a missing
section means no open positions, a malformed cell stops the build naming the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

OPEN_HEADER = "## Open Trades:"
SUMMARY_HEADER = "## A/C Summary:"
_ABSENT = "—"
_ROW = re.compile(r"^\|(.*)\|\s*$")


@dataclass(frozen=True)
class OpenPosition:
    """One position still open when the run ended, as the statement reports it."""

    ticket: int
    open_time: datetime
    direction: str
    lots: float | None
    open_price: float
    stop_loss: float | None
    take_profits: tuple[float, ...]
    mark_price: float | None
    floating_pl: float


@dataclass(frozen=True)
class StatementFacts:
    """What the results database keeps from the statement."""

    open_positions: tuple[OpenPosition, ...]
    balance: float | None
    floating_pl: float | None
    equity: float | None


def _cells(line: str) -> list[str] | None:
    """The cells of a markdown table row, `None` for any other line."""
    match = _ROW.match(line.strip())
    if match is None:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def _section(text: str, header: str) -> list[list[str]]:
    """The data rows (no header, no separator) of the first table under `header`, or []."""
    if header not in text:
        return []
    body = text.split(header, 1)[1].split("\n## ", 1)[0]
    rows = [cells for cells in (_cells(line) for line in body.splitlines()) if cells]
    return [row for row in rows[1:] if not all(re.fullmatch(r"-+", c) for c in row)]


def _money(cell: str, path: Path, what: str) -> float:
    """`10,633.10` -> 10633.10; anything else stops the build naming the file."""
    try:
        return float(cell.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"{path.name} in {path.parent}: {what} is not a number: {cell!r}") from exc


def _price(cell: str, path: Path, what: str) -> float | None:
    """A quoted price, or `None` for the statement's absence marker."""
    return None if cell in (_ABSENT, "") else _money(cell, path, what)


def _targets(cell: str, path: Path) -> tuple[float, ...]:
    """`1.01542 / 0.97722` -> (1.01542, 0.97722); the absence marker -> ()."""
    if cell in (_ABSENT, ""):
        return ()
    prices = (_price(part.strip(), path, "take profit") for part in cell.split("/"))
    return tuple(p for p in prices if p is not None)


def _position(row: list[str], path: Path) -> OpenPosition | None:
    """One Open Trades row -> `OpenPosition`; the bold totals row -> `None`."""
    if len(row) < 12 or row[0].startswith("**"):
        return None
    (ticket, open_time, side, lots, _item, open_price, stop, targets, mark, _fee, _swap,
     profit) = row[:12]
    try:
        opened = datetime.strptime(open_time, "%Y.%m.%d %H:%M").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(
            f"{path.name} in {path.parent}: open time {open_time!r} is not YYYY.MM.DD HH:MM"
        ) from exc
    return OpenPosition(
        ticket=int(ticket),
        open_time=opened,
        direction=side.lower(),
        lots=_price(lots, path, "lots"),
        open_price=_money(open_price, path, "open price"),
        stop_loss=_price(stop, path, "stop loss"),
        take_profits=_targets(targets, path),
        mark_price=_price(mark, path, "mark price"),
        floating_pl=_money(profit, path, "floating P/L"),
    )


def _summary_value(rows: list[list[str]], label: str, path: Path) -> float | None:
    """The number right of `label` in the two-column A/C Summary block, or `None`."""
    for row in rows:
        for i in range(0, len(row) - 1, 2):
            if row[i] == label and row[i + 1] not in ("", _ABSENT):
                return _money(row[i + 1], path, label)
    return None


def parse_statement(text: str, path: Path) -> StatementFacts:
    """The open positions and account summary of one statement.md."""
    positions = [p for p in (_position(r, path) for r in _section(text, OPEN_HEADER)) if p]
    summary = _section(text, SUMMARY_HEADER)
    return StatementFacts(
        open_positions=tuple(positions),
        balance=_summary_value(summary, "Balance", path),
        floating_pl=_summary_value(summary, "Floating P/L", path),
        equity=_summary_value(summary, "Equity", path),
    )


def read_statement(run_dir: Path, file_name: str) -> StatementFacts:
    """`parse_statement` over the run's statement file; an absent file means nothing open."""
    path = run_dir / file_name
    if not path.exists():
        return StatementFacts(open_positions=(), balance=None, floating_pl=None, equity=None)
    return parse_statement(path.read_text(), path)
