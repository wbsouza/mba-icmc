"""F6 — capital-management filter: wires `rules/risk_math.py`'s fixed-fractional lot-size
formula into the deterministic filter chain.

No upstream filter populates ATR/balance state yet (Wave 2's F1-F4 land in parallel, in
other worktrees), so this module defines and proves its own minimal `state.features`
contract:

    - "account_balance" (float): current account balance
    - "pip_value" (float): monetary value of one pip per 1.0 lot
    - "stop_loss_pips" (float): ATR-derived stop-loss distance, in pips
    - "margin_per_lot" (float): margin required per 1.0 lot at the current instrument/leverage
    - "available_margin" (float): currently free margin in the account

F6 enriches `state.features["proposed_lot_size"]` (specs.md §11.3.1's own enrichment
example) and vetoes if the proposed lot would need more margin than is currently available.
`risk_per_trade` (specs.md §14.7: 3% for Strategy A05, the legacy reference value from
`bean-templates.xml`'s `standardSymbolDeployment.risk`) and the sizing economics the chain
feeds this filter — `stop_loss_pips`, `pip_value_per_lot`, `lot_notional_units`,
`assumed_leverage` (`chain/wiring.py`'s `account_features`) — are the `capital_mgmt`
section of the strategy's `config.yaml` (`parse_capital_mgmt_config`, 2026-09-27
amendment, story 09), never code constants. Story 12 (execution realism) grows the same
section with the fx-manager A05 trade plan — `stop_loss_shrink`, `min_stop_pips`,
`targets[]`, `trail_stops[]`, `min_reward_risk`, `stop_distance_source`, `atr_multiplier`
— every key defaulted so older sections keep loading, the effective values written back
into the resolved config by `capital_mgmt_mapping`. The filter itself still sizes from
the fixed `stop_loss_pips` alone; building the full plan from these keys is story 12's
item B.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any, Literal, cast, get_args

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.chain.params import (
    Section,
    optional_choice,
    optional_number,
    optional_positive,
    reject_unknown_keys,
    require_fraction,
    require_non_negative,
    require_number,
    require_positive,
)
from algo_backtest.rules.risk_math import calculate_lot_size

_FILTER_NAME = "f6_capital_mgmt"
_SECTION = "capital_mgmt"
# Where the base stop distance comes from: the configured `stop_loss_pips`, the bar's ATR
# times `atr_multiplier`, or the structural distance to the rolling swing low/high
# (`price_features.swing_lookback_bars`, features `swing_low_pips`/`swing_high_pips`).
StopDistanceSource = Literal["fixed", "atr", "swing"]
_STOP_SOURCES: frozenset[str] = frozenset(get_args(StopDistanceSource))
# Tolerance on the close-fraction sum so `[0.3, 0.3, 0.4]`-style YAML is not rejected on
# a last-bit floating-point rounding while `[0.6, 0.6]` still is.
_SUM_TOLERANCE = 1e-9

_REQUIRED_FEATURE_KEYS = (
    "account_balance",
    "pip_value",
    "stop_loss_pips",
    "margin_per_lot",
    "available_margin",
)


@dataclass(frozen=True)
class TargetLevel:
    """One take-profit level of the trade plan (fx-manager `finalTargetFactor` /
    `finalTargetLotPercentage`, `closePortionOrder`).

    - ``at_level_ratio``: the level's distance from entry as a multiple of the stop
      distance (> 0; A05 final target 2.0).
    - ``close_fraction``: the fraction of the position closed when the level is hit,
      in (0, 1]; the fractions of all targets sum to at most 1.
    """

    at_level_ratio: float
    close_fraction: float


@dataclass(frozen=True)
class TrailStop:
    """One trailing-stop step (fx-manager `trailStopAtLevelFactor` / `trailStopToLevelFactor`).

    - ``at_level_ratio``: the favourable excursion, as a multiple of the stop distance,
      at which the step arms (> 0; A05 arms at 0.5).
    - ``to_level_ratio``: where the stop moves, as a signed multiple of the stop distance
      from entry (negative = still on the losing side; A05 moves it to -0.66).
    """

    at_level_ratio: float
    to_level_ratio: float


# The pre-story-12 plan: one full-size target at twice the stop distance.
_DEFAULT_TARGETS: tuple[TargetLevel, ...] = (TargetLevel(at_level_ratio=2.0, close_fraction=1.0),)


@dataclass(frozen=True)
class CapitalMgmtConfig:
    """F6's parameters: the risk fraction, the sizing economics the chain feeds it and,
    since story 12, the fx-manager A05 trade plan (specs.md §14.5–14.7).

    The five sizing keys are required (trading-impactful, §14.9.1); the plan keys default
    to the pre-story-12 behaviour (a full-size target at 2 × stop, nothing else), so an
    older section keeps loading.

    - ``risk_per_trade``: fraction of balance risked per trade, in (0, 1].
    - ``stop_loss_pips``: base stop distance in pips when ``stop_distance_source`` is
      ``"fixed"``.
    - ``pip_value_per_lot``: account-currency value of one pip per 1.0 lot.
    - ``lot_notional_units``: units of base currency in one 1.0 lot (100 000 standard).
    - ``assumed_leverage``: leverage used to derive margin per lot from notional.
    - ``stop_loss_shrink``: fraction the base stop distance is shrunk toward entry, in
      [0, 1) (A05 `stopLossDecrease` 0.20).
    - ``min_stop_pips``: floor on the shrunk stop distance, in pips (>= 0).
    - ``min_stop_factor``: multiplier on the broker's minimum stop distance
      (``execution.broker_stop_level_pips``), >= 1 (A05 ``STOP_LEVEL_FACTOR`` 1.2); the
      effective floor is max(min_stop_pips, min_stop_factor × broker_stop_level_pips).
    - ``targets``: take-profit levels, ``at_level_ratio`` strictly increasing; empty =
      no target order.
    - ``trail_stops``: trailing-stop steps, ``at_level_ratio`` strictly increasing; empty
      = no trailing.
    - ``min_reward_risk``: minimum final-target distance / stop distance before entry
      (> 0), or ``None`` = no reward:risk veto.
    - ``stop_distance_source``: ``"fixed"`` (``stop_loss_pips``), ``"atr"``
      (``atr_multiplier`` × the bar's ATR in pips) or ``"swing"`` (the distance to the
      rolling swing low/high; A05's structural template stop).
    - ``atr_multiplier``: ATR multiple for the ``"atr"`` source (> 0).
    """

    risk_per_trade: float
    stop_loss_pips: float
    pip_value_per_lot: float
    lot_notional_units: float
    assumed_leverage: float
    stop_loss_shrink: float = 0.0
    min_stop_pips: float = 0.0
    min_stop_factor: float = 1.0
    targets: tuple[TargetLevel, ...] = _DEFAULT_TARGETS
    trail_stops: tuple[TrailStop, ...] = ()
    min_reward_risk: float | None = None
    stop_distance_source: StopDistanceSource = "fixed"
    atr_multiplier: float = 2.0


_KEYS = tuple(field.name for field in fields(CapitalMgmtConfig))
_TARGET_KEYS = tuple(field.name for field in fields(TargetLevel))
_TRAIL_KEYS = tuple(field.name for field in fields(TrailStop))


def _sizing_keys(section: Section, *, strategy: str) -> dict[str, float]:
    """The five required sizing keys, each strictly positive; `risk_per_trade` also <= 1.

    Raises:
        ValueError: a key is missing, non-numeric or not strictly positive, or
            `risk_per_trade` exceeds 1.
    """
    risk_per_trade = require_positive(
        section, "risk_per_trade", section=_SECTION, strategy=strategy
    )
    if risk_per_trade > 1.0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.risk_per_trade must be a fraction in (0, 1], "
            f"got {risk_per_trade!r}"
        )
    return {
        "risk_per_trade": risk_per_trade,
        **{
            key: require_positive(section, key, section=_SECTION, strategy=strategy)
            for key in ("stop_loss_pips", "pip_value_per_lot", "lot_notional_units",
                        "assumed_leverage")
        },
    }


def _level_entries(
    section: Section, key: str, known: tuple[str, ...], *, strategy: str
) -> list[dict[str, Any]]:
    """`section[key]` as a list of mappings with exactly `known` keys (fail fast otherwise).

    Raises:
        ValueError: the value is not a list, an entry is not a mapping, or an entry has an
            unknown key — each naming `capital_mgmt.<key>[<index>]`.
    """
    entries = section.get(key, None)
    if entries is None:
        return []
    if isinstance(entries, str | Mapping) or not isinstance(entries, list | tuple):
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.{key} must be a list of mappings, got "
            f"{entries!r} — write `{key}: [{{{', '.join(f'{k}: <number>' for k in known)}}}]`"
        )
    typed: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"strategy {strategy!r}: {_SECTION}.{key}[{index}] must be a mapping with keys "
                f"{list(known)}, got {entry!r}"
            )
        reject_unknown_keys(entry, known, section=f"{_SECTION}.{key}[{index}]", strategy=strategy)
        typed.append(dict(entry))
    return typed


def _require_increasing(levels: list[float], where: str, *, strategy: str) -> None:
    """`at_level_ratio` strictly increasing along the list, so plan steps fire in order.

    Raises:
        ValueError: naming the first entry that does not exceed its predecessor.
    """
    for index in range(1, len(levels)):
        if levels[index] <= levels[index - 1]:
            raise ValueError(
                f"strategy {strategy!r}: {_SECTION}.{where}[{index}].at_level_ratio must exceed "
                f"the previous entry's ({levels[index - 1]!r}), got {levels[index]!r} — order the "
                f"entries by at_level_ratio, strictly increasing"
            )


def _close_fraction(entry: Section, where: str, *, strategy: str) -> float:
    """A target's required `close_fraction`, in (0, 1].

    Raises:
        ValueError: the key is missing, non-numeric or outside (0, 1].
    """
    require_number(entry, "close_fraction", section=where, strategy=strategy)
    return require_fraction(
        entry, "close_fraction", default=0.0, section=where, strategy=strategy,
        low_inclusive=False, high_inclusive=True,
    )


def _parse_targets(section: Section, *, strategy: str) -> tuple[TargetLevel, ...] | None:
    """The `targets` list typed and validated, or `None` when the key is absent (default).

    Raises:
        ValueError: an entry fails its range check, the close fractions sum past 1, or the
            levels are not strictly increasing.
    """
    if "targets" not in section:
        return None
    targets: list[TargetLevel] = []
    for index, entry in enumerate(
        _level_entries(section, "targets", _TARGET_KEYS, strategy=strategy)
    ):
        where = f"{_SECTION}.targets[{index}]"
        targets.append(
            TargetLevel(
                at_level_ratio=require_positive(
                    entry, "at_level_ratio", section=where, strategy=strategy
                ),
                close_fraction=_close_fraction(entry, where, strategy=strategy),
            )
        )
    total = sum(target.close_fraction for target in targets)
    if total > 1.0 + _SUM_TOLERANCE:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.targets close_fraction values sum to "
            f"{round(total, 9)!r}, more than the whole position (1.0) — lower them"
        )
    _require_increasing([t.at_level_ratio for t in targets], "targets", strategy=strategy)
    return tuple(targets)


def _parse_trail_stops(section: Section, *, strategy: str) -> tuple[TrailStop, ...]:
    """The `trail_stops` list typed and validated (empty when absent).

    Raises:
        ValueError: an arming level is not > 0, a destination is not a number, or the
            arming levels are not strictly increasing.
    """
    trail: list[TrailStop] = []
    for index, entry in enumerate(
        _level_entries(section, "trail_stops", _TRAIL_KEYS, strategy=strategy)
    ):
        where = f"{_SECTION}.trail_stops[{index}]"
        trail.append(
            TrailStop(
                at_level_ratio=require_positive(
                    entry, "at_level_ratio", section=where, strategy=strategy
                ),
                to_level_ratio=require_number(
                    entry, "to_level_ratio", section=where, strategy=strategy
                ),
            )
        )
    _require_increasing([t.at_level_ratio for t in trail], "trail_stops", strategy=strategy)
    return tuple(trail)


def _min_reward_risk(
    section: Section, targets: tuple[TargetLevel, ...], *, strategy: str
) -> float | None:
    """`min_reward_risk` (> 0) or `None` when absent/`null`; needs a target to measure against.

    Raises:
        ValueError: the value is not a positive number, or it is set while `targets` is empty.
    """
    if "min_reward_risk" not in section:
        return None
    value = optional_number(section, "min_reward_risk", section=_SECTION, strategy=strategy)
    if value is None:
        return None
    if value <= 0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.min_reward_risk must be > 0 (or null to disable), "
            f"got {value!r}"
        )
    if not targets:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.min_reward_risk needs at least one target to "
            "measure the reward against, but targets is empty — add a target or set "
            "min_reward_risk: null"
        )
    return value


def _min_stop_factor(section: Section, *, strategy: str) -> float:
    """`min_stop_factor` (>= 1: the broker's stop level can only be widened), default 1.0.

    Raises:
        ValueError: the value is not a number or is below 1.
    """
    if "min_stop_factor" not in section:
        return 1.0
    value = require_number(section, "min_stop_factor", section=_SECTION, strategy=strategy)
    if value < 1.0:
        raise ValueError(
            f"strategy {strategy!r}: {_SECTION}.min_stop_factor must be >= 1 (a multiplier on the "
            f"broker's minimum stop distance), got {value!r}"
        )
    return value


def parse_capital_mgmt_config(section: Section, *, strategy: str) -> CapitalMgmtConfig:
    """F6's parameters from a strategy config.yaml `capital_mgmt` section (fail fast).

    The five sizing keys are required; every trade-plan key defaults when omitted.

    Raises:
        ValueError: an unknown key; a sizing key missing, non-numeric or not strictly
            positive; `risk_per_trade` above 1; or any trade-plan value outside its
            documented range (see `CapitalMgmtConfig`).
    """
    reject_unknown_keys(section, _KEYS, section=_SECTION, strategy=strategy)
    sizing = _sizing_keys(section, strategy=strategy)
    explicit_targets = _parse_targets(section, strategy=strategy)
    targets = explicit_targets if explicit_targets is not None else _DEFAULT_TARGETS
    source = cast(
        StopDistanceSource,
        optional_choice(
            section, "stop_distance_source", default="fixed", choices=_STOP_SOURCES,
            section=_SECTION, strategy=strategy,
        ),
    )
    return CapitalMgmtConfig(
        **sizing,
        stop_loss_shrink=require_fraction(
            section, "stop_loss_shrink", default=0.0, section=_SECTION, strategy=strategy,
            low_inclusive=True, high_inclusive=False,
        ),
        min_stop_pips=require_non_negative(
            section, "min_stop_pips", default=0.0, section=_SECTION, strategy=strategy
        ),
        min_stop_factor=_min_stop_factor(section, strategy=strategy),
        targets=targets,
        trail_stops=_parse_trail_stops(section, strategy=strategy),
        min_reward_risk=_min_reward_risk(section, targets, strategy=strategy),
        stop_distance_source=source,
        atr_multiplier=optional_positive(
            section, "atr_multiplier", default=2.0, section=_SECTION, strategy=strategy
        ),
    )


def capital_mgmt_mapping(config: CapitalMgmtConfig) -> dict[str, Any]:
    """The effective values as a plain YAML/JSON-safe mapping (lists, not tuples), for the
    resolved config and provenance; `parse_capital_mgmt_config` accepts it back unchanged."""
    mapping = asdict(config)
    mapping["targets"] = [asdict(target) for target in config.targets]
    mapping["trail_stops"] = [asdict(step) for step in config.trail_stops]
    return mapping


def _require_float(features: dict[str, object], key: str) -> float:
    """Read `key` from `features` as a float, fail-fast if absent with a remediation message."""
    if key not in features:
        raise KeyError(
            f"{_FILTER_NAME}: required state.features key {key!r} is missing — no upstream "
            f"filter has populated it yet; see this module's docstring for the full contract"
        )
    return float(features[key])  # type: ignore[arg-type]


@dataclass
class CapitalMgmtFilter:
    """`Filter` protocol implementation for F6, backed by the configured `risk_per_trade`."""

    risk_per_trade: float

    def apply(self, state: ExecutionState) -> FilterResult:
        """Compute the proposed lot size, enrich state with it, VETO if margin is insufficient."""
        features = state.features
        balance = _require_float(features, "account_balance")
        pip_value = _require_float(features, "pip_value")
        stop_loss_pips = _require_float(features, "stop_loss_pips")
        margin_per_lot = _require_float(features, "margin_per_lot")
        available_margin = _require_float(features, "available_margin")

        lot_size = calculate_lot_size(balance, self.risk_per_trade, pip_value, stop_loss_pips)
        required_margin = lot_size * margin_per_lot
        enrichment: dict[str, object] = {"proposed_lot_size": lot_size}

        if required_margin > available_margin:
            return FilterResult(
                filter_name=_FILTER_NAME,
                recommendation=Recommendation.ABSTAIN,
                reason=(
                    f"insufficient margin: proposed lot {lot_size!r} needs "
                    f"{required_margin!r} but only {available_margin!r} is available"
                ),
                veto=True,
                enrichment=enrichment,
            )
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=Recommendation.ABSTAIN,
            reason=f"sufficient margin for proposed lot size {lot_size!r}",
            veto=False,
            enrichment=enrichment,
        )
