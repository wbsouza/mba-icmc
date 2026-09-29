"""Shared sentiment scoring value objects."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, field_validator


def _ensure_utc(value: datetime) -> datetime:
    """Reject naive/non-UTC timestamps at the scoring boundary."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"timestamp must be timezone-aware UTC; got {value!r}")
    return value


class NewsArticle(BaseModel):
    """Synthetic article fixture row consumed by the LM scorer."""

    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    publish_ts: datetime

    @field_validator("publish_ts")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class ArticleScore(BaseModel):
    """One per-article scorer output, cached by article/model version."""

    model_config = ConfigDict(frozen=True)

    article_id: str
    publish_ts: datetime
    polarity: float | None
    confidence: float
    scorer: str
    model_version: str
    abstained: bool = False
    ambiguous: bool = False

    @field_validator("publish_ts")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class SentimentFeature(BaseModel):
    """One minute-bucketed sentiment feature row."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    polarity: float | None
    confidence: float
    n_articles: int
    scorer: str
    model_version: str

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class CurrencySentimentFeature(BaseModel):
    """One minute-bucketed per-currency sentiment feature row."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    entity: str
    polarity: float | None
    confidence: float
    n_articles: int
    scorer: str
    model_version: str

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class SymbolSentimentFeature(BaseModel):
    """One derived per-symbol sentiment feature row."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    symbol: str
    polarity: float | None
    confidence: float
    n_articles: int
    scorer: str
    model_version: str

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return _ensure_utc(value)
