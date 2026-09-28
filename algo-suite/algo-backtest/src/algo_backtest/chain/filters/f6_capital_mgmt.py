"""F6 — capital-management filter: builds the fx-manager trade plan for the bar
(specs.md §14.5–14.7, Strategy A05) and enriches the chain state with it for the executor.

The plan, every number of which traces to a `capital_mgmt` / `execution` YAML key or a
market feature (story 12, execution realism, item B):

1. **Stop distance per side, in pips.** `stop_distance_source` picks the base: `fixed` →
   `stop_loss_pips` for both sides; `atr` → feature `atr_pips` × `atr_multiplier`; `swing`
   → feature `swing_low_pips` for a long, `swing_high_pips` for a short (the structural
   level is direction-specific). Then the fx-manager DECREASE_STOP_LOSS: distance ×
   (1 − `stop_loss_shrink`); then the floor `max(min_stop_pips, min_stop_factor ×
   execution.broker_stop_level_pips)` (A05: `STOP_LEVEL_FACTOR` 1.2 × the broker's
   `STOP_LEVEL`). A missing source feature fails fast naming the key and the source.
2. **Lot size** from `rules/risk_math.calculate_lot_size(balance, risk_per_trade,
   pip_value, stop_pips)`. One lot serves both sides: it is sized from the *wider* of the
   two stops, so whichever side the terminal decision takes risks at most
   `risk_per_trade` of the balance (the narrower side risks less). The margin veto
   (`lot × margin_per_lot > available_margin`) uses that lot.
3. **Targets and trailing steps in pips**, spread included exactly as the confirmed
   fx-manager / spockfx-engine formulas in `rules/trail_stop.py` (reused, not
   re-derived, by evaluating them at entry 0 with the stop at −stop_pips):
   target = stop × at_level_ratio + (at_level_ratio + 1) × spread; trail arms at
   stop × at_level_ratio + (at_level_ratio + 1) × spread; trail moves the stop to
   stop × to_level_ratio + spread (negative = still a loss, 0 = breakeven plus spread,
   positive = locked-in profit).
4. **Reward:risk** = first target's pips / stop pips (fx-manager `getRewardRiskRatio`);
   `None` with no target. With `min_reward_risk` set, a side whose ratio falls below it
   VETOES the bar (F6 runs before the direction is known, so either side failing vetoes).

`state.features` contract — the account keys always (`chain/wiring.py`'s
`account_features`), the market keys per source:

    - "account_balance" (float): current account balance
    - "pip_value" (float): monetary value of one pip per 1.0 lot
    - "margin_per_lot" (float): margin required per 1.0 lot at the current instrument/leverage
    - "available_margin" (float): currently free margin in the account
    - "atr_pips" (float): the bar's ATR in pips (`stop_distance_source: atr`)
    - "swing_low_pips" / "swing_high_pips" (float): distance in pips to the structural
      stop for a long / a short (`stop_distance_source: swing`)

Enrichment: `proposed_lot_size` (specs.md §11.3.1's own example, kept for compatibility)
and `trade_plan`, a plain JSON-safe dict the executor (item D) places orders from:

    {"lot_size": float, "spread_pips": float,
     "long":  {"stop_pips": float, "targets": [{"pips": float, "close_fraction": float}],
               "trail_stops": [{"at_pips": float, "to_pips": float}], "reward_risk": float|None},
     "short": {...same...}}

`risk_per_trade` (specs.md §14.7: 3% for A05, `bean-templates.xml`'s
`standardSymbolDeployment.risk`), the sizing economics and the plan keys are the
`capital_mgmt` section of the strategy's `config.yaml` (`parse_capital_mgmt_config`), the
spread and broker stop level its `execution` section (`chain/execution_config.py`) — never
code constants. Every plan key is defaulted so an older five-key section keeps loading;
`capital_mgmt_mapping` writes the effective values back into the resolved config.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
from algo_backtest.rules.trail_stop import (
    Direction,
    target_level,
    trail_stop_at_level,
    trail_stop_to_level,
)

_FILTER_NAME = "f6_capital_mgmt"
_SECTION = "capital_mgmt"
# Where the base stop distance comes from: the configured `stop_loss_pips`, the bar's ATR
# times `atr_multiplier`, or the structural distance to the rolling swing low/high
# (`price_features.swing_lookback_bars`, features `swing_low_pips`/`swing_high_pips`).
StopDistanceSource = Literal["fixed", "atr", "swing"]
_STOP_SOURCES: frozenset[str] = frozenset(get_args(StopDistanceSource))
_ATR_FEATURE = "atr_pips"
# (long, short) structural-stop features for the `swing` source.
_SWING_FEATURES = ("swing_low_pips", "swing_high_pips")
# Tolerance on the close-fraction sum so `[0.3, 0.3, 0.4]`-style YAML is not rejected on
# a last-bit floating-point rounding while `[0.6, 0.6]` still is.
_SUM_TOLERANCE = 1e-9

_ACCOUNT_FEATURE_KEYS = ("account_balance", "pip_value", "margin_per_lot", "available_margin")


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
    - ``min_reward_risk``: minimum first-target pips / stop pips before entry (> 0), or
      ``None`` = no reward:risk veto.
    - ``stop_distance_source``: ``"fixed"`` (``stop_loss_pips``), ``"atr"``
      (``atr_multiplier`` × the bar's ``atr_pips`` feature) or ``"swing"`` (the
      ``swing_low_pips`` / ``swing_high_pips`` features — the distance to the rolling
      swing low/high, one per side; A05's structural template stop).
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


def _require_float(features: dict[str, object], key: str, *, needed_by: str) -> float:
    """Read `key` from `features` as a float; fail fast naming the key and who needs it.

    Raises:
        KeyError: the key is absent — `needed_by` says which contract (the account keys, or
            a `stop_distance_source`) requires it so the missing upstream feature is obvious.
    """
    if key not in features:
        raise KeyError(
            f"{_FILTER_NAME}: required state.features key {key!r} is missing — needed by "
            f"{needed_by}; see this module's docstring for the full contract"
        )
    return float(features[key])  # type: ignore[arg-type]


# Plan sides, in `trade_plan` key order; `_SWING_FEATURES` pairs with them positionally.
_SIDES = ("long", "short")

TradePlan = dict[str, object]


def _pips_offset(
    level: Callable[[float, float, float, float, Direction], float],
    stop_pips: float,
    factor: float,
    spread_pips: float,
) -> float:
    """One `rules/trail_stop.py` level formula evaluated in pip space: entry 0, stop at
    −stop_pips, BUY — the returned level *is* the offset from entry, in pips, valid for
    either side because the formulas are direction-symmetric (`entry + sign × diff`)."""
    return level(0.0, -stop_pips, factor, spread_pips, Direction.BUY)


@dataclass(frozen=True)
class _SidePlan:
    """One side's plan in pips from entry: the stop, the target ladder, the trailing steps
    and the first target's reward:risk (`None` without a target)."""

    stop_pips: float
    targets: tuple[tuple[float, float], ...]
    trail_stops: tuple[tuple[float, float], ...]

    @property
    def reward_risk(self) -> float | None:
        """First target's pips / stop pips (fx-manager `getRewardRiskRatio`)."""
        return self.targets[0][0] / self.stop_pips if self.targets else None

    def as_dict(self) -> dict[str, object]:
        """The JSON-safe `trade_plan["long"|"short"]` shape."""
        return {
            "stop_pips": self.stop_pips,
            "targets": [{"pips": pips, "close_fraction": frac} for pips, frac in self.targets],
            "trail_stops": [{"at_pips": at, "to_pips": to} for at, to in self.trail_stops],
            "reward_risk": self.reward_risk,
        }


