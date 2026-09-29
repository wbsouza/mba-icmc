"""F1 — trend-regime filter (specs.md §11.3.2, Spec 04c).

Recommends BUY/SELL aligned with the multi-timeframe trend; vetoes direction
conflicts. The shared chain engine supplies EMA directions by default, or the
config-selected double-smoothed Heikin-Ashi candidate. It waits for both timeframes
to be ready before invoking this filter. Trend strength remains the EMA-gap proxy.

**Feature-key contract** (read from `state.features`, all required — a missing key is a
hard, explained failure per the workspace's fail-fast policy, not a silent default):

- ``trend_direction`` (float): signed direction from the selected perception source. Positive =
  uptrend, negative = downtrend. EMA may emit zero (flat); DSHA emits only
  -1/+1 and folds equal smoothed extremes into -1 (down).
- ``trend_strength`` (float, ``[0, 100]``): an ADX-style trend-strength reading for the
  primary timeframe.
- ``higher_tf_trend_direction`` (float): same sign convention as ``trend_direction``,
  computed on a coarser timeframe — the multi-timeframe confirmation input.

A **direction conflict** is ``trend_direction`` and ``higher_tf_trend_direction``
disagreeing in sign (both nonzero, opposite signs): the primary timeframe wants to
trade against the higher timeframe's regime, so the filter vetoes rather than pick a
side. When aligned (or the higher timeframe is flat), the filter recommends BUY/SELL
by the sign of ``trend_direction`` (NEUTRAL if the primary timeframe itself is flat)
and enriches ``trend_score`` — ``trend_direction * trend_strength / 100`` — for
downstream filters. With DSHA selected, this deliberately combines DSHA direction
with EMA-gap strength; it is not a DSHA-derived strength measure
(specs.md §11.3.1's `"trend_score"` enrichment example).

**Momentum context variant** (story 21, the confluence chain; `momentum_context` section
of the strategy's `config.yaml`, `parse_momentum_context_config`). `F1MomentumContextFilter`
is a *separate* filter class that votes the side the lagged close return allows: with
L = ``lookback_bars`` completed closes of lag (480 on H1, 120 on H4 — both 480 scheduled
trading hours) and ``close[t] / close[t-L] - 1`` positive → BUY, negative → SELL, exactly
zero → NEUTRAL. It never vetoes and does not inherit the cross-timeframe conflict veto
above; it reads nothing from `state.features`. Its result keeps ``filter_name``
``"F1_trend"`` (the runtime name the agreement terminal's voter map expects for
``f1_trend``), enriches ``momentum_return`` once ready and carries metadata
``momentum_lookback_bars``, ``momentum_sample_count`` and ``momentum_status``
(``"READY"`` / ``"WARMUP"``).

The closes come from `MomentumHistory(lookback_bars)`, a pure bounded buffer fed one
*completed* close at a time through ``push(close_time, close)``: ``close_time`` is the
bar's UTC close, strictly increasing; ``close`` is finite and > 0. It keeps only the most
recent L+1 closes, so the lagged close is always the L-th older one. Fewer than L+1 closes
is WARMUP (ABSTAIN, reason ``WARMUP: n of L+1 closes``, no directional vote, no
``momentum_return``); a naive close time, a nonfinite/nonpositive close or a duplicated
or out-of-order close time is rejected with the offending value and leaves the buffer
unchanged. The integration lane (T13) feeds the buffer from the same closed-bar clock the
decision path uses; whether an *expected* close is missing is that feed's coverage
contract, not this buffer's (it cannot tell a gap from a market closure).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.chain.params import Section, reject_unknown_keys, require_key

_REQUIRED_KEYS = ("trend_direction", "trend_strength", "higher_tf_trend_direction")
_FILTER_NAME = "F1_trend"
_MOMENTUM_SECTION = "momentum_context"
_MOMENTUM_KEYS = ("lookback_bars",)
_READY, _WARMUP = "READY", "WARMUP"


def _read_required(state: ExecutionState) -> tuple[float, float, float]:
    """Read F1's three required feature keys, failing fast with a remediation hint.

    A key counts as missing if it's absent *or* present with value `None` —
    `state.features.get(key) is None`, matching F2/F3's own "no-information-yet"
    convention, not Python's `in` operator (which a present-but-`None` value would
    incorrectly pass, falling through to `float(None)`'s unguided `TypeError`).
    """
    missing = [key for key in _REQUIRED_KEYS if state.features.get(key) is None]
    if missing:
        raise ValueError(
            f"F1TrendFilter requires state.features{_REQUIRED_KEYS!r}; missing {missing!r} "
            "— populate them upstream (perception layer / LEAN indicators) before running "
            "the chain."
        )
    trend_direction = float(state.features["trend_direction"])  # type: ignore[arg-type]
    trend_strength = float(state.features["trend_strength"])  # type: ignore[arg-type]
    higher_tf_trend_direction = float(
        state.features["higher_tf_trend_direction"]  # type: ignore[arg-type]
    )
    if not 0.0 <= trend_strength <= 100.0:
        raise ValueError(
            f"F1TrendFilter: trend_strength must be in [0, 100] (an ADX-style reading), "
            f"got {trend_strength!r} — check the upstream indicator computation"
        )
    return trend_direction, trend_strength, higher_tf_trend_direction


def _conflicts(trend_direction: float, higher_tf_trend_direction: float) -> bool:
    """Both timeframes hold a nonzero, opposite-signed trend direction."""
    return (
        trend_direction != 0.0
        and higher_tf_trend_direction != 0.0
        and (trend_direction > 0.0) != (higher_tf_trend_direction > 0.0)
    )


def _directional_recommendation(trend_direction: float) -> Recommendation:
    """BUY/SELL by the sign of the primary-timeframe slope, NEUTRAL if flat."""
    if trend_direction > 0.0:
        return Recommendation.BUY
    if trend_direction < 0.0:
        return Recommendation.SELL
    return Recommendation.NEUTRAL


class F1TrendFilter:
    """The chain's trend-regime gate: implements `Filter.apply()`."""

    def apply(self, state: ExecutionState) -> FilterResult:
        """Veto on a cross-timeframe direction conflict; otherwise recommend by trend sign."""
        trend_direction, trend_strength, higher_tf_trend_direction = _read_required(state)
        if _conflicts(trend_direction, higher_tf_trend_direction):
            return FilterResult(
                filter_name="F1_trend",
                recommendation=Recommendation.NEUTRAL,
                reason=(
                    f"direction conflict: primary trend_direction={trend_direction} vs. "
                    f"higher_tf_trend_direction={higher_tf_trend_direction}"
                ),
                veto=True,
            )
        recommendation = _directional_recommendation(trend_direction)
        trend_score = trend_direction * trend_strength / 100.0
        return FilterResult(
            filter_name="F1_trend",
            recommendation=recommendation,
            reason=(
                f"trend_direction={trend_direction}, trend_strength={trend_strength}, "
                f"higher_tf_trend_direction={higher_tf_trend_direction}"
            ),
            enrichment={"trend_score": trend_score},
        )


