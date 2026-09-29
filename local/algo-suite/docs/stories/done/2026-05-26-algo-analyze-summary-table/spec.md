# algo-analyze — summary table (pre-existing, not yesterday's work)

**Tool:** `algo-suite/algo-analyze/` · **Status:** done · **Last commit
before 2026-09-22:** `6eff181`, 2026-05-26 ("F3: multi-strategy comparison
path — second price-only strategy, baseline-meanrev").

This is separate from `../2026-09-23-algo-analyze-deflated-sharpe/` (Spec
05a, deflated Sharpe, which swarmforge built yesterday) and from
`../2026-09-25-algo-analyze-metrics-significance/` (the parked
metrics/significance/ablation/figures epic). The summary-table piece of
`algo-analyze` was already built and working nearly four months before that
session; the session only added deflated Sharpe on top of it.

**Scope (from the original spec, `docs/specs/algo-analyze.md`, relocated
into `algo-suite/algo-analyze/SPEC.md` at `50c537e`):** the final pipeline
stage — reads a backtest run directory and produces the summary metrics
table (the metrics/significance/ablation/deflated-Sharpe machinery described
there was, at this point, still unbuilt; that's what Spec 05 covers).

See `algo-suite/algo-analyze/SPEC.md` for the current, living contract.
