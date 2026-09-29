"""Step definitions for brokerage_adapter.feature (pytest-bdd)."""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator
from typing import Any

import pytest
from algo_backtest.engine.brokerage import (
    REGISTRY,
    UnknownBrokerageAdapterError,
    build_brokerage_adapter,
    register,
)
from algo_backtest.engine.brokerage.base import BrokerageAdapter
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/brokerage_adapter.feature")


@pytest.fixture(autouse=True)
def _isolate_registry() -> Iterator[None]:
    """Snapshot and restore REGISTRY so per-scenario registrations don't leak."""
    snapshot = dict(REGISTRY)
    yield
    REGISTRY.clear()
    REGISTRY.update(snapshot)


@pytest.fixture(autouse=True)
def _fake_algorithm_imports() -> Iterator[None]:
    """Stand in for LEAN's real AlgorithmImports (only present inside the container)."""
    module = types.ModuleType("AlgorithmImports")
    module.BrokerageName = types.SimpleNamespace(OANDA_BROKERAGE="OANDA_BROKERAGE")  # type: ignore[attr-defined]
    module.AccountType = types.SimpleNamespace(MARGIN="MARGIN")  # type: ignore[attr-defined]
    sys.modules["AlgorithmImports"] = module
    yield
    del sys.modules["AlgorithmImports"]


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


class _FakeAlgorithm:
    """A minimal stand-in for QCAlgorithm's ``set_brokerage_model`` call."""

    def __init__(self) -> None:
        self.brokerage_model: tuple[Any, Any] | None = None

    def set_brokerage_model(self, name: Any, account_type: Any) -> None:
        self.brokerage_model = (name, account_type)


def _make_adapter(name: str) -> type[BrokerageAdapter]:
    """Build a throwaway BrokerageAdapter subclass whose ``name`` is ``name``."""

    def _apply(self: BrokerageAdapter, algorithm: Any) -> None:
        pass

    return type(name or "Anon", (BrokerageAdapter,), {"name": name, "apply": _apply})


@given(parsers.parse('a registered adapter named "{name}"'))
def _register_demo(context: dict[str, Any], name: str) -> None:
    register(_make_adapter(name))


@when(parsers.parse('I build the brokerage adapter "{name}"'))
def _build(context: dict[str, Any], name: str) -> None:
    try:
        context["built"] = build_brokerage_adapter(name)
    except UnknownBrokerageAdapterError as exc:
        context["error"] = exc


@when(parsers.parse('I register another adapter also named "{name}"'))
def _register_clash(context: dict[str, Any], name: str) -> None:
    try:
        register(_make_adapter(name))
        context["reg_error"] = None
    except ValueError as exc:
        context["reg_error"] = exc


@given("a fake QCAlgorithm")
def _fake_algo(context: dict[str, Any]) -> None:
    context["algorithm"] = _FakeAlgorithm()


@when(parsers.parse('I apply the "{name}" brokerage adapter to it'))
def _apply_adapter(context: dict[str, Any], name: str) -> None:
    build_brokerage_adapter(name).apply(context["algorithm"])


@then(parsers.parse('I get a BrokerageAdapter whose name is "{name}"'))
def _got_adapter(context: dict[str, Any], name: str) -> None:
    built = context["built"]
    assert isinstance(built, BrokerageAdapter)
    assert built.name == name


@then("an UnknownBrokerageAdapterError is raised naming the known adapters")
def _unknown(context: dict[str, Any]) -> None:
    error = context["error"]
    assert isinstance(error, UnknownBrokerageAdapterError)
    assert "oanda" in str(error)


@then("a registration error is raised")
def _reg_error(context: dict[str, Any]) -> None:
    assert isinstance(context["reg_error"], ValueError)


@then("the algorithm's brokerage model is set to OANDA margin")
def _brokerage_set(context: dict[str, Any]) -> None:
    algorithm: _FakeAlgorithm = context["algorithm"]
    assert algorithm.brokerage_model == ("OANDA_BROKERAGE", "MARGIN")
