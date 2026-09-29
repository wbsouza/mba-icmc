# Lessons learned — Spec 05c: algo-analyze ablation table

**Sourced from the parallel Spec 05 analysis lanes opened as stacked PRs**
(05b significance, 05c ablation, 05d figures).

**A comparison table should read persisted metrics, not recompute them.** The
ablation lane is a reporting layer over completed runs. Reusing
`algo_backtest.metrics.metrics_from_artifact` keeps one source of truth for
Sharpe, drawdown, hit-rate, and total return, and avoids small drift between
the backtest and analysis tools.

**Missing inputs deserve their own scenario, even when nearby failures exist.**
The first pass covered missing metrics and unknown baseline ids; the follow-up
review caught that a missing run directory is a distinct failure mode. Adding a
separate Gherkin scenario made the fail-fast contract explicit instead of
assuming it was covered by the metrics-artifact case.

**Use the run directory name as the comparison identity.** Keeping `baseline`
matched against the run id from the path keeps the call site explicit and avoids
silent defaults when the designated baseline is not part of the comparison set.
