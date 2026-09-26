# Spec 04j — algo-backtest: money-management port gaps (lane of Spec 04)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` for full context;
governing contract `specs.md` §14 (fx-manager port map).
**Depends on:** nothing code-wise (touches only `close_portion.py`, disjoint from Spec 04i's
`trail_stop.py`) — sequence after Spec 04i lands only to avoid two lanes editing
`docs/technical-debt.md`/`specs.md` at once, not a technical dependency.
**Blocks:** nothing.
**Order:** small, standalone.
**Boundary:** `algo_backtest/rules/close_portion.py`, its tests, and `specs.md` §14.8 (a
documentation correction, not code).

## 0. Scope principle — port only what LEAN doesn't already provide

Checked directly against `QuantConnect/Lean`: it has native `StopMarketOrder` and
`TrailingStopOrder` order types, plus `CalculateOrderQuantity`/`SetHoldings` for sizing. **None of
these replace the money-management formulas this lane and Spec 04i cover** — they're a different
layer:

- `TrailingStopOrder` trails by a fixed distance/percentage from the current market price,
  continuously. fx-manager's model (`trail_stop_at_level`/`trail_stop_to_level`) is a *discrete*
  rule — "once price reaches R-multiple X of the original stop distance, relocate the stop to
  R-multiple Y of that same original distance" — computed once, from the entry trade's own risk
  distance, not a continuous trail from current price. Not the same mechanism; `TrailingStopOrder`
  does not make this formula unnecessary.
- `CalculateOrderQuantity`/`SetHoldings` size by portfolio weight or buying-power fraction, not by
  "risk a fixed % of balance against a specific stop-loss distance." `calculate_lot_size` has no
  LEAN-native equivalent.

So the genuinely missing piece — and the only thing worth porting — is the **formula/business-logic
layer** (`risk_math.py`, `trail_stop.py`, `close_portion.py`'s level/size math). Once a level is
computed, *placing or relocating the actual stop* should go through LEAN's native
`StopMarketOrder` (create/update), not a hand-rolled order-management loop reproducing
fx-manager's EJB state machine — that infrastructure is exactly what Spec 04's parent-spec §2
already establishes LEAN replaces.

## 1. Background — how this was found

Auditing `algo_backtest`'s already-ported money-management code (`rules/risk_math.py`,
`rules/trail_stop.py`, `rules/close_portion.py`, `chain/filters/f6_capital_mgmt.py`,
`rules/risk_guard.py`) against the real legacy sources turned up two independent third-party
projects by the same author beyond the originally-cited fx-manager: `spockfx-engine` (a later,
plain-Spring + Struts2 rewrite, went to production, "OK but a few bugs" per the user) and
`spockfx-jforex` (an OSGi-modular JForex/Dukascopy rewrite that never shipped — confirmed empty
of money-management logic, contributes nothing here). `spockfx-engine`'s
`MoneyManagementCalculator`/`DefaultRiskProvider` surfaced two concrete, verifiable findings
against the current python port. See the `fx-manager-borrow-analysis` memory note for the full
three-project comparison; this spec covers acting on the two findings that are still open.

## 2. Finding 1 — `close_portion.py` needs the remainder-to-last-target rounding fix

**What:** `build_close_ladder()` computes each rung's `lot_to_close` independently as
`original_lot_size * portion`. `spockfx-engine`'s `MoneyManagementCalculator.setTargetLevels()`
does the same for every rung *except the last*, where it instead assigns
`lot_size = volume - lotSizeSum` (the running remainder) and *derives* that rung's percentage
from what's left (`1.0 - lotPercentageSum`), rather than trusting the configured percentage to
divide evenly.

**Why it matters:** independent per-rung percentages are not guaranteed to sum to exactly 1.0
after floating-point rounding (`NumberUtil.setPrecision(..., 2)` on each rung independently) —
three rungs configured at "33%, 33%, 34%" or any split that doesn't divide the lot size evenly at
2-decimal precision can leave a small residual lot un-accounted for, or (less likely but still
possible) slightly over-close. `close_portion.py`'s own `_OVER_CLOSE_TOLERANCE` guard already
shows the module's author was aware over-closing was a risk; the remainder-to-last-target
technique removes the *under*-closing risk symmetrically, by construction, rather than by
tolerance-checking after the fact.

**Fix:** in `build_close_ladder`, for every rung except the last, keep the current
`lot_to_close = original_lot_size * portion`; for the *last* rung, set
`lot_to_close = original_lot_size - remaining` (i.e. `original_lot_size - sum(previous
lot_to_close)`), so `lot_remaining` on the last rung is always exactly `0.0`, never a rounding
residue.

**Test to add** (`tests/features/close_portion.feature`): a scenario with rungs whose portions
don't divide the lot size evenly in floating point (e.g. `0.33, 0.33, 0.34` on `lot_size=1.0`, or
a repeating-decimal split like `1/3` three times) asserting the *last* rung's `lot_remaining` is
exactly `0.0` and the sum of all `lot_to_close` values equals `original_lot_size` exactly — not
approximately.

## 3. Finding 2 — `specs.md` §14.8 states a factual inaccuracy about the legacy gap

**What:** §14.8 ("Risk gaps in the legacy system to address in the port") says: "The fxmanager-ejb
README explicitly lists what the legacy system does **not** enforce," including "No
portfolio-level capital cap." This is true of **fx-manager specifically**, but the same author's
later `spockfx-engine` built exactly this: `DefaultRiskProvider` sums the risk% of all currently
open trades (excluding any trade whose `riskOffset` flag is set — set by `TrailStopOrderProcessor`
once a stop trails past breakeven, meaning that trade's remaining risk is nil) and refuses a new
trade if the total exceeds a configured `riskLevel1`/`riskLimit1`.

**Why it matters:** this is a documentation-accuracy issue, not a code gap — `algo_backtest`'s own
`rules/risk_guard.py` already independently implements `portfolio_at_risk_cap` (among four other
caps) per §14.8's own design, regardless of whether fx-manager or spockfx-engine had one. The fix
is purely to correct the historical record so a future reader of `specs.md` doesn't cite "no
legacy system ever had a portfolio cap" as a novel methodological contribution when in fact a
prior (unshipped-in-python, but real and deployed) implementation existed. `specs.md` §1's
Source-of-truth convention requires amendments to be dated, not silent overwrites.

**Fix:** add a dated amendment under `specs.md` §14.8 (or its own `§14.8.1`), stating: "Amendment,
2026-09-26: `spockfx-engine`'s `DefaultRiskProvider` (a later, Spring-based rewrite by the same
author, also production-deployed) *did* implement a portfolio-level risk cap, risk-offset-aware.
This gap was specific to fx-manager, not universal to the author's prior systems. `RiskGuard`'s
`portfolio_at_risk_cap` remains a from-scratch python implementation, not a port of
`DefaultRiskProvider`'s Java (that source was read only after `RiskGuard` already existed) — no
code change follows from this correction, only the historical claim."

## Definition of done

- `close_portion.py`'s remainder-to-last-target fix implemented, with the uneven-split Gherkin
  scenario added and passing.
- `specs.md` §14.8 amendment added (dated, additive — the existing text is not deleted).
- `make check` green.
- Move to `docs/stories/done/<YYYY-MM-DD>-money-management-gaps/` with `lessons-learned.md`.
