"""Time exit — the causal bar-count expiry as a pure lifecycle (story 21, T6).

`TimeExitLifecycle` is the LEAN-free component behind `capital_mgmt.exit_after_bars`
(spec CC-15..CC-19, CC-28, CC-31; decisions D5, D6, D11 as accepted by the user on
2026-09-28). It receives actual events — the entry fill, each distinct completed
candle, tradable quotes, order submissions and order statuses, stop fills, same-side
signals and reversal fills — and answers each tradable event with at most one
*closure request* (an expiry intent). It never invents a fill: prices, fill times and
order ids come from the engine that submits the order (T13 wires this to native events).

Accepted timing (D5). Let t be the signal bar during which the entry filled: the
completed candle whose `[start, end)` contains the fill time; t counts even when the
fill is mid-bar, and a fill exactly at a candle's end belongs to the next candle. The
exit is at the open of bar t+N. Expiry becomes DUE when candle t+N-1 completes, at its
end time (the open of t+N); the lifecycle requests one closure on the first delivered
tradable event whose timestamp is at or after that time. Only completed candles count,
so a market gap (weekend, daily break) extends elapsed wall-clock time (CC-28).

Precedence and identity (D6, D11). A stop fill is reconciled before any expiry request
can be issued: a full stop fill closes the trade with reason "stop" and nothing is
requested; a partial stop fill leaves only the residual quantity eligible. A same-side
signal does not reset the age; a filled reversal closes the old trade with reason
"reversal" and starts a new identity whose bar t is the candle containing the reversal
fill. A live close order blocks a second request; a confirmed rejection or cancellation
returns the trade to DUE, and the retry waits for a *later* real event, never the same
one. Repeated identical events are idempotent. The event that carries a closure request
suppresses new entry on that same event only (CC-19). A trade still HOLDING, DUE or
PENDING when the stream ends is reported unresolved, never closed by assumption.

States: HOLDING (entry filled, counting candles), DUE (expiry due, no live order),
PENDING (a close order is live), CLOSED (reason "expiry", "stop" or "reversal").
`ExitRecord` (CC-31) carries: trade_id, clock_minutes, exit_after_bars, entry_fill_time,
completed_bars, due_at, submitted_at, order_id, order_status, fill_time, fill_quantity,
fill_price, remaining_quantity, rejections, reason, status; anything not yet observed is
null, with `status` saying why. `as_mapping()` renders it as plain JSON-safe values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
HOLDING, DUE, PENDING, CLOSED = "HOLDING", "DUE", "PENDING", "CLOSED"
_LIFECYCLE = "TimeExitLifecycle"


def _require_utc(value: datetime, *, what: str) -> None:
    """Fail fast on a naive or non-UTC datetime, naming which time it was."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(
            f"{_LIFECYCLE}: {what} must be timezone-aware UTC, got {value!r} — construct it "
            "with tzinfo=UTC"
        )


def _sign(value: float) -> float:
    """+1.0 for a positive quantity, -1.0 for a negative one (never zero here)."""
    return 1.0 if value > 0 else -1.0


@dataclass(frozen=True)
class ClosureRequest:
    """One requested closure of an open trade: the signed order quantity to submit."""

    trade_id: str
    quantity: float
    at: datetime


@dataclass(frozen=True)
class ExitRecord:
    """The observable state of one trade's time exit (CC-31); see module docstring."""

    trade_id: str
    clock_minutes: int
    exit_after_bars: int
    entry_fill_time: datetime
    completed_bars: int
    due_at: datetime | None
    submitted_at: datetime | None
    order_id: int | None
    order_status: str | None
    fill_time: datetime | None
    fill_quantity: float | None
    fill_price: float | None
    remaining_quantity: float
    rejections: int
    reason: str | None
    status: str

    def as_mapping(self) -> dict[str, Any]:
        """The record as plain JSON-safe values (datetimes as ISO-8601 strings)."""
        return {
            "trade_id": self.trade_id,
            "clock_minutes": self.clock_minutes,
            "exit_after_bars": self.exit_after_bars,
            "entry_fill_time": self.entry_fill_time.isoformat(),
            "completed_bars": self.completed_bars,
            "due_at": _iso(self.due_at),
            "submitted_at": _iso(self.submitted_at),
            "order_id": self.order_id,
            "order_status": self.order_status,
            "fill_time": _iso(self.fill_time),
            "fill_quantity": self.fill_quantity,
            "fill_price": self.fill_price,
            "remaining_quantity": self.remaining_quantity,
            "rejections": self.rejections,
            "reason": self.reason,
            "status": self.status,
        }


def _iso(value: datetime | None) -> str | None:
    """A datetime as its ISO-8601 string, `None` kept as `None`."""
    return None if value is None else value.isoformat()


