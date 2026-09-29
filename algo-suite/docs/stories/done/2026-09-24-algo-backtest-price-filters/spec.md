# Spec 04c — algo-backtest: price-derived filters F1–F3 (lane of Spec 04, Wave 2)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §4 step 2 for full
context.
**Depends on:** Spec 04b landed (`chain/model.py`). **Blocks:** Spec 04g (meta-learner) only.
**Order:** Wave 2, lane C — start once 04b merges; runs in parallel with 04d, 04e, 04f.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/chain/filters/f1_trend.py`,
`f2_indicator.py`, `f3_pattern.py` only. Do not touch `chain/model.py`, `rules/*`, or any other
filter file.

## Objective

Trend (F1), indicator (F2), pattern (F3) filters — consume TA features LEAN computes natively. No
new external data dependency, buildable and testable immediately once `chain/model.py` exists.

## Definition of done

- F1–F3 each implement the `Filter` interface from `chain/model.py`, VETO/ABSTAIN scenarios covered.
- `make check` green.
