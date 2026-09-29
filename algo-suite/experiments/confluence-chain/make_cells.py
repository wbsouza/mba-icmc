"""Fourteen-cell manifest generator — the fixed confluence-chain study grid (story 21, T10).

A deterministic generator of the seven registered arms times two clocks (spec CC-21,
CC-23, CC-28; decisions D3, D7, D9, D11): A, B, A-plan, T-only, M-only, always-short and
always-long, on H1 (60 minutes, momentum L=480) and H4 (240 minutes, momentum L=120). A
standalone script outside the `algo_backtest` package (design.md: follows the
`experiments/heikin-ashi-signals/strategies/` layout). No other arm, clock, filter or
threshold search can enter the manifest — both are closed, internal registries; a caller
passing anything outside them is refused, never silently ignored.

Each cell's `filters:` list is exactly its required voters plus the F5/F6 gates — never
an extra, non-required directional voter, which would otherwise force HOLD through the
agreement terminal's "any other voter that disagrees" rule (spec CC-02). `momentum_context`
is nonetheless declared on every cell regardless of arm: it documents the clock's
registered momentum lookback (CC-28), a per-clock study parameter, not a per-arm one.

Six of the seven arms (every arm but A-plan) share the registered time-exit plan: empty
targets/trail_stops, `exit_after_bars: 4`, `min_hold_bars: 4`, ATR-based stops, 3% risk
(CC-21). A-plan instead pins every inherited stop/target/trail setting of the existing
`experiments/heikin-ashi-signals/strategies/heikin-ashi-h4-talib-volume-on/config.yaml`
reference plan (D11) — a deliberate exit-policy comparison, not an oversight; it carries
no `exit_after_bars` key at all.

Every cell shares EUR/USD, a USD 10,000 account, the pinned OANDA cost/broker-floor
settings, the F5 caps and the 2016-03-01..2017-02-28 study window. Each cell's config is
written to `<job_dir>/<cell_id>/config.yaml`; `<job_dir>/manifest.json` is a JSON list of
`{cell_id, arm, clock_minutes, config_hash}` rows, `config_hash` a SHA-256 over the
canonical (sorted-key) JSON of that cell's config — identical across repeated runs from
the same inputs, since nothing here reads the clock or any random source.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_TOOL = "make_cells"
ARMS: tuple[str, ...] = ("A", "B", "A-plan", "T-only", "M-only", "always-short", "always-long")
CLOCK_LOOKBACK: dict[int, int] = {60: 480, 240: 120}  # clock_minutes -> momentum lookback_bars

_REQUIRED_VOTERS: dict[str, tuple[str, ...]] = {
    "A": ("f1_trend", "f4_news_context"),
    "B": ("f1_trend", "f4_news_context", "f2_indicator"),
    "A-plan": ("f1_trend", "f4_news_context"),
    "T-only": ("f4_news_context",),
    "M-only": ("f1_trend",),
    "always-short": ("constant_direction",),
    "always-long": ("constant_direction",),
}
_NEWS_ARMS = frozenset({"A", "B", "A-plan", "T-only"})
_CONSTANT_DIRECTION = {"always-short": "SELL", "always-long": "BUY"}

_WINDOW = {"start": "2016-03-01", "end": "2017-02-28"}
_RISK_GUARD = {
    "portfolio_at_risk_cap": 0.18,
    "daily_drawdown_limit": -0.05,
    "weekly_drawdown_limit": -0.15,
    "max_concurrent_trades_per_account": 2,
    "max_leverage": 30,
}
_OANDA_EXECUTION = {"spread_pips": 1.0, "commission_per_lot": 0.0, "broker_stop_level_pips": 0.0}
# The pinned Heikin-Ashi H4 reference plan A-plan inherits (D11), taken verbatim from
# experiments/heikin-ashi-signals/strategies/heikin-ashi-h4-talib-volume-on/config.yaml.
_A_PLAN_CAPITAL_MGMT = {
    "risk_per_trade": 0.03,
    "stop_distance_source": "swing",
    "stop_loss_shrink": 0.50,
    "min_stop_pips": 5.0,
    "min_stop_factor": 1.2,
    "targets": [
        {"at_level_ratio": 4.0, "close_fraction": 0.5},
        {"at_level_ratio": 6.0, "close_fraction": 0.5},
    ],
    "trail_stops": [{"at_level_ratio": 2.0, "to_level_ratio": 0.1}],
    "min_reward_risk": 2.0,
    "atr_multiplier": 2.0,
}
_TIME_EXIT_CAPITAL_MGMT = {
    "risk_per_trade": 0.03,
    "stop_distance_source": "atr",
    "atr_multiplier": 2.0,
    "targets": [],
    "trail_stops": [],
    "exit_after_bars": 4,
}


def _validate_registry(arms: Sequence[str], clock_minutes: Sequence[int]) -> None:
    """Fail fast on any arm/clock outside the two closed registries.

    Raises:
        ValueError: an arm is not one of `ARMS`, or a clock is not a key of `CLOCK_LOOKBACK`.
    """
    for arm in arms:
        if arm not in ARMS:
            raise ValueError(
                f"{_TOOL}: {arm!r} is not a registered arm — registered arms: {list(ARMS)}"
            )
    for clock in clock_minutes:
        if clock not in CLOCK_LOOKBACK:
            raise ValueError(f"{_TOOL}: {clock} is not a registered clock (H1=60, H4=240)")


def _config_for(arm: str, clock_minutes: int) -> dict[str, Any]:
    """One cell's full, self-consistent config (CC-21, CC-23, CC-28, D9, D11)."""
    voters = _REQUIRED_VOTERS[arm]
    filters = [*voters, "f5_risk_guard", "f6_capital_mgmt"]
    config: dict[str, Any] = {
        "schema_version": 2,
        "pair": "EURUSD",
        "account_balance": 10000,
        "window": dict(_WINDOW),
        "filters": filters,
        "agreement": {"required_filters": list(voters)},
        "price_features": {
            "bar_minutes": clock_minutes,
            "atr_period": 14,
            "swing_lookback_bars": 60,
        },
        "momentum_context": {"lookback_bars": CLOCK_LOOKBACK[clock_minutes]},
        "risk_guard": dict(_RISK_GUARD),
        "capital_mgmt": _capital_mgmt_for(arm),
        "execution": _execution_for(arm),
    }
    if arm in _NEWS_ARMS:
        config["news_context"] = {"direction_source": "intensity_relative", "intensity_sign": -1}
    if "f2_indicator" in voters:
        config["indicator"] = {"rsi_midline": 50, "macd_hist_threshold": 0}
    if arm in _CONSTANT_DIRECTION:
        config["constant_direction"] = {"direction": _CONSTANT_DIRECTION[arm]}
    return config


