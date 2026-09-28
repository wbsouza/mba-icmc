"""Immutable candlestick evidence and configuration contract (Story 22, T2).

One versioned contract shared by the geometry catalog, the context evaluator, the
sequence evaluator and the F3 policy. It has no chain, engine or LEAN dependency.
Every recognizer validates a closed bar through ``CandleHistory.offer`` before
advancing its state: a rejected bar raises ``ValueError`` naming the field and a
remedy and leaves the history untouched (CND-03). Hits carry their own readiness
and evidence keeps them in stable id order (CND-02). The admitted rule ids, their
polarity and lookback come from the Story 22 rule ledger; the six legacy ids keep
TA-Lib's lookback plus one closed bar.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from numbers import Integral, Real
from typing import Final

SCHEMA_VERSION: Final = "1"
CATALOG_VERSION: Final = "1"
MAX_HISTORY: Final = 256
READY: Final = "READY"
WARMUP: Final = "WARMUP"
UNDEFINED: Final = "UNDEFINED"
POLICY_MODES: Final = ("legacy", "advisory", "required_entry")
_DAY_MINUTES = 1440
_CONFIG_REMEDY = "fix the candle configuration"


@dataclass(frozen=True)
class RuleSpec:
    """Registered polarity, lookback (closed bars including the current one) and origin."""

    polarity: int
    lookback: int
    origin: str


# Declared in ascending id order; ``ADMITTED_RULES`` is the stable hit order.
CATALOG: Final[dict[str, RuleSpec]] = {
    "bearish_engulfing": RuleSpec(-1, 3, "legacy"),
    "bearish_harami": RuleSpec(-1, 2, "new"),
    "bearish_kicker": RuleSpec(-1, 2, "new"),
    "bullish_engulfing": RuleSpec(1, 3, "legacy"),
    "bullish_harami": RuleSpec(1, 2, "new"),
    "bullish_kicker": RuleSpec(1, 2, "new"),
    "dark_cloud_cover": RuleSpec(-1, 2, "new"),
    "doji": RuleSpec(0, 1, "new"),
    "doji_dragonfly": RuleSpec(0, 1, "new"),
    "doji_gravestone": RuleSpec(0, 1, "new"),
    "doji_long_legged": RuleSpec(0, 1, "new"),
    "evening_star": RuleSpec(-1, 13, "legacy"),
    "hammer": RuleSpec(1, 12, "legacy"),
    "hanging_man": RuleSpec(-1, 5, "new"),
    "inverted_hammer": RuleSpec(1, 5, "new"),
    "morning_star": RuleSpec(1, 13, "legacy"),
    "piercing_line": RuleSpec(1, 2, "new"),
    "shooting_star": RuleSpec(-1, 12, "legacy"),
    "spinning_top": RuleSpec(0, 1, "new"),
}
ADMITTED_RULES: Final[tuple[str, ...]] = tuple(CATALOG)


def _integer(value: object, name: str, minimum: int) -> int:
    """A plain integer (booleans rejected) of at least ``minimum``, or raise naming the field."""
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {value!r}; {_CONFIG_REMEDY}")
    return int(value)


def _non_empty_string(value: object, name: str) -> str:
    """A non-empty ``str``, or raise naming the field."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string, got {value!r}; {_CONFIG_REMEDY}")
    return value


def _one_of(value: object, name: str, allowed: Sequence[str]) -> str:
    """A string from ``allowed``, or raise naming the field and the vocabulary."""
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(
            f"{name} must be one of {', '.join(allowed)}, got {value!r}; {_CONFIG_REMEDY}"
        )
    return value


def _utc_datetime(value: object, name: str) -> datetime:
    """A timezone-aware UTC ``datetime``, or raise naming the field."""
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise ValueError(
            f"{name} must be a timezone-aware UTC datetime, got {value!r}; "
            "construct it with tzinfo=UTC"
        )
    return value


