# Spec 05 — algo-analyze: metrics, deflated Sharpe, significance, ablations, figures

**Tool:** `algo-suite/algo-analyze/` · **Status:** only `cli.py summary` +
`config.py` implemented; metrics/significance/ablation/figures do not exist.
**Blocks:** Spec 06 for anything beyond the summary table.
**Depends on:** nothing blocking — real price-only runs already exist
(`trades.parquet`/`decisions.parquet` from the 2026-05-26 execution pass, and
whatever Spec 04's Experiment 0/1 produce). **Can start immediately, in
parallel with Spec 01.** Its ablation/significance-on-hybrid work naturally
gets more interesting once Spec 04 lands hybrid runs, but the machinery itself
should be built and tested against price-only runs first — do not block on
Spec 04.
**Governing contract:** `algo-suite/algo-analyze/SPEC.md` (inputs/outputs,
architecture, `trade_id` join contract between `trades.parquet` and
`decisions.parquet`) and [`algo-suite/docs/experiments.md`](../../../experiments.md) (the authoritative
experiment → command → Chapter 4 artifact table — build exactly the CLI
surface that table already specifies).

## 1. Objective

Build the rest of `algo-analyze` per its SPEC.md: metrics (Sharpe, deflated
Sharpe, max drawdown, hit rate, holding time, turnover), the Monte-Carlo
Permutation Test, ablation tables, and thesis-ready figures. This is the tool
that turns `runs/<run-id>/` directories into every number and figure Chapter 4
cites.

## 2. Why this can (and should) start now

Unlike Specs 02–04, this tool's *input contract* already exists and is already
producing real data — `trades.parquet` from the price-only baseline runs. The
metrics machinery (Sharpe, drawdown, hit rate — Experiment 1 in
[`experiments.md`](../../../experiments.md)) needs zero news/sentiment data to build and test. Only the
**ablation** command (`algo-analyze ablation --runs baseline hybrid`) needs a
hybrid run to be meaningful — but it can and should be built and unit-tested
against two arbitrary price-only runs (e.g. `baseline_ma` vs `baseline_meanrev`)
first, then simply pointed at real baseline/hybrid runs once Spec 04 lands.
Do not gate any of this tool's construction on Specs 01–04.

## 3. Build order — follow [`experiments.md`](../../../experiments.md) §2 exactly

That table is the contract; build commands in this order because each is a
dependency-free increment on the last:

1. **`algo-analyze metrics --run <id>`** — per-trade metrics from
   `trades.parquet`: Sharpe, max drawdown, hit rate, avg holding time,
   turnover (Experiment 0/1). This alone unblocks Ch04 §4.3 (baseline table)
   using runs that already exist today.
2. **Deflated Sharpe** (Bailey–López de Prado) inside `metrics` — per
   `algo-analyze/SPEC.md` §3, this is the number that makes any headline
   Sharpe defensible; [`experiments.md`](../../../experiments.md) §7.1 gives the plausibility bands
   (~0.5–1.5 for the eventual hybrid; investigate anything >2.0) — implement
   against those as test fixtures/assertions where the math allows a
   known-answer check.
3. **`algo-analyze significance`** — the Monte-Carlo Permutation Test
   (Aronson), fixed-seed for reproducibility ([`experiments.md`](../../../experiments.md) §5).
4. **`algo-analyze ablation --runs <a> <b> ...`** — cross-run comparison
   table; build and test against two existing price-only runs now, reuse
   verbatim for baseline-vs-hybrid (Experiment 2) and the Core-vs-A/B/C/D
   filter ablation (Experiment 6) once those runs exist.
5. **`algo-analyze figures --run <id>`** — equity curve, drawdown curve;
   `--runs <ids> --figure` for ablation bars. Vector PDF, sized for LaTeX
   `\includegraphics`, shared style pack with the thesis (fonts/sizes/palette
   per [`experiments.md`](../../../experiments.md) §3). Coordinate with Spec 02 if the coverage-matrix
   figure ends up here instead of in `algo-transform` — resolve that
   ownership question once, don't build the plotting style twice.
6. **Forensics join** — `decisions.parquet` joined to `trades.parquet` on
   `trade_id` (not timestamp+pair — `algo-analyze/SPEC.md` §2 explicitly calls
   out the prior contract gap this fixes) for per-filter contribution analysis
   on losing trades. This is what the "overfiltering" discussion in
   [`experiments.md`](../../../experiments.md) §4 is written from — needed for Experiment 6–9, so it can
   wait until Spec 04's filter chain exists, but the join *mechanism* can be
   built and tested against Spec 04's `decisions.parquet` schema as soon as
   that schema is fixed (coordinate with Spec 04, don't wait for full hybrid
   runs).

## 4. The benchmark-plausibility discipline (build this in, don't bolt it on)

[`experiments.md`](../../../experiments.md) §7/§7.1 gives concrete literature-verified bands (Zhang 2025:
5.87/4.65 same-asset comparator — a match is a red flag, not a win; FinDPO:
Sharpe 2.0 anchor; Liu–Zhang/Melone: GPR contribution should be small and
positive). Where practical, encode these as **assertions in the metrics/
significance output itself** (e.g. a `flags` field on the metrics result that
notes "deflated Sharpe > 2.0: investigate before reporting," "GPR marginal
contribution outside expected small-positive range") rather than leaving this
check to be manually applied when writing Chapter 4 prose (Spec 06). This
turns a documentation convention into a testable, referenceable output.

## 5. Test requirements

Gherkin/pytest-bdd per house rules. Cover: metrics computed correctly against a
synthetic `trades.parquet` fixture with known expected Sharpe/drawdown (a
golden-value test, not a snapshot test); deflated Sharpe's correction actually
reduces the naive Sharpe on a fixture with multiple trials (the point of the
Bailey–López de Prado correction); MCP test determinism under a fixed seed;
ablation table correctness on two synthetic runs with a known delta; the
`trade_id` join skips `HOLD`/`NO_TRADE` decision rows correctly (this is the
exact bug class the SPEC.md's "fix for the prior contract gap" note warns
about — write a regression scenario for it explicitly); figure generation
produces a valid vector PDF (assert on file type/non-empty, not pixel content).

## 6. Definition of done

- All five commands in [`experiments.md`](../../../experiments.md) §2's "Producing commands" column exist
  and match that table exactly (do not invent a different CLI surface — that
  table is what Spec 06's Chapter 4 prose will cite verbatim).
- Deflated Sharpe and MCP test implemented per Bailey–López de Prado / Aronson,
  with the plausibility-band flags from §4 above wired in.
- Ablation table works on real existing price-only runs today (proof: run it
  against `baseline_ma` vs `baseline_meanrev` and show a real delta table).
- Figures render as vector PDF, thesis style pack applied.
- `trade_id`-based forensics join implemented and tested (schema coordinated
  with Spec 04).
- `make check`, `make audit` green.
- Tool SPEC.md updated (cli.py section currently says "summary (impl.);
  metrics|significance|… (planned)" — update once built); [`00-PLAN.md`](../../00-PLAN.md) §1
  updated.
