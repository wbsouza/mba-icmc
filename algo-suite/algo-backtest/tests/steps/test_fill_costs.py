"""Steps for fill_costs.feature — pure fill-cost math (`engine/costs.py`) and the LEAN
slippage/fee adapters (`engine/fill_models.py`) against a faked ``AlgorithmImports``
(LEAN's injected namespace exists only inside the container; the fake mirrors the
three names the adapters use: ``FeeModel``, ``OrderFee``, ``CashAmount``).
"""

from __future__ import annotations

import importlib
import sys
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from algo_backtest.engine.costs import commission_amount, pip_size_for, slippage_price
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/fill_costs.feature")


# --- fake AlgorithmImports -------------------------------------------------------------


class _FeeModel:
    """Stand-in for LEAN's ``FeeModel`` base class."""


@dataclass(frozen=True)
class _CashAmount:
    """Stand-in for LEAN's ``CashAmount(amount, currency)``."""

    amount: float
    currency: str


@dataclass(frozen=True)
class _OrderFee:
    """Stand-in for LEAN's ``OrderFee(CashAmount)``."""

    value: _CashAmount


def _fake_algorithm_imports() -> types.ModuleType:
    """One module object, built once, so the adapter module binds stable fake classes."""
    module = types.ModuleType("AlgorithmImports")
    module.FeeModel = _FeeModel  # type: ignore[attr-defined]
    module.CashAmount = _CashAmount  # type: ignore[attr-defined]
    module.OrderFee = _OrderFee  # type: ignore[attr-defined]
    return module


_FAKE_ALGORITHM_IMPORTS = _fake_algorithm_imports()


@pytest.fixture(autouse=True)
def _install_fake_lean() -> Iterator[None]:
    """Install the fake ``AlgorithmImports`` for the scenario; remove it afterwards."""
    sys.modules["AlgorithmImports"] = _FAKE_ALGORITHM_IMPORTS
    yield
    sys.modules.pop("AlgorithmImports", None)


def _fill_models() -> Any:
    """Import the adapter module (only after the fake ``AlgorithmImports`` is installed)."""
    return importlib.import_module("algo_backtest.engine.fill_models")


# --- fake LEAN securities / algorithm --------------------------------------------------


@dataclass
class _Order:
    """The slice of a LEAN ``Order`` the fee model reads."""

    quantity: float

    @property
    def absolute_quantity(self) -> float:
        return abs(self.quantity)


@dataclass
class _OrderFeeParameters:
    """The slice of LEAN's ``OrderFeeParameters`` the fee model reads."""

    order: _Order


@dataclass
class _Security:
    """A fake LEAN ``Security``: symbol properties plus the two model setters."""

    name: str
    minimum_price_variation: float
    slippage_model: Any = None
    fee_model: Any = None

    @property
    def symbol(self) -> str:
        return self.name

    @property
    def symbol_properties(self) -> Any:
        return types.SimpleNamespace(minimum_price_variation=self.minimum_price_variation)

    def set_slippage_model(self, model: Any) -> None:
        self.slippage_model = model

    def set_fee_model(self, model: Any) -> None:
        self.fee_model = model


@dataclass
class _Algorithm:
    """A fake QCAlgorithm: a ``securities`` mapping and a ``debug`` log sink."""

    securities: dict[str, _Security] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    account_currency: str = "USD"

    def debug(self, message: str) -> None:
        self.logs.append(message)


@dataclass
class _Ctx:
    """Per-scenario inputs and the outcome (result xor error)."""

    spread_pips: float = 0.0
    pip_size: float = 0.0
    quantity: float = 0.0
    lot_notional_units: float = 0.0
    commission_per_lot: float = 0.0
    min_price_variation: float = 0.0
    model: Any = None
    algorithm: _Algorithm | None = None
    result: Any = None
    error: Exception | None = None


@pytest.fixture
def ctx() -> _Ctx:
    return _Ctx()


def _capture(ctx: _Ctx, compute: Any) -> None:
    """Run ``compute``, storing its result or its ValueError on ``ctx``."""
    try:
        ctx.result = compute()
    except ValueError as exc:
        ctx.error = exc


# --- pure math -------------------------------------------------------------------------


@given(parsers.parse("a configured spread of {spread_pips:g} pips"))
def _spread(ctx: _Ctx, spread_pips: float) -> None:
    ctx.spread_pips = spread_pips


@given(parsers.parse("a pip size of {pip_size:g}"))
def _pip_size(ctx: _Ctx, pip_size: float) -> None:
    ctx.pip_size = pip_size


@when("I compute the per-side slippage price")
def _compute_slippage(ctx: _Ctx) -> None:
    _capture(ctx, lambda: slippage_price(ctx.spread_pips, ctx.pip_size))


@then(parsers.parse("the slippage price is {expected:g}"))
def _slippage_is(ctx: _Ctx, expected: float) -> None:
    assert ctx.error is None, ctx.error
    assert ctx.result == pytest.approx(expected, abs=1e-12)


