"""Step definitions for cache.feature (pytest-bdd)."""

from __future__ import annotations

import pytest
from algo_core.cache import LruCache
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/cache.feature")


@pytest.fixture
def context() -> dict[str, LruCache]:
    """Holds the cache under test (set by a Given)."""
    return {}


@pytest.fixture
def calls() -> dict[str, int]:
    return {}


@pytest.fixture
def results() -> list[int]:
    return []


@pytest.fixture
def by_key() -> dict[str, int]:
    return {}


@given("an empty in-process cache")
def _empty_cache(context: dict[str, LruCache]) -> None:
    context["cache"] = LruCache()


@given(parsers.parse("an in-process cache with capacity {capacity:d}"))
def _cache_with_capacity(context: dict[str, LruCache], capacity: int) -> None:
    context["cache"] = LruCache(maxsize=capacity)


@when(parsers.parse('I get key "{key}" computing {value:d}'))
def _get(
    context: dict[str, LruCache],
    calls: dict[str, int],
    results: list[int],
    by_key: dict[str, int],
    key: str,
    value: int,
) -> None:
    def compute() -> int:
        calls[key] = calls.get(key, 0) + 1
        return value

    result = context["cache"].get_or_compute(key, compute)
    results.append(result)
    by_key[key] = result


@then(parsers.parse("the results in order are {first:d} and {second:d}"))
def _results_order(results: list[int], first: int, second: int) -> None:
    assert results == [first, second]


@then(parsers.parse('key "{key}" holds {value:d}'))
def _holds(by_key: dict[str, int], key: str, value: int) -> None:
    assert by_key[key] == value


@then(parsers.parse('key "{key}" was computed {count:d} time'))
@then(parsers.parse('key "{key}" was computed {count:d} times'))
def _computed(calls: dict[str, int], key: str, count: int) -> None:
    assert calls.get(key, 0) == count
