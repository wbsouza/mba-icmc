"""Steps for trade_grouping.feature — ledger policy vs DecisionRecorder, in real LEAN."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pytest_bdd import parsers, scenarios, then, when

scenarios("../features/trade_grouping.feature")

_ALGOS = Path(__file__).parent.parent / "algos"
_LEAN_SUBPATH = "forex/oanda/minute/eurusd"


def _instant(raw: str) -> datetime:
    """A LEAN-logged timestamp (UTC, naive or offset) as an aware UTC datetime."""
    parsed = datetime.fromisoformat(raw.strip())
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _fields(logs: str, tag: str) -> list[list[str]]:
    """The `|`-separated fields of every `<tag>|...` log line, in order, deduplicated."""
    seen: list[list[str]] = []
    for line in logs.splitlines():
        if f"{tag}|" in line:
            fields = line.split(f"{tag}|", 1)[1].split("|")
            if fields not in seen:
                seen.append(fields)
    return seen


@when(parsers.parse('the trade-grouping probe replays "{day}" in the LEAN container'))
def _run_probe(ctx: dict[str, Any], lean_backtest: Any, tmp_path: Path, day: str) -> None:
    results = tmp_path / "results"
    results.mkdir(exist_ok=True)
    ctx["run"] = lean_backtest(
        algo_dir=_ALGOS / "trade_grouping",
        results_dir=results,
        data_mounts={_LEAN_SUBPATH: ctx["symbol_dir"]},
        parameters={"day": day},
    )


@then(parsers.parse('the ledger has trades with order ids "{first}", "{second}" and "{third}"'))
def _ledger(ctx: dict[str, Any], first: str, second: str, third: str) -> None:
    """Scale-in + partial exits stay one trade; the reversal order closes one and opens one."""
    trades = [fields[0] for fields in _fields(ctx["run"].logs, "GROUPING_TRADE")]
    assert trades == [first, second, third], ctx["run"].logs[-3000:]


@then(
    "after every fill the recorder's trade id is the first order of the ledger trade open "
    "at that instant"
)
def _temporal_identity(ctx: dict[str, Any]) -> None:
    """Identity, not membership: the id must name the trade open at the fill's instant.

    A ledger trade is open at `t` when `entry <= t < exit` — the order that flattens a
    trade leaves it closed at `t`, and a reversal order is the entry of the next trade.
    """
    logs = ctx["run"].logs
    trades = [
        (ids.split(","), _instant(entry), _instant(exit_))
        for ids, entry, exit_ in _fields(logs, "GROUPING_TRADE")
    ]
    steps = _fields(logs, "GROUPING_STEP")
    assert len(steps) == 7, logs[-3000:]
    for instant, order_id, recorded in steps:
        at = _instant(instant)
        open_now = [ids[0] for ids, entry, exit_ in trades if entry <= at < exit_]
        assert len(open_now) <= 1, (instant, open_now)
        expected = open_now[0] if open_now else "None"
        assert recorded == expected, (instant, order_id, recorded, trades)
