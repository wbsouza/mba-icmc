"""Steps for candle_sequence.feature: doji-to-engulfing next-bar confirmation."""

from __future__ import annotations

import json
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from algo_backtest.perception.candle_contract import ClosedBar, SequenceEvidence
from algo_backtest.perception.candle_sequence import (
    CalendarPolicy,
    ScheduledClosure,
    SequenceEvaluator,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/candle_sequence.feature")

_HOUR = timedelta(hours=1)
_T0 = datetime(2024, 1, 1, 1, tzinfo=UTC)
_CODES: dict[str, tuple[float, float, float, float]] = {
    "D": (1000.0, 1050.0, 950.0, 1000.0),
    "B": (990.0, 1060.0, 985.0, 1030.0),
    "S": (1010.0, 1015.0, 940.0, 970.0),
    "N": (1005.0, 1030.0, 1000.0, 1025.0),
    "F": (1000.0, 1030.0, 990.0, 1020.0),
}

_Bar = tuple[datetime, tuple[float, float, float, float]]


@pytest.fixture
def seq_ctx() -> dict[str, Any]:
    """Per-scenario state: staged (close_time, OHLC) bars, the policy, evidences and errors."""
    return {"bars": [], "policy": None}


def _codes(raw: str) -> list[str]:
    """A comma-separated list of single-letter bar codes."""
    return [item.strip() for item in raw.split(",")]


def _append_hourly(seq_ctx: dict[str, Any], codes: str) -> None:
    """Append named bars, each one hour after the previously staged bar (or 01:00 if none)."""
    start = seq_ctx["bars"][-1][0] + _HOUR if seq_ctx["bars"] else _T0
    for i, code in enumerate(_codes(codes)):
        seq_ctx["bars"].append((start + _HOUR * i, _CODES[code]))


@given(parsers.re(r'^the closed bars (?P<codes>[A-Z](?:, [A-Z])*)$'))
def closed_bars(seq_ctx: dict[str, Any], codes: str) -> None:
    """Named bars, hourly from 2024-01-01T01:00:00+00:00."""
    _append_hourly(seq_ctx, codes)


@given(
    parsers.re(
        r"^the closed bars (?P<codes>[A-Z](?:, [A-Z])*), then "
        r"\((?P<open>-?\d+(?:\.\d+)?), (?P<high>-?\d+(?:\.\d+)?), "
        r"(?P<low>-?\d+(?:\.\d+)?), (?P<close>-?\d+(?:\.\d+)?)\)$"
    )
)
def closed_bars_then_custom(
    seq_ctx: dict[str, Any], codes: str, open: str, high: str, low: str, close: str
) -> None:
    """Named bars followed by one custom-OHLC bar, staying on the hourly cadence."""
    _append_hourly(seq_ctx, codes)
    start = seq_ctx["bars"][-1][0] + _HOUR
    seq_ctx["bars"].append((start, (float(open), float(high), float(low), float(close))))


@given(
    parsers.re(
        r'^the closed bars (?P<codes>[A-Z](?:, [A-Z])*) closing hourly from "(?P<start>[^"]+)"$'
    )
)
def closed_bars_from(seq_ctx: dict[str, Any], codes: str, start: str) -> None:
    """Named bars, hourly from an explicit UTC start."""
    begin = datetime.fromisoformat(start)
    for i, code in enumerate(_codes(codes)):
        seq_ctx["bars"].append((begin + _HOUR * i, _CODES[code]))


@given(
    parsers.re(
        r'^the closed bars (?P<code1>[A-Z]) closing at "(?P<time1>[^"]+)" and '
        r'(?P<code2>[A-Z]) closing at "(?P<time2>[^"]+)"$'
    )
)
def two_explicit_bars(
    seq_ctx: dict[str, Any], code1: str, time1: str, code2: str, time2: str
) -> None:
    """Two named bars at explicit UTC close times."""
    seq_ctx["bars"].append((datetime.fromisoformat(time1), _CODES[code1]))
    seq_ctx["bars"].append((datetime.fromisoformat(time2), _CODES[code2]))


@given(parsers.re(r'^a doji bar D closing at "(?P<time>[^"]+)"$'))
def explicit_doji(seq_ctx: dict[str, Any], time: str) -> None:
    """One more doji bar at an explicit UTC close time."""
    seq_ctx["bars"].append((datetime.fromisoformat(time), _CODES["D"]))


@given(parsers.re(r'^a bullish engulfing bar B closing at "(?P<time>[^"]+)"$'))
def explicit_bullish_engulfing(seq_ctx: dict[str, Any], time: str) -> None:
    """One more bullish-engulfing bar at an explicit UTC close time."""
    seq_ctx["bars"].append((datetime.fromisoformat(time), _CODES["B"]))


@given(
    parsers.re(
        r'^a calendar policy with a scheduled closure from "(?P<start>[^"]+)" to "(?P<end>[^"]+)"$'
    )
)
def calendar_policy(seq_ctx: dict[str, Any], start: str, end: str) -> None:
    """Stage a policy with one scheduled closure."""
    seq_ctx["policy"] = CalendarPolicy(
        closures=(ScheduledClosure(datetime.fromisoformat(start), datetime.fromisoformat(end)),)
    )


@when(
    parsers.re(
        r'^a scheduled closure from "(?P<start>[^"]+)" to "(?P<end>[^"]+)" is constructed$'
    )
)
def attempt_closure(seq_ctx: dict[str, Any], start: str, end: str) -> None:
    """Attempt to construct a ScheduledClosure, capturing a rejection."""
    try:
        seq_ctx["closure"] = ScheduledClosure(
            datetime.fromisoformat(start), datetime.fromisoformat(end)
        )
        seq_ctx["closure_error"] = None
    except ValueError as error:
        seq_ctx["closure_error"] = error


@then(parsers.parse('constructing the scheduled closure raises mentioning "{fragment}"'))
def assert_closure_raises(seq_ctx: dict[str, Any], fragment: str) -> None:
    """The construction raised a ValueError naming the invariant it violated."""
    assert isinstance(seq_ctx["closure_error"], ValueError)
    assert fragment in str(seq_ctx["closure_error"])


def _closed(bars: list[_Bar]) -> list[ClosedBar]:
    """Staged (close_time, OHLC) pairs as ``ClosedBar`` values."""
    return [ClosedBar(close_time, *ohlc) for close_time, ohlc in bars]


def _stream(bars: list[ClosedBar], policy: CalendarPolicy | None) -> list[SequenceEvidence]:
    """Evidence per bar from a fresh evaluator."""
    evaluator = SequenceEvaluator(policy=policy)
    return [evaluator.update(bar) for bar in bars]


@when("the sequence evaluator processes every bar")
def process_all(seq_ctx: dict[str, Any]) -> None:
    """Stream every staged bar under the staged (or default continuous) policy."""
    seq_ctx["evidences"] = _stream(_closed(seq_ctx["bars"]), seq_ctx["policy"])


@when(
    parsers.parse(
        'the sequence evaluator processes every bar under the "{name}" calendar policy'
    )
)
def process_all_named_policy(seq_ctx: dict[str, Any], name: str) -> None:
    """Stream every staged bar under the named policy (only "continuous" is ever named)."""
    assert name == "continuous"
    seq_ctx["evidences"] = _stream(_closed(seq_ctx["bars"]), None)


@when("the sequence evaluator processes every bar under that calendar policy")
def process_all_staged_policy(seq_ctx: dict[str, Any]) -> None:
    """Stream every staged bar under the previously staged calendar policy."""
    seq_ctx["evidences"] = _stream(_closed(seq_ctx["bars"]), seq_ctx["policy"])


@when(
    "the sequence evaluator processes the bars once with the suffix N and once with the suffix S"
)
def diverging_suffixes(seq_ctx: dict[str, Any]) -> None:
    """Replay the identical prefix ahead of two different one-bar futures."""
    prefix = seq_ctx["bars"]
    start = prefix[-1][0] + _HOUR
    runs = [_stream(_closed([*prefix, (start, _CODES[code])]), seq_ctx["policy"]) for code in "NS"]
    seq_ctx["suffix_runs"] = runs


@when(parsers.parse("a bar with OHLC {prices} is offered to the sequence evaluator"))
def offer_invalid(seq_ctx: dict[str, Any], prices: str) -> None:
    """Stream the staged bars, then offer an invalid bar and keep the error."""
    evaluator = SequenceEvaluator(policy=seq_ctx["policy"])
    bars = _closed(seq_ctx["bars"])
    for bar in bars:
        evaluator.update(bar)
    seq_ctx["evaluator"] = evaluator
    seq_ctx["next_time"] = bars[-1].close_time + _HOUR
    try:
        evaluator.update(ClosedBar(seq_ctx["next_time"], *json.loads(prices)))
        seq_ctx["error"] = None
    except ValueError as error:
        seq_ctx["error"] = error


@when(
    parsers.re(
        r'^a bullish engulfing bar B closing at "(?P<time>[^"]+)" is offered '
        r"to the sequence evaluator$"
    )
)
def offer_duplicate(seq_ctx: dict[str, Any], time: str) -> None:
    """Stream the staged bars, then offer a duplicate-timed bar and keep the error."""
    evaluator = SequenceEvaluator(policy=seq_ctx["policy"])
    for bar in _closed(seq_ctx["bars"]):
        evaluator.update(bar)
    seq_ctx["evaluator"] = evaluator
    try:
        evaluator.update(ClosedBar(datetime.fromisoformat(time), *_CODES["B"]))
        seq_ctx["error"] = None
    except ValueError as error:
        seq_ctx["error"] = error


# --- assertions -----------------------------------------------------------------------


@then(parsers.parse('the sequence states per bar are "{states}"'))
def assert_states(seq_ctx: dict[str, Any], states: str) -> None:
    """The per-bar state sequence, in order."""
    expected = [state.strip() for state in states.split(",")]
    assert [evidence.state for evidence in seq_ctx["evidences"]] == expected


@then(parsers.parse('the sequence state at bar {n:d} is "{state}"'))
def assert_state_at(seq_ctx: dict[str, Any], n: int, state: str) -> None:
    """The state of one specific bar."""
    assert seq_ctx["evidences"][n - 1].state == state


def _maybe_int(raw: str) -> int | None:
    """``None`` or a signed integer."""
    return None if raw == "None" else int(raw)


@then(
    parsers.re(
        r'^the confirmed direction at bar (?P<n>\d+) is (?P<value>-?\d+|None) '
        r'with id "(?P<rule_id>[a-z_]+)"$'
    )
)
def assert_direction_with_id(seq_ctx: dict[str, Any], n: str, value: str, rule_id: str) -> None:
    """The confirmed direction, cross-checked against the ledger's named rule id."""
    direction = _maybe_int(value)
    assert seq_ctx["evidences"][int(n) - 1].confirmed_direction == direction
    expected_id = {1: "doji_engulfing_bullish", -1: "doji_engulfing_bearish"}[direction]
    assert rule_id == expected_id


@then(parsers.re(r"^the confirmed direction at bar (?P<n>\d+) is (?P<value>-?\d+|None)$"))
def assert_direction(seq_ctx: dict[str, Any], n: str, value: str) -> None:
    """The confirmed direction alone."""
    assert seq_ctx["evidences"][int(n) - 1].confirmed_direction == _maybe_int(value)


@then(parsers.parse('the confirmation_time at bar {n:d} is "{time}"'))
def assert_confirmation_time(seq_ctx: dict[str, Any], n: int, time: str) -> None:
    """The confirming bar's close_time."""
    assert seq_ctx["evidences"][n - 1].confirmation_time == datetime.fromisoformat(time)


@then(parsers.parse("the confirmation_time at bar {n:d} is None"))
def assert_confirmation_time_none(seq_ctx: dict[str, Any], n: int) -> None:
    """No confirmation yet."""
    assert seq_ctx["evidences"][n - 1].confirmation_time is None


@then(parsers.parse('the candidate_close_time at bar {n:d} is "{time}"'))
def assert_candidate_time(seq_ctx: dict[str, Any], n: int, time: str) -> None:
    """The active or just-resolved candidate's close_time."""
    assert seq_ctx["evidences"][n - 1].candidate_close_time == datetime.fromisoformat(time)


@then(parsers.parse('the reason at bar {n:d} is "{reason}"'))
def assert_reason(seq_ctx: dict[str, Any], n: int, reason: str) -> None:
    """How the previous candidate ended on this bar."""
    assert seq_ctx["evidences"][n - 1].reason == reason


@then(parsers.parse('the sequence evaluator rejects it mentioning "{fragment}" and a remedy'))
def assert_rejected(seq_ctx: dict[str, Any], fragment: str) -> None:
    """A ValueError naming the problem and the corrective action."""
    assert isinstance(seq_ctx["error"], ValueError)
    assert fragment in str(seq_ctx["error"])
    assert "repair" in str(seq_ctx["error"]).lower()


@then(parsers.parse('the sequence state is still "{state}" with candidate_close_time "{time}"'))
def assert_still_candidate(seq_ctx: dict[str, Any], state: str, time: str) -> None:
    """The rejected bar consumed nothing: the pending candidate is unchanged."""
    assert state == "CANDIDATE"
    assert seq_ctx["evaluator"].candidate_close_time == datetime.fromisoformat(time)


@then(parsers.parse('the next valid bar B confirms bullish at "{time}"'))
def assert_next_confirms(seq_ctx: dict[str, Any], time: str) -> None:
    """The next valid bar continues the series and confirms bullish."""
    evidence = seq_ctx["evaluator"].update(ClosedBar(seq_ctx["next_time"], *_CODES["B"]))
    assert evidence.state == "CONFIRMED"
    assert evidence.confirmed_direction == 1
    assert evidence.confirmation_time == datetime.fromisoformat(time)


@then("the sequence evidence over the first 5 bars is identical under both suffixes")
def assert_suffix_invariance(seq_ctx: dict[str, Any]) -> None:
    """Future bars do not change already evaluated evidence."""
    first, second = seq_ctx["suffix_runs"]
    assert first[:5] == second[:5]


@then(
    'the sequence state at bar 6 is "EXPIRED" under the suffix N and "CONFIRMED" under the suffix S'
)
def assert_suffix_diverge(seq_ctx: dict[str, Any]) -> None:
    """The sixth bar's state differs with the suffix that follows the shared prefix."""
    first, second = seq_ctx["suffix_runs"]
    assert first[5].state == "EXPIRED"
    assert second[5].state == "CONFIRMED"


@then(
    parsers.parse(
        "the sequence evidence at bar {n:d} exposes only state, candidate_close_time, "
        "confirmed_direction, confirmation_time and reason"
    )
)
def assert_fields(seq_ctx: dict[str, Any], n: int) -> None:
    """The evidence is separately typed from geometry and context."""
    names = {field.name for field in fields(seq_ctx["evidences"][n - 1])}
    assert names == {
        "state",
        "candidate_close_time",
        "confirmed_direction",
        "confirmation_time",
        "reason",
    }


@then("the sequence evidence carries no pattern hits and no context values")
def assert_no_hits(seq_ctx: dict[str, Any]) -> None:
    """Geometry hits and context values stay outside the sequence evidence."""
    names = {field.name for field in fields(seq_ctx["evidences"][-1])}
    assert not names & {"hits", "context", "pattern", "patterns"}
