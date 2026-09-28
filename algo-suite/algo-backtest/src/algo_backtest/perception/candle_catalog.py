"""Expanded multilabel candlestick catalog over closed bars (Story 22, T3).

Every enabled rule of the Story 22 rule ledger is evaluated on the final closed
bar and EVERY hit is reported (bullish, bearish and neutral) in stable id order
(CND-02). A rule that lacks its lookback appears as a WARMUP hit with polarity 0
(CND-04); a READY rule that did not fire is omitted. The six legacy ids are the
TA-Lib recognizers exactly as ``perception/candlestick.py`` calls them (default
candle settings, star penetration 0.3) so that ``legacy_label`` reproduces the
legacy selector (CND-09); the thirteen new rules are the ledger's explicit
formulas and never use TA-Lib. Pure: no chain, engine or LEAN dependency.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np

from algo_backtest.perception.candle_contract import (
    CATALOG,
    READY,
    WARMUP,
    CandleConfig,
    CandleEvidence,
    CandleHistory,
    ClosedBar,
    PatternHit,
)
from algo_backtest.perception.candlestick import PATTERN_POLARITY, select_pattern

RULE_VERSION: Final = "1"
DOJI_BODY_RATIO: Final = 0.10
DOJI_SHADOW_RATIO: Final = 0.10
LONG_LEG_RATIO: Final = 0.30
SPINNING_TOP_BODY_RATIO: Final = 0.30
UMBRELLA_SHADOW_MULTIPLE: Final = 2
UMBRELLA_OPPOSITE_RATIO: Final = 0.10
TREND_LOOKBACK: Final = 3
_STAR_PENETRATION = 0.3
_LEGACY_IDS = frozenset(PATTERN_POLARITY)


@dataclass(frozen=True)
class _Geometry:
    """Body, range and shadows of one closed bar, in price units."""

    open: float
    close: float
    body: float
    range: float
    upper: float
    lower: float

    @property
    def bullish(self) -> bool:
        """close above open."""
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        """close below open."""
        return self.close < self.open


def _geometry(bar: ClosedBar) -> _Geometry:
    """Derive the ledger's per-bar quantities from one closed bar."""
    top, bottom = max(bar.open, bar.close), min(bar.open, bar.close)
    return _Geometry(
        open=bar.open,
        close=bar.close,
        body=top - bottom,
        range=bar.high - bar.low,
        upper=bar.high - top,
        lower=bottom - bar.low,
    )


def _doji(bars: Sequence[ClosedBar]) -> bool:
    """body <= 0.10 range on a non-flat bar."""
    g = _geometry(bars[-1])
    return g.range > 0 and g.body <= DOJI_BODY_RATIO * g.range


def _doji_long_legged(bars: Sequence[ClosedBar]) -> bool:
    """A doji whose shorter shadow is at least 0.30 range."""
    g = _geometry(bars[-1])
    return _doji(bars) and min(g.upper, g.lower) >= LONG_LEG_RATIO * g.range


def _doji_dragonfly(bars: Sequence[ClosedBar]) -> bool:
    """A doji with at most 0.10 range of upper shadow."""
    g = _geometry(bars[-1])
    return _doji(bars) and g.upper <= DOJI_SHADOW_RATIO * g.range


def _doji_gravestone(bars: Sequence[ClosedBar]) -> bool:
    """A doji with at most 0.10 range of lower shadow."""
    g = _geometry(bars[-1])
    return _doji(bars) and g.lower <= DOJI_SHADOW_RATIO * g.range


def _spinning_top(bars: Sequence[ClosedBar]) -> bool:
    """0.10 range < body <= 0.30 range with both shadows at least the body."""
    g = _geometry(bars[-1])
    return (
        g.range > 0
        and DOJI_BODY_RATIO * g.range < g.body <= SPINNING_TOP_BODY_RATIO * g.range
        and g.upper >= g.body
        and g.lower >= g.body
    )


def _bullish_harami(bars: Sequence[ClosedBar]) -> bool:
    """A bullish body strictly inside the prior bearish body."""
    prior, current = _geometry(bars[-2]), _geometry(bars[-1])
    return (
        prior.bearish
        and current.bullish
        and current.open > prior.close
        and current.close < prior.open
    )


def _bearish_harami(bars: Sequence[ClosedBar]) -> bool:
    """A bearish body strictly inside the prior bullish body."""
    prior, current = _geometry(bars[-2]), _geometry(bars[-1])
    return (
        prior.bullish
        and current.bearish
        and current.open < prior.close
        and current.close > prior.open
    )


def _piercing_line(bars: Sequence[ClosedBar]) -> bool:
    """Opens below the prior close, closes above the prior body midpoint, short of its open."""
    prior, current = _geometry(bars[-2]), _geometry(bars[-1])
    mid = (prior.open + prior.close) / 2
    return (
        prior.bearish
        and current.bullish
        and current.open < prior.close
        and current.close > mid
        and current.close < prior.open
    )


def _dark_cloud_cover(bars: Sequence[ClosedBar]) -> bool:
    """Opens above the prior close, closes below the prior body midpoint, short of its open."""
    prior, current = _geometry(bars[-2]), _geometry(bars[-1])
    mid = (prior.open + prior.close) / 2
    return (
        prior.bullish
        and current.bearish
        and current.open > prior.close
        and current.close < mid
        and current.close > prior.open
    )


def _bullish_kicker(bars: Sequence[ClosedBar]) -> bool:
    """Opposite colours with the bullish open at or above the prior bearish open."""
    prior, current = _geometry(bars[-2]), _geometry(bars[-1])
    return prior.bearish and current.bullish and current.open >= prior.open


