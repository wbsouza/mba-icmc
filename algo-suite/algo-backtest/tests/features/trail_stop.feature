Feature: Target / trail-stop level math
  Ports fx-manager's `StrategyMoneyManagementFacadeBean` formulas (specs.md §14.5):

    target_level_N        = entry ± (|entry - SL| * target_factor_N + (target_factor_N + 1) * spread)
    trail_stop_at_level_N = entry ± |entry - SL| * trail_stop_at_level_factor_N
    trail_stop_to_level_N = entry ± (|entry - SL| * trail_stop_to_level_factor_N + spread)

  The legacy "±" is resolved by trade direction for `target_level` and `trail_stop_at_level`
  (both measured in the *profit* direction from entry — the target to reach, and the price
  excursion needed to arm the trail) but `trail_stop_to_level` moves in the *loss* direction
  from entry (specs.md §14.7's own worked description, "entry − 66% × SL distance" for a BUY:
  it is the *tightened stop-loss* the trail relocates to once armed — still on the loss side
  of entry, only closer than the original SL, not a breakeven/profit lock). This asymmetry
  is a deliberate reading of the ambiguous "±" against §14.7's concrete example, documented
  here since the fx-manager source itself is not available in this checkout (specs.md §14.3).

  Rule: BUY-direction levels move up for targets/arming and down (but above the original SL) for the trail destination

    Scenario: Strategy A05's target/arm/destination factors on a BUY at entry 1.1000, SL 1.0950
      Given a BUY trade with entry 1.1000 and stop-loss 1.0950
      And a spread of 0.0002
      When I compute the target level for factor 2.0
      Then the target level is 1.1106
      When I compute the trail-stop arm level for factor 0.5
      Then the trail-stop arm level is 1.1025
      When I compute the trail-stop destination level for factor 0.66
      Then the trail-stop destination level is 1.0965

  Rule: SELL-direction levels move down for targets/arming and up (but below the original SL) for the trail destination

    Scenario: Strategy A05's target/arm/destination factors on a SELL at entry 1.1000, SL 1.1050
      Given a SELL trade with entry 1.1000 and stop-loss 1.1050
      And a spread of 0.0002
      When I compute the target level for factor 2.0
      Then the target level is 1.0894
      When I compute the trail-stop arm level for factor 0.5
      Then the trail-stop arm level is 1.0975
      When I compute the trail-stop destination level for factor 0.66
      Then the trail-stop destination level is 1.1035

  Rule: An entry equal to its stop-loss fails fast (zero risk distance is meaningless)

    Scenario: a BUY with entry equal to stop-loss is rejected
      Given a BUY trade with entry 1.1000 and stop-loss 1.1000
      And a spread of 0.0002
      When I compute the target level for factor 2.0
      Then computing the level fails with a zero-distance error
