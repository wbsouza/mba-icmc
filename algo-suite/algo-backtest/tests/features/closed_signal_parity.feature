@integration
Feature: LEAN and training consume the same complete signal candles
  Quote activity comes from canonical tick counts, not zero LEAN quote sizes.
  A deliberately missing open minute exercises LEAN fill-forward and its zero activity.

  Scenario Outline: Native indicator and signal parity at <minutes> minutes
    Given five days of canonical quotes with a missing minute and varying tick activity
    When the native closed-signal probe runs with <minutes> minute candles
    Then every labeled native candle matches offline training signals and indicators
    Examples:
      | minutes |
      | 1       |
      | 60      |
      | 240     |
