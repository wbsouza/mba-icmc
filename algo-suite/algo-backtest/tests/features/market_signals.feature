Feature: Causal candlestick and quote-activity signals
  Signals use only closed candles. Tick counts measure quote activity, not traded volume.

  Scenario: A real engulfing candle is recognized by TA-Lib
    Given a warmed candle detector followed by a bullish engulfing pair
    When the candles are processed incrementally
    Then the latest pattern is "bullish_engulfing"
    And streaming patterns equal batch-prefix patterns

  Scenario: Opposing simultaneous patterns do not invent a direction
    When bullish and bearish TA-Lib detections occur together
    Then the latest pattern is absent

  Scenario: Current activity is excluded from its comparison baseline
    Given tick counts 10, 20, 30, 60 with a lookback of 3
    When quote activity is processed
    Then relative activity is 3.0

  Scenario: Zero baseline cannot manufacture volume strength
    Given tick counts 0, 0, 0, 60 with a lookback of 3
    When quote activity is processed
    Then relative activity is unavailable

  Scenario Outline: Invalid tick activity fails rather than being imputed
    When quote activity receives <value>
    Then activity validation reports an error
    Examples:
      | value |
      | -1    |
      | true  |
      | 1.5   |

  Scenario Outline: The volume gate never supplies a directional trade vote
    Given a volume gate threshold of 1.0 and relative activity <strength>
    When the volume gate is applied
    Then the volume recommendation is ABSTAIN with veto <veto>
    Examples:
      | strength | veto  |
      | 0.5      | true  |
      | 1.0      | false |
      | 2.0      | false |
      | null     | true  |
