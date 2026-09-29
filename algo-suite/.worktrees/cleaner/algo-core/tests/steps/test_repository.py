"""Step definitions for repository.feature (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core.repository import DuckDBRepository, ParquetRepository, Repository
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/repository.feature")


class _Bar(BaseModel):
    """A sample value object for exercising the generic repository."""

    ts: int
    close: float


_BARS = [_Bar(ts=1, close=1.1), _Bar(ts=2, close=2.2)]


@pytest.fixture
def state() -> dict[str, object]:
    return {}


def _repo(state: dict[str, object]) -> Repository[_Bar]:
    repo = state["repo"]
    assert isinstance(repo, Repository)
    return repo


@given(parsers.parse('a "{backend}" repository for bars in the data directory'))
def _make_repo(state: dict[str, object], backend: str, tmp_path: Path) -> None:
    path = tmp_path / "bars.parquet"
    repos: dict[str, Repository[_Bar]] = {
        "parquet": ParquetRepository(_Bar, path),
        "duckdb": DuckDBRepository(_Bar, path),
    }
    state["repo"] = repos[backend]


@when("I put 2 bars")
def _put(state: dict[str, object]) -> None:
    _repo(state).put(_BARS)


@when("I read all bars")
def _read(state: dict[str, object]) -> None:
    state["read"] = _repo(state).read_all()


@then("I get the 2 bars back with the same values")
def _same(state: dict[str, object]) -> None:
    assert state["read"] == _BARS


@then("the repository reports it exists")
def _exists(state: dict[str, object]) -> None:
    assert _repo(state).exists() is True


@then("the repository reports it does not exist")
def _not_exists(state: dict[str, object]) -> None:
    assert _repo(state).exists() is False
