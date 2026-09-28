Feature: Target / trail-stop level math
  Ports fx-manager's `StrategyMoneyManagementFacadeBean` formulas (specs.md §14.5),
  confirmed against the real Java source (both the original JavaEE/EJB version and its
  later Spring reimplementation in the author's later Heikin-Ashi trading manager agree on the formula):

    target_level_N        = entry + sign * (|entry - SL| * target_factor_N + (target_factor_N + 1) * spread)
    trail_stop_at_level_N = entry + sign * (|entry - SL| * trail_stop_at_level_factor_N + (trail_stop_at_level_factor_N + 1) * spread)
    trail_stop_to_level_N = entry + sign * (|entry - SL| * trail_stop_to_level_factor_N + spread)

  where `sign` is +1 for BUY, -1 for SELL — **the same rule for all three formulas**, no
  special-casing. `trail_stop_to_level_factor` is a *signed* config value (specs.md
  §14.9.4's canonical sample carries `-0.66`); it is that sign, not a direction-branch,
  that decides which side of entry the trail destination lands on. A negative factor
  lands on the loss side (a tightened stop-loss, closer than the original SL — specs.md
  §14.7's "entry − 66% × SL distance" example); a positive factor legitimately lands on
  the *profit* side (locking in partial profit once the trail arms — a real, deployed
  configuration, e.g. a legacy Heikin-Ashi template's `0.1`). Do not `abs()` the
  factor: an earlier version of this module did, and hard-coded a loss-side subtraction,
  which happened to match the loss-side case but flipped the sign of the `spread` term —
  wrong for every factor magnitude, not just positive ones.

  `trail_stop_at_level` was also missing its `(factor + 1) * spread` term entirely (the
  real Java source's `atLevelDiff` carries it, same shape as `target_level`) — added here,
  which changes this file's two composite-scenario arm-level values below (spread was
  previously silently dropped).

  Rule: BUY-direction levels move up for targets/arming; the trail destination's side depends on the factor's sign, not on direction

    Scenario: Strategy A05's target/arm/destination factors on a BUY at entry 1.1000, SL 1.0950
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0002
      When I compute the target level for factor 2.0
      Then the target level is 1.1106
      When I compute the trail-stop arm level for factor 0.5
      Then the trail-stop arm level is 1.1028
      When I compute the trail-stop destination level for factor -0.66
      Then the trail-stop destination level is 1.0969

    Scenario: zero spread isolates the R-multiple term of the trail-stop arm level (BUY)
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0
      When I compute the trail-stop arm level for factor 0.5
      Then the trail-stop arm level is 1.1025

    Scenario: a zero trail-stop arm factor is breakeven plus the spread cost (BUY)
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0002
      When I compute the trail-stop arm level for factor 0.0
      Then the trail-stop arm level is 1.1002

    Scenario: a positive trail-stop destination factor locks in profit instead of tightening the stop (BUY)
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0002
      When I compute the trail-stop destination level for factor 0.1
      Then the trail-stop destination level is 1.1007

    Scenario: a zero trail-stop destination factor is breakeven plus the spread cost (BUY)
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0002
      When I compute the trail-stop destination level for factor 0.0
      Then the trail-stop destination level is 1.1002

    Scenario: zero spread isolates the R-multiple term of the trail-stop destination (BUY)
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0
      When I compute the trail-stop destination level for factor -0.66
      Then the trail-stop destination level is 1.0967

  Rule: SELL-direction levels move down for targets/arming; the trail destination's side depends on the factor's sign, not on direction

    Scenario: Strategy A05's target/arm/destination factors on a SELL at entry 1.1000, SL 1.1050
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0002
      When I compute the target level for factor 2.0
      Then the target level is 1.0894
      When I compute the trail-stop arm level for factor 0.5
      Then the trail-stop arm level is 1.0972
      When I compute the trail-stop destination level for factor -0.66
      Then the trail-stop destination level is 1.1031

    Scenario: zero spread isolates the R-multiple term of the trail-stop arm level (SELL)
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0
      When I compute the trail-stop arm level for factor 0.5
      Then the trail-stop arm level is 1.0975

    Scenario: a zero trail-stop arm factor is breakeven plus the spread cost (SELL)
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0002
      When I compute the trail-stop arm level for factor 0.0
      Then the trail-stop arm level is 1.0998

    Scenario: a positive trail-stop destination factor locks in profit instead of tightening the stop (SELL)
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0002
      When I compute the trail-stop destination level for factor 0.1
      Then the trail-stop destination level is 1.0993

    Scenario: a zero trail-stop destination factor is breakeven plus the spread cost (SELL)
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0002
      When I compute the trail-stop destination level for factor 0.0
      Then the trail-stop destination level is 1.0998

    Scenario: zero spread isolates the R-multiple term of the trail-stop destination (SELL)
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0
      When I compute the trail-stop destination level for factor -0.66
      Then the trail-stop destination level is 1.1033

  Rule: An entry equal to its stop-loss fails fast (zero risk distance is meaningless)

    Scenario: a BUY with entry equal to stop-loss is rejected
      Given a BUY trade with entry 1.1000 and stop-loss 1.1000
      And a spread of 0.0002
      When I compute the target level for factor 2.0
      Then computing the level fails with a zero-distance error
