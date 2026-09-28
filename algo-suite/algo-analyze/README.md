# Corrected inference (schema 2)

`metrics --run ID --selection selection.json` separates descriptive engine
metrics from `deflated_sharpe_probability`. Missing source/search history produces
an explicit unavailable result. No default trial count or normal moments exists.

`algo-backtest run` emits `inference-inputs.json` beside each completed run as an
explicit reproducibility contract and records its SHA-256 and the resolved brokerage
adapter in `run.json`. The analyzer verifies both: a sidecar whose bytes differ from the
recorded digest, or whose `costs` does not name the recorded adapter, is an input error
(`contract_provenance: producer-verified` in the report). A historical run whose manifest
carries neither field may provide the same file through a separately archived producer
manifest and is labeled `contract_provenance: declared`:

```json
{"source":"main.json","frequency":"calendar-day","timezone":"UTC",
 "annualization":365,"risk_free_daily":0,"costs":"brokerage:oanda",
 "symbol":"EURUSD","start":"2015-09-01","end":"2015-10-01"}
```

Dates delimit return intervals: start is the initial midnight equity endpoint;
end is exclusive relative to the inclusive `run.json` evaluation dates. They must
match the run symbol and full window. The loader reads LEAN's actual marked-to-market
`charts/Strategy Equity/series/Equity/values` (`[epoch,value]` or the candle **close**:
LEAN stamps each equity candlestick with its end time and schedules a sample at every
midnight, so the midnight close is the mark), retaining flat periods. When the export
also carries LEAN's daily `Return` series, every derived return must agree with it to
1e-8; a mismatch is an input error, never a silent choice of a different mark.
Every exact UTC midnight endpoint must exist. No weekend filling,
interpolation, trimming, or trade-ledger substitution is allowed. Downsampled engine
charts without those endpoints are unavailable: rerun with a complete equity export.
Changing analysis does not itself require model retraining. Source and contract SHA256
hashes are recorded. Costs are an explicit engine convention, not a claim of realistic
execution. Zero daily risk-free rate and 365 calendar periods/year are deliberate.

Selection ledger example (the analyzer computes dispersion from the search record):

```json
{"n_trials":3,"interim_looks":1,"frequency":"calendar-day",
 "provenance":"registered candidate ledger, 2026-09 development search",
 "trials":[{"run_id":"candidate-01","daily_sharpe":0.021},
           {"run_id":"candidate-02","daily_sharpe":-0.004},
           {"run_id":"candidate-03","daily_sharpe":0.013}]}
```

This example is complete and executable: three rows, effective count three. A ledger
must not also declare `trial_sharpe_std` or `trial_count` (they are computed), and a
present but malformed `trials` field is an error, never a fallback to declared values.

