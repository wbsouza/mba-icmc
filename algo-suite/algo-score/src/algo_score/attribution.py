"""Per-currency attribution and pair feature derivation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from algo_score.scorers.models import (
    ArticleScore,
    CurrencySentimentFeature,
    NewsArticle,
    SymbolSentimentFeature,
)

_KEYWORDS = {
    "EUR": ("eur", "euro", "ecb", "european central bank"),
    "USD": ("usd", "dollar", "fomc", "fed", "federal reserve"),
    "JPY": ("jpy", "yen", "boj", "bank of japan"),
}
_PAIRS = {"EURUSD": ("EUR", "USD"), "USDJPY": ("USD", "JPY")}


def currencies_for_text(text: str) -> tuple[str, ...]:
    """Return FX currencies mentioned by the article text."""
    lowered = text.lower()
    return tuple(
        currency
        for currency, keywords in _KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    )


def currency_features(
    articles: list[NewsArticle], scores: list[ArticleScore]
) -> tuple[list[CurrencySentimentFeature], int]:
    """Route scored articles to per-currency sentiment rows."""
    by_id = {article.id: article for article in articles}
    groups: dict[tuple[datetime, str], list[ArticleScore]] = defaultdict(list)
    dropped = 0
    for score in scores:
        currencies = currencies_for_text(by_id[score.article_id].text)
        if not currencies:
            dropped += 1
            continue
        for currency in currencies:
            groups[(score.publish_ts.replace(second=0, microsecond=0), currency)].append(score)
    rows = [
        CurrencySentimentFeature(
            timestamp=timestamp,
            entity=currency,
            polarity=_mean_polarity(items),
            confidence=_mean_confidence(items),
            n_articles=len(items),
            scorer=items[0].scorer,
            model_version=items[0].model_version,
        )
        for (timestamp, currency), items in sorted(groups.items())
    ]
    return rows, dropped


def symbol_features(rows: list[CurrencySentimentFeature]) -> list[SymbolSentimentFeature]:
    """Derive FX pair sentiment as base-minus-quote polarity differential."""
    by_key = {(row.timestamp, row.entity): row for row in rows}
    timestamps = sorted({row.timestamp for row in rows})
    features = (
        _pair_feature(
            timestamp, symbol, by_key.get((timestamp, base)), by_key.get((timestamp, quote))
        )
        for timestamp in timestamps
        for symbol, (base, quote) in _PAIRS.items()
    )
    return [feature for feature in features if feature is not None]


def _pair_feature(
    timestamp: datetime,
    symbol: str,
    base_row: CurrencySentimentFeature | None,
    quote_row: CurrencySentimentFeature | None,
) -> SymbolSentimentFeature | None:
    """Combine one pair's base/quote currency rows, or ``None`` if neither exists."""
    if base_row is None and quote_row is None:
        return None
    reference = base_row if base_row is not None else quote_row
    assert reference is not None
    present = [row for row in (base_row, quote_row) if row is not None]
    confidence = sum(row.confidence for row in present) / len(present)
    n_articles = sum(row.n_articles for row in present)
    return SymbolSentimentFeature(
        timestamp=timestamp,
        symbol=symbol,
        polarity=_polarity_or_zero(base_row) - _polarity_or_zero(quote_row),
        confidence=confidence,
        n_articles=n_articles,
        scorer=reference.scorer,
        model_version=reference.model_version,
    )


def _polarity_or_zero(row: CurrencySentimentFeature | None) -> float:
    """Return a currency row's polarity, or ``0.0`` when the row or its polarity is absent."""
    if row is None or row.polarity is None:
        return 0.0
    return row.polarity


def _mean_polarity(scores: list[ArticleScore]) -> float | None:
    """Return the average polarity across non-abstained article scores."""
    values = [score.polarity for score in scores if score.polarity is not None]
    return None if not values else sum(values) / len(values)


def _mean_confidence(scores: list[ArticleScore]) -> float:
    """Return the average confidence for a bucket of article scores."""
    if not scores:
        return 0.0
    return sum(score.confidence for score in scores) / len(scores)
