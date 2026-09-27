# Experiment plan — from `algo-analyze` outputs to Chapter 4

This document closes the gap between the **tool outputs** and the **experimental
chapter** of the monografia: it maps each numbered experiment of the methodology
(`monografia/chapters/03-methodology.tex`, §subsec:experiments, Table 4) to the
concrete `algo-backtest` / `algo-analyze` command that produces it and to the
**table or figure** it becomes in Chapter 4 (Experimental Evaluation).

It is the contract that makes the empirical chapter reproducible: every number
in Chapter 4 traces to a `runs/<run-id>/` directory and a recorded command.

---

## 1. Run conventions

- A backtest produces `runs/<run-id>/` with `trades.parquet`, `decisions.parquet`,
  the equity series, and `parameters.txt` (the full provenance log).
- `run-id` = `YYYY-MM-DD-NN` (date + ordinal). The `run-id` is cited in the
  Chapter 4 caption of every table/figure derived from it.
- Strategy variants are config files under `algo-backtest/src/algo_backtest/strategies/`, composed
  with `extends:` (e.g. `hybrid` extends `baseline` adding F4; `A`/`B`/`C`/`D`
  extend `core` adding extended filters). No engine code changes between
  variants — only configuration.
- Metrics are computed by `algo-analyze` from `trades.parquet`; forensics from
  `decisions.parquet` joined on `trade_id`.
- **Validation protocol is explicit on every run:** `--cv cpcv --folds N
  --embargo D` (or `--cv walkforward`) per the methodology; `--cv single` is the
  one-pass held-out test. Combinatorial purged k-fold is driven by
  `algo-backtest` itself (spec §5.1), and `algo-analyze` reads the per-fold
  `trades.parquet` for the deflated Sharpe. Experiment commands below omit the
  `--cv` flags for brevity but every reported result names its protocol.
- **Implemented today (2026-09-26)** — the bullets above are the target contract.
  `algo-backtest run` writes `runs/<strategy>/<stamp>/` with `run.json`,
  `trades.json` (the interim ledger `algo-analyze` reads), `metrics.json`, LEAN's
  result JSON and, for `baseline`/`hybrid`, `decisions.parquet` (joins
  `trades.json` by `trade_id`). `trades.parquet`, `parameters.txt`, `--cv` and
  per-fold runs are not built; F7's train/validation/test split is set offline by
  `scripts/train_{baseline,hybrid}_meta_learner.py` (`--from/--train-end/
  --validation-end/--test-end`), the model's provenance (window, split, input
  hashes, git revision) embedded in its `f7_meta_learner.json`. Only `baseline`
  and `hybrid` exist as chain configs; Exp 4/6–9 variants are not written yet.

## 2. Experiment → command → Chapter 4 artifact

The nine experiments of methodology Table 4 (each row maps to one Chapter 4
section). "Cmd" lists the producing commands; "Artifact" is the Chapter 4 output.

| # | Experiment | Key variable | Producing commands | Chapter 4 artifact |
|---|---|---|---|---|
| 0 | **Engine sanity checks** (validate the backtester itself before trusting any signal) | known-answer strategies | `algo-backtest run --strategy {buyhold,random,perfect_foresight} --symbol EURUSD` → `algo-analyze metrics` | **Table** sanity bounds: buy-and-hold Sharpe ≈ 0 (FX no drift); random ≈ 0 with ~50% hit rate; perfect-foresight very high Sharpe, ≈ 0 drawdown. A baseline Sharpe is only trusted once these land where expected. |
| 1 | Calibrate price-only **baseline** on EUR/USD | LightGBM hyperparameters | `algo-backtest run --strategy baseline --symbol EURUSD` → `algo-analyze metrics --run <id>` | **Table** baseline metrics (Sharpe, max drawdown) + **equity-curve figure** |
| 2 | Evaluate **full hybrid vs baseline** on EUR/USD | presence/absence of news | `algo-backtest run --strategy hybrid --symbol EURUSD` → `algo-analyze ablation --runs baseline --runs hybrid` | **Table** hybrid-vs-baseline (Sharpe, drawdown, hit rate) + overlaid equity curves |
| 3 | **Replicate Exp 2 on USD/JPY** | currency pair | `algo-backtest run --strategy hybrid --symbol USDJPY` → `algo-analyze ablation --runs baseline_jpy --runs hybrid_jpy` + `significance --runs baseline_jpy --runs hybrid_jpy` | **Table** USD/JPY metrics + statistical-test result |
| 4 | **Ablation: feature-family contributions** | news sub-family activated | `algo-backtest run --strategy hybrid_{ta,ind,pat,news}` → `algo-analyze ablation --runs ...` (repeat `--runs` per run) | **Table** marginal contribution per feature family |
| 5 | **Compare vs Zhang (2025)** | validation protocol | `algo-analyze metrics --run hybrid` (deflated Sharpe) | **Table** this-work vs Zhang (cost-adjusted + deflated Sharpe) |
| 6 | **Filter ablation: Core vs A/B/C/D** | extended filter set F8–F14 | `algo-backtest run --strategy {core,A,B,C,D}` → `algo-analyze ablation --runs core --runs A --runs B --runs C --runs D` | **Table** Core vs variants (Sharpe, drawdown, turnover) + **bar figure** |
| 7 | **F9 sensitivity** | `k_ATR`, `alpha_ADF` | `algo-backtest run --strategy f9_sweep_*` → `algo-analyze metrics` | **Table/figure** trades-per-year, win-rate vs F9 params |
| 8 | **F10/F11 threshold sweep** | `theta_conf`, `theta_mag` | `algo-backtest run --strategy f1011_sweep_*` → `algo-analyze metrics` | **Figure** news-contribution vs threshold |
| 9 | **F12 consensus test** | `m ∈ {2,3,4}` | `algo-backtest run --strategy f12_m{2,3,4}` → `algo-analyze metrics` | **Table** false-positive rate vs consensus `m` |

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

