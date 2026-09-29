"""The ``Instrument`` value object and its per-asset-class ``AssetSpec``.

Composition over inheritance: one frozen ``Instrument`` holds the attributes
common to every tradable thing plus a ``details`` sub-object that is itself a
per-asset-class value object (``ForexSpec`` for the TCC). Vocabulary mirrors
LEAN's (``symbol``, ``security_type``); the named price-movement ``unit`` /
``unit_size`` is the suite's one addition for asset-agnostic risk math. See
SPEC.md §6.1.

Only forex is implemented for the TCC, with a closed registry of the two target
pairs. Another asset class is a new ``*Spec`` plugged into the same
``Instrument``, with no change to the common object or its consumers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class UnknownSymbolError(LookupError):
    """Raised when a symbol is not in the instrument registry."""


class SecurityType(StrEnum):
    """Asset class, mirroring LEAN's ``SecurityType`` so the model and the engine agree."""

    FOREX = "forex"
    EQUITY = "equity"
    FUTURE = "future"
    CFD = "cfd"
    CRYPTO = "crypto"
    INDEX = "index"
    OPTION = "option"


class Unit(StrEnum):
    """The price-movement unit label (``pip`` for FX, ``tick`` for equities)."""

    PIP = "pip"
    TICK = "tick"


class AssetSpec(BaseModel):
    """Base for the per-asset-class ``details`` value object (composition)."""

    model_config = ConfigDict(frozen=True)


class ForexSpec(AssetSpec):
    """Forex details: the two currencies of the pair."""

    base: str
    quote: str


class Instrument(BaseModel):
    """A tradable instrument: common attributes plus a composed ``details`` spec."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    security_type: SecurityType
    market: str
    digits: int
    unit: Unit
    unit_size: float
    lot_size: float
    details: ForexSpec

    def round_price(self, price: float) -> float:
        """Round a price to the instrument's decimal precision."""
        return round(price, self.digits)

    @property
    def price_increment(self) -> float:
        """The minimum price increment, ``10**-digits`` (e.g. 1e-5 for a 5-digit pair).

        This is what raw integer price points scale by — distinct from ``unit_size``
        (the pip, 1e-4 / 1e-2). Using the pip here would misprice by a factor of 10.
        """
        return 10.0**-self.digits


# LEAN-aligned forex defaults: market = the live brokerage target (OANDA).
# ``lot_size`` is the *standard FX lot* (100,000 base-currency units) — a universal
# market convention used for risk math (expressing size in lots / notional), NOT a
# broker-specific tradable unit. The broker-dependent **minimum order size and lot
# step** (e.g. OANDA trades in units of 1; MT4/MT5 brokers in 0.01-lot steps) are
# LEAN's ``SymbolProperties`` for the configured market, applied when sizing/rounding
# an order at execution (algo-backtest) — we do not hard-code per-broker lots here.
_FOREX_MARKET = "oanda"
_FOREX_LOT_SIZE = 100_000.0


def _forex(base: str, quote: str) -> Instrument:
    """Build a forex ``Instrument`` with precision from the quote-currency convention.

    A JPY-quoted pair uses a 0.01 pip and 3 digits; every other pair uses 0.0001
    and 5. A pair is therefore just its two currencies, which keeps the catalog
    below to one validated line each.
    """
    jpy = quote == "JPY"
    return Instrument(
        symbol=f"{base}{quote}",
        security_type=SecurityType.FOREX,
        market=_FOREX_MARKET,
        digits=3 if jpy else 5,
        unit=Unit.PIP,
        unit_size=0.01 if jpy else 0.0001,
        lot_size=_FOREX_LOT_SIZE,
        details=ForexSpec(base=base, quote=quote),
    )


# Versioned instrument catalog: shipped with the code, IDE/mypy-validated.
# Add a pair as one line here (a reviewed change). The TCC evaluates only EUR/USD
# and USD/JPY; the other majors are available for currency-strength and future work.
_CATALOG: tuple[Instrument, ...] = (
    _forex("EUR", "USD"),
    _forex("AUD", "USD"),
    _forex("GBP", "USD"),
    _forex("NZD", "USD"),
    _forex("USD", "CAD"),
    _forex("USD", "JPY"),
)

_REGISTRY: dict[str, Instrument] = {inst.symbol: inst for inst in _CATALOG}


def build_instrument(symbol: str) -> Instrument:
    """Return the registered ``Instrument`` for ``symbol``.

    Raises ``UnknownSymbolError`` rather than defaulting an unknown symbol, so a
    typo never silently produces a wrong unit or precision.
    """
    try:
        return _REGISTRY[symbol]
    except KeyError as exc:
        raise UnknownSymbolError(f"unknown instrument symbol: {symbol!r}") from exc