@dataclass(frozen=True)
class ContextConfig:
    """Context indicator parameters (T-line EMA, stochastic 12,3,3 zones, SMA levels)."""

    ema_period: int = 8
    stochastic_k: int = 12
    stochastic_k_smooth: int = 3
    stochastic_d: int = 3
    overbought: float = 80
    oversold: float = 20
    sma_periods: tuple[int, ...] = (20, 50, 200)

    def __post_init__(self) -> None:
        """Reject non-positive periods, inverted or out-of-range zones and bad SMA lists."""
        for name in ("ema_period", "stochastic_k", "stochastic_k_smooth", "stochastic_d"):
            _integer(getattr(self, name), name, 1)
        self._validate_zones()
        object.__setattr__(self, "sma_periods", self._validated_sma_periods())

    def _validate_zones(self) -> None:
        """Zones are real numbers in 0..100 with overbought strictly above oversold."""
        for name in ("overbought", "oversold"):
            level = getattr(self, name)
            if (
                isinstance(level, bool)
                or not isinstance(level, Real)
                or not 0 <= float(level) <= 100
            ):
                raise ValueError(
                    f"{name} must be a number in 0..100, got {level!r}; {_CONFIG_REMEDY}"
                )
        if self.overbought <= self.oversold:
            raise ValueError(
                f"overbought ({self.overbought!r}) must be greater than oversold "
                f"({self.oversold!r}); {_CONFIG_REMEDY}"
            )

    def _validated_sma_periods(self) -> tuple[int, ...]:
        """A non-empty list of unique integer periods in 1..256."""
        periods = self.sma_periods
        if isinstance(periods, str) or not isinstance(periods, Sequence) or not periods:
            raise ValueError(
                f"sma_periods must be a non-empty list of periods, got {periods!r}; "
                f"{_CONFIG_REMEDY}"
            )
        validated = tuple(_integer(period, "sma_periods entry", 1) for period in periods)
        if len(set(validated)) != len(validated) or max(validated) > MAX_HISTORY:
            raise ValueError(
                f"sma_periods must be unique and at most {MAX_HISTORY}, got {periods!r}; "
                f"{_CONFIG_REMEDY}"
            )
        return validated

    def lookbacks(self) -> list[tuple[int, str]]:
        """Every (bars needed, origin) pair an indicator of this configuration requires."""
        stochastic = self.stochastic_k + self.stochastic_k_smooth + self.stochastic_d - 2
        return [
            (self.ema_period, f"ema_period {self.ema_period}"),
            (
                stochastic,
                "the stochastic "
                f"{self.stochastic_k},{self.stochastic_k_smooth},{self.stochastic_d}",
            ),
            *((period, f"sma_periods {period}") for period in self.sma_periods),
        ]


@dataclass(frozen=True)
class SequenceConfig:
    """Which next-bar confirmation sequences the sequence evaluator runs."""

    doji_engulfing: bool = True

    def __post_init__(self) -> None:
        """The flag is a plain boolean."""
        if not isinstance(self.doji_engulfing, bool):
            raise ValueError(
                f"doji_engulfing must be a boolean, got {self.doji_engulfing!r}; {_CONFIG_REMEDY}"
            )


@dataclass(frozen=True)
class CandleConfig:
    """Versioned, bounded configuration of the catalog, context, sequences and policy."""

    catalog_version: str = CATALOG_VERSION
    enabled_rules: tuple[str, ...] = ADMITTED_RULES
    max_history: int = MAX_HISTORY
    timeframe_minutes: int = 60
    context: ContextConfig = ContextConfig()
    sequence: SequenceConfig = SequenceConfig()
    policy_mode: str = "legacy"

    def __post_init__(self) -> None:
        """Validate every field and prove max_history covers every enabled lookback."""
        _non_empty_string(self.catalog_version, "catalog_version")
        object.__setattr__(self, "enabled_rules", self._validated_rules())
        self._validate_max_history()
        self._validate_timeframe()
        if not isinstance(self.context, ContextConfig) or not isinstance(
            self.sequence, SequenceConfig
        ):
            raise ValueError(
                "context and sequence must be ContextConfig and SequenceConfig instances"
            )
        _one_of(self.policy_mode, "policy_mode", POLICY_MODES)
        required, origin = self.required_lookback()
        if self.max_history < required:
            raise ValueError(
                f"max_history={self.max_history} is below the {required}-bar lookback required by "
                f"{origin}; raise max_history to at least {required} (at most "
                f"{MAX_HISTORY}), never silently shorten a window"
            )

    def _validated_rules(self) -> tuple[str, ...]:
        """A non-empty sequence of unique admitted rule ids, kept in the given order."""
        rules = self.enabled_rules
        if isinstance(rules, str) or not isinstance(rules, Sequence) or not rules:
            raise ValueError(
                f"enabled_rules must be a non-empty list of admitted rule ids, got {rules!r}"
            )
        seen: set[str] = set()
        for rule in rules:
            if not isinstance(rule, str) or rule not in CATALOG:
                raise ValueError(
                    f"enabled_rules contains the unknown rule id {rule!r}; admitted ids are "
                    f"{list(ADMITTED_RULES)}"
                )
            if rule in seen:
                raise ValueError(
                    f"enabled_rules lists {rule!r} more than once; remove the duplicate"
                )
            seen.add(rule)
        return tuple(rules)

    def _validate_max_history(self) -> None:
        """max_history is a plain integer in 1..256."""
        value = self.max_history
        if (
            isinstance(value, bool)
            or not isinstance(value, Integral)
            or not 1 <= value <= MAX_HISTORY
        ):
            raise ValueError(
                f"max_history must be an integer in 1..{MAX_HISTORY}, got {value!r}; "
                f"{_CONFIG_REMEDY}"
            )

    def _validate_timeframe(self) -> None:
        """timeframe_minutes is a positive integer divisor of 1440."""
        value = self.timeframe_minutes
        if (
            isinstance(value, bool)
            or not isinstance(value, Integral)
            or value <= 0
            or _DAY_MINUTES % value
        ):
            raise ValueError(
                f"timeframe_minutes must be a positive integer divisor of {_DAY_MINUTES}, "
                f"got {value!r}; {_CONFIG_REMEDY}"
            )

    def required_lookback(self) -> tuple[int, str]:
        """The longest lookback among enabled rules and context indicators, with its origin."""
        candidates = [(CATALOG[rule].lookback, f"rule {rule!r}") for rule in self.enabled_rules]
        candidates.extend(self.context.lookbacks())
        return max(candidates, key=lambda item: item[0])


