"""F4 — News-context filter: wires Spec 03 (`algo-score`) output into the filter chain.

"Recommends direction by net sentiment; vetoes on active high-risk events"
(`specs.md` §11.3.2). Unlike F1/F5/F6, F4 is the one filter in the chain with a real
external-data dependency: instead of a purely synthetic `state.features` contract, it
reads real `algo-score` Parquet outputs —

- **event-feature Parquet** (mandatory): `parquet/events/_features/gdelt/year=/month=/
  data.parquet` (`algo_score.events.models.GdeltFeature`), the forward-filled per-minute
  mean daily Goldstein Scale across GDELT's Events table. Every minute of a materialized
  month has a value (`events/build.py` forward-fills the whole grid), so this is the
  filter's fail-fast-if-absent veto input.
- **per-symbol sentiment Parquet** (best-effort): `parquet/sentiment/lm_symbol/year=/
  month=/data.parquet` (`algo_score.scorers.models.SymbolSentimentFeature`), the LM
  scorer's base-minus-quote polarity differential per FX pair. This is *sparse by
  construction* (most minutes have zero published articles) and, as of this story,
  genuinely absent for the pilot month: real per-article sentiment needs GDELT Web News
  NGrams 3.0 raw text, and a full calendar month of that raw feed is ~500 GB / ~90 hours
  of strictly sequential per-minute downloads at the current adapter's throughput — an
  order of magnitude more than this story's data-preparation budget (see
  `docs/technical-debt.md` TD-48). F4 treats a missing/sparse sentiment signal exactly
  like F1/F2/F3 treat "no information yet": ABSTAIN, not a hard failure — the *event*
  Parquet is the mandatory, always-real input; sentiment upgrades the filter's opinion
  when (and where) it exists.

Both thresholds are configured (`news_context.*` in `conf/backtest.yaml`), never
hardcoded — same `algo_core.config.resolve` hybrid policy F5/F6 use, and independently
null-disableable the same way RiskGuard's caps are.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_core.config import Impact, ParameterSpec, resolve
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path
from algo_score.paths import symbol_path
from algo_score.scorers.models import SymbolSentimentFeature

_FILTER_NAME = "f4_news_context"
_EVENT_KIND = "gdelt"
_SENTIMENT_SCORER = "lm"

SCHEMA_VERSION = 1

_SCHEMA: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        name="news_context.event_intensity_veto_threshold", impact=Impact.TRADING, nullable=True
    ),
    ParameterSpec(
        name="news_context.sentiment_direction_threshold", impact=Impact.TRADING, nullable=True
    ),
)


@dataclass(frozen=True)
class NewsContextConfig:
    """The two `news_context.*` thresholds; `None` disables that half of the filter.

    - ``event_intensity_veto_threshold``: a GDELT ``event_intensity`` (mean daily
      Goldstein Scale, roughly ``[-10, 10]``, more negative = more conflictual) at or
      below this value counts as an "active high-risk event" and vetoes. ``None``
      disables the veto path entirely (F4 never vetoes).
    - ``sentiment_direction_threshold``: the minimum polarity *magnitude* required to
      recommend a direction from net sentiment; below it (or with no sentiment data at
      all) F4 ABSTAINs rather than guess. ``None`` disables the direction-recommendation
      path entirely (F4 only ever vetoes or ABSTAINs).
    """

    event_intensity_veto_threshold: float | None
    sentiment_direction_threshold: float | None


def load_news_context_config() -> NewsContextConfig:
    """Resolve the two `news_context.*` thresholds via the shared `algo_core.config` loader.

    Raises:
        ConfigError: (`MissingTradingParameter`) if a threshold is absent from config
            rather than explicitly `null`-disabled — a hard stop, per CLAUDE.md's
            fail-fast policy.
    """
    result = resolve("backtest", _SCHEMA, SCHEMA_VERSION)
    values = result.values
    return NewsContextConfig(
        event_intensity_veto_threshold=values["news_context.event_intensity_veto_threshold"],
        sentiment_direction_threshold=values["news_context.sentiment_direction_threshold"],
    )


@dataclass(frozen=True)
class NewsContextIndex:
    """An in-memory, per-minute index built from one month's real Spec 03 Parquet.

    ``sentiment_source_present`` records whether the sentiment Parquet *file* existed at
    load time — distinct from a per-minute miss in ``sentiment_polarity`` (no articles
    that minute), so `FilterResult.metadata` can tell "no Spec 03 sentiment output yet
    materialized" apart from "materialized, but this minute had nothing to say" during
    audit review of `decisions.parquet`.
    """

    event_intensity: dict[datetime, float]
    sentiment_polarity: dict[tuple[datetime, str], float]
    sentiment_source_present: bool


def load_news_context_index(
    data_root: Path, pair: str, year: int, month: int
) -> NewsContextIndex:
    """Load one pair-month's real GDELT event-intensity + per-symbol sentiment Parquet.

    The GDELT event-feature Parquet is mandatory: F4's veto path has nothing to read
    without it, so a missing file fails fast here rather than surfacing as a confusing
    per-bar `KeyError` later. The sentiment Parquet is best-effort: its absence is a
    real, expected, currently-tracked state (see this module's docstring and TD-48), not
    a data-contract violation, so it degrades to an empty index rather than raising.
    """
    event_path = event_feature_path(data_root, _EVENT_KIND, year, month)
    if not event_path.exists():
        raise ValueError(
            f"{_FILTER_NAME}: missing real Spec 03 GDELT event-feature Parquet at "
            f"{event_path} — build it first: `algo-score events --kind gdelt "
            f"--month {year:04d}-{month:02d}`"
        )
    event_rows = ParquetRepository(GdeltFeature, event_path).read_all()
    event_intensity = {
        row.timestamp: row.event_intensity
        for row in event_rows
        if row.event_intensity is not None
    }

    sentiment_source = symbol_path(data_root, _SENTIMENT_SCORER, year, month)
    sentiment_source_present = sentiment_source.exists()
    sentiment_polarity: dict[tuple[datetime, str], float] = {}
    if sentiment_source_present:
        sentiment_rows = ParquetRepository(SymbolSentimentFeature, sentiment_source).read_all()
        sentiment_polarity = {
            (row.timestamp, row.symbol): row.polarity
            for row in sentiment_rows
            if row.symbol == pair and row.polarity is not None
        }
    return NewsContextIndex(
        event_intensity=event_intensity,
        sentiment_polarity=sentiment_polarity,
        sentiment_source_present=sentiment_source_present,
    )


def _event_intensity_at(index: NewsContextIndex, timestamp: datetime) -> float:
    """Read the required event_intensity for `timestamp`, failing fast if uncovered."""
    intensity = index.event_intensity.get(timestamp)
    if intensity is None:
        raise ValueError(
            f"{_FILTER_NAME}: no GDELT event_intensity for timestamp {timestamp!r} — the "
            "materialized month partition does not cover this minute; rebuild it via "
            "`algo-score events --kind gdelt`."
        )
    return intensity


def _is_high_risk(intensity: float, threshold: float | None) -> bool:
    """Whether `intensity` crosses the configured veto threshold (disabled if `None`)."""
    return threshold is not None and intensity <= threshold


def _sentiment_recommendation(
    polarity: float | None, threshold: float | None
) -> Recommendation | None:
    """BUY/SELL by sentiment sign if it clears the direction threshold, else `None` (ABSTAIN).

    Zero polarity is always no-signal, even when `threshold` is `0.0`: `abs(polarity) <
    threshold` never rejects a zero polarity against a zero threshold (`0.0 < 0.0` is
    `False`), which would otherwise fall through to `Recommendation.SELL` — silently
    turning "no sentiment recorded" into a directional call.
    """
    if polarity is None or threshold is None or polarity == 0.0 or abs(polarity) < threshold:
        return None
    return Recommendation.BUY if polarity > 0.0 else Recommendation.SELL


@dataclass
class F4NewsContextFilter:
    """The chain's news-context gate: implements `Filter.apply()`."""

    index: NewsContextIndex
    config: NewsContextConfig = field(default_factory=load_news_context_config)

    def apply(self, state: ExecutionState) -> FilterResult:
        """VETO on an active high-risk event; otherwise recommend by net sentiment or ABSTAIN."""
        intensity = _event_intensity_at(self.index, state.timestamp)
        if _is_high_risk(intensity, self.config.event_intensity_veto_threshold):
            return FilterResult(
                filter_name=_FILTER_NAME,
                recommendation=Recommendation.ABSTAIN,
                reason=(
                    f"active high-risk event: event_intensity={intensity:.4f} <= veto "
                    f"threshold {self.config.event_intensity_veto_threshold:.4f}"
                ),
                veto=True,
                enrichment={"news_event_intensity": intensity},
                metadata={"sentiment_source_present": self.index.sentiment_source_present},
            )
        polarity = self.index.sentiment_polarity.get((state.timestamp, state.pair))
        recommendation = _sentiment_recommendation(
            polarity, self.config.sentiment_direction_threshold
        )
        if recommendation is None:
            return FilterResult(
                filter_name=_FILTER_NAME,
                recommendation=Recommendation.ABSTAIN,
                reason=(
                    f"no active high-risk event (event_intensity={intensity:.4f}); no clear "
                    f"net sentiment signal for {state.pair} at this timestamp"
                ),
                enrichment={"news_event_intensity": intensity},
                metadata={"sentiment_source_present": self.index.sentiment_source_present},
            )
        assert polarity is not None
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=recommendation,
            reason=(
                f"net sentiment polarity={polarity:.4f} for {state.pair} "
                f"(event_intensity={intensity:.4f})"
            ),
            enrichment={"news_event_intensity": intensity, "news_sentiment_score": polarity},
            metadata={"sentiment_source_present": self.index.sentiment_source_present},
        )
