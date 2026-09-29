Feature: Resample ticks into QuoteBars at a chosen timeframe
  Pure aggregation: ticks are bucketed by timeframe boundary, OHLC is computed
  per bucket, duplicate ticks count once, and buckets without ticks are absent
  (gaps are never forward-filled).

  Scenario: M1 aggregates each minute into OHLC
    Given the ticks
      | day | hour | minute | second | bid  | ask  |
      | 2   | 14   | 0      | 0      | 1.10 | 1.11 |
      | 2   | 14   | 0      | 30     | 1.12 | 1.13 |
      | 2   | 14   | 0      | 45     | 1.09 | 1.10 |
      | 2   | 14   | 1      | 0      | 1.20 | 1.21 |
    When I resample at timeframe "M1"
    Then it yields 2 bars
    And bar 0 has timestamp 2020-01-02 14:00 UTC
    And bar 0 has bid OHLC 1.10 1.12 1.09 1.09
    And bar 0 has tick_count 3
    And bar 1 has tick_count 1

  Scenario: M5 buckets ticks into 5-minute bars
    Given the ticks
      | day | hour | minute | second | bid  | ask  |
      | 2   | 14   | 0      | 0      | 1.10 | 1.11 |
      | 2   | 14   | 3      | 0      | 1.15 | 1.16 |
      | 2   | 14   | 6      | 0      | 1.20 | 1.21 |
    When I resample at timeframe "M5"
    Then the bar timestamps are
      | timestamp                |
      | 2020-01-02 14:00 UTC     |
      | 2020-01-02 14:05 UTC     |
    And bar 0 has tick_count 2
    And bar 1 has tick_count 1

  Scenario: H4 buckets into 4-hour bars anchored at midnight
    Given the ticks
      | day | hour | minute | second | bid  | ask  |
      | 2   | 13   | 0      | 0      | 1.10 | 1.11 |
      | 2   | 15   | 30     | 0      | 1.20 | 1.21 |
      | 2   | 16   | 0      | 0      | 1.05 | 1.06 |
    When I resample at timeframe "H4"
    Then the bar timestamps are
      | timestamp                |
      | 2020-01-02 12:00 UTC     |
      | 2020-01-02 16:00 UTC     |
    And bar 0 has bid_open 1.10 and bid_close 1.20 and tick_count 2

  Scenario: D1 buckets ticks by day
    Given the ticks
      | day | hour | minute | second | bid  | ask  |
      | 2   | 9    | 0      | 0      | 1.10 | 1.11 |
      | 2   | 23   | 0      | 0      | 1.30 | 1.31 |
      | 3   | 1    | 0      | 0      | 1.05 | 1.06 |
    When I resample at timeframe "D1"
    Then the bar timestamps are
      | timestamp                |
      | 2020-01-02 00:00 UTC     |
      | 2020-01-03 00:00 UTC     |
    And bar 0 has bid_high 1.30 and tick_count 2

  Scenario: Bars without ticks are absent (gaps are not filled)
    Given the ticks
      | day | hour | minute | second | bid | ask |
      | 2   | 14   | 0      | 0      | 1.1 | 1.2 |
      | 2   | 16   | 0      | 0      | 1.3 | 1.4 |
    When I resample at timeframe "H1"
    Then the bar hours are 14 and 16

  Scenario: Duplicate ticks are deduplicated
    Given the ticks
      | day | hour | minute | second | bid  | ask  |
      | 2   | 14   | 0      | 0      | 1.10 | 1.11 |
      | 2   | 14   | 0      | 0      | 1.10 | 1.11 |
      | 2   | 14   | 0      | 1      | 1.12 | 1.13 |
    When I resample at timeframe "M1"
    Then bar 0 has tick_count 2

  Scenario: Empty input yields no bars
    Given no ticks
    When I resample at timeframe "M1"
    Then it yields 0 bars
