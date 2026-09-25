# Spec 05c — algo-analyze: ablation table (parallel lane of Spec 05)

**Parent spec:** `05-algo-analyze-metrics-significance.md` — read it for full
tool context, contract, and house rules.
**Depends on:** nothing — build and test against the two existing real
price-only runs (`baseline-ma`, `baseline-meanrev`) already in
`runs/experiments/baseline-comparison/`. **Blocks:** Spec 05e (integration)
only.
**Boundary (avoid merge conflicts):** create
`algo-analyze/src/algo_analyze/ablation.py` only. **Do not touch `cli.py`**
or any other lane's file (`deflated_sharpe.py`, `significance.py`,
`figures.py`).

## Objective

A function that takes N run identifiers, loads each run's metrics (reuse
`algo_backtest.metrics.metrics_from_artifact` — the metrics are already
computed and persisted per run, confirmed by reading the actual code; do not
recompute Sharpe/drawdown/hit-rate here), and produces a comparison table —
one row per run, columns for the shared metrics plus a delta column against
a designated baseline run.

```python
def build_ablation_table(run_dirs: <sequence of Path>, *, baseline: str) -> <table/dataclass result>
```

This is the exact machinery `experiments.md` §2 calls
`algo-analyze ablation --runs <a> <b> ...` (Experiments 2, 4, 6). Build and
test it now against `baseline-ma`/`baseline-meanrev` (arbitrary two runs —
proves the mechanism), then it's reused verbatim later for
baseline-vs-hybrid once Spec 04 exists. Match `summary.py`'s validation
style: fail fast on a missing run dir, a run with no metrics artifact, or an
unrecognized `baseline` identifier — don't silently skip or default.

## Test requirements

Gherkin/pytest-bdd. Cover: two-run comparison with a known delta (fixture
metrics, assert the computed delta matches); baseline identifier not among
the given runs (fail fast, name it); a run directory missing its metrics
artifact (fail fast, name the run).

## Definition of done

- `ablation.py` implemented, tested against real
  `baseline-ma`/`baseline-meanrev` run data, `make check`/`make audit` green
  standalone.
- Function is importable and callable in isolation — Spec 05e wires it into
  the CLI, not this lane.