def _bearish_kicker(bars: Sequence[ClosedBar]) -> bool:
    """Opposite colours with the bearish open at or below the prior bullish open."""
    prior, current = _geometry(bars[-2]), _geometry(bars[-1])
    return prior.bullish and current.bearish and current.open <= prior.open


def _net(bars: Sequence[ClosedBar]) -> float:
    """close[t-1] - close[t-1-TREND_LOOKBACK]: the local trend proxy before the final bar."""
    return bars[-2].close - bars[-2 - TREND_LOOKBACK].close


def _hanging_man(bars: Sequence[ClosedBar]) -> bool:
    """Long lower shadow, tiny upper shadow, non-zero body, after a rising net(3)."""
    g = _geometry(bars[-1])
    return (
        g.body > 0
        and g.lower >= UMBRELLA_SHADOW_MULTIPLE * g.body
        and g.upper <= UMBRELLA_OPPOSITE_RATIO * g.range
        and _net(bars) > 0
    )


def _inverted_hammer(bars: Sequence[ClosedBar]) -> bool:
    """Long upper shadow, tiny lower shadow, non-zero body, after a falling net(3)."""
    g = _geometry(bars[-1])
    return (
        g.body > 0
        and g.upper >= UMBRELLA_SHADOW_MULTIPLE * g.body
        and g.lower <= UMBRELLA_OPPOSITE_RATIO * g.range
        and _net(bars) < 0
    )


_NEW_RULES: Final[dict[str, Callable[[Sequence[ClosedBar]], bool]]] = {
    "bearish_harami": _bearish_harami,
    "bearish_kicker": _bearish_kicker,
    "bullish_harami": _bullish_harami,
    "bullish_kicker": _bullish_kicker,
    "dark_cloud_cover": _dark_cloud_cover,
    "doji": _doji,
    "doji_dragonfly": _doji_dragonfly,
    "doji_gravestone": _doji_gravestone,
    "doji_long_legged": _doji_long_legged,
    "hanging_man": _hanging_man,
    "inverted_hammer": _inverted_hammer,
    "piercing_line": _piercing_line,
    "spinning_top": _spinning_top,
}


def legacy_scores(bars: Sequence[ClosedBar]) -> dict[str, int]:
    """The six legacy TA-Lib scores on the final bar, exactly as the legacy detector."""
    import talib

    opens, highs, lows, closes = np.asarray(
        [(bar.open, bar.high, bar.low, bar.close) for bar in bars], dtype=np.float64
    ).T
    engulfing = int(talib.CDLENGULFING(opens, highs, lows, closes)[-1])
    return {
        "bullish_engulfing": max(engulfing, 0),
        "bearish_engulfing": min(engulfing, 0),
        "hammer": int(talib.CDLHAMMER(opens, highs, lows, closes)[-1]),
        "shooting_star": int(talib.CDLSHOOTINGSTAR(opens, highs, lows, closes)[-1]),
        "morning_star": int(
            talib.CDLMORNINGSTAR(opens, highs, lows, closes, penetration=_STAR_PENETRATION)[-1]
        ),
        "evening_star": int(
            talib.CDLEVENINGSTAR(opens, highs, lows, closes, penetration=_STAR_PENETRATION)[-1]
        ),
    }


def _fired(rule: str, bars: Sequence[ClosedBar], scores: dict[str, int]) -> bool:
    """Whether a READY rule fires: TA-Lib sign for legacy ids, the ledger formula otherwise."""
    if rule in _LEGACY_IDS:
        return scores[rule] != 0
    return _NEW_RULES[rule](bars)


def evaluate_catalog(bars: Sequence[ClosedBar], config: CandleConfig) -> tuple[PatternHit, ...]:
    """Every enabled rule's hit on the final bar, in id order; WARMUP entries carry polarity 0.

    ``bars`` must already be validated (oldest first); a rule is READY once
    ``len(bars)`` reaches its registered lookback.
    """
    ready = [rule for rule in config.enabled_rules if len(bars) >= CATALOG[rule].lookback]
    scores = legacy_scores(bars) if any(rule in _LEGACY_IDS for rule in ready) else {}
    hits: list[PatternHit] = []
    for rule in sorted(config.enabled_rules):
        if rule not in ready:
            hits.append(PatternHit(rule, 0, RULE_VERSION, WARMUP))
        elif _fired(rule, bars, scores):
            hits.append(PatternHit(rule, CATALOG[rule].polarity, RULE_VERSION, READY))
    return tuple(hits)


def legacy_label(hits: Sequence[PatternHit]) -> str | None:
    """The legacy six-label selection from READY legacy hits only (new ids are ignored)."""
    return select_pattern(
        {hit.id: hit.polarity for hit in hits if hit.id in _LEGACY_IDS and hit.status == READY}
    )


class CandleCatalog:
    """Streaming multilabel recognizer bound to a validated, bounded closed-bar history."""

    def __init__(self, config: CandleConfig, pair: str) -> None:
        """Bind the configuration and the pair the evidence is reported for."""
        self._config = config
        self._pair = pair
        self._history = CandleHistory(config)

    @property
    def history(self) -> CandleHistory:
        """The bounded validated history behind the recognizer."""
        return self._history

    def update(self, bar: ClosedBar) -> CandleEvidence:
        """Consume one closed bar and report the evidence for it; invalid input raises first."""
        self._history.offer(bar)
        bars = self._history.bars
        hits = evaluate_catalog(bars, self._config)
        return CandleEvidence(
            pair=self._pair,
            timeframe_minutes=self._config.timeframe_minutes,
            close_time=bars[-1].close_time,
            history_count=len(bars),
            status=WARMUP if any(hit.status == WARMUP for hit in hits) else READY,
            hits=hits,
            catalog_version=self._config.catalog_version,
            max_history=self._config.max_history,
        )
