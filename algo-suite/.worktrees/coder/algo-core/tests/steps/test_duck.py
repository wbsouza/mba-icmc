"""Step definitions for duck.feature (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core import duck
from duckdb import DuckDBPyConnection
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/duck.feature")


@pytest.fixture
def state() -> dict[str, object]:
    return {}


def _conn(state: dict[str, object]) -> DuckDBPyConnection:
    conn = state["conn"]
    assert isinstance(conn, DuckDBPyConnection)
    return conn


@when("I open a DuckDB connection")
def _open(state: dict[str, object]) -> None:
    state["conn"] = duck.connect()


@then(parsers.parse('querying "{sql}" returns {expected:d}'))
def _query(state: dict[str, object], sql: str, expected: int) -> None:
    row = _conn(state).execute(sql).fetchone()
    assert row is not None
    assert row[0] == expected


@given(parsers.parse("a Parquet file with {rows:d} rows in the data directory"))
def _write_parquet(state: dict[str, object], rows: int, tmp_path: Path) -> None:
    conn = duck.connect()
    target = tmp_path / "data.parquet"
    conn.execute(f"COPY (SELECT * FROM range({rows})) TO '{target}' (FORMAT PARQUET)")
    state["conn"] = conn
    state["dir"] = tmp_path


@when("I read every Parquet file in the data directory")
def _read(state: dict[str, object]) -> None:
    directory = state["dir"]
    assert isinstance(directory, Path)
    relation = duck.read_parquet(_conn(state), f"{directory}/*.parquet")
    state["count"] = len(relation.fetchall())


@then(parsers.parse("the row count is {count:d}"))
def _count(state: dict[str, object], count: int) -> None:
    assert state["count"] == count
