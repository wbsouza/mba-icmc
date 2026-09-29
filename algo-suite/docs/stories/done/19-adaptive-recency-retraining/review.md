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
