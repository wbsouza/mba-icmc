"""Steps for confluence_time_exit.feature — the pure time-exit lifecycle (story 21, T6).

A single `TimeExitLifecycle` is built once per scenario (`Given a time-exit
lifecycle...`) and every subsequent Given/When step drives it through its real
public methods. `<event> and it is refused` (the "inconsistent event" Outline)
dispatches one of a small closed set of recognized event phrases through regex,
reusing the same parsing helpers as the dedicated steps below.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest
import yaml
from algo_backtest.chain.time_exit import ClosureRequest, TimeExitLifecycle
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_time_exit.feature")


@dataclass
class _TimeExitCtx:
    """Per-scenario context: the lifecycle under test, the last requests seen, any error."""

    lifecycle: TimeExitLifecycle | None = None
    error: Exception | None = None
    last_requests: list[ClosureRequest] = field(default_factory=list)
    order_trade_ids: dict[int, str] = field(default_factory=dict)


@pytest.fixture
def time_exit_ctx() -> _TimeExitCtx:
    """A fresh per-scenario time-exit context."""
    return _TimeExitCtx()


def _utc(raw: str) -> datetime:
    """An ISO timestamp (`Z`, an offset, or naive) as a `datetime` — naive stays naive."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _lifecycle(ctx: _TimeExitCtx) -> TimeExitLifecycle:
    assert ctx.lifecycle is not None, "no time-exit lifecycle built"
    return ctx.lifecycle


# --- Dispatch table for the "<event> and it is refused" Outline ---

_ENTRY_RE = re.compile(
    r'^the entry of trade "(?P<tid>[^"]+)" filled at "(?P<time>[^"]+)" for '
    r"(?P<qty>-?\d+) units$"
)
_TRADABLE_RE = re.compile(r'^a tradable event arrives at "(?P<time>[^"]+)"$')
_STOP_RE = re.compile(
    r'^the stop of trade "(?P<tid>[^"]+)" filled at "(?P<time>[^"]+)" for '
    r"(?P<qty>-?\d+) units at price (?P<price>-?[\d.]+)$"
)


def _dispatch(ctx: _TimeExitCtx, event: str) -> None:
    """Run one of the recognized event phrases against the scenario's lifecycle."""
    lifecycle = _lifecycle(ctx)
    match = _ENTRY_RE.match(event)
    if match:
        lifecycle.entry_filled(match["tid"], _utc(match["time"]), int(match["qty"]))
        return
    match = _TRADABLE_RE.match(event)
    if match:
        ctx.last_requests = lifecycle.tradable_event(_utc(match["time"]))
        return
    match = _STOP_RE.match(event)
    if match:
        lifecycle.stop_filled(
            match["tid"], _utc(match["time"]), float(match["qty"]), float(match["price"])
        )
        return
    raise AssertionError(f"unrecognized event phrase for dispatch: {event!r}")


