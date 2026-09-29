"""Minute bucketing for per-article sentiment scores."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from algo_score.scorers.models import ArticleScore, SentimentFeature


def bucket_scores(
    scores: list[ArticleScore],
    start: date,
    end: date,
    *,
    price_minutes: set[datetime] | None = None,
) -> list[SentimentFeature]:
    """Aggregate article scores to minute buckets, optionally aligned to price minutes."""
    groups: dict[datetime, list[ArticleScore]] = defaultdict(list)
    for score in scores:
        minute = score.publish_ts.replace(second=0, microsecond=0)
        if price_minutes is not None and minute not in price_minutes:
            continue
        groups[minute].append(score)
    if not scores:
        return []
    scorer = scores[0].scorer
    version = scores[0].model_version
    return [
        _feature(minute, groups.get(minute, []), scorer, version)
        for minute in _minutes(start, end)
        if price_minutes is None or minute in price_minutes
    ]


def _feature(
    minute: datetime, scores: list[ArticleScore], scorer: str, model_version: str
) -> SentimentFeature:
    """Build one minute feature from the scores assigned to that minute."""
    values = [score.polarity for score in scores if score.polarity is not None]
    confidence = sum(score.confidence for score in scores) / len(scores) if scores else 0.0
    return SentimentFeature(
        timestamp=minute,
        polarity=None if not values else sum(values) / len(values),
        confidence=confidence,
        n_articles=len(scores),
        scorer=scorer,
        model_version=model_version,
    )


def _minutes(start: date, end: date) -> list[datetime]:
    """Enumerate UTC minute starts across an inclusive date window."""
    cursor = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    stop = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    minutes: list[datetime] = []
    while cursor < stop:
        minutes.append(cursor)
        cursor += timedelta(minutes=1)
    return minutes
