Feature: Offline DSHA matches the native serving contract
  Model training consumes only completed candles and the same binary directions.

  Scenario: Default smoothing follows the hand-computed native oracle
    Given an offline DSHA with default periods
    When six candles have OHLC 10 14 8 12
    Then offline DSHA refuses premature output
    When the seventh candle has OHLC 14 18 12 16
    Then offline smoothed buffers match 94/9 112/9 11 103/9

  Scenario: Wilder seeds the full period before applying recurrence
    Given an offline DSHA with periods 3 and 1
    When flat candles at 1 3 8 are replayed
    Then offline smoothed buffers equal 4 4 4 4
    When a flat candle at 10 is replayed
    Then offline smoothed buffers equal 4 6 4 6

  Scenario: Closed higher candles are held stable while the next bucket forms
    Given offline timeframes with periods 1 and 1 over 5 minutes
    When four minutes of OHLC 10 14 8 12 start at 2014-05-07T00:00:00
    Then offline timeframes refuse premature output
    When OHLC 10 14 8 12 arrives at 2014-05-07T00:04:00
    Then offline primary and higher directions are 1 and 1
    When OHLC 20 25 18 24 arrives at 2014-05-07T00:05:00
    Then offline primary and higher directions are -1 and 1
    When OHLC 20 25 18 24 arrives at 2014-05-07T00:09:00
    Then offline primary and higher directions are -1 and -1

  Scenario: Missing buckets do not invent smoothing samples
    Given offline timeframes with periods 2 and 1 over 5 minutes
    When OHLC 10 14 8 12 arrives at 2014-05-07T00:04:00
    When OHLC 10 14 8 12 arrives at 2014-05-07T03:00:00
    Then offline timeframes refuse premature output
    When OHLC 10 14 8 12 arrives at 2014-05-07T03:04:00
    Then offline primary and higher directions are 1 and 1

  Scenario: Default hourly readiness requires seven closed buckets
    Given offline timeframes with periods 6 and 2 over 60 minutes
    When 419 minutes of OHLC 10 14 8 12 start at 2014-05-07T00:00:00
    Then offline timeframes refuse premature output
    When OHLC 10 14 8 12 arrives at 2014-05-07T06:59:00
    Then offline primary and higher directions are 1 and 1

  Scenario: Flat ties preserve the historical down classification
    Given offline timeframes with periods 1 and 1 over 5 minutes
    When OHLC 10 10 10 10 arrives at 2014-05-07T00:04:00
    Then offline primary and higher directions are -1 and -1

  Scenario Outline: Invalid periods fail before replay
    When offline timeframes are constructed with <first> <second> <higher>
    Then offline construction fails with a period remediation
    Examples:
      | first | second | higher |
      | 0     | 2      | 60     |
      | 6     | 0      | 60     |
      | 6     | 2      | 0      |
      | 6     | 2      | 1      |

  Scenario: Seven-minute buckets use the native year-one tick origin
    Given offline timeframes with periods 1 and 1 over 7 minutes
    When OHLC 10 14 8 12 arrives at 2014-05-07T00:00:00
    Then offline timeframes refuse premature output
    When OHLC 10 14 8 12 arrives at 2014-05-07T00:03:00
    Then offline primary and higher directions are 1 and 1

  Scenario: Intervals longer than a day start at the first observed minute
    Given offline timeframes with periods 1 and 1 over 1500 minutes
    When OHLC 10 14 8 12 arrives at 2014-05-07T09:31:00
    When OHLC 10 14 8 12 arrives at 2014-05-08T10:29:00
    Then offline timeframes refuse premature output
    When OHLC 10 14 8 12 arrives at 2014-05-08T10:30:00
    Then offline primary and higher directions are 1 and 1

  Scenario: A gap closes the observed partial bucket before consuming the next bucket
    Given offline timeframes with periods 1 and 1 over 5 minutes
    When OHLC 10 14 8 12 arrives at 2014-05-07T00:01:00
    Then offline timeframes refuse premature output
    When OHLC 20 25 18 24 arrives at 2014-05-07T02:01:00
    Then offline primary and higher directions are -1 and 1
