"""Deterministic Loughran-McDonald-style lexicon sentiment scorer."""

from __future__ import annotations

import re
from datetime import datetime

from algo_score.scorers.models import ArticleScore

SCORER = "lm"
DEFAULT_MODEL_VERSION = "lm-fixture-v1"

_POSITIVE = {
    "benefit",
    "benefits",
    "gain",
    "gains",
    "improve",
    "improved",
    "positive",
    "profit",
    "profits",
    "raise",
    "raising",
    "stability",
    "strong",
    "success",
}
_NEGATIVE = {
    "concern",
    "crisis",
    "cut",
    "cuts",
    "decline",
    "default",
    "loss",
    "losses",
    "negative",
    "risk",
    "risks",
    "weak",
}
_TOKEN = re.compile(r"[A-Za-z]+")


class LexiconScorer:
    """Scores English financial text using a small LM-compatible fixture lexicon."""

    name = SCORER

    def __init__(self, model_version: str = DEFAULT_MODEL_VERSION) -> None:
        self.model_version = model_version

    def score(self, article_id: str, text: str, publish_ts: datetime) -> ArticleScore:
        """Return polarity/confidence for one article, or abstain for non-scorable text."""
        if not _looks_english(text):
            return ArticleScore(
                article_id=article_id,
                publish_ts=publish_ts,
                polarity=None,
                confidence=0.0,
                scorer=self.name,
                model_version=self.model_version,
                abstained=True,
            )
        positive, negative = _counts(text)
        total = positive + negative
        if total == 0:
            return ArticleScore(
                article_id=article_id,
                publish_ts=publish_ts,
                polarity=0.0,
                confidence=0.0,
                scorer=self.name,
                model_version=self.model_version,
            )
        polarity = (positive - negative) / total
        confidence = total / max(len(_tokens(text)), total)
        return ArticleScore(
            article_id=article_id,
            publish_ts=publish_ts,
            polarity=polarity,
            confidence=min(1.0, confidence),
            scorer=self.name,
            model_version=self.model_version,
            ambiguous=_is_ambiguous(text),
        )


def _counts(text: str) -> tuple[int, int]:
    """Count positive and negative lexicon hits."""
    tokens = _tokens(text)
    positive = sum(token in _POSITIVE for token in tokens)
    negative = sum(token in _NEGATIVE for token in tokens)
    return positive, negative


def _tokens(text: str) -> list[str]:
    """Tokenize text into lowercase ASCII words."""
    return [match.group(0).lower() for match in _TOKEN.finditer(text)]


def _looks_english(text: str) -> bool:
    """Cheap fixture-oriented English guard."""
    if not text.strip():
        return False
    ascii_letters = sum(char.isascii() and char.isalpha() for char in text)
    non_ascii_letters = sum((not char.isascii()) and char.isalpha() for char in text)
    return ascii_letters > 0 and non_ascii_letters == 0


def _is_ambiguous(text: str) -> bool:
    """Return true when text carries both positive and negative LM evidence."""
    positive, negative = _counts(text)
    return positive > 0 and negative > 0
