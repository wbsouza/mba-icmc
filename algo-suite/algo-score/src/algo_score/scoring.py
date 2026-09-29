"""Orchestrate LM scoring, bucketing, and attribution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from algo_score.attribution import currency_features, symbol_features
from algo_score.bucket import bucket_scores
from algo_score.scorers.lexicon import DEFAULT_MODEL_VERSION, LexiconScorer
from algo_score.scorers.models import ArticleScore, NewsArticle
from algo_score.storage import (
    ScoreCache,
    read_articles,
    read_price_minutes,
    write_sentiment_outputs,
)


@dataclass(frozen=True)
class ScoreReport:
    """Summary of one scoring run."""

    articles: int
    computed: int
    dropped: int
    sentiment_path: Path


def run_lm_scoring(
    data_root: Path,
    source: str,
    start: date,
    end: date,
    *,
    model_version: str = DEFAULT_MODEL_VERSION,
) -> ScoreReport:
    """Score synthetic article text with the LM scorer and persist feature outputs."""
    articles = read_articles(data_root, source, start, end)
    scorer = LexiconScorer(model_version=model_version)
    scores, computed = _score_articles(articles, scorer, ScoreCache(data_root, "lm"))
    price_minutes = read_price_minutes(data_root)
    features = bucket_scores(scores, start, end, price_minutes=price_minutes)
    currency_rows, dropped = currency_features(articles, scores)
    symbol_rows = symbol_features(currency_rows)
    output_paths = write_sentiment_outputs(
        data_root,
        "lm",
        start.year,
        start.month,
        features=features,
        scores=scores,
        currency_rows=currency_rows,
        symbol_rows=symbol_rows,
    )
    return ScoreReport(
        articles=len(articles),
        computed=computed,
        dropped=dropped,
        sentiment_path=output_paths.sentiment,
    )


def _score_articles(
    articles: list[NewsArticle], scorer: LexiconScorer, cache: ScoreCache
) -> tuple[list[ArticleScore], int]:
    """Score articles through the cache and return ``(scores, computed_count)``."""
    computed = 0
    scores: list[ArticleScore] = []
    for article in articles:
        key = _cache_key(article, scorer.model_version)

        def compute(article: NewsArticle = article) -> ArticleScore:
            nonlocal computed
            computed += 1
            return scorer.score(article.id, article.text, article.publish_ts)

        scores.append(cache.get_or_compute(key, compute))
    return scores, computed


def _cache_key(article: NewsArticle, model_version: str) -> str:
    """Build a model-version-sensitive cache key for one article text."""
    digest = hashlib.sha256(article.text.encode()).hexdigest()
    published = article.publish_ts.isoformat()
    return f"lm:{model_version}:{article.id}:{published}:{digest}"
