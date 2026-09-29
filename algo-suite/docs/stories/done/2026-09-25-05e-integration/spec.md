# Spec 05e — algo-analyze: integration (consolidates 05a–05d)

**Parent spec:** `05-algo-analyze-metrics-significance.md`.
**Depends on:** Spec 05a, 05b, 05c, 05d all merged. **This is the sync-up
task** — do not start until all four lane branches are merged into the same
base (per the user's request: split into small parallel tasks, then
consolidate into one feature).
**Blocks:** Spec 06 (Chapter 4 needs these CLI commands to exist).

## Objective

Wire the four independent modules (`deflated_sharpe.py`, `significance.py`,
`ablation.py`, `figures.py`) into `algo-analyze`'s CLI, exactly matching the
command surface [`experiments.md`](../../../experiments.md) §2 already specifies:

- `algo-analyze metrics --run <id>` — per-trade metrics (already available
  via `algo_backtest.metrics`, per parent spec's correction) **plus**
  deflated Sharpe (05a) folded in, **plus** the plausibility-band flags from
  parent Spec 05 §4 (e.g. `deflated Sharpe > 2.0: investigate before
  reporting`).
- `algo-analyze significance --runs <a> <b>` — wraps 05b.
- `algo-analyze ablation --runs <a> <b> ...` — wraps 05c.
- `algo-analyze figures --run <id>` / `--runs <ids> --figure` — wraps 05d.

This is also where any small inconsistency between the four lanes' module
interfaces gets reconciled (e.g. if 05d's `ablation_bars_figure` expects a
shape slightly different from what 05c's `build_ablation_table` returns —
this is the expected, cheap cost of parallelizing; fix it here, once,
instead of forcing the four lanes to coordinate mid-flight).

## Test requirements

CLI-level Gherkin/pytest-bdd (the parent Spec 05 §5 scenarios, if not already
covered by each lane's own module-level tests) — confirm each command
produces the right file/output end to end, not just that the underlying
function works in isolation.

## Definition of done

- All four [`experiments.md`](../../../experiments.md) §2 commands exist and work end to end against
  real run data.
- `make check`, `make audit` green for the whole `algo-analyze` package.
- Tool SPEC.md's `cli.py` line updated (no longer "planned").
- [`00-PLAN.md`](../../00-PLAN.md) §1 and §2 updated: Spec 05 (all lanes) marked done; Spec 06
  unblocked.
