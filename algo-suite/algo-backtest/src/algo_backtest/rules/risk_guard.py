"""RiskGuard: closes the risk gaps the fx-manager README documents as unenforced
(specs.md §14.8) — no portfolio-level capital cap, no daily/weekly drawdown limit, no
per-account concurrent-trade cap, no leverage cap. Every cap is a `risk_guard.*` config
parameter, independently `null`-disableable; a cap the schema declares but that is absent
from config is a hard stop (CLAUDE.md fail-fast policy, specs.md §14.9.1) — the numeric
values themselves are never hardcoded here, and there is no legacy reference value for any
of them (specs.md §14.8: "the numeric values for each parameter are not specified in this
document").
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from algo_core.config import Impact, ParameterSpec, resolve

SCHEMA_VERSION = 1

_SCHEMA: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        name="risk_guard.portfolio_at_risk_cap", impact=Impact.TRADING, nullable=True
    ),
    ParameterSpec(
        name="risk_guard.daily_drawdown_limit", impact=Impact.TRADING, nullable=True
    ),
    ParameterSpec(
        name="risk_guard.weekly_drawdown_limit", impact=Impact.TRADING, nullable=True
    ),
    ParameterSpec(
        name="risk_guard.max_concurrent_trades_per_account", impact=Impact.TRADING, nullable=True
    ),
    ParameterSpec(name="risk_guard.max_leverage", impact=Impact.TRADING, nullable=True),
)


class RiskCap(StrEnum):
    """The five caps RiskGuard enforces, named after their `risk_guard.*` config key."""

    PORTFOLIO_AT_RISK = "portfolio_at_risk_cap"
    DAILY_DRAWDOWN = "daily_drawdown_limit"
    WEEKLY_DRAWDOWN = "weekly_drawdown_limit"
    MAX_CONCURRENT_TRADES = "max_concurrent_trades_per_account"
    MAX_LEVERAGE = "max_leverage"


@dataclass(frozen=True)
class RiskGuardCaps:
    """The five configured caps; `None` means that cap is explicitly disabled.

    The drawdown limits are PnL fractions a day/week may not fall *below*, so they are
    negative (``-0.05`` = a 5% loss) or zero. A positive limit would breach on every flat
    or merely-less-profitable bar and veto all trading, so it is rejected at construction.
    """

    portfolio_at_risk_cap: float | None
    daily_drawdown_limit: float | None
    weekly_drawdown_limit: float | None
    max_concurrent_trades_per_account: int | None
    max_leverage: float | None

    def __post_init__(self) -> None:
        """Fail fast on a positive (sign-flipped) drawdown limit."""
        for name in ("daily_drawdown_limit", "weekly_drawdown_limit"):
            limit = getattr(self, name)
            if limit is not None and limit > 0:
                raise ValueError(
                    f"risk_guard.{name} must be <= 0 (a PnL fraction the period may not "
                    f"fall below, e.g. -0.05 for a 5% loss); got {limit!r}"
                )


@dataclass(frozen=True)
class AccountState:
    """The account/position facts RiskGuard evaluates caps against."""

    portfolio_at_risk: float
    daily_pnl_fraction: float
    weekly_pnl_fraction: float
    open_trade_count: int
    leverage: float


@dataclass(frozen=True)
class RiskGuardBreach:
    """One breached cap and why."""

    cap: RiskCap
    reason: str


@dataclass(frozen=True)
class RiskGuardVerdict:
    """The single return value of `evaluate_risk_guard()`: every breach found, if any."""

    breaches: tuple[RiskGuardBreach, ...]

    @property
    def breached(self) -> bool:
        """Whether any cap was breached."""
        return bool(self.breaches)


def evaluate_risk_guard(account: AccountState, caps: RiskGuardCaps) -> RiskGuardVerdict:
    """Check `account` against every non-disabled cap in `caps`, reporting all breaches."""
    breaches: list[RiskGuardBreach] = []
    par_cap = caps.portfolio_at_risk_cap
    if par_cap is not None and account.portfolio_at_risk > par_cap:
        breaches.append(
            RiskGuardBreach(
                RiskCap.PORTFOLIO_AT_RISK,
                f"portfolio_at_risk {account.portfolio_at_risk!r} exceeds cap "
                f"{caps.portfolio_at_risk_cap!r}",
            )
        )
    daily_limit = caps.daily_drawdown_limit
    if daily_limit is not None and account.daily_pnl_fraction < daily_limit:
        breaches.append(
            RiskGuardBreach(
                RiskCap.DAILY_DRAWDOWN,
                f"daily_pnl_fraction {account.daily_pnl_fraction!r} is below limit "
                f"{caps.daily_drawdown_limit!r}",
            )
        )
    weekly_limit = caps.weekly_drawdown_limit
    if weekly_limit is not None and account.weekly_pnl_fraction < weekly_limit:
        breaches.append(
            RiskGuardBreach(
                RiskCap.WEEKLY_DRAWDOWN,
                f"weekly_pnl_fraction {account.weekly_pnl_fraction!r} is below limit "
                f"{caps.weekly_drawdown_limit!r}",
            )
        )
    if (
        caps.max_concurrent_trades_per_account is not None
        and account.open_trade_count >= caps.max_concurrent_trades_per_account
    ):
        breaches.append(
            RiskGuardBreach(
                RiskCap.MAX_CONCURRENT_TRADES,
                f"open_trade_count {account.open_trade_count!r} has reached the cap "
                f"{caps.max_concurrent_trades_per_account!r}",
            )
        )
    if caps.max_leverage is not None and account.leverage > caps.max_leverage:
        breaches.append(
            RiskGuardBreach(
                RiskCap.MAX_LEVERAGE,
                f"leverage {account.leverage!r} exceeds cap {caps.max_leverage!r}",
            )
        )
    return RiskGuardVerdict(breaches=tuple(breaches))


def load_risk_guard_caps() -> RiskGuardCaps:
    """Resolve the five `risk_guard.*` caps via the shared `algo_core.config` loader.

    Raises:
        ConfigError: (`MissingTradingParameter`) if a cap is absent from config rather
            than explicitly `null`-disabled — a hard stop, per CLAUDE.md's fail-fast policy.
    """
    result = resolve("backtest", _SCHEMA, SCHEMA_VERSION)
    values = result.values
    return RiskGuardCaps(
        portfolio_at_risk_cap=values["risk_guard.portfolio_at_risk_cap"],
        daily_drawdown_limit=values["risk_guard.daily_drawdown_limit"],
        weekly_drawdown_limit=values["risk_guard.weekly_drawdown_limit"],
        max_concurrent_trades_per_account=values["risk_guard.max_concurrent_trades_per_account"],
        max_leverage=values["risk_guard.max_leverage"],
    )
