"""Repository port: persist and read domain value objects, engine-agnostic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class Repository(ABC, Generic[M]):
    """Stores and retrieves value objects of type ``M`` behind a stable interface.

    Callers depend only on this port, never on the storage engine, so a backend
    swap (Parquet writer, DuckDB reader, a future server store) touches no caller
    (SPEC.md §13.5).
    """

    @abstractmethod
    def put(self, items: Sequence[M]) -> None:
        """Persist a batch of value objects."""

    @abstractmethod
    def read_all(self) -> list[M]:
        """Return all stored value objects."""

    @abstractmethod
    def exists(self) -> bool:
        """Report whether the backing store has been written."""