1. **Setup** — the strategy config (cite `parameters.txt`), pair, window.
2. **Result** — the metrics table + figure (from `algo-analyze`), with `run-id`.
3. **Significance** — deflated Sharpe and the Monte-Carlo Permutation Test
   p-value (Exp 2/3/5/6), so a headline number is never reported without its
   selection-bias-corrected counterpart.
4. **Interpretation** — what the marginal contribution means for hypothesis H1.

The "overfiltering" discussion (methodology §subsec:extended-filters) is written
from the Exp 6 ablation: where adding quality gates (A→D) reduces turnover but
also trade count, the deflated Sharpe vs trade-count trade-off is read directly
off the ablation table.

## 5. Reproducibility

Every Chapter 4 number is reproducible: `parameters.txt` records the exact config
+ provenance, `features_hash` pins the input feature stream, fixed seeds make the
MCP test and any model inference deterministic, and the `run-id` links caption to
artifact. Re-running a cited command reproduces the table.

## 6. Hypothesis mapping

| Hypothesis | Decided by |
|---|---|
| **H1** — hybrid beats price-only after costs, risk-adjusted | Exp 2 (EUR/USD) + Exp 3 (USD/JPY), deflated Sharpe + MCP test |
| Feature-family value | Exp 4 |
| Position vs prior art | Exp 5 (vs Zhang 2025) |
| Quality-gate value / overfiltering | Exp 6–9 |

## 7. Benchmark comparison — expected ranges from the cited literature

Each experiment is sanity-checked against comparable results in the papers we
cite, so a result that lands wildly outside the literature's range is a flag to
investigate (data leak, look-ahead, cost model), and a result inside it is
corroboration. Numbers below are verified against the source PDFs.

| Our experiment | Comparable result (verified) | How we use it |
|---|---|---|
| **Exp 5** — vs Zhang (2025), our closest prior art | `zhang2025macroalpha`: cost-adjusted Sharpe **5.87 EUR/USD, 4.65 USD/JPY** (FinBERT→XGBoost over GDELT, 2017–2025) | Direct comparator. Same pairs, same GDELT+FinBERT lineage. Our deflated Sharpe is reported beside it; per López de Prado, a Sharpe near 5.87 is **above** the plausible band without scrutiny — so we treat a close match as a red flag, not a win. |
| **Exp 2/3** — hybrid Sharpe after costs (EUR/USD, USD/JPY) | `iacovides2025findpo` (FinDPO): Sharpe **2.0**, 67% annual at **5 bps** costs — but on **S&P 500 equities**, not FX | Calibration **anchor** for a defensible post-cost Sharpe. A deflated Sharpe in the ~1–2 range after costs is credible; materially above 2.0 warrants scrutiny. Not a same-asset comparator. |
| **GPR feature contribution** (within Exp 4) | `liu2024gprcurrency`: zero-cost GPR currency strategy **5.72% p.a. before / 4.73% after** costs (42 currencies, 2002–2019); `melone2026geopolitical` (working paper): GHML **3.28% annual / 2.76% alpha** | Establishes that GPR carries directional FX information. Our GPR-feature ablation should show a **positive, modest** marginal contribution; a large one is implausible given these effect sizes. |
| **algo-score scorer choice** (informs algo-score, not a backtest exp) | `kirtac2024sentiment`: on **US equities**, OPT 74.4% > BERT 72.5% > FinBERT 72.2% accuracy; long-short Sharpe OPT **3.05** > FinBERT **2.07** | Pedigree that a frontier LLM scorer beats FinBERT — motivates the Tier-A scorer swap (Ch.5), and sets expectation that our FinBERT baseline is a floor, not a ceiling. Equities, not FX. |

Caveats carried into the prose: Zhang's figures are the same-asset comparator but
sit above the plausible band; FinDPO and Kirtac–Germano are **equities** (anchors,
not comparators); Melone is a **working paper**. Effect sizes, not just direction,
are compared — a hybrid that "beats baseline" by an implausibly large margin is
investigated before it is reported.

### 7.1 Expected result bands

Derived from the benchmarks above, these are the plausibility bands the results
are read against (not targets — gates for "investigate before reporting"):

| Quantity | Plausible | Investigate |
|---|---|---|
| Hybrid deflated Sharpe after costs (Exp 2/3) | ~0.5–1.5 | > 2.0 (above the FinDPO anchor) — check leakage/costs |
| GPR-feature marginal contribution (Exp 4) | small, positive | large — implausible vs Liu–Zhang / Melone effect sizes |
| Match to Zhang's 5.87 / 4.65 (Exp 5) | well below | at/above — treat as a red flag, not a win |

### 7.2 Reading a negative baseline

A **price-only baseline with a zero or negative Sharpe is not a failure** — it is
the expected outcome for unleveraged major-pair FX without an informational edge
(efficient, deep, low-drift). The experiment does not need the baseline to be
profitable; it needs the baseline to be a *competitive, honestly-costed control*.
The quantity that tests hypothesis H1 is the **hybrid − baseline delta** (and its
deflated significance), not the absolute baseline level. Exp 1 therefore reports
the baseline as a control, and Exp 2/3 report the delta as the result.

## 8. Cross-references

- Methodology numbered experiments: `monografia/chapters/03-methodology.tex`
  §subsec:experiments (Table 4).
- Metrics & significance methods: `algo-suite/algo-analyze/SPEC.md`.
- Run artifacts (`trades.parquet`, `decisions.parquet`): `algo-suite/algo-backtest/SPEC.md` §6.
- Phases & schedule: `PRD.md` §6.
