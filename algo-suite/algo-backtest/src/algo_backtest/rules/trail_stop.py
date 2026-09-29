"""Target / trail-stop level math (specs.md §14.5, ported from the EJB version's
strategy money-management façade):

    target_level_N        = entry ± (|entry - SL| * target_factor_N
                                      + (target_factor_N + 1) * spread)
    trail_stop_at_level_N = entry ± (|entry - SL| * trail_stop_at_level_factor_N
                                      + (trail_stop_at_level_factor_N + 1) * spread)
    trail_stop_to_level_N = entry ± (|entry - SL| * trail_stop_to_level_factor_N + spread)

The legacy "±" is resolved by trade direction **the same way for all three formulas** —
confirmed against the EJB version's real source (its strategy money-management façade,
both the original JavaEE/EJB version and its later Spring reimplementation in
the author's Spring version agree): each formula computes a `diff` and returns
`entry + sign * diff`, where `sign` is `+1` for BUY and `-1` for SELL. There is no
separate "loss-side" case — `trail_stop_to_level_factor` is a **signed** config value
(specs.md §14.9.4's canonical sample carries it as `-0.66`), and it is that sign, not a
direction-branch, that puts the trail destination on the loss side. A positive factor
(e.g. `0.1`, seen in a legacy Heikin-Ashi template config) legitimately places the
destination on the *profit* side — that is a real, deployed "lock in partial profit
after arming" trail configuration, not a misconfiguration.

An earlier version of this module took `abs(trail_stop_to_level_factor)` and
hard-coded the loss-side subtraction before the real source was available in this
checkout; that flipped the sign of the `spread` term relative to the legacy formula.
Fixed here to match the confirmed source exactly.

`trail_stop_at_level` was also missing its `(factor + 1) * spread` term entirely — the
real source (the Spring version's money-management calculator, its
trail-stop arming-level computation) carries the same `(ratio + 1) * spread` shape as
`target_level`. Added here to match.
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
    entry: float,
    stop_loss: float,
    trail_stop_at_level_factor: float,
    spread: float,
    direction: Direction,
) -> float:
    """Price that must be reached to arm the trailing stop.

    Same `entry + sign*(SL_distance*factor + (factor+1)*spread)` shape as `target_level`
    (specs.md §14.9.4; the Spring version's trail-stop arming level agrees).
    """
    distance = _sl_distance(entry, stop_loss)
    offset = distance * trail_stop_at_level_factor + (trail_stop_at_level_factor + 1) * spread
    return entry + _profit_sign(direction) * offset


def trail_stop_to_level(
    entry: float,
    stop_loss: float,
    trail_stop_to_level_factor: float,
    spread: float,
    direction: Direction,
) -> float:
    """The price the armed trail relocates the stop-loss to.

    Same sign convention as `target_level`/`trail_stop_at_level`: `entry + sign * diff`,
    `sign` = +1 for BUY, -1 for SELL. `trail_stop_to_level_factor` is used as-is, signed —
    a negative factor (specs.md §14.9.4's canonical `-0.66`) places the destination on the
    loss side of entry (a tightened stop, still short of the original SL); a positive
    factor places it on the profit side (locking in partial profit once armed — a real,
    deployed configuration, e.g. a legacy Heikin-Ashi template's `0.1`). Do not `abs()`
    the factor — the sign is the caller's explicit direction choice, not a magnitude.
    """
    distance = _sl_distance(entry, stop_loss)
    offset = distance * trail_stop_to_level_factor + spread
    return entry + _profit_sign(direction) * offset
