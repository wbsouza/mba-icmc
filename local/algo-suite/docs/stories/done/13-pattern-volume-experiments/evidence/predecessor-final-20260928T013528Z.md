# Final predecessor results snapshot (20260928T013528Z)

Read-only collection from the finished run directories of the three predecessor jobs
(`2026-09-27-execution-realism`, `2026-09-27-variant-sweep-sept{,-b}`,
`2026-09-28-one-year-protocol`) under `algo-suite/data/training (local, gitignored)`. This snapshot supplements, and does not
replace, the frozen 00:36 UTC archive (`intermediate-results-20260928T003601Z.md`) and its
per-run parameter appendix; the R references are the same. All three parent scripts recorded
`exit_code=0`; every run below has its own successful `run.json`, `metrics.json`,
`trades.json`, `equity.csv`, `strategy-config.{json,yaml}` and `strategy-provenance.json`.

Definitions: trades and net P/L from `trades.json` (closed trades with order ids); win rate =
share of closed trades with positive profit (LEAN's `hit_rate` in `metrics.json` also counts
partially closed positions and is a few points higher, e.g. 0.30 vs 0.22 for R08); return from
`equity.csv` endpoints; max drawdown from `metrics.json`; profit factor = gross profit / gross
loss. Monthly runs start from a fresh $10,000; the one-year runs are single accounts.

## Execution-model reruns and the one-year protocol

| Ref. | Run | Run id | Closed trades | Win rate | Net P/L ($) | Return | Max DD | Profit factor |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R08 | baseline-2015-09 | `baseline/20260927T234946-8b17461d5460` | 320 | 22.2% | -5,256.84 | -52.57% | 53.8% | 0.70 |
| R13 | hybrid-2015-09 | `hybrid/20260927T235410-8b548f4bfa30` | 322 | 22.0% | -5,275.22 | -52.75% | 54.0% | 0.70 |
| R09 | baseline-2015-10 | `baseline/20260928T000257-8bcf7832dc99` | 319 | 24.1% | -5,334.65 | -53.35% | 55.2% | 0.69 |
| R14 | hybrid-2015-10 | `hybrid/20260928T001007-8c33716e9a9f` | 349 | 24.6% | -5,137.39 | -51.37% | 53.3% | 0.72 |
| R10 | baseline-2015-11 | `baseline/20260928T001557-8c84def875ee` | 107 | 15.0% | -5,047.12 | -50.47% | 51.6% | 0.29 |
| P01 | hybrid-2015-11 | `hybrid/20260928T004327-8e053507dfb3` | 132 | 16.7% | -5,281.94 | -52.82% | 53.3% | 0.41 |
| R19 | baseline-2016-03..10 | `baseline/20260928T000117-8bb8148c2302` | 1,029 | 25.0% | -8,840.72 | -88.41% | 88.8% | 0.64 |
| R20 | hybrid-2016-03..10 | `hybrid/20260928T000142-8bbdd0d8fd2c` | 1,029 | 24.8% | -8,775.76 | -87.50% | 88.2% | 0.63 |

Models: R08–R10/R13/R14/P01 use the frozen 2026-09-26 six-month pilot models (`1a6fd37e96de`,
`a6dda4c2effc`); R19/R20 use the one-year models (`0b41fd39ebf3`, `b67ac32e1fc5`, fitted
2015-03-02..2015-12-31, calibrated on January 2016, February 2016 held out). Code revision
`7165308` for all. Effective filter parameters: the baseline `config.yaml` values recorded in
`per-run-parameters-20260928T003601Z.md` (F6 reference plan: risk 0.03, swing stop, shrink 0.20,
min 5 pips, target 2R/50 %, trail 0.5R→−0.66R, min R:R 2; F7 0.55/0.45, gate off, 15-minute
label; execution spread 1 pip, commission 0, close_on_veto false; F5 caps −0.05/−0.15,
2 concurrent, leverage 30).

Monthly returns of the one-year simulation (percent of the equity at the start of each month):

| Run | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R19 baseline | -37.9% | -34.5% | -14.1% | -16.4% | -36.3% | -20.2% | -16.1% | -6.8% |
| R20 hybrid | -40.8% | -41.5% | -7.7% | -13.6% | -24.9% | -19.7% | -15.0% | -11.4% |

September baseline (R08) exit breakdown from the LEAN order records: 249 trades closed at the
stop-market order (gross −17,327), 65 at the 2R limit (gross +11,179), 6 liquidated at the
window end. Stops resolved to 5–7 pips; lots were margin-capped near 1.66, so realized risk
per trade was about 0.8 % of the deposit, not the configured 3 %.

## September-2015 variant sweeps (frozen pilot baseline model)

| Ref. | Variant | Closed trades | Return | Max DD |
| --- | --- | ---: | ---: | ---: |
| R01 | reference-conservative | 3 | -0.81% | 10.8% |
| R02 | reference-gated | 0 | 0.00% | 0.0% |
| R03 | reference-risk1 | 552 | -55.28% | 55.4% |
| R04 | reference-selective | 6 | -3.76% | 5.6% |
| R05 | reference-wide-stop | 14 | -17.65% | 21.5% |
| R15 | ha-h1-template | 144 | -53.47% | 55.8% |
| R16 | ha-h1-template-atr | 437 | -42.16% | 50.1% |
| R17 | ha-1r2r-template | 0 | 0.00% | 0.0% |
| R18 | ha-setup-template | 0 | 0.00% | 0.0% |

Variant overrides (all extend baseline; provenance in each run's `strategy-provenance.json`):
risk1 `risk_per_trade 0.01`; wide-stop `stop_distance_source atr, atr_multiplier 2.0,
min_stop_pips 10, stop_loss_shrink 0.0`; selective `theta 0.60/0.40`; gated `regime_gate true`;
conservative = risk1 + wide-stop + selective + `min_hold_bars 15`; ha-h1-template `shrink 0.5,
targets [3R/100 %], trail [1R→−0.66R, 1.5R→0R], min R:R 3`; ha-1r2r-template `shrink 0.5, targets
[1R/50 %, 2R/50 %], trail [1R→0R]`; ha-setup-template `shrink 0.5, targets [1R/50 %, 1.5R/50 %], trail
[0.5R→0R], min R:R 1.5`; ha-h1-template-atr = ha-h1-template + `risk 0.01, atr stop, atr_multiplier 4.0,
min_stop_pips 10`.

## Reading

No predecessor run is profitable. Frequent-trading settings lose about half the account per
month and 88 % over the one-year window; rare-trading settings lose little because they hardly
trade. The one-year window was untouched by any decision when the protocol was registered, so
R19/R20 are an out-of-sample negative result for the pilot models under the registered
execution model. No paired inference is computed (block length and trial count were not
registered before evaluation; the selection history grew afterwards). The consolidated equity
charts are `monografia/img/equity-consolidated.png` (R19/R20) and
`monografia/img/equity-consolidated-2015q4.png` (R08–R10 and R13/R14/P01 chained per strategy),
both produced by `algo-analyze equity-curves` from the runs' `equity.csv`.
