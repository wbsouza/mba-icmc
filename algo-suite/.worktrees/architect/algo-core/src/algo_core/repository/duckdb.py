"""DuckDB-backed Repository: analytical reads over the Parquet store.

Writing is pyarrow's job, so this repository *composes* a ParquetRepository for
`put`/`exists` and overrides only `read_all` to read through DuckDB's analytical
engine. Composition over inheritance: the DuckDB reader reuses the Parquet writer
rather than duplicating it.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from algo_core import duck
from algo_core.repository import serde
from algo_core.repository.base import Repository
from algo_core.repository.parquet import ParquetRepository

M = TypeVar("M", bound=BaseModel)


class DuckDBRepository(Repository[M]):
    """Reads value objects via DuckDB; delegates writing to a composed ParquetRepository."""

    def __init__(self, model: type[M], path: Path) -> None:
        """Bind to a value-object type and Parquet path; reuse a Parquet writer."""
        self._model = model
        self._path = path
        self._writer: ParquetRepository[M] = ParquetRepository(model, path)

    def put(self, items: Sequence[M]) -> None:
        """Write via the composed Parquet writer."""
        self._writer.put(items)

    def read_all(self) -> list[M]:
        """Read the Parquet store through DuckDB's analytical engine."""
        connection = duck.connect()
        table = duck.read_parquet(connection, str(self._path)).to_arrow_table()
        return serde.from_table(table, self._model)

    def exists(self) -> bool:
        """Delegate existence to the composed Parquet writer."""
        return self._writer.exists()
