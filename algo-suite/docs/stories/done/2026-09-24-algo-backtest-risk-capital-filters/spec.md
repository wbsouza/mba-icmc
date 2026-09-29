# Spec 04d — algo-backtest: risk & capital-management filters F5/F6 (lane of Spec 04, Wave 2)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §4 step 3, and
`specs.md` §14.5–§14.8 (formulas given verbatim) for full context.
**Depends on:** Spec 04b landed (`chain/model.py`). **Blocks:** Spec 04g (meta-learner) only.
**Order:** Wave 2, lane D — start once 04b merges; runs in parallel with 04c, 04e, 04f.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/rules/*.py` (new:
`risk_math.py`, `trail_stop.py`, `close_portion.py`, `risk_guard.py`) and
`chain/filters/f5_risk_guard.py`, `f6_capital_mgmt.py` only.

## Objective

Port the EJB version's lot-size formula, trail-stop math, and `RiskGuard` gap-closing parameters
(`risk=0.03`, `stop_level_factor=1.2`, etc.) into `rules/`, then wire F5 (risk guard) and F6
(capital management) filters on top. Regression test: the Python port must reproduce the legacy
decisions on identical synthetic input (`specs.md` §14.3's stated discipline). Independent of news
data — buildable in parallel with 04c.

## Definition of done

- `rules/*.py` reproduces the EJB version's legacy decisions on synthetic input (regression test).
- F5/F6 filters implement the `Filter` interface, VETO/ABSTAIN scenarios covered.
- `make check` green.
