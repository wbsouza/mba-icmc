"""F2 — indicator (oscillator confirmation) filter (specs.md §11.3.2, Spec 04c).

"Recommends direction confirmed by oscillators; ABSTAIN on no-information bars." No
upstream perception layer populates `ExecutionState.features` from real LEAN indicators
yet (`engine/algorithm.py` — future 04a/04h integration work), so this filter defines
and documents its own minimal feature-key contract, proven here with synthetic
`ExecutionState` fixtures (`tests/features/f2_indicator.feature`).

**Feature-key contract** (read from `state.features`, both optional/nullable):

- ``rsi`` (float | None, ``[0, 100]``): the RSI reading, or ``None``/absent on a
  no-information bar (e.g. still warming up). Above 50 is a bullish bias, below 50
  bearish — "50" being the configured ``indicator.rsi_midline``.
- ``macd_hist`` (float | None): the MACD histogram (signal-line distance), or
  ``None``/absent on a no-information bar. Beyond +``macd_hist_threshold`` is bullish
  momentum, beyond -``macd_hist_threshold`` bearish (default threshold 0: the zero line).

A **no-information bar** is either oscillator being absent or `None` — F2 needs both
readings to confirm a direction, so it abstains rather than guess from a partial
signal. F2 never vetoes: a lack of confirmation is "no opinion this bar", not a hard
stop. When both are present, F2 recommends BUY/SELL only when they agree on direction;
disagreement (e.g. RSI bullish but MACD histogram bearish) yields NEUTRAL — a call, but
not a confirmed one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.chain.params import require_number

_SECTION = "indicator"


@dataclass(frozen=True)
class IndicatorConfig:
    """F2's thresholds (the `indicator` section; 2026-09-27 amendment, story 09).

    - ``rsi_midline``: RSI above it is a bullish bias, below it bearish; strictly inside
      (0, 100). Default 50, the oscillator's neutral line.
    - ``macd_hist_threshold``: the histogram must exceed +threshold (bullish) or fall below
      -threshold (bearish); >= 0. Default 0, the zero line.
    """

    rsi_midline: float = 50.0
    macd_hist_threshold: float = 0.0


_DEFAULTS = IndicatorConfig()


def parse_indicator_config(section: Mapping[str, Any], *, strategy: str) -> IndicatorConfig:
    """F2's thresholds from the `indicator` section, defaulting every key it omits.

    Raises:
        ValueError: an unknown key, a non-numeric value, a midline outside (0, 100) or a
            negative histogram threshold.
    """
    unknown = sorted(set(section) - set(asdict(_DEFAULTS)))
    if unknown:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION} has unknown keys {unknown!r}; known keys: "
            f"{sorted(asdict(_DEFAULTS))}"
        )
    filled = {**asdict(_DEFAULTS), **section}
    midline = require_number(filled, "rsi_midline", section=_SECTION, strategy=strategy)
    if not 0.0 < midline < 100.0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.rsi_midline must be strictly inside (0, 100), "
            f"got {midline!r}"
        )
    threshold = require_number(filled, "macd_hist_threshold", section=_SECTION, strategy=strategy)
    if threshold < 0.0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.macd_hist_threshold must be >= 0, got {threshold!r}"
        )
    return IndicatorConfig(rsi_midline=midline, macd_hist_threshold=threshold)


def indicator_mapping(config: IndicatorConfig) -> dict[str, float]:
    """The effective values as a plain mapping, for the resolved config."""
    return asdict(config)


def _bullish(rsi: float, macd_hist: float, config: IndicatorConfig) -> bool:
    """Both oscillators agree on an uptrend."""
    return rsi > config.rsi_midline and macd_hist > config.macd_hist_threshold


def _bearish(rsi: float, macd_hist: float, config: IndicatorConfig) -> bool:
    """Both oscillators agree on a downtrend."""
    return rsi < config.rsi_midline and macd_hist < -config.macd_hist_threshold


@dataclass
class F2IndicatorFilter:
    """The chain's oscillator-confirmation gate: implements `Filter.apply()`."""

    config: IndicatorConfig

    def apply(self, state: ExecutionState) -> FilterResult:
        """ABSTAIN on a no-information bar; otherwise recommend by oscillator agreement."""
        rsi = state.features.get("rsi")
        macd_hist = state.features.get("macd_hist")
        if rsi is None or macd_hist is None:
            return FilterResult(
                filter_name="F2_indicator",
                recommendation=Recommendation.ABSTAIN,
                reason=f"no-information bar: rsi={rsi!r}, macd_hist={macd_hist!r}",
            )
        rsi = float(rsi)  # type: ignore[arg-type]
        macd_hist = float(macd_hist)  # type: ignore[arg-type]
        if not 0.0 <= rsi <= 100.0:
            raise ValueError(
                f"F2IndicatorFilter: rsi must be in [0, 100], got {rsi!r} — check the "
                "upstream indicator computation"
            )
        if _bullish(rsi, macd_hist, self.config):
            recommendation = Recommendation.BUY
        elif _bearish(rsi, macd_hist, self.config):
            recommendation = Recommendation.SELL
        else:
            recommendation = Recommendation.NEUTRAL
        return FilterResult(
            filter_name="F2_indicator",
            recommendation=recommendation,
            reason=f"rsi={rsi}, macd_hist={macd_hist}, rsi_midline={self.config.rsi_midline}, "
            f"macd_hist_threshold={self.config.macd_hist_threshold}",
        )
