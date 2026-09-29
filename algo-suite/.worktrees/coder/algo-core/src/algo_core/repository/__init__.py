"""Repository data-access pattern: one port, swappable backends.

`Repository` is the port; `ParquetRepository` is the canonical pyarrow writer and
`DuckDBRepository` reads the same store through DuckDB (composing the writer).
Callers depend only on `Repository`, so the backend is swappable with no caller
change (SPEC.md §13.5).
"""

from algo_core.repository.base import Repository
from algo_core.repository.duckdb import DuckDBRepository
from algo_core.repository.parquet import ParquetRepository

__all__ = ["DuckDBRepository", "ParquetRepository", "Repository"]
