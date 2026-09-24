"""F5 — RiskGuard filter: wires `rules/risk_guard.py` into the deterministic filter chain.

No upstream filter populates account/position state yet (Wave 2's F1-F4 land in parallel,
in other worktrees), so this module defines and proves its own minimal `state.features`
contract — the same situation Spec 04c documented for its own filter:

    - "account_portfolio_at_risk" (float): fraction of balance currently at risk
    - "account_daily_pnl_fraction" (float): today's signed P&L as a fraction of balance
    - "account_weekly_pnl_fraction" (float): this week's signed P&L as a fraction of balance
    - "account_open_trade_count" (int): currently open trades on this account
    - "account_leverage" (float): currently employed leverage

F5 never proposes a trade direction — it only gates: VETO if any configured RiskGuard cap
is breached, PASS (ABSTAIN, no veto) otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.rules.risk_guard import (
    AccountState,
    RiskGuardCaps,
    evaluate_risk_guard,
    load_risk_guard_caps,
)

_FILTER_NAME = "f5_risk_guard"


def _require(features: dict[str, object], key: str) -> object:
    """Read `key` from `features`, fail-fast if absent with a remediation message."""
    if key not in features:
        raise KeyError(
            f"{_FILTER_NAME}: required state.features key {key!r} is missing — no upstream "
            f"filter has populated it yet; see this module's docstring for the full contract"
        )
    return features[key]


def _require_float(features: dict[str, object], key: str) -> float:
    """`_require()`, coerced to `float`."""
    return float(_require(features, key))  # type: ignore[arg-type]


def _require_int(features: dict[str, object], key: str) -> int:
    """`_require()`, coerced to `int`."""
    return int(_require(features, key))  # type: ignore[call-overload, no-any-return]


def _account_state_from_features(features: dict[str, object]) -> AccountState:
    """Build an `AccountState` from `state.features`, per this module's documented contract."""
    return AccountState(
        portfolio_at_risk=_require_float(features, "account_portfolio_at_risk"),
        daily_pnl_fraction=_require_float(features, "account_daily_pnl_fraction"),
        weekly_pnl_fraction=_require_float(features, "account_weekly_pnl_fraction"),
        open_trade_count=_require_int(features, "account_open_trade_count"),
        leverage=_require_float(features, "account_leverage"),
    )


@dataclass
class RiskGuardFilter:
    """`Filter` protocol implementation for F5, backed by the configured RiskGuard caps."""

    caps: RiskGuardCaps = field(default_factory=load_risk_guard_caps)

    def apply(self, state: ExecutionState) -> FilterResult:
        """VETO if any configured RiskGuard cap is breached by the synthetic account state."""
        account = _account_state_from_features(state.features)
        verdict = evaluate_risk_guard(account, self.caps)
        if verdict.breached:
            reason = "; ".join(breach.reason for breach in verdict.breaches)
            return FilterResult(
                filter_name=_FILTER_NAME,
                recommendation=Recommendation.ABSTAIN,
                reason=reason,
                veto=True,
            )
        return FilterResult(
            filter_name=_FILTER_NAME,
            recommendation=Recommendation.ABSTAIN,
            reason="no risk-guard caps breached",
            veto=False,
        )