@dataclass(frozen=True)
class PatternHit:
    """One catalog rule's result on a closed bar, with its own readiness."""

    id: str
    polarity: int
    rule_version: str
    status: str

    def __post_init__(self) -> None:
        """Reject unknown ids, out-of-range or contradictory polarities and bad status."""
        if not isinstance(self.id, str) or self.id not in CATALOG:
            raise ValueError(
                f"unknown pattern id {self.id!r}; admitted ids are {list(ADMITTED_RULES)}"
            )
        if (
            isinstance(self.polarity, bool)
            or not isinstance(self.polarity, Integral)
            or self.polarity not in (-1, 0, 1)
        ):
            raise ValueError(f"polarity must be -1, 0 or 1, got {self.polarity!r} for {self.id!r}")
        _non_empty_string(self.rule_version, "rule_version")
        _one_of(self.status, "status", (READY, WARMUP))
        expected = CATALOG[self.id].polarity if self.status == READY else 0
        if self.polarity != expected:
            raise ValueError(
                f"a {self.status} hit for {self.id!r} must carry polarity {expected}, got "
                f"{self.polarity!r}; repair the recognizer output"
            )


@dataclass(frozen=True)
class IndicatorValue:
    """One indicator reading: a finite value when READY, None when WARMUP or UNDEFINED."""

    value: float | None
    status: str

    def __post_init__(self) -> None:
        """READY carries a finite number; WARMUP and UNDEFINED carry None."""
        _one_of(self.status, "status", (READY, WARMUP, UNDEFINED))
        ready = self.status == READY
        finite = (
            isinstance(self.value, Real)
            and not isinstance(self.value, bool)
            and isfinite(self.value)
        )
        if ready != finite or (not ready and self.value is not None):
            raise ValueError(
                f"indicator status {self.status} contradicts value {self.value!r}; "
                "repair the evaluator"
            )


@dataclass(frozen=True)
class StochasticEvidence:
    """Raw %K, slow %K, %D and the zone derived from %D."""

    raw_k: IndicatorValue
    slow_k: IndicatorValue
    d: IndicatorValue
    zone: str

    def __post_init__(self) -> None:
        """The zone vocabulary is closed."""
        _one_of(self.zone, "zone", ("OVERBOUGHT", "OVERSOLD", "NEUTRAL", UNDEFINED))


@dataclass(frozen=True)
class LevelEvidence:
    """One simple moving average level and the normalized distance of the close to it."""

    period: int
    sma: IndicatorValue
    distance: float | None

    def __post_init__(self) -> None:
        """The distance exists exactly when the level is READY."""
        if (self.sma.status == READY) != (self.distance is not None):
            raise ValueError(
                f"level {self.period}: distance and sma readiness disagree; repair the evaluator"
            )


