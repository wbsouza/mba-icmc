"""The fill-cost and holding-rule parameters of a strategy: its `execution` section.

Story 12 (execution realism, 2026-09-27): the spread every fill pays, the per-lot
commission, the minimum bars a position is held and the broker's minimum stop distance
are strategy parameters — the
optional top-level `execution:` section of `strategies/<name>/config.yaml` (specs.md
§14.7, Strategy A05) — not code constants and not brokerage-model defaults. The section
belongs to no filter: the loader always resolves it (like `price_features`), defaulting
every key it omits, and writes the effective values back into the resolved config so a
run's `strategy-config.{json,yaml}` records the cost assumptions its result rests on. The
LEAN adapters (story 12 item C) read the typed object; the executor (item D) reads
`min_hold_bars`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

from algo_backtest.chain.params import Section, reject_unknown_keys, require_non_negative

_SECTION = "execution"


@dataclass(frozen=True)
class ExecutionConfig:
    """Fill costs and the holding rule. Defaults are the frictionless, hold-free case.

    - ``spread_pips``: bid/ask spread charged on every fill, in pips (A05 pilot: 1.0).
    - ``commission_per_lot``: account-currency fee per 1.0 lot traded, per side.
    - ``min_hold_bars``: bars a position must stay open before an opposite signal may
      close it (0 = a reversal closes immediately).
    - ``broker_stop_level_pips``: the broker's minimum distance between price and a stop
      or target order, in pips (LEAN does not expose OANDA's, so it is declared here; 0 =
      no broker minimum). F6 floors the stop at ``capital_mgmt.min_stop_factor`` × this.
    """

    spread_pips: float = 0.0
    commission_per_lot: float = 0.0
    min_hold_bars: int = 0
    broker_stop_level_pips: float = 0.0


_KEYS = tuple(field.name for field in fields(ExecutionConfig))


def _min_hold_bars(section: Section, *, strategy: str) -> int:
    """`min_hold_bars` as a non-negative integer, defaulting to 0; fractions and booleans fail.

    Raises:
        ValueError: the value is not an integer or is negative.
    """
    value = section.get("min_hold_bars", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.min_hold_bars must be an integer >= 0 (bars), "
            f"got {value!r} — fix it under '{_SECTION}:' in strategies/{strategy}/config.yaml"
        )
    return value


def parse_execution_config(section: Section, *, strategy: str) -> ExecutionConfig:
    """The section's values, defaulting every key it omits (fail fast on anything else).

    Raises:
        ValueError: an unknown key, a negative or non-numeric cost, or a `min_hold_bars`
            that is not a non-negative integer — each named with the strategy and section.
    """
    reject_unknown_keys(section, _KEYS, section=_SECTION, strategy=strategy)
    return ExecutionConfig(
        spread_pips=require_non_negative(
            section, "spread_pips", default=0.0, section=_SECTION, strategy=strategy
        ),
        commission_per_lot=require_non_negative(
            section, "commission_per_lot", default=0.0, section=_SECTION, strategy=strategy
        ),
        min_hold_bars=_min_hold_bars(section, strategy=strategy),
        broker_stop_level_pips=require_non_negative(
            section, "broker_stop_level_pips", default=0.0, section=_SECTION, strategy=strategy
        ),
    )


def execution_mapping(config: ExecutionConfig) -> dict[str, Any]:
    """The effective values as a plain mapping, for the resolved config and provenance."""
    return asdict(config)
