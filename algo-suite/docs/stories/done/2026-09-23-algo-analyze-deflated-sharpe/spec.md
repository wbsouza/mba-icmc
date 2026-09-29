# Spec 05a — algo-analyze: deflated Sharpe (parallel lane of Spec 05)

**Parent spec:** `05-algo-analyze-metrics-significance.md` — read it for full
tool context, contract, and house rules. This file only narrows scope to one
independently buildable lane.
**Depends on:** nothing. **Blocks:** Spec 05e (integration) only.
**Boundary (avoid merge conflicts with 05b/05c/05d):** create
`algo-analyze/src/algo_analyze/deflated_sharpe.py` only. **Do not touch
`cli.py`** — wiring a CLI subcommand is Spec 05e's job, after all four lanes
land. Do not touch any file another lane owns (`significance.py`,
`ablation.py`, `figures.py`).

## Objective

One pure function: given a `trades.parquet` (or the already-loaded trade
returns), compute the **deflated Sharpe ratio** (Bailey–López de Prado —
corrects the naive Sharpe for the number of trials/strategy variants tested,
so a headline number isn't inflated by selection bias).

```python
def deflated_sharpe(returns: <appropriate array type>, *, n_trials: int, skew: float | None = None, kurtosis: float | None = None) -> float:
    """Bailey–López de Prado deflated Sharpe ratio for one strategy's returns."""
```

Exact signature is the implementing agent's call — match whatever
`algo_analyze`'s existing style favors (check `summary.py` for the house
style: typed, frozen dataclasses for results, fail-fast on bad input). Read
the parent spec §4 for the plausibility-band context this feeds
(`experiments.md` §7.1: ~0.5–1.5 plausible, >2.0 investigate) — that's Spec
05e's job to wire in as a flag on the combined output, not this lane's.

## Test requirements

Gherkin/pytest-bdd, golden-value fixtures: the deflated correction must
provably reduce the naive Sharpe on a fixture with multiple trials (that's
the entire point of the correction — a test that doesn't show a reduction
hasn't tested anything). Cover: single-trial case (deflation ≈ no-op),
degenerate input (zero variance — fail fast, don't divide by zero silently).

## Definition of done

- `deflated_sharpe.py` implemented, tested, `make check`/`make audit` green
  standalone (this module has no dependency on the other three lanes).
- Function is importable and callable in isolation — Spec 05e will import it,
  not re-derive it.
