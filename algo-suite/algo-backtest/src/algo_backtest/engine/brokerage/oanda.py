"""OANDA brokerage-model adapter: LEAN's backtest-mode OANDA fill/fee/spread model.

No live connection — this only selects LEAN's simulated OANDA brokerage model
(margin account), reading price data purely from the materialized ``lean-data/``
store (``leandata.py``, already ``IMPLEMENTED``). Live/paper OANDA brokerage is
Phase 6, out of scope here (``PRD.md`` Sec 6).

``BrokerageName``/``AccountType`` come from ``AlgorithmImports``, which only
exists inside the pinned LEAN container's Python — imported lazily inside
``apply()`` so this module (and the registry around it) stays importable and
unit-testable in the normal ``algo-backtest`` environment.
"""

from __future__ import annotations

from typing import Any

from .base import BrokerageAdapter
from .registry import register


@register
class OandaBrokerageAdapter(BrokerageAdapter):
    """Applies LEAN's OANDA margin-account brokerage model."""

    name = "oanda"

    def apply(self, algorithm: Any) -> None:
        """Select the OANDA backtest brokerage model on ``algorithm``."""
        from AlgorithmImports import AccountType, BrokerageName  # noqa: PLC0415

        algorithm.set_brokerage_model(BrokerageName.OANDA_BROKERAGE, AccountType.MARGIN)
