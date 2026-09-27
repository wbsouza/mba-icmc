Feature: Double-smoothed Heikin-Ashi is a selectable F1 perception candidate
  Preserve the historical classifier: down when smoothed far >= smoothed near,
  including a tie. Use native LEAN Wilder(6) then LWMA(2), and expose no
  directional feature until both primary and closed higher-timeframe bars are ready.

  Scenario: The first transformed candle seeds its open from the smoothed body
    Given smoothed OHLC 10, 14, 8, 12 with no previous HA candle
    When the Heikin-Ashi transform is applied
    Then the HA OHLC is 11, 14, 8, 11
    And the reordered near and far are 14 and 8

  Scenario: Recurrence uses the previous unsmoothed HA body
    Given smoothed OHLC 14, 18, 12, 16 after HA open 11 and close 11
    When the Heikin-Ashi transform is applied
    Then the HA OHLC is 11, 18, 11, 15
    And the reordered near and far are 11 and 18

  Scenario Outline: Classification uses the reordered extrema and folds ties into down
    Given smoothed near <near> and smoothed far <far>
    When the double-smoothed Heikin-Ashi direction is classified
    Then the classified direction is <direction>

    Examples:
      | near | far | direction |
      | 8    | 10  | -1        |
      | 10   | 8   | 1         |
      | 10   | 10  | -1        |

  Scenario: Omitting the selector preserves the EMA default
    Given an empty perception configuration
    When the perception configuration is parsed
    Then the selected perception source is "ema"

  Scenario: The candidate has the original MT4 smoothing defaults
    Given perception_source "double_smoothed_heikin_ashi"
    When the perception configuration is parsed
    Then the smoothing periods are 6 and 2 with higher timeframe 60 minutes

  Scenario Outline: Invalid configuration fails explicitly
    Given invalid perception configuration "<case>"
    When the perception configuration is parsed
    Then perception configuration fails naming "<field>"

    Examples:
      | case                      | field                       |
      | unknown source            | perception_source           |
      | zero first period         | period1                     |
      | negative second period    | period2                     |
      | boolean first period      | period1                     |
      | fractional second period  | period2                     |
      | primary-sized higher bar  | higher_tf_minutes           |
      | unknown candidate setting | double_smoothed_heikin_ashi  |

  @integration
  Scenario: Both native smoothing passes must be ready
    Given a native double-smoothed Heikin-Ashi indicator with periods 6 and 2
    When six completed primary bars have been supplied
    Then the indicator reports not ready and refuses to expose direction
    When the seventh completed primary bar is supplied
    Then the indicator is ready with a classified direction

  @integration
  Scenario: Higher-timeframe perception uses completed consolidated bars only
    Given native primary and higher-timeframe Heikin-Ashi perception
    When the primary indicator is ready but the higher indicator is not
    Then no multi-timeframe directional features are exposed
    When enough higher-timeframe bars close to make both indicators ready
    Then both F1 directional features are exposed
    And an unfinished higher-timeframe bar does not change higher-timeframe direction

  @integration
  Scenario: Native custom indicator publishes its timestamp and direction
    Given a native double-smoothed Heikin-Ashi indicator with periods 6 and 2
    When the native indicator receives completed TradeBars
    Then its current value and timestamp match the published update event
    And its warm-up period is seven bars
    And native Wilder and LWMA produce the expected smoothed values

  @integration
  Scenario: Reset restarts smoothing and the Heikin-Ashi recurrence
    Given a native double-smoothed Heikin-Ashi indicator with periods 6 and 2
    When a ready native indicator is reset
    Then it becomes unready and a replay matches a fresh indicator

  @integration
  Scenario: Default higher timeframe needs seven completed hourly bars
    Given native primary and higher-timeframe Heikin-Ashi perception
    When default perception receives 419 completed minute bars
    Then the default hourly direction remains unavailable
    When the 420th minute closes the seventh hourly bar
    Then the default hourly direction becomes available

  @integration
  Scenario: A flat native candle classifies ties as down
    Given a native double-smoothed Heikin-Ashi indicator with periods 6 and 2
    When a native indicator receives a fully flat candle after warm-up
    Then the native direction is down on equal smoothed extrema

  @integration
  Scenario: Forex candles use the bid and ask midpoint
    Given native primary and higher-timeframe Heikin-Ashi perception
    When completed quote bars have asymmetric bid and ask candles
    Then both directions follow the midpoint candle

  Scenario: The ablation variant changes the perception source only
    Given the packaged baseline and baseline-dsha strategy configurations
    When the inherited strategy configurations are resolved
    Then baseline keeps EMA and baseline-dsha selects double-smoothed Heikin-Ashi
    And the model artifact and remaining filter configuration are identical
