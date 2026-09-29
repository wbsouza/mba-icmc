"""Typed event/index rows written by algo-transform."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class GdeltEvent(BaseModel):
    """One canonical row from the GDELT Events export table."""

    model_config = ConfigDict(frozen=True)

    global_event_id: int
    event_date: date
    event_code: str
    goldstein_scale: float
    avg_tone: float
    actor1_code: str
    actor2_code: str
    num_mentions: int
    num_sources: int
    num_articles: int
    source_url: str


class GprEvent(BaseModel):
    """One verbatim headline GPR index observation."""

    model_config = ConfigDict(frozen=True)

    period: date
    gpr: float
