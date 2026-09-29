# Story 25 — Five-policy adaptive retraining comparison

Status: planned. Continuation of Story 19 (recency-weighted adaptive
retraining), closed 2026-09-28 for what it actually delivered: the
on-demand bundle provider wired into the live engine (T11/T12, minimum
viable slice), and a real, honestly-disclosed full-year backtest result for
Policy F (frozen bundle, fit once at D0=2016-03-01): 4,964 orders, 1,603
closed trades, 26% win rate, net profit -97.782%, Sharpe -1.499, Sortino
-2.541, max drawdown 97.9%. See
`../../done/19-adaptive-recency-retraining/progress.md` for the full record.

## Problem statement

The original spec registered five retraining policies (F frozen, Q
thresholds-only, R rolling uniform, U expanding uniform, E expanding
exponential) to be compared on one continuous account. Only Policy F ran
the full registered year. A shorter, exploratory 60-day rolling-window
pre-check (D60) was also run and did not beat the frozen model on that
shorter window — kept as a control, not treated as a substitute for the
full comparison.

## Goals

- [ ] Fit and run Policies Q, R, U and E over the same full registered year
      (2016-03-01 to 2017-02-28), same starting cash, same execution model
      as Policy F, so all five are directly comparable.
- [ ] Boundary-based bundle selection and mid-replay adaptive-cycle
      retraining triggers (deferred from T11/T12's minimum-viable slice) —
      needed for R/U/E to actually retrain mid-replay rather than reuse one
      frozen bundle.
- [ ] Paired statistical comparison across all five policies, not just
      eyeballing net P&L.
- [ ] Feed the result into Chapter 4/5 as the completed registered study
      (T18 in the original spec).

## Out of scope

- Anything already delivered by Story 19 (the provider wiring, Policy F's
  real result, the D60 pre-check) — this story only picks up the remaining
  four policies and the engine features they need.

## Notes

Given Policy F's own result was a near-total account wipeout (97.9%
drawdown) and the D60 pre-check already showed rolling retraining doesn't
beat frozen on a shorter window, the honest expectation going in is that
retraining cadence is unlikely to be the lever that fixes this — the likely
finding is that all five policies remain negative, consistent with the
broader pattern this session found across every other filter/pattern
combination tested. That is a legitimate, useful result to register and
report, not a reason to skip the comparison.