# --- Momentum context variant (story 21) -------------------------------------------------


@dataclass(frozen=True)
class MomentumContextConfig:
    """The `momentum_context.*` parameters: ``lookback_bars`` (L), the lag in completed
    signal bars of the close return the vote is the sign of; the vote needs L+1 closes."""

    lookback_bars: int


def _positive_int(value: object) -> bool:
    """A real integer > 0 — never a bool, a float (even a whole one) or a string."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def parse_momentum_context_config(section: Section, *, strategy: str) -> MomentumContextConfig:
    """F1's momentum parameters from a strategy config.yaml `momentum_context` section.

    Raises:
        ValueError: an unknown key; `lookback_bars` absent, or not a positive integer
            (a bool, a float, a string or null are all rejected, never coerced).
    """
    reject_unknown_keys(section, _MOMENTUM_KEYS, section=_MOMENTUM_SECTION, strategy=strategy)
    value = require_key(section, "lookback_bars", section=_MOMENTUM_SECTION, strategy=strategy)
    if not _positive_int(value):
        raise ValueError(
            f"strategy {strategy!r}: {_MOMENTUM_SECTION}.lookback_bars must be a positive "
            f"integer (L completed closes of lag; the vote needs L+1 closes), got {value!r} — "
            f"fix strategies/{strategy}/config.yaml"
        )
    return MomentumContextConfig(lookback_bars=value)


def momentum_context_mapping(config: MomentumContextConfig) -> dict[str, Any]:
    """The effective values as a plain mapping, for the resolved config."""
    return {"lookback_bars": config.lookback_bars}


@dataclass
class MomentumHistory:
    """A pure, bounded buffer of the most recent L+1 completed closes (see the module
    docstring for the `push` contract).

    Raises:
        ValueError: `lookback_bars` is not a positive integer.
    """

    lookback_bars: int
    _closes: deque[tuple[datetime, float]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Size the buffer to L+1 closes."""
        if not _positive_int(self.lookback_bars):
            raise ValueError(
                f"MomentumHistory: lookback_bars must be a positive integer, got "
                f"{self.lookback_bars!r}"
            )
        self._closes = deque(maxlen=self.lookback_bars + 1)

    @property
    def sample_count(self) -> int:
        """How many closes the buffer currently holds (at most L+1)."""
        return len(self._closes)

    @property
    def last_close_time(self) -> datetime | None:
        """The UTC close time of the newest close, or `None` while empty."""
        return self._closes[-1][0] if self._closes else None

    def push(self, close_time: datetime, close: float) -> None:
        """Append one completed close; the oldest beyond L+1 is dropped.

        Raises:
            ValueError: `close_time` is naive or not UTC, `close` is not finite and > 0, or
                `close_time` is not strictly after the last recorded close time. The buffer
                is left unchanged.
        """
        if close_time.tzinfo is None or close_time.utcoffset() != timedelta(0):
            raise ValueError(
                f"MomentumHistory: close_time must be timezone-aware UTC, got {close_time!r}"
            )
        if not math.isfinite(close) or close <= 0.0:
            raise ValueError(
                f"MomentumHistory: close must be finite and > 0, got {close!r} at "
                f"{close_time.isoformat()} — check the closed-bar feed"
            )
        last = self.last_close_time
        if last is not None and close_time <= last:
            raise ValueError(
                f"MomentumHistory: close_time {close_time.isoformat()} is not after the last "
                f"close {last.isoformat()} — completed closes must be pushed once each, in "
                "chronological order"
            )
        self._closes.append((close_time, close))

    def lagged_return(self) -> float | None:
        """`close[t] / close[t-L] - 1` over the buffer, or `None` while fewer than L+1 closes."""
        if len(self._closes) < self.lookback_bars + 1:
            return None
        return self._closes[-1][1] / self._closes[0][1] - 1.0


