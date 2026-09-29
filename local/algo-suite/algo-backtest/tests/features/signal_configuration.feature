Feature: Strategy signal contracts are explicit and portable
  Scenario: A candle and volume candidate resolves both producers
    Given a baseline extension with TA-Lib and the volume filter enabled
    When the signal candidate is loaded
    Then the resolved signal contract has TA-Lib and 20-bar activity
    And its resolved YAML survives a round trip

  Scenario: Legacy models cannot be used with newly enabled candle detection
    Given a baseline extension with TA-Lib and the volume filter enabled
    When legacy model signal provenance is checked
    Then the model is rejected with a retraining instruction

  Scenario Outline: The decision timeframe must partition UTC days
    When a decision timeframe of <minutes> minutes is parsed
    Then the timeframe outcome is <outcome>
    Examples:
      | minutes | outcome |
      | 1       | valid   |
      | 60      | valid   |
      | 240     | valid   |
      | 7       | invalid |
      | 0       | invalid |

  Scenario: A sub-bar label horizon is refused before launching LEAN
    Given a baseline extension with TA-Lib and the volume filter enabled
    And the candidate uses H4 candles with a fifteen-minute label horizon
    When the invalid signal candidate is loaded
    Then the signal configuration error explains "label_horizon_minutes"

  Scenario: DSHA cannot silently consume resampled candles under its minute contract
    Given a baseline extension with TA-Lib and the volume filter enabled
    And the candidate uses H4 candles with DSHA perception
    When the invalid signal candidate is loaded
    Then the signal configuration error explains "EMA"
