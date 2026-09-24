Feature: Market-data value objects (Tick, QuoteBar, Timeframe)
  Frozen, timezone-aware market-data value objects. A Timeframe floors a
  timestamp to its bar start and reports its width in minutes. A Tick and a
  QuoteBar carry their quote fields, reject naive timestamps and negative
  counts, and are immutable.

  Scenario Outline: a timeframe floors a timestamp to its bar start
    Given the timestamp 2020-01-02 14:37:45.123 UTC
    When I floor it with timeframe "<timeframe>"
    Then the floored timestamp is <hour>:<minute> UTC on 2020-01-02

    Examples:
      | timeframe | hour | minute |
      | M1        | 14   | 37     |
      | M5        | 14   | 35     |
      | M15       | 14   | 30     |
      | M30       | 14   | 30     |
      | H1        | 14   | 0      |
      | H4        | 12   | 0      |
      | D1        | 0    | 0      |

  Scenario Outline: a timeframe reports its width in minutes
    Then timeframe "<timeframe>" has <minutes> minutes

    Examples:
      | timeframe | minutes |
      | M5        | 5       |
      | H4        | 240     |
      | D1        | 1440    |

  Scenario: a tick carries its quote and volumes
    Given a tick
    Then its bid is 1.11963
    And its ask is 1.11966
    And its bid_volume is 0.75
    And its ask_volume is 4.39

  Scenario: a tick is frozen
    Given a tick
    When I assign 9.9 to the tick bid
    Then a validation error is raised

  Scenario: a tick rejects a naive timestamp
    When I build a tick with a naive timestamp
    Then a validation error is raised

  Scenario: a tick rejects a negative volume
    When I build a tick with a negative bid_volume
    Then a validation error is raised

  Scenario: a quotebar carries its bid/ask OHLC and tick count
    Given a quotebar
    Then its bid_close is 1.15
    And its ask_high is 1.2002
    And its tick_count is 42

  Scenario: a quotebar is frozen
    Given a quotebar
    When I assign 9.9 to the quotebar bid_close
    Then a validation error is raised

  Scenario: a quotebar rejects a naive timestamp
    When I build a quotebar with a naive timestamp
    Then a validation error is raised

  Scenario: a quotebar rejects a negative tick count
    When I build a quotebar with a negative tick_count
    Then a validation error is raised
