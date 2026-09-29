# Lessons learned — Spec 04j (money-management port gaps)

## What actually happened

Both findings were smaller and more isolated than the parent Spec 04's scale suggested —
this lane really was "small, standalone" as the spec's own header claimed, and finished in
a single pass with no surprises.

## Vs. the spec

- Finding 1 (`close_portion.py` rounding fix) matched the spec's proposed fix exactly:
  keep `original_lot_size * portion` for every rung except the last, and derive the last
  rung as the running remainder. The only implementation choice not spelled out in the
  spec was making the last rung's `lot_remaining` a literal `0.0` (not a computed
  subtraction) — computing it as `original_lot_size - lot_closed` would very likely still
  land on exactly `0.0` for realistic inputs (the two operands are the same value by
  construction, and IEEE 754 guarantees `x - x == 0.0` exactly), but asserting it as a
  literal removes any doubt for future edge cases instead of relying on that argument.
- Finding 2 (`specs.md` §14.8) was a pure documentation amendment, additive as the spec
  required — no code followed from it, confirmed by grepping `close_portion.py`'s only
  caller (its own test file; no production caller exists yet for the laddering mechanic).

## What would be done differently

The spec's own two findings were independently verifiable (one against the existing
`_OVER_CLOSE_TOLERANCE` guard's intent, one against `risk_guard.py`'s existing
`portfolio_at_risk_cap`) — but the *implementation* of Finding 1 introduced a real
regression the spec didn't anticipate: gating the remainder-override on "is this the last
rung" (a positional check) instead of "does this ladder actually reach 1.0" (a semantic
check) silently forced a full close on any ladder whose portions were declared to sum to
*less* than 1.0 — a case the function's own pre-existing validation explicitly allows (only
`>1.0` is rejected) and a legitimate real-world pattern (scaling out of most of a position
while leaving a runner open). Caught in PR #37 review — three independent reviewers flagged
the identical gap. Fixed by adding a `fully_closes = cumulative_portion >= 1.0 - tolerance`
gate alongside the last-rung check, and adding the missing partial-ladder scenario
(`0.3, 0.3, 0.2` → rungs close their own declared portions, `lot_remaining` reflects the
still-open 0.2, not forced to zero). Next time: when a spec's fix only reasons about the
full-close case, explicitly test the boundary the surrounding validation *already* allows
(here, sums `< 1.0`) before calling the lane done — don't assume "spec's proposed fix,
implemented verbatim" is sufficient self-review for a function whose contract is broader
than the one case the spec walked through.
