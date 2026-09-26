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

Nothing — the spec's own two findings were independently verifiable (one against the
existing `_OVER_CLOSE_TOLERANCE` guard's intent, one against `risk_guard.py`'s existing
`portfolio_at_risk_cap`), so there was no ambiguity to resolve at implementation time.
