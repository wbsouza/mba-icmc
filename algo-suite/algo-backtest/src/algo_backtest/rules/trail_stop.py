"""Target / trail-stop level math (specs.md §14.5, ported from fx-manager's
`StrategyMoneyManagementFacadeBean`):

    target_level_N        = entry ± (|entry - SL| * target_factor_N
                                      + (target_factor_N + 1) * spread)
    trail_stop_at_level_N = entry ± |entry - SL| * trail_stop_at_level_factor_N
    trail_stop_to_level_N = entry ± (|entry - SL| * trail_stop_to_level_factor_N + spread)

The legacy "±" is resolved by trade direction, but not uniformly: `target_level` and
`trail_stop_at_level` move in the *profit* direction from entry (the price to take profit
at, and the price excursion needed to arm the trail); `trail_stop_to_level` moves in the
*loss* direction from entry — it is the tightened stop-loss the trail relocates to once
armed, still on the loss side of entry but closer than the original SL (specs.md §14.7's
worked example: "entry − 66% × SL distance" for a BUY). This is a documented interpretation
of an ambiguous "±" against §14.7's concrete description; the fx-manager Java source that
would otherwise disambiguate it is not present in this checkout (specs.md §14.3).
"""

from __future__ import annotations

from enum import StrEnum


class Direction(StrEnum):
    """Which way the trade profits, and therefore which way "±" resolves."""

    BUY = "BUY"
    SELL = "SELL"


def _profit_sign(direction: Direction) -> float:
    """+1 for BUY (profits as price rises), -1 for SELL (profits as price falls)."""
    return 1.0 if direction is Direction.BUY else -1.0


def _sl_distance(entry: float, stop_loss: float) -> float:
    """`|entry - stop_loss|`, fail-fast on a zero (meaningless risk) distance."""
    distance = abs(entry - stop_loss)
    if distance == 0:
        raise ValueError(
            "trail_stop: entry and stop_loss are equal, giving a zero SL distance "
            f"(entry={entry!r}, stop_loss={stop_loss!r}) — set a genuine stop-loss price"
        )
    return distance


def target_level(
    entry: float, stop_loss: float, target_factor: float, spread: float, direction: Direction
) -> float:
    """Profit-taking level N: `entry ± (SL_distance*target_factor + (target_factor+1)*spread)`."""
    distance = _sl_distance(entry, stop_loss)
    offset = distance * target_factor + (target_factor + 1) * spread
    return entry + _profit_sign(direction) * offset


def trail_stop_at_level(
    entry: float, stop_loss: float, trail_stop_at_level_factor: float, direction: Direction
) -> float:
    """Price (in the profit direction) that must be reached to arm the trailing stop."""
    distance = _sl_distance(entry, stop_loss)
    offset = distance * trail_stop_at_level_factor
    return entry + _profit_sign(direction) * offset


def trail_stop_to_level(
    entry: float,
    stop_loss: float,
    trail_stop_to_level_factor: float,
    spread: float,
    direction: Direction,
) -> float:
    """The tightened stop-loss price the armed trail relocates to (loss side of entry).

    `trail_stop_to_level_factor` is normalized to its magnitude before use. specs.md
    §14.9.4's canonical config carries this factor as a *negative* value
    (`strategy_math.trail_stop_to_level_factor: -0.66`), encoding "loss side" via sign —
    but this function already derives the loss-side direction independently from
    `direction` (see the module docstring's documented asymmetry). Applying the signed
    config value on top of that direction logic would double-apply the sign and move the
    result to the profit side instead. `abs()` here lets a caller pass the real config
    value (`-0.66`) and get the direction-correct result, rather than requiring callers
    to know to pre-negate it.
    """
    distance = _sl_distance(entry, stop_loss)
    offset = distance * abs(trail_stop_to_level_factor) + spread
    return entry - _profit_sign(direction) * offset
