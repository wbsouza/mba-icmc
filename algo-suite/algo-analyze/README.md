# Corrected inference (schema 2)

`metrics --run ID --selection selection.json` separates descriptive engine
metrics from `deflated_sharpe_probability`. Missing source/search history produces
an explicit unavailable result. No default trial count or normal moments exists.

Each run needs `inference-inputs.json`, an explicit reproducibility contract:

```json
{"source":"main.json","frequency":"calendar-day","timezone":"UTC",
 "annualization":365,"risk_free_daily":0,"costs":"engine fees and execution slippage included",
 "symbol":"EURUSD","start":"2015-09-01","end":"2015-10-01"}
```

Dates delimit return intervals: start is the initial midnight equity endpoint;
end is exclusive relative to the inclusive `run.json` evaluation dates. They must
match the run symbol and full window. The loader reads LEAN's actual marked-to-market
`charts/Strategy Equity/series/Equity/values` (`[epoch,value]` or OHLC close), retaining
flat periods. Every exact UTC midnight endpoint must exist. No weekend filling,
interpolation, trimming, or trade-ledger substitution is allowed. Downsampled engine
charts without those endpoints are unavailable: rerun with a complete equity export.
Changing analysis does not itself require model retraining. Source and contract SHA256
hashes are recorded. Costs are an explicit engine convention, not a claim of realistic
execution. Zero daily risk-free rate and 365 calendar periods/year are deliberate.

Selection manifest example (numbers must come from the actual search record):

```json
{"n_trials":10,"trial_count":20,"interim_looks":1,"trial_sharpe_std":0.02,
 "frequency":"calendar-day","provenance":"registered candidate ledger and dependence estimate"}
```

`n_trials` is effective independent count; `trial_count` retains actual searched
variants. Dispersion is the across-trial SD of nonannualized daily Sharpe, never
one strategy's standard error. One registered trial permits null dispersion and uses
PSR against zero. Return moments use sample SD (ddof1) for SR and uncorrected central
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
the same empirical error distribution (including the Monte Carlo correction).
The first length is primary; all others are sensitivity results, never a minimum-p
selection. Require at least 30 observations and ten expected blocks. Constant paired
differences, including all-zero differences, are unavailable because uncertainty cannot
be estimated. Stationarity, weak dependence and adequate finite moments remain assumptions.
Predeclare lengths on development data, before examining evaluation outcomes.

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

## Verification

Run `make check-inference` in this directory for lint, strict types, Gherkin
coverage, dependency-boundary checks and CRAP <= 8. Each new inference module
requires at least 95% line coverage. The story's evidence directory archives
independent formula/simulation validation, CLI QA, saved-run diagnostics and
an exhaustive arithmetic/comparison/boolean mutation campaign over the four
inference modules. The mutation runner uses disposable source copies and
fails on surviving mutants; raw run directories are never mutation targets.
