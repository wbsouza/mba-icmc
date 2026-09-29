"""Step definitions for cache_factory.feature (pytest-bdd)."""

from __future__ import annotations

import pytest
from algo_core.cache import LruCache, build_cache
from pytest_bdd import parsers, scenarios, then, when

scenarios("../features/cache_factory.feature")


@pytest.fixture
def state() -> dict[str, object]:
    return {}


@when(parsers.parse('I build the cache backend "{name}"'))
def _build(state: dict[str, object], name: str) -> None:
    try:
        state["cache"] = build_cache(name)
    except ValueError as error:
        state["error"] = error


@then("it is an in-process LRU cache")
def _is_lru(state: dict[str, object]) -> None:
    assert isinstance(state["cache"], LruCache)


@then("building the backend fails")
def _fails(state: dict[str, object]) -> None:
    assert isinstance(state.get("error"), ValueError)
