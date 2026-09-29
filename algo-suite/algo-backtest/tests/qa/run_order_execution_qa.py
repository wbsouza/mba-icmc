"""Executable QA procedure for the order-execution engine (Spec 04a).

The companion procedure is ``spec-algo-backtest-order-execution.qa.md``. Keep this
script in lockstep with that document: it drives the public ``algo-backtest`` CLI
only (no direct calls into ``algo_backtest.engine.*``) against the real, pinned LEAN
container (``@integration`` — needs Docker; not part of ``make check``).
"""

from __future__ import annotations

import json
import shlex
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from algo_backtest.cli import app
from algo_backtest.materialize import materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from typer.testing import CliRunner

_EURUSD = build_instrument("EURUSD")
_FIRST_BAR = datetime(2014, 5, 7, 13, 0, tzinfo=UTC)
_FROM, _TO = "2014-05-07", "2014-05-09"


class QaFailure(AssertionError):
    """Raised when an executable QA check fails."""


def main() -> None:
    """Run the complete automated QA procedure."""
    scratch = _clean_scratch()
    _happy_path(scratch / "happy")
    _flat_market(scratch / "flat")
    _brokerage_is_config_selected(scratch / "brokerage")
    _meanrev_migration_regression(scratch / "meanrev")
    print("run_order_execution_qa: all sections passed")


def _clean_scratch() -> Path:
    """Create an empty worktree-local scratch directory for this QA run."""
    worktree_root = Path(__file__).resolve().parents[4]
    scratch = worktree_root / "tmp" / "qa-order-execution"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    return scratch


def _swing_bars(count: int = 60) -> list[QuoteBar]:
    """Triangular price swing (up then down) so fast/slow SMA crosses both ways."""
    bars = []
    for i in range(count):
        offset = min(i, count - 1 - i)
        mid = 1.3800 + 0.0003 * offset
        bid = round(mid, 5)
        ask = round(mid + 0.0001, 5)
        bars.append(
            QuoteBar(
                timestamp=_FIRST_BAR + timedelta(minutes=i),
                bid_open=bid,
                bid_high=bid,
                bid_low=bid,
                bid_close=bid,
                ask_open=ask,
                ask_high=ask,
                ask_low=ask,
                ask_close=ask,
                tick_count=1,
            )
        )
    return bars


def _flat_bars(count: int = 60) -> list[QuoteBar]:
    """A flat price — fast and slow SMA never cross, so the strategy never trades."""
    bid, ask = 1.38000, 1.38010
    return [
        QuoteBar(
            timestamp=_FIRST_BAR + timedelta(minutes=i),
            bid_open=bid,
            bid_high=bid,
            bid_low=bid,
            bid_close=bid,
            ask_open=ask,
            ask_high=ask,
            ask_low=ask,
            ask_close=ask,
            tick_count=1,
        )
        for i in range(count)
    ]


def _materialize(data_root: Path, bars: list[QuoteBar]) -> None:
    """Write bars to canonical Parquet for 2014-05 and materialize them to lean-data."""
    ParquetRepository(
        QuoteBar, price_path_for(data_root, _EURUSD, Timeframe.M1.value, 2014, 5)
    ).put(bars)
    materialize_month(data_root, _EURUSD, 2014, 5, ZoneInfo("UTC"))


def _invoke(data_root: Path, args: str, broker_adapter: str = "oanda") -> Any:
    """Invoke the algo-backtest CLI with an isolated data root and broker adapter."""
    env = {
        "ALGO_DATA_ROOT": str(data_root),
        "ALGO_CONF_DIR": str(data_root / "conf"),
        "ALGO_BROKER__ADAPTER": broker_adapter,
    }
    return CliRunner().invoke(app, shlex.split(args), env=env)


def _latest_run_dir(data_root: Path, strategy: str) -> Path:
    """The most recently created runs/<strategy>/<stamp> directory."""
    strategy_root = data_root / "runs" / strategy
    stamps = sorted(strategy_root.iterdir(), key=lambda p: p.stat().st_mtime)
    return stamps[-1]


def _trades(run_dir: Path) -> list[dict[str, Any]]:
    """Load the closed-trade ledger written by this run."""
    return json.loads((run_dir / "trades.json").read_text())


def _expect(condition: bool, message: str) -> None:
    """Raise a readable QA failure when a condition is false."""
    if not condition:
        raise QaFailure(message)


