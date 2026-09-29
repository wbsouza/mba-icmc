# Story 19 — review of the plan (2026-09-28, before any implementation)

Reviewed: `spec.md`, `progress.md`, `.specs/features/recency-weighted-retraining/{spec,design,tasks,context}.md`
(28 requirements RWT-01..28, 19 tasks). The core is sound: causal spans, five matched policies
(F frozen, Q thresholds only, R rolling, U expanding, E exponential), one continuous account, a
ledger of every attempt, paired daily inference. What follows are the changes and additions the
reviewer asks for before T1 freezes the protocol. None of them is applied to `tasks.md` yet.

## Changes

1. **Pre-computed bundles are the primary path for the backtest study.** Every input is
   historical, so all monthly fits can run on the host before the replay under the same cutoff
   rules; LEAN loads the bundle whose deployment interval contains the bar (RWT-12). The design
   makes this the "secondary reproducibility path" and puts the LEAN pause / host-training
   barrier (T10, T12) on the critical path. That barrier is the hardest and least certain piece
   and adds nothing to the evidence of this study. Move it to a later task for live use.
2. **Policy F must reproduce the session-2 model bit for bit.** With the proposed spans (family
   fit to C−60, combiner [C−60, C−30), thresholds [C−30, C)) the first bundle differs from the
   session-2 model (combiner and thresholds both on January 2016). If the initial epoch uses the
   session-2 spans, F equals the Chapter 4 model (free reproduction check, story 20) and every
   later policy is a controlled departure from it. Separate combiner/threshold spans can start
   from the second epoch.
3. **Add the H4 q10 price-only cell as a second base cell.** The H1 q10 cell lost 44 % on 516
   trades in session 2; E−U on it is valid but sits on a losing account. H4 (223 trades, −4.5 %)
   costs about 3 minutes per year-run. Ten runs instead of five, same protocol.
4. **Prediction quality is a registered endpoint, not a diagnostic.** With 40–500 trades the
   trading endpoint is noisy. Register per-epoch out-of-sample log-loss, Brier and directional
   hit rate at the thresholds, E vs U on identical rows, as the model endpoint; the paired daily
   equity difference stays the thesis endpoint.

## Additions

5. **T2 names the real artifacts.** "Validated batches" are: M1 parquet month partitions
   (`parquet/forex/<SYMBOL>/m1/`), GDELT daily event partitions with the next-day lag and their
   `.done` markers, the feature cache. The watermark is "last complete partition".
6. **Report n_eff of E beside R's row count** per epoch. With a 60-day half-life on expanding
   history, E behaves like a soft 180-day window; E−U and R−U are interpretable only with the
   effective sample sizes side by side.
7. **T1 carries a compute budget.** Session 2: 12 fits in about 2 minutes in parallel; H1
   year-run 8–20 minutes, H4 3 minutes; six LEAN slots at 4 CPUs. The whole study fits one
   evening. State it, with the slot limits, so the trial budget is credible.
8. **Determinism gate for the whole cycle.** Session 2 proved fits and runs are bit-identical.
   Add a gate: running the cycle twice yields identical bundle hashes *and* identical decision
   records (RWT-11 covers artifacts, not the replay).
9. **Viewer task (new T20).** Decisions carry the model epoch (RWT-16). Show the epoch per
   decision in the decision log and the trade drawer, and mark model change points on the
   equity chart; otherwise the audit exists but nobody sees it.
10. **Thresholds per epoch in the ledger, plotted.** 30 days of H1 bars is about 500 rows for
    two quantiles on a p̂ band of 0.51–0.54; a small shift moves the trade count a lot. Treat a
    jump as a diagnostic, not a finding.

## Housekeeping

