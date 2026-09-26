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

    The caller reports every *filled* order via `on_fill` with the position quantity
    before and after it; `record` attaches whatever id is current to the row. The id
    follows flat-to-flat trade grouping — the policy `engine/chain_algorithm.py`
    configures LEAN's ledger with (LEAN's default is fill-to-fill) — so it names the
    `trades.json` trade (its `orderIds[0]`) open at the row's instant:

    - flat -> position, or a reversal (sign flip): LEAN opens a new trade whose first
      order is this one, so this order id becomes current;
    - a same-side scale-in/scale-out: still the same LEAN trade, so the id is kept;
    - position -> flat: the trade closed, so no id is current.

    A rejected/unfilled order is simply never reported, so it cannot clear or replace the
    id of a trade that is in fact still open. `decision_row_from_outcome` itself forces
    the id to `None` for a `NO_TRADE` decision (SPEC.md §6.2).
    """

    def __init__(self) -> None:
        self._rows: list[DecisionRow] = []
        self._current_trade_id: str | None = None

    @property
    def rows(self) -> tuple[DecisionRow, ...]:
        """Every row recorded so far, in recording order."""
        return tuple(self._rows)

    @property
    def current_trade_id(self) -> str | None:
        """The id of the LEAN trade currently open, if any."""
        return self._current_trade_id

    def on_fill(self, order_id: str, prior_quantity: float, new_quantity: float) -> None:
        """Update the current trade id from one filled order's position transition."""
        if new_quantity == 0:
            self._current_trade_id = None
        elif prior_quantity == 0 or (prior_quantity > 0) != (new_quantity > 0):
            self._current_trade_id = order_id

    def record(self, outcome: ChainOutcome) -> None:
        """Append one `DecisionRow` for `outcome`, joined to the currently-open trade, if any."""
        self._rows.append(decision_row_from_outcome(outcome, self._current_trade_id))

    def write(self, path: Path) -> None:
        """Persist every accumulated row to `path` as the `decisions.parquet` audit trail."""
        write_decisions(self._rows, path)
