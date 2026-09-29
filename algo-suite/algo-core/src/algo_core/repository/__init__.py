"""Repository data-access pattern: one port, swappable backends.

`Repository` is the port; `ParquetRepository` is the canonical pyarrow writer and
`DuckDBRepository` reads the same store through DuckDB (composing the writer).
Callers depend only on `Repository`, so the backend is swappable with no caller
change (SPEC.md §13.5).

`DuckDBRepository` is imported lazily (module `__getattr__`, PEP 562): the pinned LEAN
container (Spec 04h) ships `pyarrow` but not `duckdb`, and every chain-driven algorithm
(`algos/{baseline,hybrid}/main.py`, via `chain/audit.py`) only ever needs
`ParquetRepository` — an eager top-level `duckdb` import here made that path fail with
`No module named 'duckdb'` even though nothing on it touches DuckDB.
"""

from typing import TYPE_CHECKING

from algo_core.repository.base import Repository
from algo_core.repository.parquet import ParquetRepository

if TYPE_CHECKING:
    from algo_core.repository.duckdb import DuckDBRepository

__all__ = ["DuckDBRepository", "ParquetRepository", "Repository"]


def __getattr__(name: str) -> object:
    """Resolve `DuckDBRepository` on first access, not at package-import time."""
    if name == "DuckDBRepository":
        from algo_core.repository.duckdb import DuckDBRepository

        return DuckDBRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
