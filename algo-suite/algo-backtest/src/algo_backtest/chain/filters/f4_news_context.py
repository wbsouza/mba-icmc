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

Both thresholds are the `news_context` section of the strategy's `config.yaml`
(`parse_news_context_config`, 2026-09-27 amendment, story 09), never hardcoded, and
independently null-disableable the same way RiskGuard's caps are.

`direction_source` (story 14, the rule-only news strategy) chooses where F4's direction
comes from once the veto has not fired: `sentiment` (the default, the behaviour above) or
`intensity` — BUY when the day's event_intensity is at or above `intensity_buy_threshold`,
SELL at or below `intensity_sell_threshold`, NEUTRAL between; `intensity_sign: -1` swaps
BUY and SELL so the sign convention of the Goldstein reading is a registered experiment
cell rather than a guess. With `intensity` as the source F4 can be the chain's terminal
filter (`terminal_filter: f4_news_context`, no F7).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.chain.params import optional_choice, optional_number, require_number
from algo_backtest.months import BAR_DURATION, months_between
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path
from algo_score.paths import symbol_path
from algo_score.scorers.models import SymbolSentimentFeature

_FILTER_NAME = "f4_news_context"
_EVENT_KIND = "gdelt"
_SENTIMENT_SCORER = "lm"

_SECTION = "news_context"
_SENTIMENT, _INTENSITY = "sentiment", "intensity"
_DIRECTION_SOURCES = frozenset({_SENTIMENT, _INTENSITY})
_INTENSITY_KEYS = ("intensity_buy_threshold", "intensity_sell_threshold")


@dataclass(frozen=True)
class NewsContextConfig:
    """The `news_context.*` parameters; a `None` threshold disables that half of the filter.

    - ``event_intensity_veto_threshold``: a GDELT ``event_intensity`` (mean daily
      Goldstein Scale, roughly ``[-10, 10]``, more negative = more conflictual) at or
      below this value counts as an "active high-risk event" and vetoes. ``None``
      disables the veto path entirely (F4 never vetoes).
    - ``sentiment_direction_threshold``: the minimum polarity *magnitude* required to
      recommend a direction from net sentiment; below it (or with no sentiment data at
      all) F4 ABSTAINs rather than guess. ``None`` disables the direction-recommendation
      path entirely (F4 only ever vetoes or ABSTAINs).
    - ``direction_source``: ``sentiment`` (the above) or ``intensity`` — the direction
      comes from the event intensity itself: BUY at or above
      ``intensity_buy_threshold``, SELL at or below ``intensity_sell_threshold``,
      NEUTRAL in between (both required, buy strictly above sell); ``intensity_sign``
      ``-1`` swaps BUY and SELL.
    """

    event_intensity_veto_threshold: float | None
    sentiment_direction_threshold: float | None
    direction_source: str = _SENTIMENT
    intensity_buy_threshold: float | None = None
    intensity_sell_threshold: float | None = None
    intensity_sign: int = 1


def parse_news_context_config(section: Mapping[str, Any], *, strategy: str) -> NewsContextConfig:
    """F4's parameters from a strategy config.yaml `news_context` section (fail fast).

    Raises:
        ValueError: a threshold key is absent (an explicit `null` disables that half
            instead) or not a number; `direction_source` is not `sentiment`/`intensity`;
            with `intensity`, a missing intensity threshold or a buy threshold not
            strictly above the sell one; with `sentiment`, an intensity threshold that
            would be silently ignored; `intensity_sign` other than 1 or -1.
    """
    source = optional_choice(
        section, "direction_source", default=_SENTIMENT, choices=_DIRECTION_SOURCES,
        section=_SECTION, strategy=strategy,
    )
    buy, sell = _intensity_thresholds(section, source, strategy)
    return NewsContextConfig(
        event_intensity_veto_threshold=optional_number(
            section, "event_intensity_veto_threshold", section=_SECTION, strategy=strategy
        ),
        sentiment_direction_threshold=optional_number(
            section, "sentiment_direction_threshold", section=_SECTION, strategy=strategy
        ),
        direction_source=source,
        intensity_buy_threshold=buy,
        intensity_sell_threshold=sell,
        intensity_sign=_intensity_sign(section, strategy),
    )


def _intensity_thresholds(
    section: Mapping[str, Any], source: str, strategy: str
) -> tuple[float | None, float | None]:
    """The two intensity thresholds: required and ordered under `intensity`, refused
    under `sentiment` (they would change nothing, so their presence is a config error)."""
    if source == _SENTIMENT:
        stray = [key for key in _INTENSITY_KEYS if key in section]
        if stray:
            raise ValueError(
                f"strategy {strategy!r}: {_SECTION} declares {stray!r} but direction_source is "
                f"'{_SENTIMENT}' — set direction_source: {_INTENSITY} or remove the thresholds"
            )
        return None, None
    buy = require_number(section, "intensity_buy_threshold", section=_SECTION, strategy=strategy)
    sell = require_number(section, "intensity_sell_threshold", section=_SECTION, strategy=strategy)
    if buy <= sell:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.intensity_buy_threshold ({buy}) must be strictly "
            f"above intensity_sell_threshold ({sell}) — the NEUTRAL band between them cannot "
            "be empty or inverted"
        )
    return buy, sell


