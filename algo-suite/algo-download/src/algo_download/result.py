"""Normalized download value objects: the vocabulary the orchestrator aggregates.

A source owns what a *unit* is (an hour, a 15-minute slot, a single file); the
orchestrator only ever sees a ``DownloadUnit`` plus a normalized ``UnitStatus``,
so one orchestrator serves every source. See ../../SPEC.md §2.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class UnitStatus(StrEnum):
    """The orchestrator-visible outcome of one unit of work."""

    WRITTEN = "written"   # fetched and persisted this run
    SKIPPED = "skipped"   # already on disk (idempotent resume)
    MISSING = "missing"   # provider has no data for this unit (not an error)
    FAILED = "failed"     # fetch did not complete (retried internally, gave up)


class DownloadUnit(BaseModel):
    """One source-native unit of work and its canonical raw destination."""

    model_config = ConfigDict(frozen=True)

    key: str
    raw_path: Path


class UnitResult(BaseModel):
    """The outcome of processing one unit."""

    model_config = ConfigDict(frozen=True)

    unit: DownloadUnit
    status: UnitStatus
    bytes: int = 0


class RunReport(BaseModel):
    """Aggregate of a run's per-unit results."""

    model_config = ConfigDict(frozen=True)

    results: tuple[UnitResult, ...]

    def count(self, status: UnitStatus) -> int:
        """Number of units that ended in ``status``."""
        return sum(1 for r in self.results if r.status is status)

    @property
    def exit_code(self) -> int:
        """``1`` if any unit FAILED, else ``0`` (MISSING gaps are not failures)."""
        return 1 if self.count(UnitStatus.FAILED) else 0
