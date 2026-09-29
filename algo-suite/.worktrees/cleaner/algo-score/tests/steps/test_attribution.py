"""Step definitions for attribution.feature."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from algo_score.attribution import currencies_for_text, currency_features, symbol_features
from algo_score.scorers.models import ArticleScore, NewsArticle
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/attribution.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Per-scenario mutable context."""
    return {}


@given(parsers.re(r"an article about (?P<subject>.+)"))
def _article_subject(context: dict[str, object], subject: str) -> None:
    context["article"] = NewsArticle(
        id="article-1",
        text=subject,
        publish_ts=datetime(2020, 1, 5, 12, 0, tzinfo=UTC),
    )
    context["score"] = ArticleScore(
        article_id="article-1",
        publish_ts=datetime(2020, 1, 5, 12, 0, tzinfo=UTC),
        polarity=0.5,
        confidence=0.5,
        scorer="lm",
        model_version="test",
    )


@given("an FOMC article attributed to USD")
def _fomc_article(context: dict[str, object]) -> None:
    _article_subject(context, "an FOMC decision")


@given("an article concerning none of EUR, USD, JPY")
def _other_article(context: dict[str, object]) -> None:
    _article_subject(context, "Brazil local election")


@when("attribution runs")
def _attribution_runs(context: dict[str, object]) -> None:
    article = context["article"]
    score = context["score"]
    assert isinstance(article, NewsArticle)
    assert isinstance(score, ArticleScore)
    rows, dropped = currency_features([article], [score])
    context["currency_rows"] = rows
    context["dropped"] = dropped


@when("the feature layer forms pair features")
def _form_pairs(context: dict[str, object]) -> None:
    _attribution_runs(context)
    context["symbol_rows"] = symbol_features(context["currency_rows"])  # type: ignore[arg-type]


@then(parsers.re(r"it contributes to currency (?P<currency>[A-Z]{3})"))
def _contributes_currency(context: dict[str, object], currency: str) -> None:
    assert currency in currencies_for_text(context["article"].text)  # type: ignore[union-attr]


@then("both EURUSD and USDJPY consume the USD sentiment stream")
def _usd_feeds_pairs(context: dict[str, object]) -> None:
    symbols = {row.symbol for row in context["symbol_rows"]}  # type: ignore[union-attr]
    assert {"EURUSD", "USDJPY"} <= symbols


@then("it is excluded from per-currency output")
def _excluded(context: dict[str, object]) -> None:
    assert context["currency_rows"] == []


@then("it is counted in the run report, not raised as an error")
def _dropped_counted(context: dict[str, object]) -> None:
    assert context["dropped"] == 1