`n_trials` is the effective independent count and stays a declared research judgment;
`trial_count` and `trial_sharpe_std` are computed from the ledger (across-trial SD of
nonannualized daily Sharpe, never one strategy's standard error) and the ledger file is
hashed. `interim_looks`, `frequency` and `provenance` must be declared in either form;
nothing is defaulted. A declared manifest without `trials` remains accepted only for
explicitly registered external histories and is labeled `source_kind: declared`;
ledgers are labeled `source_kind: computed`. One registered trial permits null
dispersion and uses PSR against zero. Fewer than four daily returns is insufficient
evidence and reports `status: unavailable`; nonfinite equity is an input error.
Return moments use sample SD (ddof1) for SR and uncorrected central
moments for skew/Pearson kurtosis. DSR implements Bailey–López de Prado (2014), Eq2,
including the expected-maximum selection threshold. Its classical asymptotic assumptions
do not establish validity for serially dependent returns.

`significance --runs BASE --runs CHALLENGER --block-length 20 --block-length 10
--block-length 40 --block-rule registered-development-rule --resamples 999 --seed 42`
uses a paired stationary bootstrap: geometric blocks with declared mean length,
circular ordered continuation, and common indices for both arms. The estimand is the
mean daily net return difference (challenger minus baseline); the two-sided null is
zero mean difference. Centered paired differences generate the null distribution.
The plus-one absolute-tail p-value and symmetric basic confidence interval invert
the same empirical error distribution (including the Monte Carlo correction). The
interval is not studentized: its coverage is approximate when the bootstrap error
distribution is skewed, which fat-tailed return differences can be (technical-debt
TD-62 tracks a bootstrap-t variant).
The first length is primary; all others are sensitivity results, never a minimum-p
selection. Require at least 30 observations and ten expected blocks. Constant paired
differences, including all-zero differences, are unavailable because uncertainty cannot
be estimated. Stationarity, weak dependence and adequate finite moments remain assumptions.
Predeclare lengths on development data, before examining evaluation outcomes, and
pass the primary as the first `--block-length`. A length with fewer than ten expected
blocks is reported unavailable, never silently shortened. Two block-length rules were
registered and evaluated for 90–180-day windows and **both failed the size gate**
(Story 11 `method-design.md`); at those lengths this procedure is not size-calibrated,
so a confirmatory paired claim needs a materially longer window (n=1200 passed at
L=20) or a studentized variant (TD-62). The analyzer reports the diagnostics regardless.

Primary method sources: [DSR](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf),
[Politis & Romano (1994)](https://users.ssc.wisc.edu/~behansen/718/Politis%20Romano.pdf).
The old independent pooled-trade shuffle is isolated in `legacy_iid.py`, opt-in library
only, with exchangeability/independence required. It is never the default CLI inference.

`inference-inventory` prints schema2 correctability and unavailable reasons for saved
runs. Preserve old outputs unchanged and redirect corrected JSON into separate v2 files.
Legacy `deflated_sharpe` values were Sharpe adjustments, not probabilities; old pooled
trade p-values are exploratory. Missing search records cannot be reconstructed from two
published strategies. Missing equity requires simulation reruns, not fabricated daily
returns. Existing trade-sequence figures remain descriptive and are not portfolio series.

## Consolidated equity curves

`equity-curves --run DIR [--run DIR ...] [--label strategy=Label ...] --out DIR` overlays
several finished runs on one time axis, one line per strategy, like a robustness-testing
chart. Each `--run` is a results directory (`runs/<strategy>/<stamp>/`) holding `run.json`
and the `equity.csv` that `algo-backtest statement --run <dir>` writes next to
`equity.png` (`time,equity,drawdown_pct`, one row per LEAN equity sample); a run without
it fails fast naming that command.

Consecutive windows of the same strategy (e.g. `baseline` run for 2015-09, 2015-10 and
2015-11 as three one-month backtests, each from a fresh 10,000 deposit) are **chained**
into one continuous curve: each later window is re-based by
`previous_window_chained_end / this_window_raw_start`, compounding along the chain, so a
monthly redeposit does not show as a reset. The un-chained `equity_raw` stays beside the
`equity_chained` column in `equity-consolidated.csv` (long format: `strategy, run_id,
time, equity_raw, equity_chained, drawdown_pct`; the drawdown follows the running peak of
the chained curve), and `equity-consolidated.png` draws the chained line per strategy
with a starting-deposit reference, dotted window boundaries, a legend and a UTC date
axis titled with the covered window. `equity-consolidated.html` is a self-contained
comparison dashboard (inline CSS + SVG, opens from `file://`): a KPI card per strategy
(start/end equity, chained net %, max drawdown %, trades and win rate pooled from the
runs' `trades.json`, `n/a` when not recorded), one chart with a colour per strategy and
month labels, and the table of runs behind each curve. One summary line per strategy
prints first/last equity, chained net % and max drawdown %.

```sh
algo-analyze equity-curves \
  --run data/runs/baseline/20260901T000000-aaaaaaaa \
  --run data/runs/baseline/20261001T000000-bbbbbbbb \
  --run data/runs/hybrid/20260901T000000-cccccccc \
  --label "baseline=Baseline (F1-F7)" --out data/analysis/equity
```

## Verification

Run `make check-inference` in this directory for lint, strict types, Gherkin
coverage, dependency-boundary checks and CRAP <= 8. Each new inference module
requires at least 95% line coverage. The story's evidence directory archives
independent formula/simulation validation, CLI QA, saved-run diagnostics and
an exhaustive arithmetic/comparison/boolean mutation campaign over the four
inference modules. The mutation runner uses disposable source copies and
fails on surviving mutants; raw run directories are never mutation targets.
