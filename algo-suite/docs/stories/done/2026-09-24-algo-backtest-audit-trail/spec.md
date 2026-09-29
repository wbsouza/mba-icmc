# Spec 04f — algo-backtest: decisions.parquet audit trail (lane of Spec 04, Wave 2)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` §6 and `specs.md`
§11.3.4 (columns) for full context.
**Depends on:** Spec 04b landed (`chain/model.py`) only — no filter dependency, can run alongside
04c/04d/04e. **Blocks:** Spec 04h (hybrid integration) and Spec 05 (ablation joins on `trade_id`).
**Order:** Wave 2, lane G — start once 04b merges; runs in parallel with 04c, 04d, 04e.
**Boundary (avoid merge conflicts):** `algo-backtest/src/algo_backtest/chain/audit.py` only.

## Objective

`decisions.parquet` writer per `specs.md` §11.3.4's column contract — the cross-tool contract
`algo-analyze` (Spec 05c, ablation) joins on `trade_id`. Depends only on `chain/model.py`'s
`ChainOutcome` shape, not on any concrete filter.

## Definition of done

- `chain/audit.py` writes `decisions.parquet` with the full §11.3.4 column set.
- `make check` green.
