"""Fixed-fractional lot sizing (specs.md §14.5, ported from the EJB version's
money-management façade).

`specs.md` §14.7 documents `risk = 0.03` as the reference strategy's *tuned parameter value*, not a
language-level constant — so this module never hardcodes a risk fraction. Every call site
(a filter, a strategy config) supplies its own `risk`, sourced from `config.yaml` per
CLAUDE.md's fail-fast config policy.
"""

from __future__ import annotations


def calculate_lot_size(
    account_balance: float, risk: float, pip_value: float, stop_loss_pips: float
) -> float:
    """Fixed-fractional lot size: `(account_balance * risk) / (pip_value * stop_loss_pips)`.

    Raises:
        ValueError: if any input is not strictly positive — a non-positive balance, risk
            fraction, pip value or stop-loss distance makes the formula meaningless (zero or
            negative lot size, or a division by zero).
    """
    for name, value in (
        ("account_balance", account_balance),
        ("risk", risk),
        ("pip_value", pip_value),
        ("stop_loss_pips", stop_loss_pips),
    ):
        if value <= 0:
            raise ValueError(
                f"risk_math.calculate_lot_size: {name} must be positive, got {value!r}"
            )
    return (account_balance * risk) / (pip_value * stop_loss_pips)
