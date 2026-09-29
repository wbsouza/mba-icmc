"""The ``DataSource`` port: the one abstraction the orchestrator depends on.

Every external feed is adapted to this interface (Strategy + Adapter). The
orchestrator never knows a source's unit shape or fetch mechanics — only
``plan`` / ``is_done`` / ``fetch`` in terms of ``DownloadUnit`` and
``UnitResult``. See ../../SPEC.md §2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from enum import StrEnum
from typing import ClassVar

from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, UnitResult


class RequestShape(StrEnum):
    """The CLI-facing request contract exposed by a download source."""

    INSTRUMENT_MONTHS = "instrument_months"
    GLOBAL_MONTHS = "global_months"
    WHOLE_WINDOW = "whole_window"


class DataSource(ABC):
    """A bulk-download source: plan units, skip done ones, fetch the rest."""

    name: ClassVar[str]
    request_shape: ClassVar[RequestShape] = RequestShape.INSTRUMENT_MONTHS

    @abstractmethod
    def plan(self, request: DownloadRequest) -> Iterator[DownloadUnit]:
        """Yield the source-native units for ``request``. No I/O, no network."""

    def is_done(self, unit: DownloadUnit) -> bool:
        """True iff the unit's raw artifact already exists (filesystem-only resume)."""
        return unit.raw_path.exists()

    @abstractmethod
    def fetch(self, unit: DownloadUnit) -> UnitResult:
        """Fetch and persist the unit's raw bytes, returning a normalized result."""
