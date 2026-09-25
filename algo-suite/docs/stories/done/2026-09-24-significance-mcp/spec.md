# Spec 05b — algo-analyze: Monte-Carlo Permutation Test (parallel lane of Spec 05)

**Parent spec:** `05-algo-analyze-metrics-significance.md` — read it for full
tool context, contract, and house rules.
**Depends on:** nothing. **Blocks:** Spec 05e (integration) only.
**Boundary (avoid merge conflicts):** create
`algo-analyze/src/algo_analyze/significance.py` only. **Do not touch
`cli.py`** or any other lane's file (`deflated_sharpe.py`, `ablation.py`,
`figures.py`).

## Objective

One function implementing Aronson's Monte-Carlo Permutation Test: given two
strategies' trade returns (e.g. baseline vs. hybrid, or any two runs), test
whether the observed difference in return distributions is significant under
random permutation, fixed-seed for reproducibility ([`experiments.md`](../../../experiments.md) §5 —
every Chapter 4 number must be reproducible).

```python
def mcp_test(returns_a: <array type>, returns_b: <array type>, *, n_permutations: int, seed: int) -> <result type with p-value>
```

Same note as 05a: match existing `algo_analyze` style (check `summary.py`).

## Test requirements

Gherkin/pytest-bdd. Cover: determinism under a fixed seed (run twice, same
p-value); a fixture with a known, large, real difference should reject the
null (low p-value); a fixture with identical distributions should not reject
(p-value near 1 / not significant); permutation count sensitivity (does a
tiny `n_permutations` still return without crashing? if that's insufficient
for meaningful results, fail fast with a clear minimum, don't silently
under-sample).

## Definition of done

- `significance.py` implemented, tested, `make check`/`make audit` green
  standalone.
- Function is importable and callable in isolation — Spec 05e wires it into
  the CLI, not this lane.
