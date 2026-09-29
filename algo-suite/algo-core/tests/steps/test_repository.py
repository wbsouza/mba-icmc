"""Step definitions for repository.feature (pytest-bdd)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
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
_BAR_SCHEMA = pa.schema([("ts", pa.int64()), ("close", pa.float64())])


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
    state["path"] = path


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


@when("I put 0 bars with the bar schema")
def _put_empty_with_schema(state: dict[str, object]) -> None:
    repo = state["repo"]
    assert isinstance(repo, ParquetRepository)
    repo.put([], schema=_BAR_SCHEMA)


@then("the written file has the ts and close columns")
def _written_columns(state: dict[str, object]) -> None:
    path = state["path"]
    assert isinstance(path, Path)
    table = pq.read_table(path)
    assert table.column_names == ["ts", "close"]


@then("it has 0 rows")
def _zero_rows(state: dict[str, object]) -> None:
    path = state["path"]
    assert isinstance(path, Path)
    table = pq.read_table(path)
    assert table.num_rows == 0


@given("duckdb is not installed")
def _duckdb_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate a real absence: drop any cached modules, then poison `sys.modules`.

    `sys.modules["duckdb"] = None` makes any subsequent `import duckdb` raise
    `ImportError` (a standard, well-documented Python import-system behavior) --
    a closer simulation of the pinned LEAN container (no duckdb package at all) than
    mocking `builtins.__import__` would be. `monkeypatch` restores every entry this
    touches after the scenario, so this cannot leak into other tests.

    Deleting a submodule from `sys.modules` alone is not enough: Python also binds it
    as an attribute on its *parent* package object as a side effect of the original
    import, and `from algo_core import duck` would silently find that stale attribute
    without re-running `duck.py` (and its own `import duckdb`) at all. `algo_core.duck`
    hangs off the `algo_core` package itself (not `algo_core.repository`, which this
    step's own reimport already replaces wholesale), so its stale attribute is cleared
    explicitly here.
    """
    import algo_core

    # The fresh imports in the When steps rebind `algo_core.repository` to a new module
    # object; pin the original so teardown restores it and later tests never see two
    # distinct `ParquetRepository` classes.
    if hasattr(algo_core, "repository"):
        monkeypatch.setattr(algo_core, "repository", algo_core.repository)
    for name in [
        m for m in sys.modules if m == "duckdb" or m.startswith("algo_core.repository")
        or m.startswith("algo_core.duck")
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, "duckdb", None)
    monkeypatch.delattr(algo_core, "duck", raising=False)


@when("algo_core.repository.parquet is imported fresh")
def _import_parquet_module(state: dict[str, object]) -> None:
    state["parquet_module"] = importlib.import_module("algo_core.repository.parquet")


@then("ParquetRepository is importable and duckdb was never imported")
def _parquet_importable_without_duckdb(state: dict[str, object]) -> None:
    module = state["parquet_module"]
    assert module.ParquetRepository.__name__ == "ParquetRepository"
    # The package __init__ ran (it is the parent of .parquet) without pulling in the
    # DuckDB adapter -- the eager import that used to fail in the LEAN container.
    assert "algo_core.repository" in sys.modules
    assert "algo_core.repository.duckdb" not in sys.modules


@when("algo_core.repository is imported fresh")
def _import_repository_package(state: dict[str, object]) -> None:
    state["repository_module"] = importlib.import_module("algo_core.repository")


@then("accessing DuckDBRepository on it raises ImportError")
def _duckdb_access_raises(state: dict[str, object]) -> None:
    module = state["repository_module"]
    with pytest.raises(ImportError):
        module.DuckDBRepository  # noqa: B018  (attribute access is the point under test)
