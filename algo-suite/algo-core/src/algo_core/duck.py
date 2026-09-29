"""DuckDB connection and Parquet-reading helpers.

DuckDB is the analytical engine over the canonical Parquet store; these helpers
keep the wiring in one place so tools never re-implement it.
"""

from __future__ import annotations

import duckdb
from duckdb import DuckDBPyConnection, DuckDBPyRelation


def connect(database: str = ":memory:") -> DuckDBPyConnection:
    """Open a DuckDB connection (in-memory by default)."""
    return duckdb.connect(database)


def read_parquet(connection: DuckDBPyConnection, glob: str) -> DuckDBPyRelation:
    """Return a relation over the Parquet files matching ``glob``.

    ``glob`` is a DuckDB path pattern (e.g. ``parquet/forex/EURUSD/**/*.parquet``);
    DuckDB reads the files lazily, so callers can filter/aggregate before fetching.
    """
    return connection.read_parquet(glob)
