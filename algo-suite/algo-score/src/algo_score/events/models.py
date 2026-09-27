"""Value objects for event-derived score features."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


@dataclass(frozen=True)
class EventFeatureReport:
    """Summary of a written event-feature run.

    ``rows`` counts the minutes this run (re)built — not the resulting partition sizes:
    a partial rebuild merges into existing partitions (``events/build.py``), so a
    one-day rebuild of an already-complete month reports 1,440 while the partition
    still holds the whole month.
    """

    kind: str
    rows: int
    output_root: Path


@dataclass(frozen=True)
class DailyValue:
    """One daily event-derived value before minute-grid expansion."""

    day: date
    value: float


class GprFeature(BaseModel):
    """One minute-bucketed GPR feature row."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    gpr: float | None


class GdeltFeature(BaseModel):
    """One minute-bucketed GDELT event-intensity feature row."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    event_intensity: float | None