@dataclass
class _Trade:
    """One trade identity under a time-exit lifecycle; mutated in place as events arrive."""

    trade_id: str
    entry_fill_time: datetime
    entry_quantity: float
    bar_t_start: datetime
    remaining_quantity: float
    completed_bars: int = 0
    due_at: datetime | None = None
    status: str = HOLDING
    submitted_at: datetime | None = None
    order_id: int | None = None
    order_status: str | None = None
    fill_time: datetime | None = None
    fill_quantity: float | None = None
    fill_price: float | None = None
    rejections: int = 0
    reason: str | None = None
    last_requested_at: datetime | None = None


@dataclass
class TimeExitLifecycle:
    """The causal bar-count expiry for one instrument's time-exit trades; see module docstring.

    Raises:
        ValueError: `clock_minutes` or `exit_after_bars` is not a positive integer.
    """

    clock_minutes: int
    exit_after_bars: int
    _trades: dict[str, _Trade] = field(init=False, default_factory=dict)
    _open_trade_id: str | None = field(init=False, default=None)
    _last_time: datetime | None = field(init=False, default=None)
    _last_candle: tuple[datetime, datetime] | None = field(init=False, default=None)
    _requests_total: int = field(init=False, default=0)
    _suppressed_at: set[datetime] = field(init=False, default_factory=set)

    def __post_init__(self) -> None:
        """Validate the clock and horizon; both must be plain positive integers."""
        clock = self.clock_minutes
        if isinstance(clock, bool) or not isinstance(clock, int) or clock <= 0:
            raise ValueError(
                f"{_LIFECYCLE}: clock_minutes must be a positive integer, got {clock!r}"
            )
        bars = self.exit_after_bars
        if isinstance(bars, bool) or not isinstance(bars, int) or bars <= 0:
            raise ValueError(
                f"{_LIFECYCLE}: exit_after_bars must be a positive integer, got {bars!r}"
            )

    @property
    def _clock_delta(self) -> timedelta:
        """One signal bar's duration."""
        return timedelta(minutes=self.clock_minutes)

    def _bar_start(self, at: datetime) -> datetime:
        """The start of the clock-grid bar whose half-open `[start, end)` contains `at`."""
        whole_bars = (at - _EPOCH) // self._clock_delta
        return _EPOCH + whole_bars * self._clock_delta

    def _advance(self, at: datetime) -> None:
        """Track the newest timestamp seen across every kind of event."""
        self._last_time = at if self._last_time is None else max(self._last_time, at)

    def _open_trade(self) -> _Trade | None:
        """The currently open trade, or `None` if flat."""
        if self._open_trade_id is None:
            return None
        trade = self._trades[self._open_trade_id]
        return None if trade.status == CLOSED else trade

    def _known_trade(self, trade_id: str) -> _Trade:
        """A trade that must currently be open (HOLDING/DUE/PENDING).

        Raises:
            ValueError: `trade_id` is unknown or already closed.
        """
        trade = self._trades.get(trade_id)
        if trade is None or trade.status == CLOSED:
            raise ValueError(f"{_LIFECYCLE}: trade {trade_id!r} is not open")
        return trade

    # --- Queries -----------------------------------------------------------------

    def state(self, trade_id: str) -> str:
        """The trade's current state: HOLDING, DUE, PENDING or CLOSED."""
        return self._trades[trade_id].status

    def due_at(self, trade_id: str) -> datetime | None:
        """When the trade's expiry became due, or `None` while still counting bars."""
        return self._trades[trade_id].due_at

    def completed_bars(self, trade_id: str) -> int:
        """How many completed candles have counted toward the trade's horizon."""
        return self._trades[trade_id].completed_bars

    def remaining_quantity(self, trade_id: str) -> float:
        """The trade's quantity still open (reduced by any partial stop fill)."""
        return self._trades[trade_id].remaining_quantity

    def exit_record(self, trade_id: str) -> ExitRecord:
        """The trade's full observable exit state (CC-31)."""
        trade = self._trades[trade_id]
        return ExitRecord(
            trade_id=trade.trade_id,
            clock_minutes=self.clock_minutes,
            exit_after_bars=self.exit_after_bars,
            entry_fill_time=trade.entry_fill_time,
            completed_bars=trade.completed_bars,
            due_at=trade.due_at,
            submitted_at=trade.submitted_at,
            order_id=trade.order_id,
            order_status=trade.order_status,
            fill_time=trade.fill_time,
            fill_quantity=trade.fill_quantity,
            fill_price=trade.fill_price,
            remaining_quantity=trade.remaining_quantity,
            rejections=trade.rejections,
            reason=trade.reason,
            status=trade.status,
        )

    def tracked_trade_ids(self) -> list[str]:
        """Every trade identity ever created, open or closed, in creation order."""
        return list(self._trades)

    def unresolved_trade_ids(self) -> list[str]:
        """Trade identities not CLOSED: still HOLDING, DUE or PENDING at end of stream."""
        return [trade_id for trade_id, trade in self._trades.items() if trade.status != CLOSED]

    def closure_requests_total(self) -> int:
        """How many closure requests this lifecycle has issued in total."""
        return self._requests_total

    def suppresses_entry(self, at: datetime) -> bool:
        """Whether `at` is an event that carried a closure request (CC-19)."""
        return at in self._suppressed_at

    # --- Events --------------------------------------------------------------

    def entry_filled(self, trade_id: str, fill_time: datetime, quantity: float) -> None:
        """Record a filled entry, starting bar-t counting from the candle containing it.

        A repeat of the same trade_id/fill_time/quantity while that trade is still open
        is idempotent. Raises when quantity is zero, or another trade is still open.
        """
        _require_utc(fill_time, what="entry_fill_time")
        if isinstance(quantity, bool) or not isinstance(quantity, int | float) or quantity == 0:
            raise ValueError(f"{_LIFECYCLE}: quantity must be a nonzero number, got {quantity!r}")
        open_trade = self._open_trade()
        if open_trade is not None:
            if (
                trade_id == open_trade.trade_id
                and fill_time == open_trade.entry_fill_time
                and quantity == open_trade.entry_quantity
            ):
                return
            raise ValueError(f"{_LIFECYCLE}: trade {open_trade.trade_id!r} is still open")
        self._trades[trade_id] = _Trade(
            trade_id=trade_id,
            entry_fill_time=fill_time,
            entry_quantity=quantity,
            bar_t_start=self._bar_start(fill_time),
            remaining_quantity=abs(quantity),
        )
        self._open_trade_id = trade_id
        self._advance(fill_time)

    def completed_candle(self, start: datetime, end: datetime) -> None:
        """Deliver one completed candle `[start, end)`; counts toward the open trade's horizon.

        An exact repeat of the last delivered candle is idempotent. Raises on a partial
        bucket, an off-grid close, a naive time, or a candle not after the last delivered one.
        """
        self._validate_candle_bounds(start, end)
        if self._is_repeat_of_last_candle(start, end):
            return
        self._last_candle = (start, end)
        self._advance(end)
        self._count_bar_toward_horizon(start, end)

    def _validate_candle_bounds(self, start: datetime, end: datetime) -> None:
        """Fail fast on a naive time, a partial bucket, or an off-grid close.

        Raises:
            ValueError: `start`/`end` is naive, `[start, end)` is not one complete
                clock-minute candle, or `end` is not on the clock-minute UTC grid.
        """
        _require_utc(start, what="candle start")
        _require_utc(end, what="candle end")
        if end - start != self._clock_delta:
            raise ValueError(
                f"{_LIFECYCLE}: candle {start.isoformat()}..{end.isoformat()} is not one "
                f"complete {self.clock_minutes}-minute candle"
            )
        if (end - _EPOCH) % self._clock_delta != timedelta(0):
            raise ValueError(
                f"{_LIFECYCLE}: candle ending at {end.isoformat()} is not on the "
                f"{self.clock_minutes}-minute UTC grid"
            )

    def _is_repeat_of_last_candle(self, start: datetime, end: datetime) -> bool:
        """Whether `[start, end)` is an idempotent repeat of the last delivered candle.

        Raises:
            ValueError: `[start, end)` is not after the last delivered candle.
        """
        if self._last_candle is None:
            return False
        last_start, last_end = self._last_candle
        if (start, end) == (last_start, last_end):
            return True
        if end <= last_end:
            raise ValueError(
                f"{_LIFECYCLE}: candle ending at {end.isoformat()} is not after the last "
                f"completed candle ending at {last_end.isoformat()}"
            )
        return False

    def _count_bar_toward_horizon(self, start: datetime, end: datetime) -> None:
        """Advance the open HOLDING trade's completed-bar count, moving it to DUE at horizon."""
        trade = self._open_trade()
        if trade is not None and trade.status == HOLDING and start >= trade.bar_t_start:
            trade.completed_bars += 1
            if trade.completed_bars == self.exit_after_bars:
                trade.due_at = end
                trade.status = DUE

    def tradable_event(self, at: datetime) -> list[ClosureRequest]:
        """Advance the clock to `at`; request one closure if the open trade is DUE.

        Raises when `at` is naive or before the last processed time.
        """
        _require_utc(at, what="tradable event time")
        if self._last_time is not None and at < self._last_time:
            raise ValueError(
                f"{_LIFECYCLE}: tradable event at {at.isoformat()} is not at or after the "
                f"last processed time {self._last_time.isoformat()}"
            )
        self._advance(at)
        trade = self._open_trade()
        if trade is None or trade.status != DUE or trade.last_requested_at == at:
            return []
        request = ClosureRequest(
            trade_id=trade.trade_id,
            quantity=-_sign(trade.entry_quantity) * trade.remaining_quantity,
            at=at,
        )
        trade.last_requested_at = at
        self._requests_total += 1
        self._suppressed_at.add(at)
        return [request]

    def same_side_signal(self, at: datetime) -> None:
        """A same-side vote while a trade is open: never resets its age (D6)."""
        _require_utc(at, what="same-side signal time")
        self._advance(at)

    def reversal_filled(
        self, closing_trade_id: str, opening_trade_id: str, at: datetime, quantity: float
    ) -> None:
        """Close `closing_trade_id` with reason "reversal" and open a new identity at `at`."""
        _require_utc(at, what="reversal fill time")
        closing = self._known_trade(closing_trade_id)
        self._advance(at)
        closing.status = CLOSED
        closing.reason = "reversal"
        closing.fill_time = at
        closing.fill_quantity = -_sign(closing.entry_quantity) * closing.remaining_quantity
        closing.remaining_quantity = 0.0
        self._trades[opening_trade_id] = _Trade(
            trade_id=opening_trade_id,
            entry_fill_time=at,
            entry_quantity=quantity,
            bar_t_start=self._bar_start(at),
            remaining_quantity=abs(quantity),
        )
        self._open_trade_id = opening_trade_id

    def stop_filled(self, trade_id: str, at: datetime, quantity: float, price: float) -> None:
        """A (partial or full) stop fill; reconciled before any expiry request (CC-17).

        Raises when the trade is not open, or `quantity` exceeds the remaining position.
        """
        _require_utc(at, what="stop fill time")
        trade = self._known_trade(trade_id)
        if abs(quantity) > trade.remaining_quantity:
            raise ValueError(
                f"{_LIFECYCLE}: stop fill of {quantity:g} units exceeds the remaining "
                f"{trade.remaining_quantity:g} units of trade {trade_id!r}"
            )
        self._advance(at)
        trade.remaining_quantity -= abs(quantity)
        if trade.remaining_quantity == 0:
            trade.status = CLOSED
            trade.reason = "stop"
            trade.fill_time = at
            trade.fill_quantity = quantity
            trade.fill_price = price
            # trade was open (status != CLOSED per _known_trade) and only one trade is
            # ever open at a time, so trade_id is necessarily self._open_trade_id here.
            self._open_trade_id = None

    def order_submitted(self, trade_id: str, order_id: int, at: datetime) -> None:
        """The engine reports a close order live for the trade; blocks a second request."""
        _require_utc(at, what="order submission time")
        trade = self._known_trade(trade_id)
        self._advance(at)
        trade.submitted_at = at
        trade.order_id = order_id
        trade.order_status = "SUBMITTED"
        trade.status = PENDING

    def order_status_report(
        self,
        trade_id: str,
        order_id: int,
        status: str,
        at: datetime,
        *,
        quantity: float | None = None,
        price: float | None = None,
    ) -> None:
        """The engine reports the live close order's terminal status.

        `status` is one of "filled", "rejected" or "canceled". A rejection/cancellation
        returns the trade to DUE; the retry waits for a strictly later tradable event.

        Raises:
            ValueError: `order_id` is not the trade's live close order.
        """
        _require_utc(at, what="order status time")
        trade = self._trades.get(trade_id)
        if trade is None or trade.status != PENDING or trade.order_id != order_id:
            raise ValueError(
                f"{_LIFECYCLE}: order {order_id} is not the live close order of trade {trade_id!r}"
            )
        self._advance(at)
        if status == "filled":
            trade.order_status = "FILLED"
            trade.fill_time = at
            trade.fill_quantity = quantity
            trade.fill_price = price
            trade.remaining_quantity = 0.0
            trade.reason = "expiry"
            trade.status = CLOSED
            # trade was PENDING, reachable only for the currently open trade, so
            # trade_id is necessarily self._open_trade_id here.
            self._open_trade_id = None
        elif status in ("rejected", "canceled"):
            trade.rejections += 1
            trade.order_status = "REJECTED" if status == "rejected" else "CANCELED"
            trade.status = DUE
        else:
            raise ValueError(
                f"{_LIFECYCLE}: unknown order status {status!r} for trade {trade_id!r} — "
                "expected 'filled', 'rejected' or 'canceled'"
            )