def _intensity_sign(section: Mapping[str, Any], strategy: str) -> int:
    """`intensity_sign`: 1 (default) or -1, an integer, never a bool or another number."""
    value = section.get("intensity_sign", 1)
    if isinstance(value, bool) or not isinstance(value, int) or value not in (1, -1):
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.intensity_sign must be 1 or -1, got {value!r}"
        )
    return value


def news_context_mapping(config: NewsContextConfig) -> dict[str, Any]:
    """The effective values as a plain mapping, for the resolved config (defaults included;
    the intensity thresholds only under `direction_source: intensity`)."""
    mapping: dict[str, Any] = {
        "event_intensity_veto_threshold": config.event_intensity_veto_threshold,
        "sentiment_direction_threshold": config.sentiment_direction_threshold,
        "direction_source": config.direction_source,
        "intensity_sign": config.intensity_sign,
    }
    if config.direction_source == _INTENSITY:
        mapping["intensity_buy_threshold"] = config.intensity_buy_threshold
        mapping["intensity_sell_threshold"] = config.intensity_sell_threshold
    return mapping


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


# A minute bar is decided at its *end* (LEAN's `self.time` in on_data), so a run over the
# inclusive [start, end] days evaluates F4 at decision minutes start 00:01 ... (end + 1)
# 00:00 UTC — one minute past the last requested day, possibly in the next month's
# partition. This is the single coverage contract preflight, loading and remediation use.


def decision_window(start: date, end: date) -> tuple[datetime, datetime]:
    """First and last F4 decision minute of a run over the inclusive [start, end] days."""
    first = datetime.combine(start, time(), UTC) + BAR_DURATION
    last = datetime.combine(end + timedelta(days=1), time(), UTC)
    return first, last


def news_build_command(start: date, end: date) -> str:
    """The `algo-score events` invocation that covers a [start, end] run's decision window."""
    first, last = decision_window(start, end)
    return f"algo-score events --kind gdelt --from {first.date()} --to {last.date()}"


def news_coverage_problems(data_root: Path, pair: str, start: date, end: date) -> list[str]:
    """Why the event features cannot serve a [start, end] run (empty when they can).

    Checks what F4 will actually look up, not just which files exist: every partition
    the decision window touches must exist, and *every* decision minute in the window —
    first to last, interior included — must carry an event_intensity (a partition built
    through `end` alone lacks the final bar's `end + 1` 00:00 decision; one built in
    pieces can have interior gaps). The event grid covers every UTC minute, so this is
    exact regardless of which minutes LEAN later delivers. Lets the `run` CLI reject the
    run on the host before a LEAN container starts.
    """
    first, last = decision_window(start, end)
    missing = [
        str(event_feature_path(data_root, _EVENT_KIND, year, month))
        for year, month in months_between(first.date(), last.date())
        if not event_feature_path(data_root, _EVENT_KIND, year, month).exists()
    ]
    if missing:
        return [f"missing GDELT event-feature partitions {missing}"]
    covered = load_news_context_window(data_root, pair, start, end).event_intensity
    uncovered = [minute for minute in _minutes(first, last) if minute not in covered]
    if not uncovered:
        return []
    if len(uncovered) == 1:
        return [f"no GDELT event_intensity at decision minute {uncovered[0].isoformat()}"]
    return [
        f"no GDELT event_intensity at {len(uncovered)} decision minutes (first "
        f"{uncovered[0].isoformat()}, last {uncovered[-1].isoformat()})"
    ]


def _minutes(first: datetime, last: datetime) -> Iterator[datetime]:
    """Every minute from `first` through `last`, inclusive, lazily (multi-year windows)."""
    minute = first
    while minute <= last:
        yield minute
        minute += BAR_DURATION


