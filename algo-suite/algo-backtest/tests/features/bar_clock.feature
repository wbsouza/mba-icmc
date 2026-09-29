Feature: Causal aggregation of complete UTC minute buckets
  Only complete buckets enter perception and warmup collections.
  Initial, final, and gap-interrupted partial buckets are deliberately omitted.

  Scenario: Aggregate independent bid and ask prices and tick counts at closure
    Given a closed bar clock of 5 minutes starting at "2026-09-25T12:00:00+00:00"
    And the following minute quotes
      | offset | bid_open | bid_high | bid_low | bid_close | ask_open | ask_high | ask_low | ask_close | tick_count |
      | 0      | 10       | 12       | 9       | 11        | 20       | 22       | 19      | 21        | 2          |
      | 1      | 11       | 15       | 8       | 12        | 21       | 23       | 18      | 22        | 3          |
      | 2      | 12       | 14       | 7       | 13        | 22       | 29       | 20      | 23        | 0          |
      | 3      | 13       | 14       | 10      | 11        | 23       | 25       | 16      | 24        | 5          |
      | 4      | 11       | 13       | 10      | 12        | 24       | 26       | 22      | 25        | 7          |
    When the minute quotes are consumed by the clock
    Then bars are emitted only on input offsets "4" with bucket offsets "0"
    And the closed quote has bid OHLC "10,15,7,12" and ask OHLC "20,29,16,25" and 17 ticks
    And batch results match streaming results for every input prefix
    And the input quotes are unchanged

  Scenario Outline: Every positive divisor of a UTC day closes without a future minute
    Given a closed bar clock of <minutes> minutes starting at "2026-09-25T00:00:00+00:00"
    And exactly one complete bucket of minute quotes
    When the minute quotes are consumed by the clock
    Then exactly one bucket is emitted on its last minute
    And batch results match the streaming results

    Examples:
      | minutes |
      | 1       |
      | 2       |
      | 3       |
      | 4       |
      | 5       |
      | 6       |
      | 8       |
      | 9       |
      | 10      |
      | 12      |
      | 15      |
      | 16      |
      | 18      |
      | 20      |
      | 24      |
      | 30      |
      | 32      |
      | 36      |
      | 40      |
      | 45      |
      | 48      |
      | 60      |
      | 72      |
      | 80      |
      | 90      |
      | 96      |
      | 120     |
      | 144     |
      | 160     |
      | 180     |
      | 240     |
      | 288     |
      | 360     |
      | 480     |
      | 720     |
      | 1440    |

  Scenario Outline: Partial buckets and market breaks never produce fabricated bars
    Given a closed bar clock of 5 minutes starting at "2026-09-25T23:50:00+00:00"
    And minute quotes at offsets "<inputs>"
    When the minute quotes are consumed by the clock
    Then bars are emitted only on input offsets "<emissions>" with bucket offsets "<buckets>"
    And batch results match streaming results for every input prefix

    Examples:
      | inputs                    | emissions | buckets |
      | 2,3,4,5,6,7,8,9,10,11    | 9         | 5       |
      | 0,1,3,4,5,6,7,8,9        | 9         | 5       |
      | 0,1,2,3,5,6,7,8,9        | 9         | 5       |
      | 0,1,2,3,4,10,11,12,13,14 | 4,14      | 0,10    |
      | 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 | 4,9,14 | 0,5,10 |
      | 0,1,2880,2881,2882,2883,2884 | 2884   | 2880    |
      | 0,1,2                     |           |         |
      | 4                         |           |         |
      |                           |           |         |

  Scenario Outline: Buckets are anchored at UTC midnight independently of the first quote
    Given a closed bar clock of <minutes> minutes starting at "<start>"
    And exactly one complete bucket of minute quotes
    When the minute quotes are consumed by the clock
    Then exactly one bucket is emitted on its last minute

    Examples:
      | minutes | start                     |
      | 240     | 2026-09-25T20:00:00+00:00 |
      | 1440    | 2026-09-25T00:00:00+00:00 |
      | 5       | 2026-09-25T23:55:00+00:00 |

  Scenario Outline: Reject malformed aggregation periods even for empty batches
    When a closed bar clock and an empty batch are requested with minutes <value>
    Then both requests fail with a minutes validation error

    Examples:
      | value |
      | 0     |
      | -1    |
      | true  |
      | false |
      | 7     |
      | 1441  |
      | 2880  |
      | 5.0   |
      | "5"   |
      | null  |

  Scenario Outline: Reject duplicate, unordered, or unaligned minute timestamps
    Given a closed bar clock of 1 minutes starting at "2026-09-25T12:00:00+00:00"
    And minute quotes at offsets "0,1"
    When the minute quotes are consumed by the clock
    And a minute quote at "<timestamp>" is submitted
    Then the quote fails with a timestamp validation error containing "<reason>"
    And a subsequent valid minute can still close

    Examples:
      | timestamp                        | reason           |
      | 2026-09-25T12:01:00+00:00         | strictly ordered |
      | 2026-09-25T12:00:00+00:00         | strictly ordered |
      | 2026-09-25T12:02:01+00:00         | minute-aligned   |
      | 2026-09-25T12:02:00.000001+00:00  | minute-aligned   |
