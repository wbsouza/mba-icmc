"""Serialization between pydantic value objects and Arrow/Parquet.

Shared by every Repository backend so the value-object <-> Parquet mapping lives
in one place.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


def to_table(items: Sequence[BaseModel]) -> pa.Table:
    """Convert value objects to an Arrow table via their dict representation."""
    return pa.Table.from_pylist([item.model_dump() for item in items])


def write_table(path: Path, table: pa.Table) -> None:
    """Write an Arrow table to a Parquet file, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)  # type: ignore[no-untyped-call]  # pyarrow.parquet is untyped


def from_table(table: pa.Table, model: type[M]) -> list[M]:
    """Validate each Arrow row into the value-object type ``model``."""
    return [model.model_validate(row) for row in table.to_pylist()]
