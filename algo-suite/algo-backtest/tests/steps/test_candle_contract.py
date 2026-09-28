"""Steps for candle_contract.feature: the Story 22 evidence and configuration contract."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pytest
from algo_backtest.perception.candle_contract import (
    ADMITTED_RULES,
    CATALOG,
    READY,
    WARMUP,
    CandleConfig,
    CandleEvidence,
    CandleHistory,
    ClosedBar,
    ContextConfig,
    PatternHit,
    SequenceEvidence,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/candle_contract.feature")

_HOUR = timedelta(hours=1)
_T0 = datetime(2024, 1, 1, tzinfo=UTC)
_VALID = (1000, 1060, 980, 1040)


@pytest.fixture
def cctx() -> dict[str, Any]:
    """Per-scenario state: builders, results and captured errors."""
    return {}


def _json(raw: str) -> Any:
    """A table cell as a Python value (JSON), keeping quoted strings as strings."""
    return json.loads(raw)


def _ints(raw: str) -> list[int]:
    """A comma-separated cell as integers."""
    return [int(item) for item in raw.split(",")]


def _bar(close_time: datetime, prices: tuple[Any, Any, Any, Any] = _VALID) -> ClosedBar:
    """A closed bar with float prices so that retained bars compare equal to offered ones."""
    return ClosedBar(close_time, *(float(price) for price in prices))


def _hourly(count: int, end: datetime) -> list[ClosedBar]:
    """``count`` consecutive valid hourly bars ending at ``end``."""
    return [_bar(end - _HOUR * (count - 1 - index)) for index in range(count)]


def _hit(rule: str, status: str = READY) -> PatternHit:
    """A hit for ``rule`` with the catalog polarity when READY, 0 when WARMUP."""
    polarity = CATALOG[rule].polarity if rule in CATALOG and status == READY else 0
    return PatternHit(rule, polarity, "1", status)


def _evidence(**overrides: Any) -> CandleEvidence:
    """READY evidence with no hits unless overridden."""
    fields: dict[str, Any] = {
        "pair": "EURUSD",
        "timeframe_minutes": 60,
        "close_time": _T0 + 10 * _HOUR,
        "history_count": 1,
        "status": READY,
        "hits": (),
    }
    fields.update(overrides)
    return CandleEvidence(**fields)


def _attempt(cctx: dict[str, Any], key: str) -> None:
    """Run the staged builder, keeping the value or the ValueError it raised."""
    try:
        cctx[key] = cctx["build"]()
        cctx["error"] = None
    except ValueError as error:
        cctx["error"] = error


def _assert_outcome(cctx: dict[str, Any], outcome: str, mention: str) -> None:
    """``accepts`` means no error; ``rejects`` means a ValueError naming ``mention``."""
    if outcome == "accepts":
        assert cctx["error"] is None
    else:
        assert isinstance(cctx["error"], ValueError)
        assert mention in str(cctx["error"])


# --- configuration --------------------------------------------------------------------


@given("the default candle configuration")
def default_config(cctx: dict[str, Any]) -> None:
    """The zero-argument configuration."""
    cctx["config"] = CandleConfig()


@then(
    parsers.parse(
        'the configuration has catalog_version "{version}", max_history {history:d} and '
        'policy_mode "{mode}"'
    )
)
def assert_defaults(cctx: dict[str, Any], version: str, history: int, mode: str) -> None:
    """Pin the default version, bound and policy mode."""
    config = cctx["config"]
    assert (config.catalog_version, config.max_history, config.policy_mode) == (
        version,
        history,
        mode,
    )


@then("the enabled rules are exactly, in id order:")
def assert_enabled_rules(cctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """The default enables the whole admitted catalog with the registered metadata."""
    rows = [(row[0], int(row[1]), int(row[2])) for row in datatable[1:]]
    assert list(cctx["config"].enabled_rules) == [row[0] for row in rows]
    assert list(ADMITTED_RULES) == sorted(ADMITTED_RULES)
    assert [
        (rule, CATALOG[rule].polarity, CATALOG[rule].lookback) for rule in ADMITTED_RULES
    ] == rows


@then(
    parsers.parse(
        "the context parameters are ema_period {ema:d}, stochastic {k:d},{ks:d},{d:d}, "
        "overbought {overbought:d}, oversold {oversold:d} and sma_periods {smas}"
    )
)
def assert_context_defaults(
    cctx: dict[str, Any],
    ema: int,
    k: int,
    ks: int,
    d: int,
    overbought: int,
    oversold: int,
    smas: str,
) -> None:
    """Pin the default context parameters."""
    assert cctx["config"].context == ContextConfig(
        ema, k, ks, d, overbought, oversold, tuple(_ints(smas))
    )


@given(parsers.parse('a READY candle evidence with one hit "{rule}"'))
def ready_evidence(cctx: dict[str, Any], rule: str) -> None:
    """READY evidence carrying one READY hit."""
    cctx["evidence"] = _evidence(hits=(_hit(rule),))


@when("any attribute of the configuration or the evidence is assigned")
def assign_attributes(cctx: dict[str, Any]) -> None:
    """Attempt to mutate both frozen values, keeping the raised errors."""
    cctx["errors"] = []
    for target, name in ((cctx["config"], "max_history"), (cctx["evidence"], "status")):
        try:
            setattr(target, name, 1)
        except FrozenInstanceError as error:
            cctx["errors"].append(error)


@then("the assignment raises an immutability error and the values are unchanged")
def assert_frozen(cctx: dict[str, Any]) -> None:
    """Both assignments raised and nothing changed."""
    assert len(cctx["errors"]) == 2
    assert cctx["config"].max_history == 256
    assert cctx["evidence"].status == READY


@given(
    parsers.parse(
        'a candle configuration with max_history {value}, enabled rules "{rules}", ema_period '
        '{ema:d}, stochastic {stoch} and sma_periods "{smas}"'
    )
)
def config_with_bounds(
    cctx: dict[str, Any], value: str, rules: str, ema: int, stoch: str, smas: str
) -> None:
    """Stage a configuration builder with explicit history, rules and context lookbacks."""
    k, ks, d = _ints(stoch)
    enabled = ADMITTED_RULES if rules == "all" else tuple(rules.split(","))
    context = ContextConfig(ema, k, ks, d, sma_periods=tuple(_ints(smas)))
    cctx["build"] = lambda: CandleConfig(
        enabled_rules=enabled, max_history=_json(value), context=context
    )


@given(parsers.parse("a candle configuration whose enabled_rules is {rules}"))
def config_with_rules(cctx: dict[str, Any], rules: str) -> None:
    """Stage a builder with the raw enabled_rules value."""
    cctx["build"] = lambda: CandleConfig(enabled_rules=_json(rules))


@given(parsers.parse("a candle configuration with policy_mode {value}"))
def config_with_mode(cctx: dict[str, Any], value: str) -> None:
    """Stage a builder with the raw policy_mode value."""
    cctx["build"] = lambda: CandleConfig(policy_mode=_json(value))


@given(parsers.parse("a candle configuration with timeframe_minutes {value}"))
def config_with_timeframe(cctx: dict[str, Any], value: str) -> None:
    """Stage a builder with the raw timeframe_minutes value."""
    cctx["build"] = lambda: CandleConfig(timeframe_minutes=_json(value))


@given(parsers.parse("a candle configuration with catalog_version {value}"))
def config_with_version(cctx: dict[str, Any], value: str) -> None:
    """Stage a builder with the raw catalog_version value."""
    cctx["build"] = lambda: CandleConfig(catalog_version=_json(value))


@when("the candle configuration is validated")
def validate_config(cctx: dict[str, Any]) -> None:
    """Construct the configuration, capturing a rejection."""
    _attempt(cctx, "config")


@then(parsers.parse('candle configuration validation {outcome} mentioning "{mention}"'))
def assert_config_outcome(cctx: dict[str, Any], outcome: str, mention: str) -> None:
    """Accepted, or rejected with a message naming the field or bound."""
    _assert_outcome(cctx, outcome, mention)


# --- pattern hits ---------------------------------------------------------------------


@given(
    parsers.parse(
        "a pattern hit with id {rule}, polarity {polarity}, rule_version {version} and "
        "status {status}"
    )
)
def hit_builder(cctx: dict[str, Any], rule: str, polarity: str, version: str, status: str) -> None:
    """Stage a hit builder from raw JSON cells."""
    cctx["build"] = lambda: PatternHit(_json(rule), _json(polarity), _json(version), _json(status))


@when("the pattern hit is validated")
def validate_hit(cctx: dict[str, Any]) -> None:
    """Construct the hit, capturing a rejection."""
    _attempt(cctx, "hit")


@then(parsers.parse('pattern hit validation {outcome} mentioning "{mention}"'))
def assert_hit_outcome(cctx: dict[str, Any], outcome: str, mention: str) -> None:
    """Accepted, or rejected naming the offending field or id."""
    _assert_outcome(cctx, outcome, mention)


# --- evidence -------------------------------------------------------------------------


@given(parsers.parse("candle evidence whose hit ids are {ids}"))
def evidence_with_ids(cctx: dict[str, Any], ids: str) -> None:
    """Stage evidence whose hits follow the given id order."""
    cctx["build"] = lambda: _evidence(hits=tuple(_hit(rule) for rule in _json(ids)))


@given(parsers.parse("candle evidence whose close_time is {close_time}"))
def evidence_with_close_time(cctx: dict[str, Any], close_time: str) -> None:
    """A quoted cell stays a string; an unquoted cell is parsed as an ISO datetime."""
    value = _json(close_time) if close_time.startswith('"') else datetime.fromisoformat(close_time)
    cctx["build"] = lambda: _evidence(close_time=value)


@given(
    parsers.parse(
        "candle evidence with status {status}, history_count {count} and max_history {bound}"
    )
)
def evidence_with_counts(cctx: dict[str, Any], status: str, count: str, bound: str) -> None:
    """Stage evidence with an explicit history bound; WARMUP evidence carries one WARMUP hit."""
    hits = (_hit("hammer", WARMUP),) if _json(status) == WARMUP else ()
    cctx["build"] = lambda: _evidence(
        status=_json(status), history_count=_json(count), max_history=_json(bound), hits=hits
    )


@given(parsers.re(r'candle evidence with status (?P<status>"[^"]*") whose hits are ?(?P<hits>.*)'))
def evidence_with_hits(cctx: dict[str, Any], status: str, hits: str) -> None:
    """Stage evidence from ``id:STATUS`` pairs (possibly none)."""
    pairs = [item.split(":") for item in hits.split(",") if item]
    cctx["build"] = lambda: _evidence(
        status=_json(status), hits=tuple(_hit(rule, state) for rule, state in pairs)
    )


@when("the candle evidence is validated")
def validate_evidence(cctx: dict[str, Any]) -> None:
    """Construct the evidence, capturing a rejection."""
    _attempt(cctx, "evidence")


@then(parsers.parse('candle evidence validation {outcome} mentioning "{mention}"'))
def assert_evidence_outcome(cctx: dict[str, Any], outcome: str, mention: str) -> None:
    """Accepted, or rejected naming the offending field, id or order."""
    _assert_outcome(cctx, outcome, mention)


@given(
    parsers.parse(
        "a sequence evidence with state {state}, confirmed_direction {direction} and "
        "confirmation_time {confirmation_time}"
    )
)
def sequence_evidence_builder(
    cctx: dict[str, Any], state: str, direction: str, confirmation_time: str
) -> None:
    """Stage a builder for a directly constructed SequenceEvidence."""
    state_value = _json(state)
    direction_value = _json(direction)
    time_value = (
        None if confirmation_time == "null" else datetime.fromisoformat(_json(confirmation_time))
    )
    cctx["build"] = lambda: SequenceEvidence(
        state=state_value,
        candidate_close_time=None,
        confirmed_direction=direction_value,
        confirmation_time=time_value,
        reason=None,
    )


@when("the sequence evidence is validated")
def validate_sequence_evidence(cctx: dict[str, Any]) -> None:
    """Construct the sequence evidence, capturing a rejection."""
    _attempt(cctx, "sequence_evidence")


@then(parsers.parse('sequence evidence validation {outcome} mentioning "{mention}"'))
def assert_sequence_evidence_outcome(cctx: dict[str, Any], outcome: str, mention: str) -> None:
    """Accepted, or rejected naming the state/confirmation contradiction."""
    _assert_outcome(cctx, outcome, mention)


# --- closed-bar history ---------------------------------------------------------------


@given(parsers.parse("a candle history with {count:d} valid 60-minute bars"))
def history_default_end(cctx: dict[str, Any], count: int) -> None:
    """A default-configured history holding ``count`` hourly bars ending at 10:00 UTC."""
    history_ending(cctx, count, "2024-01-01T10:00:00+00:00")


@given(parsers.parse('a candle history with {count:d} valid 60-minute bars ending at "{end}"'))
def history_ending(cctx: dict[str, Any], count: int, end: str) -> None:
    """A default-configured history holding ``count`` hourly bars ending at ``end``."""
    history = CandleHistory(CandleConfig())
    for bar in _hourly(count, datetime.fromisoformat(end)):
        history.offer(bar)
    cctx["history"] = history
    cctx["next_time"] = datetime.fromisoformat(end) + _HOUR


def _invalid_price(raw: str) -> Any:
    """Runtime numeric types that JSON cannot express, else the JSON value."""
    special = {"complex": 10 + 1j, "huge_integer": 10**400, "numpy_bool": np.bool_(True)}
    return special[raw] if raw in special else json.loads(raw)


@given(parsers.parse('a next bar whose "{field}" price is {value}'))
def next_bar_bad_price(cctx: dict[str, Any], field: str, value: str) -> None:
    """A bar at the next hour with exactly one corrupted price."""
    prices = dict(zip(("open", "high", "low", "close"), _VALID, strict=True))
    prices[field] = _invalid_price(value)
    cctx["next"] = ClosedBar(cctx["next_time"], **prices)


@given(parsers.parse("a next bar with OHLC {prices}"))
def next_bar_prices(cctx: dict[str, Any], prices: str) -> None:
    """A bar at the next hour with the given (possibly impossible) prices."""
    cctx["next"] = ClosedBar(cctx["next_time"], *_json(prices))


@given(parsers.parse("a next valid bar whose close_time is {close_time}"))
def next_bar_time(cctx: dict[str, Any], close_time: str) -> None:
    """A valid-priced bar at an arbitrary (possibly naive or misaligned) close time."""
    cctx["next"] = _bar(datetime.fromisoformat(close_time))


def _offer(cctx: dict[str, Any], bar: ClosedBar) -> None:
    """Offer ``bar`` to the history, keeping a snapshot and the error, if any."""
    cctx["before"] = cctx["history"].bars
    try:
        cctx["history"].offer(bar)
        cctx["error"] = None
    except ValueError as error:
        cctx["error"] = error


@when("the next bar is offered to the candle history")
def offer_next(cctx: dict[str, Any]) -> None:
    """Offer the staged next bar."""
    _offer(cctx, cctx["next"])


@when(parsers.parse('a valid bar closing at "{close_time}" is offered to the candle history'))
def offer_at(cctx: dict[str, Any], close_time: str) -> None:
    """Offer a valid bar at the given close time."""
    _offer(cctx, _bar(datetime.fromisoformat(close_time)))


@when(parsers.parse("a bar with OHLC {prices} is offered to the candle history"))
def offer_prices(cctx: dict[str, Any], prices: str) -> None:
    """Offer a bar at the next hour with the given prices."""
    last = cctx["history"].bars[-1].close_time
    _offer(cctx, ClosedBar(last + _HOUR, *_json(prices)))


@then(parsers.parse('the candle history rejects it mentioning "{fragment}" and a remedy'))
def assert_rejected(cctx: dict[str, Any], fragment: str) -> None:
    """A ValueError naming the field and the corrective action."""
    assert isinstance(cctx["error"], ValueError)
    assert fragment in str(cctx["error"])
    assert "repair" in str(cctx["error"]).lower()


@then(parsers.parse('the candle history {outcome} mentioning "{mention}"'))
def assert_history_outcome(cctx: dict[str, Any], outcome: str, mention: str) -> None:
    """Accepted, or rejected naming the timing problem."""
    _assert_outcome(cctx, outcome, mention)


@then(
    parsers.parse(
        "the candle history still holds {count:d} bars and accepts the following valid bar"
    )
)
def assert_untouched_then_accepts(cctx: dict[str, Any], count: int) -> None:
    """The rejection consumed nothing; the next valid bar is accepted normally."""
    history = cctx["history"]
    assert history.history_count == count
    assert history.bars == cctx["before"]
    history.offer(_bar(history.bars[-1].close_time + _HOUR))
    assert history.history_count == count + 1


@then(parsers.parse("the candle history still holds {count:d} bars"))
def assert_still_holds(cctx: dict[str, Any], count: int) -> None:
    """The retained count after the offer."""
    assert cctx["history"].history_count == count


@then(parsers.parse("the candle history holds {count:d} bars"))
def assert_holds(cctx: dict[str, Any], count: int) -> None:
    """The retained count."""
    assert cctx["history"].history_count == count


@then(
    parsers.parse("the history reports a gap of {count:d} missing expected bar before the last bar")
)
def assert_gap(cctx: dict[str, Any], count: int) -> None:
    """The continuous-grid gap before the most recent accepted bar."""
    assert cctx["history"].last_gap == count


@given("a candle history built from that configuration")
def history_from_config(cctx: dict[str, Any]) -> None:
    """An empty history bound to the staged configuration."""
    cctx["history"] = CandleHistory(cctx["build"]())


@given(parsers.parse("the candle history's config has max_history {value:d}"))
def assert_history_config(cctx: dict[str, Any], value: int) -> None:
    """The history exposes its bound configuration via the ``config`` accessor."""
    assert cctx["history"].config.max_history == value


@given(parsers.parse("a candle history built from that configuration holding {count:d} valid bars"))
def history_from_config_filled(cctx: dict[str, Any], count: int) -> None:
    """A history bound to the staged configuration, filled with ``count`` hourly bars."""
    history_from_config(cctx)
    offer_many(cctx, count)


@when(parsers.parse("{count:d} valid consecutive 60-minute bars are offered"))
def offer_many(cctx: dict[str, Any], count: int) -> None:
    """Offer ``count`` consecutive hourly bars from 01:00 UTC, remembering them."""
    cctx["offered"] = [_bar(_T0 + _HOUR * (index + 1)) for index in range(count)]
    for bar in cctx["offered"]:
        cctx["history"].offer(bar)


@then(parsers.parse("the retained bars are the last {count:d} offered bars in order"))
def assert_retained(cctx: dict[str, Any], count: int) -> None:
    """Eviction keeps the newest ``count`` bars, oldest first."""
    assert cctx["history"].bars == tuple(cctx["offered"][-count:])


@then("the retained bars are unchanged")
def assert_unchanged(cctx: dict[str, Any]) -> None:
    """The rejected bar neither consumed nor evicted anything."""
    assert cctx["history"].bars == cctx["before"]


@then("the next valid bar is accepted and evicts exactly the oldest bar")
def assert_evicts_oldest(cctx: dict[str, Any]) -> None:
    """A full history accepts a valid bar by dropping only its oldest bar."""
    history = cctx["history"]
    before = history.bars
    newest = _bar(before[-1].close_time + _HOUR)
    history.offer(newest)
    assert history.bars == before[1:] + (newest,)
