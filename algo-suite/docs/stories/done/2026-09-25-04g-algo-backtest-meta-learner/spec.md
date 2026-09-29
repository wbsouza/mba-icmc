# Spec 04g — algo-backtest: F7 meta-learner (lane of Spec 04, Wave 3)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §4 step 5, and
`PRD.md` §1/§4 for full context.
**Depends on:** Spec 04c, 04d, 04e all landed — trains over their combined feature output.
**Blocks:** Spec 04h (hybrid integration).
**Order:** Wave 3 — start once 04c+04d+04e all merge.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py`,
plus adding the `lightgbm` dependency to `algo-backtest/pyproject.toml` (currently absent despite
the package description already naming it).

## Objective

LightGBM sub-models per feature family + logistic meta-learner combining them into `p̂ₜ`
(`PRD.md` §1), trained on the walk-forward split (`PRD.md` §4).

## Definition of done

- `lightgbm` declared as a dependency.
- F7 implements the `Filter` interface, walk-forward training reproducible.
- `make check` green.
