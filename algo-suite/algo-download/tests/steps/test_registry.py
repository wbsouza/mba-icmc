"""Step definitions for registry.feature (pytest-bdd)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from algo_download.registry import (
    REGISTRY,
    UnknownSourceError,
    build_data_source,
    register,
)
from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, UnitResult, UnitStatus
from algo_download.source import DataSource
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/registry.feature")


@pytest.fixture(autouse=True)
def _isolate_registry() -> Iterator[None]:
    """Snapshot and restore REGISTRY so per-scenario registrations don't leak."""
    snapshot = dict(REGISTRY)
    yield
    REGISTRY.clear()
    REGISTRY.update(snapshot)


@pytest.fixture
def context() -> dict[str, object]:
    return {}


def _make_source(source_name: str) -> type[DataSource]:
    """Build a throwaway DataSource subclass whose ``name`` is ``source_name``."""

    def _plan(self: DataSource, request: DownloadRequest) -> Iterator[DownloadUnit]:
        yield from ()

    def _fetch(self: DataSource, unit: DownloadUnit) -> UnitResult:
        return UnitResult(unit=unit, status=UnitStatus.MISSING)

    return type(
        source_name or "Anon",
        (DataSource,),
        {"name": source_name, "plan": _plan, "fetch": _fetch},
    )


@given(parsers.parse('a registered source named "{name}"'))
def _register_demo(context: dict[str, object], name: str) -> None:
    register(_make_source(name))
    context["registered"] = name


@when(parsers.parse('I build the source "{name}"'))
def _build(context: dict[str, object], name: str) -> None:
    try:
        context["built"] = build_data_source(name)
    except UnknownSourceError as exc:
        context["error"] = exc


@when(parsers.parse('I register another source also named "{name}"'))
def _register_clash(context: dict[str, object], name: str) -> None:
    try:
        register(_make_source(name))
        context["reg_error"] = None
    except ValueError as exc:
        context["reg_error"] = exc


@then(parsers.parse('I get a DataSource whose name is "{name}"'))
def _got_source(context: dict[str, object], name: str) -> None:
    built = context["built"]
    assert isinstance(built, DataSource)
    assert built.name == name


@then("an UnknownSourceError is raised naming the known sources")
def _unknown(context: dict[str, object]) -> None:
    error = context["error"]
    assert isinstance(error, UnknownSourceError)
    assert str(context["registered"]) in str(error)


@then("a registration error is raised")
def _reg_error(context: dict[str, object]) -> None:
    assert isinstance(context["reg_error"], ValueError)