@dataclass(frozen=True)
class ContextEvidence:
    """Separately typed causal context: T-line, stochastic, levels and trend (CND-06)."""

    close_time: datetime
    history_count: int
    ema: IndicatorValue
    t_line_position: str
    stochastic: StochasticEvidence
    levels: tuple[LevelEvidence, ...]
    trend: str
    status: str

    def __post_init__(self) -> None:
        """Closed vocabularies, UTC availability time and bounded history."""
        _utc_datetime(self.close_time, "close_time")
        _integer(self.history_count, "history_count", 0)
        _one_of(self.t_line_position, "t_line_position", ("ABOVE", "BELOW", "ON", WARMUP))
        _one_of(self.trend, "trend", ("UP", "DOWN", "FLAT", WARMUP))
        _one_of(self.status, "status", (READY, WARMUP))


@dataclass(frozen=True)
class SequenceEvidence:
    """Next-bar confirmation state; confirmation_time belongs to the confirming bar (CND-07)."""

    state: str
    candidate_close_time: datetime | None
    confirmed_direction: int | None
    confirmation_time: datetime | None
    reason: str | None

    def __post_init__(self) -> None:
        """Closed vocabularies and a direction only when CONFIRMED."""
        _one_of(self.state, "state", ("IDLE", "CANDIDATE", "CONFIRMED", "EXPIRED"))
        if self.reason is not None:
            _one_of(self.reason, "reason", ("confirmed", "not_engulfing", "missing_expected_bar"))
        confirmed = self.state == "CONFIRMED"
        if confirmed != (self.confirmed_direction in (-1, 1)) or confirmed != (
            self.confirmation_time is not None
        ):
            raise ValueError(
                f"sequence state {self.state} contradicts its confirmation fields; "
                "repair the evaluator"
            )


@dataclass(frozen=True)
class CandleEvidence:
    """One closed-bar observation: ordered hits plus optional context and confirmation."""

    pair: str
    timeframe_minutes: int
    close_time: datetime
    history_count: int
    status: str
    hits: tuple[PatternHit, ...]
    context: ContextEvidence | None = None
    confirmation: SequenceEvidence | None = None
    schema_version: str = SCHEMA_VERSION
    catalog_version: str = CATALOG_VERSION
    max_history: int = MAX_HISTORY

    def __post_init__(self) -> None:
        """Validate timing, bounds, hit order and the status/readiness agreement."""
        _non_empty_string(self.pair, "pair")
        _integer(self.timeframe_minutes, "timeframe_minutes", 1)
        _utc_datetime(self.close_time, "close_time")
        _non_empty_string(self.schema_version, "schema_version")
        _non_empty_string(self.catalog_version, "catalog_version")
        count, bound = self.history_count, self.max_history
        if isinstance(count, bool) or not isinstance(count, Integral) or not 0 <= count <= bound:
            raise ValueError(
                f"history_count must be an integer in 0..{bound}, got {count!r}; "
                "repair the producer"
            )
        _one_of(self.status, "status", (READY, WARMUP))
        object.__setattr__(self, "hits", self._validated_hits())
        self._validate_status()
        if self.context is not None and not isinstance(self.context, ContextEvidence):
            raise ValueError("context must be a ContextEvidence or None; repair the producer")
        if self.confirmation is not None and not isinstance(self.confirmation, SequenceEvidence):
            raise ValueError("confirmation must be a SequenceEvidence or None; repair the producer")

    def _validated_hits(self) -> tuple[PatternHit, ...]:
        """Hits are PatternHit values in strictly ascending id order."""
        hits = tuple(self.hits)
        if any(not isinstance(hit, PatternHit) for hit in hits):
            raise ValueError("hits must contain PatternHit values only; repair the producer")
        ids = [hit.id for hit in hits]
        for previous, current in zip(ids, ids[1:], strict=False):
            if current == previous:
                raise ValueError(f"hits list {current!r} more than once; repair the producer")
            if current < previous:
                raise ValueError(
                    f"hits must be in ascending id order, got {ids}; repair the producer"
                )
        return hits

    def _validate_status(self) -> None:
        """READY evidence has no WARMUP hit; WARMUP evidence has at least one."""
        warming = [hit.id for hit in self.hits if hit.status == WARMUP]
        if self.status == READY and warming:
            raise ValueError(f"status READY contradicts WARMUP hits {warming}; repair the producer")
        if self.status == WARMUP and not warming:
            raise ValueError("status WARMUP requires at least one WARMUP hit; repair the producer")

    @property
    def ready_hits(self) -> tuple[PatternHit, ...]:
        """The READY hits only, in id order."""
        return tuple(hit for hit in self.hits if hit.status == READY)


