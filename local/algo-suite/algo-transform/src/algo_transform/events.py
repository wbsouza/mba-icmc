"""Typed event/index rows written by algo-transform."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class GdeltEvent(BaseModel):
    """One canonical row from the GDELT Events export table.

    ``date_added`` is GDELT's own ``DATEADDED`` column (when GDELT ingested this
    event) -- kept as availability provenance so downstream features never assume
    a day's aggregate was knowable before its slowest-arriving contributing event
    actually arrived.
    """

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
    date_added: datetime
    source_url: str


class GprEvent(BaseModel):
    """One verbatim headline GPR index observation."""

    model_config = ConfigDict(frozen=True)

    period: date
    gpr: float


class GdeltNewsArticle(BaseModel):
    """One article reconstructed from GDELT Web News NGrams 3.0 (TD-28).

    Field set matches ``algo_score.scorers.models.NewsArticle`` exactly (``id``,
    ``text``, ``publish_ts``) -- that contract is already fixed; this is the
    dataset it reads. ``id`` is the article's URL, GDELT's natural unique key.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    publish_ts: datetime