@given(parsers.parse("a filled quantity of {quantity:g} units"))
def _quantity(ctx: _Ctx, quantity: float) -> None:
    ctx.quantity = quantity


@given(parsers.parse("a standard lot of {lot_notional_units:g} units"))
def _lot(ctx: _Ctx, lot_notional_units: float) -> None:
    ctx.lot_notional_units = lot_notional_units


@given(parsers.parse("a commission of {commission_per_lot:g} per lot"))
def _commission(ctx: _Ctx, commission_per_lot: float) -> None:
    ctx.commission_per_lot = commission_per_lot


@when("I compute the commission amount")
def _compute_commission(ctx: _Ctx) -> None:
    _capture(
        ctx,
        lambda: commission_amount(ctx.quantity, ctx.lot_notional_units, ctx.commission_per_lot),
    )


@then(parsers.parse("the commission amount is {expected:g}"))
def _commission_is(ctx: _Ctx, expected: float) -> None:
    assert ctx.error is None, ctx.error
    assert ctx.result == pytest.approx(expected, abs=1e-12)


@given(parsers.parse("a minimum price variation of {min_price_variation:g}"))
def _mpv(ctx: _Ctx, min_price_variation: float) -> None:
    ctx.min_price_variation = min_price_variation


@when("I derive the pip size")
def _derive_pip(ctx: _Ctx) -> None:
    _capture(ctx, lambda: pip_size_for(ctx.min_price_variation))


@then(parsers.parse("the pip size is {expected:g}"))
def _pip_is(ctx: _Ctx, expected: float) -> None:
    assert ctx.error is None, ctx.error
    assert ctx.result == pytest.approx(expected, rel=1e-9)


@then(parsers.parse('the fill-cost computation fails naming "{field}"'))
def _fails_naming(ctx: _Ctx, field: str) -> None:
    assert ctx.result is None
    assert isinstance(ctx.error, ValueError), ctx.error
    assert field in str(ctx.error), str(ctx.error)


# --- LEAN adapters ---------------------------------------------------------------------


@given(
    parsers.parse(
        "a pip-spread slippage model with spread {spread_pips:g} pips and pip size {pip_size:g}"
    )
)
def _slippage_model(ctx: _Ctx, spread_pips: float, pip_size: float) -> None:
    ctx.model = _fill_models().PipSpreadSlippageModel(spread_pips=spread_pips, pip_size=pip_size)


@when(
    parsers.parse(
        "LEAN asks the model for the slippage approximation of an order of {quantity:g} units"
    )
)
def _ask_slippage(ctx: _Ctx, quantity: float) -> None:
    ctx.result = ctx.model.get_slippage_approximation(object(), _Order(quantity))


@then(parsers.parse("the slippage approximation is {expected:g}"))
def _slippage_approx_is(ctx: _Ctx, expected: float) -> None:
    assert ctx.result == pytest.approx(expected, abs=1e-12)


@given(
    parsers.parse(
        "a per-lot fee model charging {commission_per_lot:g} per {lot_notional_units:g}-unit lot "
        'in "{currency}"'
    )
)
def _fee_model(
    ctx: _Ctx, commission_per_lot: float, lot_notional_units: float, currency: str
) -> None:
    ctx.model = _fill_models().PerLotFeeModel(
        commission_per_lot=commission_per_lot,
        lot_notional_units=lot_notional_units,
        account_currency=currency,
    )
    assert isinstance(ctx.model, _FeeModel), "PerLotFeeModel must subclass LEAN's FeeModel"


@when(parsers.parse("LEAN asks the model for the fee of an order of {quantity:g} units"))
def _ask_fee(ctx: _Ctx, quantity: float) -> None:
    ctx.result = ctx.model.get_order_fee(_OrderFeeParameters(_Order(quantity)))


@then(parsers.parse('the order fee is {expected:g} "{currency}"'))
def _fee_is(ctx: _Ctx, expected: float, currency: str) -> None:
    assert isinstance(ctx.result, _OrderFee), ctx.result
    assert ctx.result.value.amount == pytest.approx(expected, abs=1e-12)
    assert ctx.result.value.currency == currency


# --- apply_fill_costs over an algorithm's securities -----------------------------------


@given(
    parsers.parse(
        'an algorithm subscribed to "{symbol}" with minimum price variation {mpv:g}'
    )
)
def _algorithm_with(ctx: _Ctx, symbol: str, mpv: float) -> None:
    ctx.algorithm = _Algorithm({symbol: _Security(symbol, mpv)})


@given(
    parsers.parse(
        'the algorithm is subscribed to "{symbol}" with minimum price variation {mpv:g}'
    )
)
def _also_subscribed(ctx: _Ctx, symbol: str, mpv: float) -> None:
    assert ctx.algorithm is not None
    ctx.algorithm.securities[symbol] = _Security(symbol, mpv)


@given("an algorithm with no subscribed securities")
def _empty_algorithm(ctx: _Ctx) -> None:
    ctx.algorithm = _Algorithm()


