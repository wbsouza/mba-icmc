"""Partial-close ladder (specs.md §14.5, ported from fx-manager's
`ClosePortionOrderFacadeBean` rule logic): an ordered sequence of rungs, each closing a
fraction ("portion") of the *original* lot size. Strategy A05's specific two-rung ladder
(50% intermediate close, 50% final-target close — specs.md §14.7) is a caller-supplied
list of portions, never hardcoded here; this module only proves the general laddering
mechanic and its running-remainder bookkeeping.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

_OVER_CLOSE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class CloseRung:
    """One ladder rung: how much of the original lot it closes, and what remains after."""

    level: int
    lot_to_close: float
    lot_remaining: float


@dataclass(frozen=True)
class CloseLadder:
    """The single return value of `build_close_ladder()`: its rungs, in order."""

    rungs: tuple[CloseRung, ...]


def build_close_ladder(original_lot_size: float, portions: Sequence[float]) -> CloseLadder:
    """Build a partial-close ladder from ordered rung portions of `original_lot_size`.

    When the portions fully close the position (cumulative sum reaches 1.0, within
    tolerance), the last such rung closes exactly `original_lot_size - lot_closed_so_far`
    (the running remainder) rather than trusting `original_lot_size * portion` —
    independent per-rung percentages are not guaranteed to sum to exactly 1.0 after
    floating-point rounding, so that rung derives its size from what's actually left
    instead of risking a residual under-close (spockfx-engine's `MoneyManagementCalculator
    .setTargetLevels()`, specs.md §14.8 amendment 2026-09-26). A ladder whose portions sum
    to strictly less than 1.0 is a valid *partial* close (e.g. scaling out of most of a
    position while leaving a runner) — every rung, including the last, closes exactly its
    own declared portion in that case, and `lot_remaining` reports the still-open fraction.

    Raises:
        ValueError: if `original_lot_size` is not positive, any portion is outside
            `(0, 1]`, or the portions' cumulative sum exceeds 1.0 (closing more than the
            position ever held).
    """
    if original_lot_size <= 0:
        raise ValueError(
            f"close_portion.build_close_ladder: original_lot_size must be positive, "
            f"got {original_lot_size!r}"
        )
    rungs: list[CloseRung] = []
    cumulative_portion = 0.0
    lot_closed = 0.0
    last_level = len(portions)
    for level, portion in enumerate(portions, start=1):
        if not 0.0 < portion <= 1.0:
            raise ValueError(
                f"close_portion.build_close_ladder: rung {level} portion must be in "
                f"(0, 1], got {portion!r}"
            )
        cumulative_portion += portion
        if cumulative_portion > 1.0 + _OVER_CLOSE_TOLERANCE:
            raise ValueError(
                "close_portion.build_close_ladder: over-close — cumulative portion "
                f"{cumulative_portion!r} exceeds 1.0 by rung {level}"
            )
        lot_to_close = original_lot_size * portion
        lot_closed += lot_to_close
        fully_closes = cumulative_portion >= 1.0 - _OVER_CLOSE_TOLERANCE
        if level == last_level and fully_closes:
            lot_to_close = original_lot_size - (lot_closed - lot_to_close)
            lot_remaining = 0.0
        else:
            lot_remaining = original_lot_size - lot_closed
        rungs.append(
            CloseRung(level=level, lot_to_close=lot_to_close, lot_remaining=lot_remaining)
        )
    return CloseLadder(rungs=tuple(rungs))
