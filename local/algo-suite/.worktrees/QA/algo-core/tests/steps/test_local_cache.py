"""Step definitions for local_cache.feature (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core.cache import LocalCache
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/local_cache.feature")


class _Doc(BaseModel):
    """A sample value object cached by the local cache."""

    id: int


@pytest.fixture
def state() -> dict[str, object]:
    return {"calls": 0, "reads": []}


def _cache(state: dict[str, object], slot: str = "cache") -> LocalCache:
    cache = state[slot]
    assert isinstance(cache, LocalCache)
    return cache


def _get(state: dict[str, object], slot: str, key: str, doc_id: int) -> None:
    def compute() -> _Doc:
        state["calls"] = int(state["calls"]) + 1  # type: ignore[call-overload]
        return _Doc(id=doc_id)

    result = _cache(state, slot).get_or_compute(key, compute)
    reads = state["reads"]
    assert isinstance(reads, list)
    reads.append(result)


@given("a local cache in a fresh directory")
def _make(state: dict[str, object], tmp_path: Path) -> None:
    state["dir"] = tmp_path
    state["cache"] = LocalCache(_Doc, tmp_path)


@when(parsers.parse('I get key "{key}" computing document {doc_id:d}'))
def _get_first(state: dict[str, object], key: str, doc_id: int) -> None:
    _get(state, "cache", key, doc_id)


@when("a second local cache opens the same directory")
def _second(state: dict[str, object]) -> None:
    directory = state["dir"]
    assert isinstance(directory, Path)
    state["cache2"] = LocalCache(_Doc, directory)


@when(parsers.parse('I get key "{key}" from the second cache computing document {doc_id:d}'))
def _get_second(state: dict[str, object], key: str, doc_id: int) -> None:
    _get(state, "cache2", key, doc_id)


@then(parsers.parse("both reads are document {doc_id:d}"))
def _both(state: dict[str, object], doc_id: int) -> None:
    reads = state["reads"]
    assert isinstance(reads, list)
    assert reads == [_Doc(id=doc_id), _Doc(id=doc_id)]


@then(parsers.parse("the second read is document {doc_id:d}"))
def _second_read(state: dict[str, object], doc_id: int) -> None:
    reads = state["reads"]
    assert isinstance(reads, list)
    assert reads[-1] == _Doc(id=doc_id)


@then(parsers.parse("the document was computed {count:d} time"))
@then(parsers.parse("the document was computed {count:d} times"))
def _computed(state: dict[str, object], count: int) -> None:
    assert state["calls"] == count


@when(parsers.parse('I cache a non-model value at key "{key}"'))
def _cache_bad(state: dict[str, object], key: str) -> None:
    try:
        _cache(state).get_or_compute(key, lambda: 42)
    except TypeError as error:
        state["error"] = error


@then("caching fails with a type error")
def _type_error(state: dict[str, object]) -> None:
    assert isinstance(state.get("error"), TypeError)