def load_news_context_window(
    data_root: Path, pair: str, start: date, end: date
) -> NewsContextIndex:
    """Merge every partition a [start, end] run's decision window touches into one index.

    `load_news_context_index` is scoped to a single (year, month) partition; the
    decision window (`decision_window`) may cross month boundaries — including into the
    month after `end` for the final bar's `end + 1` 00:00 decision.
    `sentiment_source_present` is true only if *every* touched month had its sentiment
    Parquet — claiming a source for the whole run when some months lacked one would
    mislabel those months' audit rows.

    Raises:
        ValueError: if any touched month's GDELT event-feature Parquet is missing.
    """
    first, last = decision_window(start, end)
    event_intensity: dict[datetime, float] = {}
    sentiment_polarity: dict[tuple[datetime, str], float] = {}
    sentiment_everywhere = True
    for year, month in months_between(first.date(), last.date()):
        index = load_news_context_index(data_root, pair, year, month)
        event_intensity.update(index.event_intensity)
        sentiment_polarity.update(index.sentiment_polarity)
        sentiment_everywhere = sentiment_everywhere and index.sentiment_source_present
    return NewsContextIndex(
        event_intensity=event_intensity,
        sentiment_polarity=sentiment_polarity,
        sentiment_source_present=sentiment_everywhere,
    )


def _event_intensity_at(index: NewsContextIndex, timestamp: datetime) -> float:
    """Read the required event_intensity for `timestamp`, failing fast if uncovered."""
    intensity = index.event_intensity.get(timestamp)
    if intensity is None:
        raise ValueError(
            f"{_FILTER_NAME}: no GDELT event_intensity for timestamp {timestamp!r} — the "
            "materialized partitions do not cover this decision minute; rebuild them via "
            "`algo-score events --kind gdelt` through the day after the run's last day."
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


def _intensity_recommendation(intensity: float, config: NewsContextConfig) -> Recommendation:
    """BUY at or above the buy threshold, SELL at or below the sell one, NEUTRAL between —
    then swapped when `intensity_sign` is -1."""
    assert config.intensity_buy_threshold is not None
    assert config.intensity_sell_threshold is not None
    if intensity >= config.intensity_buy_threshold:
        recommendation = Recommendation.BUY
    elif intensity <= config.intensity_sell_threshold:
        recommendation = Recommendation.SELL
    else:
        return Recommendation.NEUTRAL
    if config.intensity_sign == -1:
        return Recommendation.SELL if recommendation is Recommendation.BUY else Recommendation.BUY
    return recommendation


@dataclass
class F4NewsContextFilter:
    """The chain's news-context gate: implements `Filter.apply()`."""

    index: NewsContextIndex
    config: NewsContextConfig

    def apply(self, state: ExecutionState) -> FilterResult:
        """VETO on an active high-risk event; otherwise recommend by the configured
        direction source (net sentiment, else ABSTAIN; or the intensity thresholds)."""
        intensity = _event_intensity_at(self.index, state.timestamp)
        if _is_high_risk(intensity, self.config.event_intensity_veto_threshold):
            return self._result(
                Recommendation.ABSTAIN,
                f"active high-risk event: event_intensity={intensity:.4f} <= veto "
                f"threshold {self.config.event_intensity_veto_threshold:.4f}",
                intensity, veto=True,
            )
        if self.config.direction_source == _INTENSITY:
            return self._intensity_result(intensity)
        return self._sentiment_result(state, intensity)

    def _intensity_result(self, intensity: float) -> FilterResult:
        """Direction from the event intensity itself against the two thresholds."""
        recommendation = _intensity_recommendation(intensity, self.config)
        return self._result(
            recommendation,
            f"event_intensity={intensity:.4f} vs intensity_buy_threshold="
            f"{self.config.intensity_buy_threshold} / intensity_sell_threshold="
            f"{self.config.intensity_sell_threshold} (intensity_sign="
            f"{self.config.intensity_sign}): {recommendation.value}",
            intensity,
        )

    def _sentiment_result(self, state: ExecutionState, intensity: float) -> FilterResult:
        """Direction from net per-symbol sentiment when it clears the threshold, else ABSTAIN."""
        polarity = self.index.sentiment_polarity.get((state.timestamp, state.pair))
        recommendation = _sentiment_recommendation(
            polarity, self.config.sentiment_direction_threshold
        )
        if recommendation is None:
            return self._result(
                Recommendation.ABSTAIN,
                f"no active high-risk event (event_intensity={intensity:.4f}); no clear "
                f"net sentiment signal for {state.pair} at this timestamp",
                intensity,
            )
        assert polarity is not None
        return self._result(
            recommendation,
            f"net sentiment polarity={polarity:.4f} for {state.pair} "
            f"(event_intensity={intensity:.4f})",
            intensity, sentiment=polarity,
        )

    def _result(
        self,
        recommendation: Recommendation,
        reason: str,
        intensity: float,
        *,
        veto: bool = False,
        sentiment: float | None = None,
    ) -> FilterResult:
        """One F4 result: the intensity always enriched, the sentiment when it decided."""
        enrichment: dict[str, object] = {"news_event_intensity": intensity}
        if sentiment is not None:
            enrichment["news_sentiment_score"] = sentiment
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=recommendation,
            reason=reason,
            veto=veto,
            enrichment=enrichment,
            metadata={"sentiment_source_present": self.index.sentiment_source_present},
        )