@dataclass
class CapitalMgmtFilter:
    """`Filter` protocol implementation for F6: the trade plan from the strategy's
    `capital_mgmt` section plus the `execution` section's spread and broker stop level.

    - ``spread_pips``: `ExecutionConfig.spread_pips`, added to every target and trail level.
    - ``broker_stop_level_pips``: `ExecutionConfig.broker_stop_level_pips`; the stop is
      floored at `config.min_stop_factor` × it.
    """

    config: CapitalMgmtConfig
    spread_pips: float
    broker_stop_level_pips: float = 0.0

    def apply(self, state: ExecutionState) -> FilterResult:
        """Build the plan, enrich the state with it, VETO on a poor reward:risk or thin margin.

        Raises:
            KeyError: an account or source-specific feature is missing (see the module docstring).
            ValueError: a stop distance resolves to zero after the floors, so no lot can be sized.
        """
        features = state.features
        balance, pip_value, margin_per_lot, available_margin = (
            _require_float(features, key, needed_by="the F6 account contract")
            for key in _ACCOUNT_FEATURE_KEYS
        )
        sides = {
            side: self._side_plan(self._effective_stop_pips(base))
            for side, base in zip(_SIDES, self._base_stop_pips(features), strict=True)
        }
        widest_stop = max(side.stop_pips for side in sides.values())
        lot_size = calculate_lot_size(balance, self.config.risk_per_trade, pip_value, widest_stop)
        plan: TradePlan = {
            "lot_size": lot_size,
            "spread_pips": self.spread_pips,
            **{name: side.as_dict() for name, side in sides.items()},
        }
        enrichment: dict[str, object] = {"proposed_lot_size": lot_size, "trade_plan": plan}
        summary = self._summary(sides, lot_size)
        shortfall = self._reward_risk_shortfall(sides)
        if shortfall is not None:
            return self._result(f"{shortfall}; {summary}", veto=True, enrichment=enrichment)
        required_margin = lot_size * margin_per_lot
        if required_margin > available_margin:
            return self._result(
                f"insufficient margin: proposed lot {lot_size!r} needs {required_margin!r} but "
                f"only {available_margin!r} is available; {summary}",
                veto=True, enrichment=enrichment,
            )
        return self._result(
            f"sufficient margin for proposed lot size {lot_size!r}; {summary}",
            veto=False, enrichment=enrichment,
        )

    def _base_stop_pips(self, features: dict[str, object]) -> tuple[float, float]:
        """(long, short) base stop distance in pips per `stop_distance_source`, before the
        shrink and the floors.

        Raises:
            KeyError: the source's market feature is absent from `features`.
        """
        source = self.config.stop_distance_source
        needed_by = f"stop_distance_source: {source}"
        if source == "fixed":
            return self.config.stop_loss_pips, self.config.stop_loss_pips
        if source == "atr":
            atr = _require_float(features, _ATR_FEATURE, needed_by=needed_by)
            return atr * self.config.atr_multiplier, atr * self.config.atr_multiplier
        long_stop, short_stop = (
            _require_float(features, key, needed_by=needed_by) for key in _SWING_FEATURES
        )
        return long_stop, short_stop

    def _effective_stop_pips(self, base_pips: float) -> float:
        """The base distance shrunk toward entry by `stop_loss_shrink`, then floored at
        `max(min_stop_pips, min_stop_factor × broker_stop_level_pips)`.

        Raises:
            ValueError: the result is not strictly positive (a zero base with no floor), which
                would make the lot formula meaningless — naming the source and the floor keys.
        """
        config = self.config
        floor = max(config.min_stop_pips, config.min_stop_factor * self.broker_stop_level_pips)
        stop_pips = max(base_pips * (1.0 - config.stop_loss_shrink), floor)
        if stop_pips <= 0.0:
            raise ValueError(
                f"{_FILTER_NAME}: the stop distance resolved to {stop_pips!r} pips from "
                f"stop_distance_source: {config.stop_distance_source} (base {base_pips!r}) with "
                f"no floor — set capital_mgmt.min_stop_pips or execution.broker_stop_level_pips "
                f"(× capital_mgmt.min_stop_factor) so a trade can be sized"
            )
        return stop_pips

    def _side_plan(self, stop_pips: float) -> _SidePlan:
        """One side's targets and trailing steps in pips from entry, via `rules/trail_stop.py`."""
        spread = self.spread_pips
        return _SidePlan(
            stop_pips=stop_pips,
            targets=tuple(
                (_pips_offset(target_level, stop_pips, t.at_level_ratio, spread), t.close_fraction)
                for t in self.config.targets
            ),
            trail_stops=tuple(
                (
                    _pips_offset(trail_stop_at_level, stop_pips, step.at_level_ratio, spread),
                    _pips_offset(trail_stop_to_level, stop_pips, step.to_level_ratio, spread),
                )
                for step in self.config.trail_stops
            ),
        )

    def _reward_risk_shortfall(self, sides: dict[str, _SidePlan]) -> str | None:
        """The veto reason when a side's reward:risk is below `min_reward_risk`, else `None`.

        `parse_capital_mgmt_config` guarantees a target exists whenever the floor is set, so
        the ratio is never `None` here.
        """
        minimum = self.config.min_reward_risk
        if minimum is None:
            return None
        failing = [
            f"{name} {side.reward_risk!r}"
            for name, side in sides.items()
            if side.reward_risk is not None and side.reward_risk < minimum
        ]
        if not failing:
            return None
        return f"reward:risk below {_SECTION}.min_reward_risk {minimum!r}: {', '.join(failing)}"

    def _summary(self, sides: dict[str, _SidePlan], lot_size: float) -> str:
        """The reason's plan digest: source, per-side stop pips, lot, spread and reward:risk."""
        stops = ", ".join(f"{name} {side.stop_pips!r}" for name, side in sides.items())
        ratios = ", ".join(f"{name} {side.reward_risk!r}" for name, side in sides.items())
        return (
            f"trade plan from {self.config.stop_distance_source} stop ({stops} pips), "
            f"lot {lot_size!r}, spread {self.spread_pips!r} pips, reward:risk {ratios}"
        )

    @staticmethod
    def _result(reason: str, *, veto: bool, enrichment: dict[str, object]) -> FilterResult:
        """F6's result: always ABSTAIN (it sizes, it does not vote), vetoing or not."""
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=Recommendation.ABSTAIN,
            reason=reason,
            veto=veto,
            enrichment=enrichment,
        )
