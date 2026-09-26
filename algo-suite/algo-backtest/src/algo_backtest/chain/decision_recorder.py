"""Per-run decision accumulator shared by every chain-driven LEAN algorithm.

`chain/audit.py` (Spec 04f) already knows how to turn one `ChainOutcome` into a
`DecisionRow` and how to write a batch of rows to Parquet; it holds no state across
bars. `algos/baseline/main.py` and `algos/hybrid/main.py` both need the same
per-bar bookkeeping (accumulate one row per `on_data()` call, track which
`trade_id` is "currently open" so a HOLD row can still be joined to the trade it is
managing, write the batch once at `on_end_of_algorithm()`) — this module is that
bookkeeping, factored out once so neither algorithm duplicates it (Spec 04h,
"`decisions.parquet` joins `trades.json` by `trade_id`").
"""

from __future__ import annotations

from pathlib import Path

from algo_backtest.chain.audit import DecisionRow, decision_row_from_outcome, write_decisions
from algo_backtest.chain.model import ChainOutcome


class DecisionRecorder:
    """Accumulates `DecisionRow`s for one run, threading the "currently open trade" id.

    The caller tells this class when a trade opens (`open_trade`) or closes
    (`close_trade`); `record` reads whatever id is current at the time of the call
    and attaches it to the row. `decision_row_from_outcome` itself forces the id to
    `None` for a `NO_TRADE` decision regardless of what is passed in (SPEC.md §6.2:
    a stand-aside/veto row has no trade to be a foreign key to), so `record` does not
    need to special-case that decision here.
    """

    def __init__(self) -> None:
        self._rows: list[DecisionRow] = []
        self._current_trade_id: str | None = None

    def open_trade(self, trade_id: str) -> None:
        """Mark `trade_id` as the currently-open trade (an entry order just filled)."""
        self._current_trade_id = trade_id

    def close_trade(self) -> None:
        """Clear the currently-open trade (an exit order just filled, or none was open)."""
        self._current_trade_id = None

    def record(self, outcome: ChainOutcome) -> None:
        """Append one `DecisionRow` for `outcome`, joined to the currently-open trade, if any."""
        self._rows.append(decision_row_from_outcome(outcome, self._current_trade_id))

    def write(self, path: Path) -> None:
        """Persist every accumulated row to `path` as the `decisions.parquet` audit trail."""
        write_decisions(self._rows, path)
