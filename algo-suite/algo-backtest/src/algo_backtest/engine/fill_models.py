"""LEAN adapters for the configured fill costs: a pip-spread slippage model and a per-lot
fee model, plus ``apply_fill_costs`` which installs them on every subscribed security.

The economics live in the LEAN-free ``engine/costs.py``; these classes only translate
LEAN's model protocols (``ISlippageModel.get_slippage_approximation``,
``FeeModel.get_order_fee``) into calls to that math. ``FeeModel``/``OrderFee``/
``CashAmount`` come from ``AlgorithmImports`` — LEAN's injected namespace, real only
inside the pinned container — so this module imports them by name (not ``*``) and the
BDD suite (``fill_costs.feature``) installs a fake ``AlgorithmImports`` to exercise it
offline, the same trick ``brokerage_adapter.feature`` uses.

Zero is meaningful: a zero ``spread_pips`` or ``commission_per_lot`` leaves LEAN's
default model for that cost untouched (the brokerage adapter's own), so a strategy that
sets neither behaves exactly as before story 12.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from AlgorithmImports import CashAmount, FeeModel, OrderFee

from .costs import (
    commission_amount,
    pip_size_for,
    require_non_negative,
    require_positive,
    slippage_price,
)


class PipSpreadSlippageModel:
    """LEAN ``ISlippageModel``: every fill slips by half the configured spread.

    Duck-typed (LEAN wraps any Python object exposing ``get_slippage_approximation``);
    the slippage is constant per security, so it is computed — and validated — once.
    """

    def __init__(self, spread_pips: float, pip_size: float) -> None:
        self.spread_pips = spread_pips
        self.pip_size = pip_size
        self._slippage = slippage_price(spread_pips, pip_size)

    def get_slippage_approximation(self, asset: Any, order: Any) -> float:
        """The per-side slippage in price units, independent of ``asset``/``order``."""
        return self._slippage


class PerLotFeeModel(FeeModel):  # type: ignore[misc]
    """LEAN ``FeeModel``: ``commission_per_lot`` pro rata on the order's absolute quantity.

    ``account_currency`` labels the fee's ``CashAmount`` — the algorithm's own account
    currency (``QCAlgorithm.account_currency``), since ``commission_per_lot`` is quoted in
    it. Rates are validated at construction so a negative commission fails before the
    first bar, not on the first fill.
    """

    def __init__(
        self, commission_per_lot: float, lot_notional_units: float, account_currency: str
    ) -> None:
        super().__init__()
        require_non_negative("commission_per_lot", commission_per_lot)
        require_positive("lot_notional_units", lot_notional_units)
        self.commission_per_lot = commission_per_lot
        self.lot_notional_units = lot_notional_units
        self.account_currency = account_currency

    def get_order_fee(self, parameters: Any) -> Any:
        """The order's commission as an ``OrderFee`` in ``account_currency``."""
        amount = commission_amount(
            parameters.order.absolute_quantity, self.lot_notional_units, self.commission_per_lot
        )
        return OrderFee(CashAmount(amount, self.account_currency))


def _subscribed_securities(algorithm: Any) -> Iterator[Any]:
    """Every ``Security`` the algorithm has subscribed (LEAN's ``SecurityManager.values()``)."""
    yield from algorithm.securities.values()


def apply_fill_costs(
    algorithm: Any,
    *,
    spread_pips: float,
    commission_per_lot: float,
    lot_notional_units: float | None,
    pip_size: float | None,
    log_tag: str,
) -> None:
    """Install the configured fill-cost models on every subscribed security.

    A positive ``spread_pips`` sets a :class:`PipSpreadSlippageModel` (pip size from
    ``pip_size`` when given, else derived from the security's
    ``symbol_properties.minimum_price_variation`` via :func:`pip_size_for`); a positive
    ``commission_per_lot`` sets a :class:`PerLotFeeModel` charging in the algorithm's
    ``account_currency``, pro rata on ``lot_notional_units`` (the strategy's
    ``capital_mgmt.lot_notional_units`` — required whenever a commission is charged, never
    defaulted here). Zero leaves that model alone. One ``<log_tag>_FILL_COSTS|model=...``
    debug line is logged per model per security.

    Raises:
        ValueError: on a negative rate or a commission without a lot size (both before any
            security is touched), or when a cost is configured but no security is
            subscribed yet — the caller must subscribe (``add_forex``) before
            ``init_execution``.
    """
    require_non_negative("spread_pips", spread_pips)
    require_non_negative("commission_per_lot", commission_per_lot)
    if commission_per_lot > 0 and lot_notional_units is None:
        raise ValueError(
            f"{log_tag}: commission_per_lot={commission_per_lot} is configured but "
            "lot_notional_units is missing; pass the strategy's capital_mgmt.lot_notional_units "
            "to init_execution(...) — the per-lot commission cannot be pro-rated without it"
        )
    if spread_pips == 0 and commission_per_lot == 0:
        return
    securities = list(_subscribed_securities(algorithm))
    if not securities:
        raise ValueError(
            f"{log_tag}: fill costs configured (spread_pips={spread_pips}, "
            f"commission_per_lot={commission_per_lot}) but no subscribed securities to apply "
            "them to; call add_forex(...) before init_execution(...)"
        )
    for security in securities:
        if spread_pips > 0:
            _apply_slippage(algorithm, security, spread_pips, pip_size, log_tag)
        if commission_per_lot > 0 and lot_notional_units is not None:
            _apply_fee(algorithm, security, commission_per_lot, lot_notional_units, log_tag)


def _apply_slippage(
    algorithm: Any, security: Any, spread_pips: float, pip_size: float | None, log_tag: str
) -> None:
    """Set the pip-spread slippage model on one security and log it."""
    pip = (
        pip_size
        if pip_size is not None
        else pip_size_for(float(security.symbol_properties.minimum_price_variation))
    )
    security.set_slippage_model(PipSpreadSlippageModel(spread_pips, pip))
    algorithm.debug(
        f"{log_tag}_FILL_COSTS|model=slippage|symbol={security.symbol}|"
        f"spread_pips={spread_pips}|pip_size={pip}"
    )


def _apply_fee(
    algorithm: Any,
    security: Any,
    commission_per_lot: float,
    lot_notional_units: float,
    log_tag: str,
) -> None:
    """Set the per-lot fee model, in the algorithm's account currency, on one security; log it."""
    currency = str(algorithm.account_currency)
    security.set_fee_model(PerLotFeeModel(commission_per_lot, lot_notional_units, currency))
    algorithm.debug(
        f"{log_tag}_FILL_COSTS|model=fee|symbol={security.symbol}|"
        f"commission_per_lot={commission_per_lot}|lot_notional_units={lot_notional_units}|"
        f"currency={currency}"
    )
