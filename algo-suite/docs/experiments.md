# Experiment plan — from `algo-analyze` outputs to Chapter 4

This document closes the gap between the **tool outputs** and the **experimental
chapter** of the monografia: it maps each numbered experiment of the methodology
(`monografia/chapters/03-methodology.tex`, §subsec:experiments, Table 4) to the
concrete `algo-backtest` / `algo-analyze` command that produces it and to the
**table or figure** it becomes in Chapter 4 (Experimental Evaluation).

It is the contract that makes the empirical chapter reproducible: every number
in Chapter 4 traces to a `runs/<run-id>/` directory and a recorded command.

---

## 1. Workflow and implemented run conventions

Follow [the experimental workflow](experimental-workflow.md) before selecting
an experiment below. In particular, fit family models, calibrate the combiner,
and freeze model artifacts before held-out replay. The current six-month pilot
uses February–June 2015 for family fitting, July for calibration, August for
the trainer's held-out partition, and September for the first simulation.

- `algo-backtest run` writes `runs/<strategy>/<stamp>/` with `run.json`,
  `trades.json`, `metrics.json`, and LEAN outputs. Chain runs also write
  `decisions.parquet` and `strategy-config.json`.
- The F7 model JSON records training dates, row counts, input hashes, code
  revision, and package versions. Pass the frozen artifact with `--model`;
  record its hash and exact command alongside each result.
- The analyzer's descriptive trade-sequence figures read `trades.json` and use
  per-trade notional returns, not actual portfolio-equity compounding; label
  them accordingly. Inference uses actual LEAN equity on the explicit daily
  UTC grid; see the analyzer README for `inference-inputs.json`.
- `trades.parquet`, `parameters.txt`, `--cv`, automatic rolling refits, CPCV,
  and per-fold orchestration are target contracts, not implemented CLI options.
- Strategy names in the experiment catalog are a research plan, not proof of
  implementation. Baseline, hybrid, and baseline-dsha are available; extended
  feature/filter variants need their own configurations and evidence.
- [Story 11](stories/done/11-statistical-inference-corrections/spec.md)
  implements schema-v2 DSR and paired stationary-bootstrap inference. Legacy
  outputs remain exploratory. Missing equity coverage, costs or trial-history
  metadata makes corrected inference unavailable; software completion alone
  does not authorize a significance claim.

## 2. Experiment → command → Chapter 4 artifact

The numbered experiments (0–9, including engine controls) (each row maps to one Chapter 4
section). "Cmd" lists the producing commands; "Artifact" is the Chapter 4 output.

| # | Experiment | Key variable | Producing commands | Chapter 4 artifact |
|---|---|---|---|---|
| 0 | **Engine sanity checks** (validate the backtester itself before trusting any signal) | known-answer strategies | `algo-backtest run --strategy {buyhold,random,perfect_foresight} --symbol EURUSD` → `algo-analyze metrics` | **Table** sanity bounds: buy-and-hold Sharpe ≈ 0 (FX no drift); random ≈ 0 with ~50% hit rate; perfect-foresight very high Sharpe, ≈ 0 drawdown. A baseline Sharpe is only trusted once these land where expected. |
| 1 | Calibrate price-only **baseline** on EUR/USD | LightGBM hyperparameters | `algo-backtest run --strategy baseline --symbol EURUSD` → `algo-analyze metrics --run <id>` | **Table** baseline metrics (Sharpe, max drawdown) + **equity-curve figure** |
| 2 | Evaluate **full hybrid vs baseline** on EUR/USD | presence/absence of news | `algo-backtest run --strategy hybrid --symbol EURUSD` → `algo-analyze ablation --runs baseline --runs hybrid` | **Table** hybrid-vs-baseline (Sharpe, drawdown, hit rate) + overlaid equity curves |
| 3 | **Replicate Exp 2 on USD/JPY** | currency pair | `algo-backtest run --strategy hybrid --symbol USDJPY` → `algo-analyze ablation --runs baseline_jpy --runs hybrid_jpy` + `significance --runs baseline_jpy --runs hybrid_jpy --block-length <L> --block-rule <registered-rule>` | **Table** USD/JPY metrics + statistical-test result |
| 4 | **Ablation: feature-family contributions** | news sub-family activated | `algo-backtest run --strategy hybrid_{ta,ind,pat,news}` → `algo-analyze ablation --runs ...` (repeat `--runs` per run) | **Table** marginal contribution per feature family |
| 5 | **Compare vs Zhang (2025)** | validation protocol | `algo-analyze metrics --run hybrid` (deflated Sharpe) | **Table** this-work vs Zhang (cost-adjusted + deflated Sharpe) |
| 6 | **Filter ablation: Core vs A/B/C/D** | extended filter set F8–F14 | `algo-backtest run --strategy {core,A,B,C,D}` → `algo-analyze ablation --runs core --runs A --runs B --runs C --runs D` | **Table** Core vs variants (Sharpe, drawdown, turnover) + **bar figure** |
| 7 | **F9 sensitivity** | `k_ATR`, `alpha_ADF` | `algo-backtest run --strategy f9_sweep_*` → `algo-analyze metrics` | **Table/figure** trades-per-year, win-rate vs F9 params |
| 8 | **F10/F11 threshold sweep** | `theta_conf`, `theta_mag` | `algo-backtest run --strategy f1011_sweep_*` → `algo-analyze metrics` | **Figure** news-contribution vs threshold |
| 9 | **F12 consensus test** | `m ∈ {2,3,4}` | `algo-backtest run --strategy f12_m{2,3,4}` → `algo-analyze metrics` | **Table** false-positive rate vs consensus `m` |

