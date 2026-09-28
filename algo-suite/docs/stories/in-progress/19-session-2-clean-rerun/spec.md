# Story 19 — session 2: brand-new trading-year run after the confidentiality rename (registered 2026-09-28 07:40 UTC, before any cell ran)

## Question

1. Does the execution reproduce? Every reported trading-year cell of session 1 is re-run from clean
   template names with retrained models; models, equity curves and per-trade P/L must be identical.
2. What does each strategy do when BUY and SELL live in the same simulation? Every learned strategy is
   reported as ONE run over the trading year with symmetric January-2016 quantile thresholds (5 % or
   10 % per side), so both directions fire. No buy-only or sell-only cell is reported.

## Design

Registration text, cell list (26), model list (12), primary comparison and reproduction criterion:
[`registration.md`](registration.md) (copy of the job README written before any cell ran). Scripts as
run: [`scripts/`](scripts/) — `run-train.sh` (12 trainers, six at a time), `run-train-fix.sh` (the
two news-only trainers re-run after the strategies-dir fallback failure, then calibration, variants
and parameter dumps), `run-simulate.sh` (26 cells, six LEAN slots, tables, reproduction check),
`compare.py` (session-2 vs archived session-1 models and runs), `stop-all-jobs.sh`.

Inputs: EUR/USD M1 2015-01..2017-03, GDELT event intensity 2015-03..2017-02, the isolated data root
`data/training/2026-09-28-broad-window-h4/data` with its run directory emptied before the session.
Session-1 artifacts moved (not deleted) to `experiment-test-archives/pre-rename-session-1/`.

## Acceptance

- `reproduction.md`: 12 models identical after dropping metadata; 15 comparable cells with identical
  `equity.csv` and per-trade P/L. Any difference is reported with its cause, not patched.
- `results.md`: month-by-month table for all 26 cells; paired inference for the primary pair
  (`h1-q10-hybrid` vs `h1-q10-base`) on the untouched months.
- Viewer database rebuilt from session-2 runs only, one run per strategy, headline cells only.
- Chapter 4 updated with the both-sides table; the session-1 numbers stay as the reproduction reference.
