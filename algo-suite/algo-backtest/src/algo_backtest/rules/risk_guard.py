"""RiskGuard: closes the risk gaps the EJB version's README documents as unenforced
(specs.md §14.8) — no portfolio-level capital cap, no daily/weekly drawdown limit, no
per-account concurrent-trade cap, no leverage cap. Every cap is a key of the `risk_guard`
section of the strategy's `config.yaml` (`parse_risk_guard_caps`, 2026-09-27 amendment,
story 09), independently `null`-disableable; a cap absent from the section is a hard stop
(CLAUDE.md fail-fast policy, specs.md §14.9.1) — the numeric values themselves are never
hardcoded here, and there is no legacy reference value for any of them (specs.md §14.8:
"the numeric values for each parameter are not specified in this document").
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from algo_backtest.chain.params import optional_int, optional_number

_SECTION = "risk_guard"


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


def parse_risk_guard_caps(section: Mapping[str, Any], *, strategy: str) -> RiskGuardCaps:
    """The five caps from a strategy config.yaml `risk_guard` section (fail fast).

    Raises:
        ValueError: a cap is absent (an explicit `null` disables it instead), is not a
            number (or not an integer, for the trade count), or a drawdown limit is
            positive (`RiskGuardCaps.__post_init__`).
    """

    def cap(key: str) -> float | None:
        return optional_number(section, key, section=_SECTION, strategy=strategy)

    return RiskGuardCaps(
        portfolio_at_risk_cap=cap(RiskCap.PORTFOLIO_AT_RISK),
        daily_drawdown_limit=cap(RiskCap.DAILY_DRAWDOWN),
        weekly_drawdown_limit=cap(RiskCap.WEEKLY_DRAWDOWN),
        max_concurrent_trades_per_account=optional_int(
            section, RiskCap.MAX_CONCURRENT_TRADES, section=_SECTION, strategy=strategy
        ),
        max_leverage=cap(RiskCap.MAX_LEVERAGE),
    )