@when(parsers.parse("{event} and it is refused"))
def _event_refused(time_exit_ctx: _TimeExitCtx, event: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _dispatch(time_exit_ctx, event)
    time_exit_ctx.error = exc_info.value


# --- Construction ---


@given(
    parsers.parse("a time-exit lifecycle on a {clock:d}-minute clock with exit_after_bars {n:d}")
)
def _build(time_exit_ctx: _TimeExitCtx, clock: int, n: int) -> None:
    time_exit_ctx.lifecycle = TimeExitLifecycle(clock_minutes=clock, exit_after_bars=n)


@when(
    parsers.parse(
        "a time-exit lifecycle on a {clock:S}-minute clock with exit_after_bars {n:S} is "
        "built and refused"
    )
)
def _build_fails(time_exit_ctx: _TimeExitCtx, clock: str, n: str) -> None:
    """`clock`/`n` are flow-style YAML tokens, so `0`, `true` and `4.5` keep their types."""
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        TimeExitLifecycle(clock_minutes=yaml.safe_load(clock), exit_after_bars=yaml.safe_load(n))
    time_exit_ctx.error = exc_info.value


# --- Entries ---


@given(parsers.parse('the entry of trade "{tid}" filled at "{time}" for {qty:d} units'))
@when(parsers.parse('the entry of trade "{tid}" filled at "{time}" for {qty:d} units'))
def _entry_filled(time_exit_ctx: _TimeExitCtx, tid: str, time: str, qty: int) -> None:
    _lifecycle(time_exit_ctx).entry_filled(tid, _utc(time), qty)


@when(
    parsers.parse(
        'the entry of trade "{tid}" filled at "{time}" for {qty:d} units is reported again'
    )
)
def _entry_filled_again(time_exit_ctx: _TimeExitCtx, tid: str, time: str, qty: int) -> None:
    _lifecycle(time_exit_ctx).entry_filled(tid, _utc(time), qty)


@when(
    parsers.parse(
        'the reversal filled at "{time}" closing trade "{closing}" and opening trade '
        '"{opening}" for {qty:d} units'
    )
)
def _reversal(time_exit_ctx: _TimeExitCtx, time: str, closing: str, opening: str, qty: int) -> None:
    _lifecycle(time_exit_ctx).reversal_filled(closing, opening, _utc(time), qty)


@when(parsers.parse('a same-side signal arrives at "{time}"'))
def _same_side(time_exit_ctx: _TimeExitCtx, time: str) -> None:
    _lifecycle(time_exit_ctx).same_side_signal(_utc(time))


# --- Candles ---


def _deliver_range(lifecycle: TimeExitLifecycle, first: str, last: str) -> None:
    delta = timedelta(minutes=lifecycle.clock_minutes)
    start = _utc(first)
    last_start = _utc(last)
    while start <= last_start:
        lifecycle.completed_candle(start, start + delta)
        start += delta


@given(parsers.parse('completed candles on the clock from "{first}" through "{last}"'))
@when(parsers.parse('completed candles on the clock from "{first}" through "{last}"'))
def _candle_range(time_exit_ctx: _TimeExitCtx, first: str, last: str) -> None:
    _deliver_range(_lifecycle(time_exit_ctx), first, last)


@given(parsers.parse('the completed candle "{start}".."{end}" is delivered'))
@when(parsers.parse('the completed candle "{start}".."{end}" is delivered'))
def _candle_one(time_exit_ctx: _TimeExitCtx, start: str, end: str) -> None:
    _lifecycle(time_exit_ctx).completed_candle(_utc(start), _utc(end))


@when(parsers.parse('the candle "{start}".."{end}" is delivered and refused'))
def _candle_refused(time_exit_ctx: _TimeExitCtx, start: str, end: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _lifecycle(time_exit_ctx).completed_candle(_utc(start), _utc(end))
    time_exit_ctx.error = exc_info.value


# --- Tradable events ---


@when(parsers.parse('a tradable event arrives at "{time}"'))
def _tradable_event(time_exit_ctx: _TimeExitCtx, time: str) -> None:
    time_exit_ctx.last_requests = _lifecycle(time_exit_ctx).tradable_event(_utc(time))


# --- Order lifecycle ---


@when(
    parsers.parse(
        'the engine reports close order {order_id:d} submitted for trade "{tid}" at "{time}"'
    )
)
def _order_submitted(time_exit_ctx: _TimeExitCtx, order_id: int, tid: str, time: str) -> None:
    time_exit_ctx.order_trade_ids[order_id] = tid
    _lifecycle(time_exit_ctx).order_submitted(tid, order_id, _utc(time))


@when(
    parsers.parse(
        'the engine reports close order {order_id:d} "{status}" at "{time}" for {qty:d} '
        "units at price {price:g}"
    )
)
def _order_filled(
    time_exit_ctx: _TimeExitCtx, order_id: int, status: str, time: str, qty: int, price: float
) -> None:
    tid = time_exit_ctx.order_trade_ids[order_id]
    _lifecycle(time_exit_ctx).order_status_report(
        tid, order_id, status, _utc(time), quantity=float(qty), price=price
    )


@when(parsers.parse('the engine reports close order {order_id:d} "{status}" at "{time}"'))
def _order_status(time_exit_ctx: _TimeExitCtx, order_id: int, status: str, time: str) -> None:
    tid = time_exit_ctx.order_trade_ids[order_id]
    _lifecycle(time_exit_ctx).order_status_report(tid, order_id, status, _utc(time))


@when(
    parsers.parse(
        'the engine reports close order {order_id:d} "{status}" at "{time}" for {qty:d} '
        "units at price {price:g} and is refused"
    )
)
def _order_status_refused(
    time_exit_ctx: _TimeExitCtx, order_id: int, status: str, time: str, qty: int, price: float
) -> None:
    lifecycle = _lifecycle(time_exit_ctx)
    (tid,) = lifecycle.tracked_trade_ids()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        lifecycle.order_status_report(
            tid, order_id, status, _utc(time), quantity=float(qty), price=price
        )
    time_exit_ctx.error = exc_info.value


# --- Stop fills ---


@when(
    parsers.parse(
        'the stop of trade "{tid}" filled at "{time}" for {qty:d} units at price {price:g}'
    )
)
def _stop_filled(time_exit_ctx: _TimeExitCtx, tid: str, time: str, qty: int, price: float) -> None:
    _lifecycle(time_exit_ctx).stop_filled(tid, _utc(time), float(qty), price)


@when(
    parsers.parse(
        'the stop of trade "{tid}" filled at "{time}" for {qty:d} units at price {price:g} '
        "and is refused"
    )
)
def _stop_filled_refused(
    time_exit_ctx: _TimeExitCtx, tid: str, time: str, qty: int, price: float
) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _lifecycle(time_exit_ctx).stop_filled(tid, _utc(time), float(qty), price)
    time_exit_ctx.error = exc_info.value


_FOLLOWING_RE = re.compile(
    r"^an event at (?P<time1>\S+), then close order (?P<order_id>\d+) submitted at (?P<time2>\S+)$"
)


@given(parsers.parse("the following happens: {events}"))
def _following_happens(time_exit_ctx: _TimeExitCtx, events: str) -> None:
    """A tiny closed vocabulary of pre-stream-end event sequences: "nothing", or one
    tradable event followed by a close-order submission."""
    if events.strip() == "nothing":
        return
    match = _FOLLOWING_RE.match(events.strip())
    if not match:
        raise AssertionError(f"unrecognized events phrase: {events!r}")
    lifecycle = _lifecycle(time_exit_ctx)
    time_exit_ctx.last_requests = lifecycle.tradable_event(_utc(match["time1"]))
    (tid,) = lifecycle.tracked_trade_ids()
    order_id = int(match["order_id"])
    time_exit_ctx.order_trade_ids[order_id] = tid
    lifecycle.order_submitted(tid, order_id, _utc(match["time2"]))


# --- End of stream (a no-op marker: assertions below read current state) ---


@when("the event stream ends")
def _stream_ends(time_exit_ctx: _TimeExitCtx) -> None:
    assert time_exit_ctx.lifecycle is not None


# --- Assertions ---


@then(
    parsers.parse(
        'the lifecycle requests one closure of trade "{tid}" for {qty:d} units at "{time}"'
    )
)
def _requests_one(time_exit_ctx: _TimeExitCtx, tid: str, qty: int, time: str) -> None:
    assert len(time_exit_ctx.last_requests) == 1, time_exit_ctx.last_requests
    request = time_exit_ctx.last_requests[0]
    assert request.trade_id == tid
    assert request.quantity == qty
    assert request.at == _utc(time)


@then("the lifecycle requests no closure")
def _requests_none(time_exit_ctx: _TimeExitCtx) -> None:
    assert time_exit_ctx.last_requests == []


@then(parsers.parse('the expiry of trade "{tid}" is due at "{time}"'))
def _due_at(time_exit_ctx: _TimeExitCtx, tid: str, time: str) -> None:
    assert _lifecycle(time_exit_ctx).due_at(tid) == _utc(time)


@then(parsers.parse('the expiry of trade "{tid}" is not yet due'))
def _not_yet_due(time_exit_ctx: _TimeExitCtx, tid: str) -> None:
    assert _lifecycle(time_exit_ctx).due_at(tid) is None


@then(parsers.parse('the lifecycle has counted {n:d} completed bars for trade "{tid}"'))
def _completed_bars(time_exit_ctx: _TimeExitCtx, n: int, tid: str) -> None:
    assert _lifecycle(time_exit_ctx).completed_bars(tid) == n


@then(parsers.parse('the lifecycle suppresses new entry at "{time}"'))
def _suppresses(time_exit_ctx: _TimeExitCtx, time: str) -> None:
    assert _lifecycle(time_exit_ctx).suppresses_entry(_utc(time)) is True


@then(parsers.parse('the lifecycle does not suppress new entry at "{time}"'))
def _does_not_suppress(time_exit_ctx: _TimeExitCtx, time: str) -> None:
    assert _lifecycle(time_exit_ctx).suppresses_entry(_utc(time)) is False


@then(parsers.parse('new entry is {suppressed} at "{time}"'))
def _new_entry_suppressed(time_exit_ctx: _TimeExitCtx, suppressed: str, time: str) -> None:
    expected = {"suppressed": True, "not suppressed": False}[suppressed]
    assert _lifecycle(time_exit_ctx).suppresses_entry(_utc(time)) is expected


@then(parsers.parse('trade "{tid}" is "{state}" with reason "{reason}"'))
def _trade_state_with_reason(
    time_exit_ctx: _TimeExitCtx, tid: str, state: str, reason: str
) -> None:
    lifecycle = _lifecycle(time_exit_ctx)
    assert lifecycle.state(tid) == state
    assert lifecycle.exit_record(tid).reason == reason


@then(parsers.parse('trade "{tid}" is "{state}"'))
def _trade_state(time_exit_ctx: _TimeExitCtx, tid: str, state: str) -> None:
    assert _lifecycle(time_exit_ctx).state(tid) == state


@then(parsers.parse('the remaining quantity of trade "{tid}" is {qty:g}'))
def _remaining(time_exit_ctx: _TimeExitCtx, tid: str, qty: float) -> None:
    assert _lifecycle(time_exit_ctx).remaining_quantity(tid) == qty


@then(parsers.parse('the lifecycle tracks exactly the trades "{tids}"'))
def _tracks_exactly(time_exit_ctx: _TimeExitCtx, tids: str) -> None:
    expected = sorted(token.strip() for token in tids.split(","))
    assert sorted(_lifecycle(time_exit_ctx).tracked_trade_ids()) == expected


@then(parsers.parse('the unresolved trades are "{tids}"'))
def _unresolved(time_exit_ctx: _TimeExitCtx, tids: str) -> None:
    expected = sorted(token.strip() for token in tids.split(","))
    assert sorted(_lifecycle(time_exit_ctx).unresolved_trade_ids()) == expected


@then("the unresolved trades are none")
def _unresolved_none(time_exit_ctx: _TimeExitCtx) -> None:
    assert _lifecycle(time_exit_ctx).unresolved_trade_ids() == []


@then(parsers.parse("the lifecycle has requested {n:d} closures in total"))
def _requested_total(time_exit_ctx: _TimeExitCtx, n: int) -> None:
    assert _lifecycle(time_exit_ctx).closure_requests_total() == n


@then(
    parsers.parse(
        "the elapsed time from the entry fill to the closure request is {h:d} hours "
        "{m:d} minutes {s:d} seconds"
    )
)
def _elapsed(time_exit_ctx: _TimeExitCtx, h: int, m: int, s: int) -> None:
    assert len(time_exit_ctx.last_requests) == 1, time_exit_ctx.last_requests
    request = time_exit_ctx.last_requests[0]
    entry_fill_time = _lifecycle(time_exit_ctx).exit_record(request.trade_id).entry_fill_time
    assert request.at - entry_fill_time == timedelta(hours=h, minutes=m, seconds=s)


@then(parsers.parse('the time-exit failure names "{fragment}"'))
def _failure_names(time_exit_ctx: _TimeExitCtx, fragment: str) -> None:
    assert time_exit_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(time_exit_ctx.error), str(time_exit_ctx.error)


# --- Exit record ---


def _field_str(value: object) -> str:
    """Render one exit-record field the way the feature's flow-YAML tables write it."""
    if value is None:
        return "null"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


@then(parsers.parse('the exit record of trade "{tid}" is:'))
def _exit_record_table(time_exit_ctx: _TimeExitCtx, tid: str, datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    record = _lifecycle(time_exit_ctx).exit_record(tid)
    for field_name, expected in rows:
        assert _field_str(getattr(record, field_name)) == expected, (field_name, record)


@then(
    parsers.parse(
        'the exit record of trade "{tid}" has fill_time "{time}", fill_quantity {qty:g} '
        "and fill_price {price:g}"
    )
)
def _exit_record_fill(
    time_exit_ctx: _TimeExitCtx, tid: str, time: str, qty: float, price: float
) -> None:
    record = _lifecycle(time_exit_ctx).exit_record(tid)
    assert record.fill_time == _utc(time)
    assert record.fill_quantity == qty
    assert record.fill_price == pytest.approx(price)


@then(
    parsers.parse(
        'the exit record of trade "{tid}" has rejections {n:d} and order_status "{status}"'
    )
)
def _exit_record_rejections(time_exit_ctx: _TimeExitCtx, tid: str, n: int, status: str) -> None:
    record = _lifecycle(time_exit_ctx).exit_record(tid)
    assert record.rejections == n
    assert record.order_status == status


@then(
    parsers.parse(
        'the exit record of trade "{tid}" has order_id {order_id:d}, rejections {n:d} '
        'and order_status "{status}"'
    )
)
def _exit_record_order_id(
    time_exit_ctx: _TimeExitCtx, tid: str, order_id: int, n: int, status: str
) -> None:
    record = _lifecycle(time_exit_ctx).exit_record(tid)
    assert record.order_id == order_id
    assert record.rejections == n
    assert record.order_status == status


@then(
    parsers.parse(
        'the exit record of trade "{tid}" has status "{status}", reason null and fill_time null'
    )
)
def _exit_record_unresolved(time_exit_ctx: _TimeExitCtx, tid: str, status: str) -> None:
    record = _lifecycle(time_exit_ctx).exit_record(tid)
    assert record.status == status
    assert record.reason is None
    assert record.fill_time is None


@then(parsers.parse('the exit record of trade "{tid}" round-trips through plain JSON-safe values'))
def _exit_record_json(time_exit_ctx: _TimeExitCtx, tid: str) -> None:
    mapping = _lifecycle(time_exit_ctx).exit_record(tid).as_mapping()
    assert json.loads(json.dumps(mapping)) == mapping