@given(parsers.parse('the algorithm\'s account currency is "{currency}"'))
def _account_currency(ctx: _Ctx, currency: str) -> None:
    assert ctx.algorithm is not None
    ctx.algorithm.account_currency = currency


def _apply_costs(
    ctx: _Ctx, spread_pips: float, commission_per_lot: float, lot: float | None, tag: str
) -> None:
    """Call apply_fill_costs on the scenario's algorithm, capturing the outcome."""
    _capture(
        ctx,
        lambda: _fill_models().apply_fill_costs(
            ctx.algorithm,
            spread_pips=spread_pips,
            commission_per_lot=commission_per_lot,
            lot_notional_units=lot,
            pip_size=None,
            log_tag=tag,
        ),
    )


@when(
    parsers.parse(
        "fill costs of {spread_pips:g} spread pips and {commission_per_lot:g} commission per lot "
        'are applied under tag "{tag}"'
    )
)
def _apply(ctx: _Ctx, spread_pips: float, commission_per_lot: float, tag: str) -> None:
    _apply_costs(ctx, spread_pips, commission_per_lot, 100_000.0, tag)


@when(
    parsers.parse(
        "fill costs of {spread_pips:g} spread pips and {commission_per_lot:g} commission per lot "
        "are applied without a lot size"
    )
)
def _apply_no_lot(ctx: _Ctx, spread_pips: float, commission_per_lot: float) -> None:
    _apply_costs(ctx, spread_pips, commission_per_lot, None, "T")


@when(
    parsers.parse(
        "fill costs of {spread_pips:g} spread pips are applied with an explicit pip size "
        "of {pip_size:g}"
    )
)
def _apply_explicit_pip(ctx: _Ctx, spread_pips: float, pip_size: float) -> None:
    _capture(
        ctx,
        lambda: _fill_models().apply_fill_costs(
            ctx.algorithm,
            spread_pips=spread_pips,
            commission_per_lot=0.0,
            lot_notional_units=100_000.0,
            pip_size=pip_size,
            log_tag="T",
        ),
    )


def _securities(ctx: _Ctx) -> list[_Security]:
    assert ctx.algorithm is not None
    return list(ctx.algorithm.securities.values())


@then("every security carries a pip-spread slippage model")
def _all_slippage(ctx: _Ctx) -> None:
    assert ctx.error is None, ctx.error
    cls = _fill_models().PipSpreadSlippageModel
    assert all(isinstance(s.slippage_model, cls) for s in _securities(ctx)), _securities(ctx)


@then("no security carries a pip-spread slippage model")
def _no_slippage(ctx: _Ctx) -> None:
    assert all(s.slippage_model is None for s in _securities(ctx)), _securities(ctx)


@then("every security carries a per-lot fee model")
def _all_fee(ctx: _Ctx) -> None:
    assert ctx.error is None, ctx.error
    cls = _fill_models().PerLotFeeModel
    assert all(isinstance(s.fee_model, cls) for s in _securities(ctx)), _securities(ctx)


@then(parsers.parse('every fee model charges in the algorithm\'s account currency "{currency}"'))
def _fee_currency(ctx: _Ctx, currency: str) -> None:
    assert ctx.error is None, ctx.error
    assert ctx.algorithm is not None
    assert ctx.algorithm.account_currency == currency
    for security in _securities(ctx):
        assert security.fee_model.account_currency == currency, security


@then("no security carries a per-lot fee model")
def _no_fee(ctx: _Ctx) -> None:
    assert all(s.fee_model is None for s in _securities(ctx)), _securities(ctx)


@then(parsers.parse('the "{symbol}" slippage model uses pip size {pip_size:g}'))
def _pip_size_used(ctx: _Ctx, symbol: str, pip_size: float) -> None:
    assert ctx.error is None, ctx.error
    assert ctx.algorithm is not None
    model = ctx.algorithm.securities[symbol].slippage_model
    assert model.pip_size == pytest.approx(pip_size, rel=1e-9), model


@then(parsers.parse('the log has a "{prefix}" line for each security'))
def _log_per_security(ctx: _Ctx, prefix: str) -> None:
    assert ctx.algorithm is not None
    lines = [line for line in ctx.algorithm.logs if line.startswith(prefix)]
    assert len(lines) == len(ctx.algorithm.securities), ctx.algorithm.logs
    for security in ctx.algorithm.securities.values():
        assert any(f"symbol={security.symbol}" in line for line in lines), ctx.algorithm.logs


@then(parsers.parse('the log has no "{prefix}" line'))
def _log_absent(ctx: _Ctx, prefix: str) -> None:
    assert ctx.algorithm is not None
    assert not [line for line in ctx.algorithm.logs if line.startswith(prefix)], ctx.algorithm.logs


@then(parsers.parse('applying fill costs fails naming "{needle}"'))
def _apply_fails(ctx: _Ctx, needle: str) -> None:
    assert isinstance(ctx.error, ValueError), ctx.error
    assert needle in str(ctx.error), str(ctx.error)
