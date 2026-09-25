# Progress — Spec 05c (ablation table)

- [x] `algo-analyze/src/algo_analyze/ablation.py` — ablation table implementation
- [ ] Build/test against existing real price-only runs (`baseline-ma`, `baseline-meanrev` in
      `runs/experiments/baseline-comparison/`)
  - Blocked locally: `algo-suite/runs/experiments/baseline-comparison/` is absent in this checkout.
- [x] Do not touch `cli.py` or another lane's file (`deflated_sharpe.py`, `significance.py`, `figures.py`)
- [x] `make check` green
