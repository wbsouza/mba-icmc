# 2026-09-28 session 2 — brand-new run after the confidentiality rename (registered before any cell ran)

Purpose. (1) Re-run the reported trading-year cells from clean template names and confirm the execution
reproduces session 1 bit for bit (models and equity curves). (2) Report every learned strategy as ONE
simulation that trades both sides — BUY and SELL in the same run — using symmetric January-2016 quantile
thresholds (5 % or 10 % per side). No cell is a buy-only or sell-only page.

Setup, unchanged from session 1: EUR/USD, one $10,000 account per cell, OANDA cost model, Heikin-Ashi H4
risk/exit template (3 % risk, targets 4R/6R, trail 2R→+0.1R, portfolio at risk 18 %), models fit
2015-03-02..2015-12-31, combiner calibrated January 2016, February 2016 held out, models reused unchanged
for the trading year 2016-03-01..2017-02-28. March..October 2016 is development data; November 2016..
February 2017 are the untouched months, read last.

Session-1 archive used for the reproduction check: `experiment-test-archives/pre-rename-session-1/`
(job directories and `broad-window-h4-runs/`); nothing in it is re-used as an input — twelve models are
retrained here under clean names (`h1-baseline`, `h1-hybrid`, `h4-baseline`, `h4-hybrid`, `m5/m15/m30-*`,
`news-only-h1/h4`), thresholds recomputed by `calibrate.py` / `calibrate_intensity.py`.

Cells (26), one run each over the year:
- Both-sides headline (viewer): `h1-q05-base`, `h1-q05-hybrid` (activity veto on), `h1-q10-base`,
  `h1-q10-hybrid`, `h1-q10-gate-base`, `h1-q10-gate-hybrid`, `h4-q10-base`, `h4-q10-hybrid`,
  `h4-q10-atr-stop`, `m5/m15/m30-q10-base`, `m5/m15/m30-q10-hybrid`, `news-only-h1-q10`, `news-only-h4-q10`,
  `news-rule-h1-plus/minus`, `news-rule-h4-plus/minus` (rule = F4 direction from the intensity, no F7).
- Controls: `always-short-h1`, `always-short-h4` (short whenever flat; drift reference for the reversed-sign rule).
- Reproduction only (fixed 0.55/0.45 thresholds as reported in session 1, effectively long-only, not for
  the viewer): `h1-fixed-base` (= session-1 `h1-candle-vol-off`), `h1-fixed-hybrid` (= `h1-hybrid-vol-off`),
  `h1-fixed-vol-0.8` (= `h1-vol-0.8`).

Primary comparison for this session: `h1-q10-hybrid` vs `h1-q10-base`, paired daily equity on the untouched
months (stationary bootstrap, block 4, sensitivity 2, 999 resamples, seed 42); secondary: the same at H4 and
the q05 pair. Reproduction criterion: identical model coefficients after dropping metadata, identical
`equity.csv` and per-trade P/L for the 15 cells that finished in session 1 (`compare.py` → `reproduction.md`).
Known: session-1 M5 q10 cells failed after the backtest in the statement step (trade-plans inconsistency,
same-bar OCO double fill, TD-71); if it recurs it is reported, not patched mid-session. Trial count 26.