def _momentum_recommendation(momentum_return: float) -> Recommendation:
    """BUY for a positive lagged return, SELL for a negative one, NEUTRAL for exactly zero."""
    if momentum_return > 0.0:
        return Recommendation.BUY
    if momentum_return < 0.0:
        return Recommendation.SELL
    return Recommendation.NEUTRAL


@dataclass
class F1MomentumContextFilter:
    """The momentum-context variant of F1: implements `Filter.apply()` from `history`.

    Raises:
        ValueError: `history` was sized for a different `lookback_bars` than `config`.
    """

    config: MomentumContextConfig
    history: MomentumHistory

    def __post_init__(self) -> None:
        """The buffer and the config must agree on L."""
        if self.history.lookback_bars != self.config.lookback_bars:
            raise ValueError(
                f"F1MomentumContextFilter: history.lookback_bars "
                f"{self.history.lookback_bars!r} != momentum_context.lookback_bars "
                f"{self.config.lookback_bars!r} — build the history from the same config"
            )

    def apply(self, state: ExecutionState) -> FilterResult:
        """Vote the sign of the lagged close return; WARMUP (ABSTAIN) until L+1 closes."""
        lookback = self.config.lookback_bars
        count = self.history.sample_count
        momentum_return = self.history.lagged_return()
        metadata: dict[str, object] = {
            "momentum_lookback_bars": lookback,
            "momentum_sample_count": count,
            "momentum_status": _WARMUP if momentum_return is None else _READY,
        }
        if momentum_return is None:
            return FilterResult(
                filter_name=_FILTER_NAME,
                recommendation=Recommendation.ABSTAIN,
                reason=(
                    f"{_MOMENTUM_SECTION} WARMUP: {count} of {lookback + 1} closes collected; "
                    "no directional vote until the lagged close exists"
                ),
                metadata=metadata,
            )
        recommendation = _momentum_recommendation(momentum_return)
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=recommendation,
            reason=(
                f"{_MOMENTUM_SECTION}: close[t] / close[t-{lookback}] - 1 = "
                f"{momentum_return:+.6f}: {recommendation.value}"
            ),
            enrichment={"momentum_return": momentum_return},
            metadata=metadata,
        )
