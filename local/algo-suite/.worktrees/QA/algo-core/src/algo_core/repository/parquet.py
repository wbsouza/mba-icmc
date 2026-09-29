"""Parquet-backed Repository: pyarrow writes and reads a single Parquet file."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import pyarrow.parquet as pq
from pydantic import BaseModel

from algo_core.repository import serde
from algo_core.repository.base import Repository

M = TypeVar("M", bound=BaseModel)


class ParquetRepository(Repository[M]):
    """Stores value objects as a Parquet file (the canonical writer)."""

    def __init__(self, model: type[M], path: Path) -> None:
        """Bind the repository to a value-object type and a Parquet file path."""
        self._model = model
        self._path = path

    def put(self, items: Sequence[M]) -> None:
        """Write the batch to the Parquet file."""
        serde.write_table(self._path, serde.to_table(items))

    def read_all(self) -> list[M]:
        """Read the Parquet file and validate each row into the model type."""
        table = pq.read_table(self._path)  # type: ignore[no-untyped-call]  # pyarrow.parquet is untyped
        return serde.from_table(table, self._model)

    def exists(self) -> bool:
        """Report whether the Parquet file exists."""
        return self._path.exists()
