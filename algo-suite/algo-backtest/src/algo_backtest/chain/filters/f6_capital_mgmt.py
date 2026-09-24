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
`risk_per_trade` (specs.md §14.7: 3% for Strategy A05) is resolved from config exactly like
`rules/risk_guard.py` resolves its caps — never hardcoded — but has a legacy reference value
(`0.03`, from `bean-templates.xml`'s `standardSymbolDeployment.risk`, specs.md §14.5),
unlike RiskGuard's five gap-closing caps which have none.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.rules.risk_math import calculate_lot_size
from algo_core.config import Impact, ParameterSpec, resolve

_FILTER_NAME = "f6_capital_mgmt"

_SCHEMA_VERSION = 1
_SCHEMA: tuple[ParameterSpec, ...] = (
    ParameterSpec(name="risk_math.risk_per_trade", impact=Impact.TRADING, reference_value=0.03),
)

_REQUIRED_FEATURE_KEYS = (
    "account_balance",
    "pip_value",
    "stop_loss_pips",
    "margin_per_lot",
    "available_margin",
)


@dataclass(frozen=True)
class CapitalMgmtConfig:
    """The single configured capital-management parameter F6 needs."""

    risk_per_trade: float


def load_capital_mgmt_config() -> CapitalMgmtConfig:
    """Resolve `risk_math.risk_per_trade` via the shared `algo_core.config` loader.

    Raises:
        ConfigError: (`MissingTradingParameter`) if `risk_per_trade` is absent from
            config — a hard stop, per CLAUDE.md's fail-fast policy.
    """
    result = resolve("backtest", _SCHEMA, _SCHEMA_VERSION)
    return CapitalMgmtConfig(risk_per_trade=float(result.values["risk_math.risk_per_trade"]))


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

    risk_per_trade: float = field(default_factory=lambda: load_capital_mgmt_config().risk_per_trade)

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