def _happy_path(data_root: Path) -> None:
    """Section 1 — a BUY order is placed and its fill lands in trades.json."""
    data_root.mkdir(parents=True)
    _materialize(data_root, _swing_bars())
    result = _invoke(
        data_root,
        f"run --strategy baseline-ma --symbol EURUSD --from {_FROM} --to {_TO} "
        "--param fast=3 --param slow=8 --param size=0.5",
    )
    _expect(result.exit_code == 0, f"happy path exits 0 (got {result.exit_code}: {result.output})")
    trades = _trades(_latest_run_dir(data_root, "baseline-ma"))
    _expect(len(trades) >= 1, "trades.json has at least one closed trade")
    trade = trades[0]
    _expect(trade.get("direction") == 0, f"first trade is LONG (direction=0): {trade}")
    _expect(trade.get("entryPrice") is not None, "entry price is set")
    _expect(trade.get("exitPrice") is not None, "exit price is set")


def _flat_market(data_root: Path) -> None:
    """Section 2 — flat market: no order is placed, no trade record is created."""
    data_root.mkdir(parents=True)
    _materialize(data_root, _flat_bars())
    result = _invoke(
        data_root,
        f"run --strategy baseline-ma --symbol EURUSD --from {_FROM} --to {_TO} "
        "--param fast=3 --param slow=8 --param size=0.5",
    )
    _expect(result.exit_code == 0, f"flat market exits 0 (got {result.exit_code}: {result.output})")
    trades = _trades(_latest_run_dir(data_root, "baseline-ma"))
    _expect(trades == [], f"trades.json is empty on a flat market, got {trades}")
    _expect("closed_trades=0" in result.output, "CLI reports zero closed trades")


def _brokerage_is_config_selected(data_root: Path) -> None:
    """Section 3 — the brokerage model is config-selected, not hardcoded."""
    data_root.mkdir(parents=True)
    _materialize(data_root, _swing_bars())
    ok = _invoke(
        data_root,
        f"run --strategy baseline-ma --symbol EURUSD --from {_FROM} --to {_TO} "
        "--param fast=3 --param slow=8 --param size=0.5",
        broker_adapter="oanda",
    )
    _expect(
        ok.exit_code == 0, f"default (oanda) adapter run exits 0 (got {ok.exit_code}: {ok.output})"
    )

    bad = _invoke(
        data_root,
        f"run --strategy baseline-ma --symbol EURUSD --from {_FROM} --to {_TO} "
        "--param fast=3 --param slow=8 --param size=0.5",
        broker_adapter="not-a-real-adapter",
    )
    _expect(bad.exit_code == 1, f"unknown adapter exits 1 (got {bad.exit_code}: {bad.output})")
    _expect(
        "not-a-real-adapter" in bad.output,
        f"error names the invalid adapter: {bad.output}",
    )


def _meanrev_migration_regression(data_root: Path) -> None:
    """Section 4 — baseline-meanrev still runs end-to-end through the shared OrderExecutor.

    Simplified from the .qa.md's original "identical to pre-migration" framing: no
    pre-migration trades.json snapshot was ever recorded to diff against (the
    OrderExecutor migration and baseline-meanrev's first automated coverage landed in
    the same Spec 04a change). What this proves instead: baseline-meanrev, migrated
    off set_holdings/liquidate onto OrderExecutor + the same brokerage-adapter port as
    baseline-ma, still runs to completion on LEAN and produces a well-formed ledger —
    no order-placement logic duplicated or broken by sharing the engine.
    """
    data_root.mkdir(parents=True)
    _materialize(data_root, _swing_bars())
    result = _invoke(
        data_root,
        f"run --strategy baseline-meanrev --symbol EURUSD --from {_FROM} --to {_TO} "
        "--param window=5 --param band=0.001 --param size=0.5",
    )
    _expect(
        result.exit_code == 0, f"baseline-meanrev exits 0 (got {result.exit_code}: {result.output})"
    )
    trades = _trades(_latest_run_dir(data_root, "baseline-meanrev"))
    reported = int(result.output.split("closed_trades=")[1].split()[0])
    _expect(
        len(trades) == reported,
        f"trades.json count ({len(trades)}) matches CLI-reported count ({reported})",
    )


if __name__ == "__main__":
    main()