The command catalog assumes complete run contracts. For `metrics`, pass an
actual `--selection selection.json` to obtain DSR; omitting it intentionally
reports unavailable selection history. For `significance`, supply the registered
primary `--block-length` and repeat it for every sensitivity length, plus
`--block-rule`, `--resamples` and `--seed`. The placeholder L is not a recommended
setting or permission to tune on evaluation results. Archive all schema-v2
outputs separately from legacy files, starting with `inference-inventory`.

## 3. Figures inventory (Chapter 4)

| Figure | Source | Command |
|---|---|---|
| Data-coverage matrix | `algo-transform` | `algo-transform coverage` → matrix figure |
| Equity curve (per run) | `algo-analyze` | `algo-analyze figures --run <id>` |
| Drawdown curve (per run) | `algo-analyze` | `algo-analyze figures --run <id>` |
| Ablation bars (Core vs A/B/C/D) | `algo-analyze` | `algo-analyze ablation --runs core --runs A --runs B --runs C --runs D --figure` |
| Threshold/sensitivity sweeps (Exp 7–8) | `algo-analyze` | not yet built — `figures` currently renders one run's equity/drawdown curves (`--run <id>`) or an ablation bar chart; a multi-run sweep figure is future work |

All figures render as vector PDF for LaTeX `\includegraphics`; the figure style
pack is shared with the thesis (fonts/sizes/palette) so they drop in cleanly.

## 4. From tool output to thesis prose

For each experiment, the Chapter 4 subsection follows the same skeleton:

1. **Setup** — the resolved `strategy-config.json`, frozen model hash, and recorded command, pair, window.
2. **Result** — the metrics table + figure (from `algo-analyze`), with `run-id`.
3. **Inference** — DSR probability with registered selection history, and paired
   stationary-bootstrap mean-return effect, confidence interval and two-sided
   p-value. Preserve unavailable reasons; never substitute a legacy statistic.
   Declare block lengths and inspect every sensitivity result, not just the
   smallest p-value. This mean-return test does not test Sharpe superiority.
4. **Interpretation** — what the marginal contribution means for hypothesis H1.

The "overfiltering" discussion (methodology §subsec:extended-filters) is written
from the Exp 6 ablation: where adding quality gates (A→D) reduces turnover but
also trade count, the descriptive Sharpe vs trade-count trade-off is read directly
off the ablation table.

## 5. Reproducibility

Every reported number must link to an archived run ID, command, configuration,
model hash, and input provenance. Current artifacts are listed in §1. Verify
reproduction before claiming it; deterministic software alone does not validate
the statistical method. Store rejected/failed runs and the search history too.

## 6. Hypothesis mapping

| Hypothesis | Decided by |
|---|---|
| **H1** — hybrid beats price-only after costs, risk-adjusted | Exp 2 (EUR/USD) + Exp 3 (USD/JPY); descriptive risk-adjusted metrics, DSR when supported, and paired mean-return uncertainty (not a Sharpe-superiority test) |
| Feature-family value | Exp 4 |
| Position vs prior art | Exp 5 (vs Zhang 2025) |
| Quality-gate value / overfiltering | Exp 6–9 |

## 7. Benchmark comparison and interpretation

The existing bibliography identifies Zhang (2025) as the closest Forex
comparison, with FinDPO and Kirtac–Germano as examples from equities and the
GPR studies as evidence motivating an event feature. Before transferring any
reported number into Chapter 4, verify its source, sampling frequency, costs,
window, asset class, and validation protocol. Similar source names do not make
the current event-only pilot a replication of an NLP-sentiment study.

The earlier bands (~0.5–1.5 as plausible, above 2 as suspicious, and an expected
positive GPR contribution) are withdrawn as decision criteria. They neither
establish a universal Sharpe limit nor determine the sign of an effect in this
sample. In particular, a probability-valued DSR cannot exceed 1 and must never
be assessed using a Sharpe-scale cutoff. Schema v2 removes the legacy CLI rule.

A result inside a literature range does not validate this pipeline; a result
outside it is not automatically invalid. Audit coverage, leakage, costs,
selection, and the return convention regardless of the outcome. Report
negative, zero, and positive effects without changing the protocol to favor a
preferred answer. A zero-trade run needs diagnosis before performance
interpretation; a nonsignificant result does not establish absence of value.

H1 concerns the paired hybrid-minus-baseline comparison under matched economic
assumptions. That delta, its uncertainty, and its generalization limits matter
more than whether a single baseline appears profitable. Since hybrid changes
both a family model and an event gate, an isolated feature-contribution claim
requires separate ablations.

## 8. Cross-references

- Methodology numbered experiments: `monografia/chapters/03-methodology.tex`
  §subsec:experiments (Table 4).
- Metrics & significance methods: `algo-suite/algo-analyze/SPEC.md`.
- Run artifacts (`trades.parquet`, `decisions.parquet`): `algo-suite/algo-backtest/SPEC.md` §6.
- Phases & schedule: `PRD.md` §6.