def _capital_mgmt_for(arm: str) -> dict[str, Any]:
    """A-plan pins the reference plan (D11); every other arm uses the time-exit plan (CC-21)."""
    return dict(_A_PLAN_CAPITAL_MGMT) if arm == "A-plan" else dict(_TIME_EXIT_CAPITAL_MGMT)


def _execution_for(arm: str) -> dict[str, Any]:
    """The time-exit arms register `min_hold_bars: 4` (D11); A-plan keeps the reference default."""
    execution = dict(_OANDA_EXECUTION)
    execution["min_hold_bars"] = 0 if arm == "A-plan" else 4
    execution["close_on_veto"] = False
    return execution


def _config_hash(config: dict[str, Any]) -> str:
    """SHA-256 over the config's canonical (sorted-key) JSON — order-independent."""
    canonical = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cell_id(arm: str, clock_minutes: int) -> str:
    """A filesystem-safe, unique id: e.g. "a-plan-h1", "always-short-h4"."""
    clock_label = {60: "h1", 240: "h4"}[clock_minutes]
    return f"{arm.lower()}-{clock_label}"


@dataclass(frozen=True)
class Cell:
    """One generated cell: its identity, clock, full config and content hash."""

    cell_id: str
    arm: str
    clock_minutes: int
    config: dict[str, Any]
    config_hash: str

    def required_voters(self) -> list[str]:
        """The agreement terminal's required voters, as declared in this cell's config."""
        return list(self.config["agreement"]["required_filters"])


def generate_manifest(
    job_dir: Path,
    *,
    arms: Sequence[str] = ARMS,
    clock_minutes: Sequence[int] = tuple(CLOCK_LOOKBACK),
) -> list[Cell]:
    """Generate every requested arm x clock cell, write it, and return the 14 (default) cells.

    Raises:
        ValueError: `arms`/`clock_minutes` names anything outside the closed registries.
    """
    _validate_registry(arms, clock_minutes)
    cells = []
    for arm in arms:
        for clock in clock_minutes:
            config = _config_for(arm, clock)
            cells.append(
                Cell(
                    cell_id=_cell_id(arm, clock),
                    arm=arm,
                    clock_minutes=clock,
                    config=config,
                    config_hash=_config_hash(config),
                )
            )
    job_dir.mkdir(parents=True, exist_ok=True)
    for cell in cells:
        cell_dir = job_dir / cell.cell_id
        cell_dir.mkdir(parents=True, exist_ok=True)
        (cell_dir / "config.yaml").write_text(yaml.safe_dump(cell.config, sort_keys=False))
    manifest_rows = [
        {
            "cell_id": cell.cell_id,
            "arm": cell.arm,
            "clock_minutes": cell.clock_minutes,
            "config_hash": cell.config_hash,
        }
        for cell in cells
    ]
    (job_dir / "manifest.json").write_text(json.dumps(manifest_rows, indent=2))
    return cells


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point: `--job-dir` is the only argument."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    generate_manifest(args.job_dir)


if __name__ == "__main__":
    main()
