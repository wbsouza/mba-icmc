# Spec 05d — algo-analyze: figures (parallel lane of Spec 05)

**Parent spec:** `05-algo-analyze-metrics-significance.md` — read it for full
tool context, contract, and house rules.
**Depends on:** nothing — build and test against the two existing real
price-only runs. **Blocks:** Spec 05e (integration) only.
**Boundary (avoid merge conflicts):** create
`algo-analyze/src/algo_analyze/figures.py` only. **Do not touch `cli.py`**
or any other lane's file (`deflated_sharpe.py`, `significance.py`,
`ablation.py`).

## Objective

Equity-curve and drawdown-curve figures for one run, plus an ablation-bars
figure across multiple runs (consumes Spec 05c's ablation table shape if
that's landed by the time this integrates — at the module level, this lane
can build its own minimal input contract now and Spec 05e reconciles the two
at wiring time; don't block on 05c to start).

```python
def equity_curve_figure(run_dir: Path, out: Path) -> Path
def drawdown_curve_figure(run_dir: Path, out: Path) -> Path
def ablation_bars_figure(rows: <ablation rows>, out: Path) -> Path
```

Vector PDF output, sized for LaTeX `\includegraphics`, matching the thesis
figure style (fonts/sizes/palette — check if a shared style module/constants
already exist anywhere in the suite before inventing your own; if not,
define one small `_style.py` here and note it in the SPEC.md for
`algo-transform`'s coverage-matrix figure, per parent Spec 05 §3 step 5, to
reuse rather than duplicate later).

## Test requirements

Gherkin/pytest-bdd. Cover: figure file is produced, non-empty, valid PDF
(assert on file type/size, not pixel content — a snapshot test on rendered
pixels is brittle and not what's being verified here); a run with zero
closed trades still produces a sane (empty-but-valid) equity curve rather
than crashing.

## Definition of done

- `figures.py` implemented, tested against real run data, `make check`/
  `make audit` green standalone.
- Functions are importable and callable in isolation — Spec 05e wires them
  into the CLI, not this lane.
