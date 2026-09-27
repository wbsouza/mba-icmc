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
amendment, story 09), never code constants. No ATR indicator is wired yet, so the stop
distance is a fixed configured value, not derived from volatility.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.chain.params import require_positive
from algo_backtest.rules.risk_math import calculate_lot_size

_FILTER_NAME = "f6_capital_mgmt"
_SECTION = "capital_mgmt"

_REQUIRED_FEATURE_KEYS = (
    "account_balance",
    "pip_value",
    "stop_loss_pips",
    "margin_per_lot",
    "available_margin",
)


@dataclass(frozen=True)
class CapitalMgmtConfig:
    """F6's parameters: the risk fraction plus the sizing economics the chain feeds it.

    - ``risk_per_trade``: fraction of balance risked per trade, in (0, 1].
    - ``stop_loss_pips``: fixed stop distance in pips (no ATR wired yet).
    - ``pip_value_per_lot``: account-currency value of one pip per 1.0 lot.
    - ``lot_notional_units``: units of base currency in one 1.0 lot (100 000 standard).
    - ``assumed_leverage``: leverage used to derive margin per lot from notional.
    """

    risk_per_trade: float
    stop_loss_pips: float
    pip_value_per_lot: float
    lot_notional_units: float
    assumed_leverage: float


def parse_capital_mgmt_config(
    section: Mapping[str, Any], *, strategy: str
) -> CapitalMgmtConfig:
    """F6's parameters from a strategy config.yaml `capital_mgmt` section (fail fast).

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
    return CapitalMgmtConfig(
        risk_per_trade=risk_per_trade,
        stop_loss_pips=require_positive(
            section, "stop_loss_pips", section=_SECTION, strategy=strategy
        ),
        pip_value_per_lot=require_positive(
            section, "pip_value_per_lot", section=_SECTION, strategy=strategy
        ),
        lot_notional_units=require_positive(
            section, "lot_notional_units", section=_SECTION, strategy=strategy
        ),
        assumed_leverage=require_positive(
            section, "assumed_leverage", section=_SECTION, strategy=strategy
        ),
    )


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
