# algo-backtest — LEAN integration + price-only baselines (pre-existing, not yesterday's work)

**Tool:** `algo-suite/algo-backtest/` · **Status:** done · **Last commit
before 2026-09-22:** `3af7aee`, 2026-05-26 ("F3 review: make the single-run
CLI strategy-agnostic + sync docs"). Built across several commits on
2026-05-25/26, including the LEAN-data materializer/testcontainers
integration (PR #1, `6e80640`) and the `baseline_ma`/`baseline_meanrev`
strategies plus the experiment runner.

Nothing from yesterday's swarmforge session (2026-09-22 onward) touched
`algo-backtest` — Spec 04 (the filter-chain/hybrid strategy extension) is
still `planned/`, not started.

**Scope (from the original spec, `docs/specs/algo-backtest.md`, relocated
into [`algo-suite/algo-backtest/SPEC.md`](../../../../algo-backtest/SPEC.md) at `50c537e`):** runs strategies over
the canonical Parquet data and produces run artifacts — LEAN engine
integration, two price-only strategies (`baseline_ma`, `baseline_meanrev`),
and the experiment runner. First real numbers exist: EUR/USD 2024-06, both
price-only baselines lose (expected — see
[`algo-suite/docs/first-baseline-results.md`](../../../first-baseline-results.md)).

See [`algo-suite/algo-backtest/SPEC.md`](../../../../algo-backtest/SPEC.md) for the current, living contract.
