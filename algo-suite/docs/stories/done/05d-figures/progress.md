# Progress — Spec 05d (figures)

- [x] `algo-analyze/src/algo_analyze/figures.py` — figures implementation
- [x] Gherkin/pytest-bdd coverage for equity, drawdown, ablation bars, and zero-trade curves
- [x] Do not touch `cli.py` or another lane's file (`deflated_sharpe.py`, `significance.py`, `ablation.py`)
- [x] Focused test gate green
- [x] `make check` green

Note: this lane uses a small shared `algo_analyze._style` module so the later coverage-matrix
figure can reuse the same matplotlib PDF settings instead of duplicating plot style.