@dataclass(frozen=True)
class ClosedBar:
    """One closed bar; ``close_time`` is the END of its bucket, aligned to the timeframe."""

    close_time: datetime
    open: float
    high: float
    low: float
    close: float


def _price(value: object, name: str) -> float:
    """A finite positive real scalar as float; booleans and complex values are rejected."""
    message = f"Candle {name} must be a finite positive real number; repair the OHLC source"
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(message)
    try:
        price = float(value)
    except OverflowError as error:
        raise ValueError(message) from error
    if not isfinite(price) or price <= 0:
        raise ValueError(message)
    return price


def _aligned_utc_close_time(value: object, timeframe_minutes: int) -> datetime:
    """An aware UTC close time on the timeframe grid (whole minutes since UTC midnight)."""
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise ValueError(
            f"Candle close_time must be a timezone-aware UTC datetime, got {value!r}; "
            "repair the bar clock"
        )
    minute_of_day = value.hour * 60 + value.minute
    if value.second or value.microsecond or minute_of_day % timeframe_minutes:
        raise ValueError(
            f"Candle close_time {value.isoformat()} is not aligned to the "
            f"{timeframe_minutes}-minute timeframe; repair the bar clock"
        )
    return value


def _strictly_after(value: datetime, previous: datetime | None) -> datetime:
    """``value`` strictly later than ``previous`` (duplicates and reversals rejected)."""
    if previous is not None and value == previous:
        raise ValueError(
            f"Candle close_time {value.isoformat()} is a duplicate; repair the bar stream"
        )
    if previous is not None and value < previous:
        raise ValueError(
            f"Candle close_time {value.isoformat()} is out of order (last was "
            f"{previous.isoformat()}); repair the bar stream"
        )
    return value


def validate_bar(
    bar: ClosedBar, *, timeframe_minutes: int, previous_close_time: datetime | None
) -> ClosedBar:
    """Normalize prices to floats and reject malformed bars before any state advances.

    Raises:
        ValueError: a non-finite, non-positive or non-real price, an impossible OHLC
            ordering, or a close_time that is naive, non-UTC, misaligned, duplicated or
            earlier than ``previous_close_time``; every message names a remedy.
    """
    close_time = _strictly_after(
        _aligned_utc_close_time(bar.close_time, timeframe_minutes), previous_close_time
    )
    open_, high, low, close = (
        _price(getattr(bar, name), name) for name in ("open", "high", "low", "close")
    )
    if not low <= min(open_, close) <= max(open_, close) <= high:
        raise ValueError(
            "Candle OHLC ordering is invalid (needs low <= min(open, close) <= max(open, close) "
            "<= high); repair the OHLC source"
        )
    return ClosedBar(close_time, open_, high, low, close)


class CandleHistory:
    """Bounded, validated closed-bar history shared by every Story 22 recognizer.

    Retains at most ``config.max_history`` bars, evicting the oldest first. A rejected
    bar changes nothing; the next valid bar is accepted normally. ``last_gap`` reports
    how many expected bars (under the continuous timeframe grid) were missing before
    the most recent accepted bar; the calendar policy that explains a gap is a
    sequence-evaluator input, not a history concern.
    """

    def __init__(self, config: CandleConfig) -> None:
        """Bind the configuration; the history starts empty."""
        self._config = config
        self._period = timedelta(minutes=config.timeframe_minutes)
        self._bars: deque[ClosedBar] = deque(maxlen=config.max_history)
        self._last_gap = 0

    @property
    def config(self) -> CandleConfig:
        """The bound configuration."""
        return self._config

    @property
    def bars(self) -> tuple[ClosedBar, ...]:
        """The retained bars, oldest first."""
        return tuple(self._bars)

    @property
    def history_count(self) -> int:
        """How many closed bars are retained."""
        return len(self._bars)

    @property
    def last_gap(self) -> int:
        """Missing expected bars between the previous bar and the last accepted one."""
        return self._last_gap

    def offer(self, bar: ClosedBar) -> ClosedBar:
        """Validate then append one closed bar; invalid input raises without changing state."""
        previous = self._bars[-1].close_time if self._bars else None
        validated = validate_bar(
            bar, timeframe_minutes=self._config.timeframe_minutes, previous_close_time=previous
        )
        self._last_gap = (
            0 if previous is None else (validated.close_time - previous) // self._period - 1
        )
        self._bars.append(validated)
        return validated
