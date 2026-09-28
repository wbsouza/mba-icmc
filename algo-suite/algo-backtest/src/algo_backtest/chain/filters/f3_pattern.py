"""F3 — candlestick pattern filter (specs.md §11.3.2, Spec 04c).

Recommends BUY/SELL on a detected pattern; ABSTAIN if none on the current closed bar.
With `pattern.detector: talib`, the shared perception layer supplies causal TA-Lib
labels in training and LEAN. The default remains disabled for historical models;
changing the detector requires retraining F7, not silently reusing old provenance.

**Feature-key contract** (read from `state.features`):

- ``candlestick_pattern`` (str | None): `None`/absent means no pattern was detected
  this bar. A present value must be one of the recognized pattern names below —
  canonical labels mapped from TA-Lib's signed `CDL*` outputs, for this filter's
  closed vocabulary. An unrecognized name is a data-contract violation
  (upstream produced something this filter's key catalogue doesn't cover) and raises,
  per the workspace's fail-fast policy.

ABSTAIN means "no opinion this bar" — F3 never vetoes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation

_SECTION = "pattern"
_BULLISH_DEFAULT = frozenset({"bullish_engulfing", "hammer", "morning_star"})
_BEARISH_DEFAULT = frozenset({"bearish_engulfing", "shooting_star", "evening_star"})


@dataclass(frozen=True)
class PatternConfig:
    """F3's vocabulary (the `pattern` section; 2026-09-27 amendment, story 09): which
    detected pattern names count as bullish and which as bearish."""

    bullish_patterns: frozenset[str] = _BULLISH_DEFAULT
    bearish_patterns: frozenset[str] = _BEARISH_DEFAULT
    detector: str = "disabled"

    @property
    def known_patterns(self) -> frozenset[str]:
        """Every pattern name the filter accepts."""
        return self.bullish_patterns | self.bearish_patterns


_KEYS = ("bullish_patterns", "bearish_patterns", "detector")


def _names(
    section: Mapping[str, Any], key: str, default: frozenset[str], strategy: str
) -> frozenset[str]:
    """One non-empty list of pattern-name strings, or the default when the key is absent."""
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, str) or not isinstance(value, list) or not value:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.{key} must be a non-empty list of pattern "
            f"names, got {value!r}"
        )
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"strategy {strategy!r}: {_SECTION}.{key} must contain only strings")
    return frozenset(value)


def parse_pattern_config(section: Mapping[str, Any], *, strategy: str) -> PatternConfig:
    """F3's vocabulary from the `pattern` section, defaulting a list it omits.

    Raises:
        ValueError: an unknown key, a list that is empty or not a list of strings, or a
            name present in both lists.
    """
    unknown = sorted(set(section) - set(_KEYS))
    if unknown:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION} has unknown keys {unknown!r}; known keys: "
            f"{list(_KEYS)}"
        )
    bullish = _names(section, "bullish_patterns", _BULLISH_DEFAULT, strategy)
    bearish = _names(section, "bearish_patterns", _BEARISH_DEFAULT, strategy)
    both = sorted(bullish & bearish)
    if both:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION} lists {both!r} as both bullish and bearish"
        )
    detector = section.get("detector", "disabled")
    _validate_detector(detector, bullish, bearish)
    return PatternConfig(bullish_patterns=bullish, bearish_patterns=bearish, detector=detector)


def _validate_detector(detector: str, bullish: frozenset[str], bearish: frozenset[str]) -> None:
    """Enabled TA-Lib uses the closed six-pattern vocabulary shared with F7."""
    if detector not in ("disabled", "talib"):
        raise ValueError("pattern.detector must be disabled or talib; fix the strategy config")
    if detector == "talib" and (bullish != _BULLISH_DEFAULT or bearish != _BEARISH_DEFAULT):
        raise ValueError(
            "TA-Lib requires the default six-pattern vocabulary; restore pattern names"
        )


def pattern_mapping(config: PatternConfig) -> dict[str, Any]:
    """The effective vocabulary as sorted lists, for the resolved config."""
    return {
        "bullish_patterns": sorted(config.bullish_patterns),
        "bearish_patterns": sorted(config.bearish_patterns),
        "detector": config.detector,
    }


@dataclass
class F3PatternFilter:
    """The chain's candlestick-pattern gate: implements `Filter.apply()`."""

    config: PatternConfig

    def apply(self, state: ExecutionState) -> FilterResult:
        """ABSTAIN with no pattern this bar; otherwise recommend by pattern polarity."""
        pattern = state.features.get("candlestick_pattern")
        if pattern is None:
            return FilterResult(
                filter_name="F3_pattern",
                recommendation=Recommendation.ABSTAIN,
                reason="no pattern detected this bar",
            )
        known = self.config.known_patterns
        if pattern not in known:
            raise ValueError(
                f"F3PatternFilter does not recognize candlestick_pattern={pattern!r}; "
                f"known patterns are {sorted(known)!r} — extend the strategy's `pattern` "
                "section if the upstream detector added a new pattern name."
            )
        bullish = pattern in self.config.bullish_patterns
        recommendation = Recommendation.BUY if bullish else Recommendation.SELL
        return FilterResult(
            filter_name="F3_pattern",
            recommendation=recommendation,
            reason=f"detected candlestick pattern {pattern!r}",
        )