11. Story number 19 is kept for this story; the session-2 story becomes 20 (PR #78).
12. The empty `planned/18-adaptive-recency-retraining/` directory is removed in this commit.

## Kept as proposed

Monthly cadence; one half-life (60 days), no sweep; one-day embargo; rejection instead of
last-good-model fallback; no live deployment; exploratory label on the already-inspected year;
TD-71 out of scope (affected runs fail visibly).

## Amendment — 2026-09-28, after the offline pre-checks (T0 evidence)

Two pre-checks were run on the session-2 rows (H1 price-only cell, same code, same seed, nothing
traded; scripts `rolling_precheck.py` and `daily_precheck.py` under
`algo-suite/data/training/2026-09-28-session-2/`, logs beside them). They exist to decide whether the
retraining machinery is worth building, before T1 freezes the protocol.

### Monthly refit (done): frozen vs rolling 3 / rolling 6 / expanding, one fit per test month

| policy | hit rate (p̂ > 0.5) | log-loss (coin flip 0.6931) | hit on the q10 cut bars | cut bars | months below coin-flip log-loss |
|---|---:|---:|---:|---:|---:|
| F frozen (session-2 model) | 0.498 | 0.6948 | 0.502 | 1,103 | 2 / 12 |
| R3 rolling 3 months | 0.507 | 0.6932 | **0.529** | 1,120 | 5 / 12 |
| R6 rolling 6 months | 0.503 | 0.6937 | 0.515 | 1,106 | 5 / 12 |
| U expanding | 0.505 | 0.6934 | 0.514 | 1,219 | 4 / 12 |

R3's edge on the cut bars is concentrated in the last three months (Dec 0.591, Jan 0.562, Feb 0.582
against 0.494 / 0.586 / 0.459 for F); about two standard errors over the year; exploratory (the year
was viewed, four policies compared). Enough to register the study, not a result.

### Daily refit (running): windows 15 / 30 / 45 / 60 days, thresholds-only vs full refit

The user's proposal: two months of initial history, then retraining on demand as trades close. Scored
day by day on the next day; table to be appended here when the run ends.

### Policy changes requested from this evidence

1. **Initial window 60 days, cadence daily.** R3 beat longer windows; the daily pre-check settles
   whether 60 days holds day to day. The 180-day rolling and expanding arms stay as controls.
2. **"Retrain when a trade closes" is implemented as daily bundles loaded on demand.** Training
   data are bars and labels, independent of trades, so the host fits one bundle per day (seconds on
   these windows) and the engine loads the newest bundle whose cutoff precedes the bar after the
   close. Same behaviour, no trigger in the trade loop, no LEAN pause, fully reproducible; and it
   makes the pre-computed path the only sane primary path (review item 1 above).
3. **Prediction quality per epoch is a registered endpoint** (log-loss, hit on the cut bars), because
   at coin-flip log-loss the trading endpoint cannot distinguish policies.
4. **The calibration-month check becomes a gate**: January 2016 was an outlier month for the event
   intensity (story 21 evidence); any threshold span is checked against the monthly table before use,
   and the thresholds themselves come from the trailing window of each epoch.

The `.specs/features/recency-weighted-retraining/` documents are Codex's and are being edited in the
`mba-main` checkout at the time of writing; they must absorb items 1–4 before T1.

### D60 trial (done, 2026-09-28): the user's proposal as a backtest

Job `data/training/2026-09-28-d60-trial` (registration in `evidence/d60-trial-registration.md`, table in
`evidence/d60-trial-results.md`): for each month of the trading year, the H1 and H4 price-only models
were refitted on the 60 days before the month (about 800 H1 rows, 190 H4 rows), thresholds taken from
that window's validation p̂, and the month simulated alone from $10,000; months chained; frozen
session-2 cells as comparators. 23 of 24 months completed (H1 January 2017 stopped at the statement
step on TD-71 after trading).

| clock | D60 chained year | frozen chained year | D60 − frozen, untouched Nov–Feb (block 4) | full year (block 5) |
|---|---:|---:|---|---|
| H1 | −45.4 % (11 months) | −51.3 % | −0.123 %/day, 95 % CI [−0.742, +0.496], p = 0.725 | +0.035 %/day, p = 0.835 |
| H4 | −12.3 % | −4.3 % | −0.095 %/day, 95 % CI [−0.283, +0.092], p = 0.327 | −0.017 %/day, p = 0.784 |

Prediction quality of the 60-day models on their own months: log-loss above the coin-flip value in
most months (H1 0.690–0.735, H4 0.679–0.763), hit rate on the cut bars swinging 0.14–0.64 on 4–118
bars. Reading: with 60 days of H1 or H4 bars the family models fit noise; the small edge the monthly
pre-check found for a 3-month window does not survive at 60 days with real trades and costs. The
trial's bias (each month starts flat, month-end positions closed) works in neither direction that
would change the reading.

Consequence for the protocol: the D60 arm stays in the study as the short-window control, not as the
candidate; the candidate windows are 90–180 days (R3/R6 of the pre-check) with the daily on-demand
loader, and the prediction-quality endpoint must be reported before any equity comparison is read.
