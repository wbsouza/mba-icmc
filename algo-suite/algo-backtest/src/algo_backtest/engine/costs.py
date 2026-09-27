"""Pure fill-cost math: pip-spread slippage, per-lot commission, pip size (story 12, item C).

LEAN-free and typed, so the economics of a fill are unit-tested from
``tests/features/fill_costs.feature`` without the container; the LEAN adapters in
``engine/fill_models.py`` only call these functions. Every rate is a caller-supplied
parameter sourced from the strategy YAML's ``execution`` section (specs.md §14.5–14.7,
strategy A05) — this module carries no default spread, commission or lot size.

Conventions:

- **Pip.** One pip is ten times the instrument's minimum price variation, i.e. the
  fourth decimal of a 5-digit FX quote (EURUSD ``0.00001`` → pip ``0.0001``) and the
  second decimal of a 3-digit JPY quote (USDJPY ``0.001`` → pip ``0.01``). LEAN's
  ``SymbolProperties.minimum_price_variation`` for the OANDA market is fractional-pip
  (5/3-digit) for every FX pair, which is the quoting this convention assumes.
- **Spread.** ``spread_pips`` is the full bid–ask spread; each side of a round trip
  pays half of it, so a fill's slippage is ``spread_pips / 2`` pips.
- **Commission.** ``commission_per_lot`` is charged per side, pro rata on the absolute
  filled quantity against ``lot_notional_units`` (the standard 100,000-unit FX lot).
"""

from __future__ import annotations

_PIPS_PER_MIN_PRICE_VARIATION = 10.0


def require_non_negative(name: str, value: float) -> None:
    """Fail fast on a negative cost rate (zero is a legitimate "no cost")."""
    if value < 0:
        raise ValueError(
            f"fill costs: {name} must be >= 0, got {value!r}; fix the strategy YAML's "
            f"execution.{name} (0 means no cost of this kind)"
        )


def require_positive(name: str, value: float) -> None:
    """Fail fast on a zero or negative divisor/scale (it would zero or invert a cost)."""
    if value <= 0:
        raise ValueError(f"fill costs: {name} must be > 0, got {value!r}")


def pip_size_for(min_price_variation: float) -> float:
    """The pip size of a fractional-pip FX quote: ten times its minimum price variation.

    Raises:
        ValueError: if ``min_price_variation`` is not strictly positive (a zero tick size
            is a corrupt symbol-properties entry, never a real instrument).
    """
    require_positive("min_price_variation", min_price_variation)
    return min_price_variation * _PIPS_PER_MIN_PRICE_VARIATION


def slippage_price(spread_pips: float, pip_size: float) -> float:
    """Per-side slippage in price units: half the configured spread, converted by pip size.

    Raises:
        ValueError: if ``spread_pips`` is negative or ``pip_size`` is not strictly positive.
    """
    require_non_negative("spread_pips", spread_pips)
    require_positive("pip_size", pip_size)
    return (spread_pips / 2.0) * pip_size


def commission_amount(
    quantity: float, lot_notional_units: float, commission_per_lot: float
) -> float:
    """Per-side commission: the per-lot rate pro rata on ``|quantity| / lot_notional_units``.

    Direction-agnostic (a short fill pays the same as a long one of the same size).

    Raises:
        ValueError: if ``commission_per_lot`` is negative or ``lot_notional_units`` is not
            strictly positive.
    """
    require_non_negative("commission_per_lot", commission_per_lot)
    require_positive("lot_notional_units", lot_notional_units)
    return (abs(quantity) / lot_notional_units) * commission_per_lot
