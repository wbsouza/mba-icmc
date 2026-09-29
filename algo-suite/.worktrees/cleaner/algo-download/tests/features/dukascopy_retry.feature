Feature: Dukascopy adapter retry, backoff and throttle
  Retry timing is the adapter's concern: transient failures (connection errors,
  429, 5xx) are retried up to the limit; non-transient codes (403) are not.
  Requests are spaced by a minimum interval, and an invalid min-interval env
  value fails fast.

  Scenario: A flaky connection is retried then succeeds
    Given a client that fails 2 times then returns 200 with "TICKS"
    And the source retries 3 times with no backoff
    When the source fetches the EURUSD 14h unit
    Then the client was called 3 times
    And the unit status is WRITTEN
    And the raw payload bytes are "TICKS"

  Scenario: A persistent connection error gives up and writes nothing
    Given a client that fails 99 times then returns 200 with "TICKS"
    And the source retries 2 times with no backoff
    When the source fetches the EURUSD 14h unit
    Then the client was called 3 times
    And the unit status is FAILED
    And no raw payload was written

  Scenario Outline: A transient HTTP status is retried then failed
    Given a client that always returns HTTP <code>
    And the source retries 2 times with no backoff
    When the source fetches the EURUSD 14h unit
    Then the client was called <attempts> times
    And the unit status is FAILED
    And no raw payload was written

    Examples:
      | code | attempts |
      | 503  | 3        |
      | 429  | 3        |

  Scenario: A forbidden status is not transient and is not retried
    Given a client that always returns HTTP 403
    And the source retries 2 times with no backoff
    When the source fetches the EURUSD 14h unit
    Then the client was called 1 times
    And the unit status is FAILED
    And no raw payload was written

  Scenario: The throttle enforces the minimum interval between requests
    Given an always-OK client and a 5.0s minimum interval
    When the source fetches the EURUSD 14h and 15h units in turn
    Then at least one recorded wait is 4.0s or more

  Scenario Outline: An invalid min-interval env value fails fast
    Given the env ALGO_DUKASCOPY_MIN_INTERVAL is "<value>"
    When I construct a Dukascopy source with an always-OK client
    Then it fails with a ValueError matching "<message>"

    Examples:
      | value | message        |
      | abc   | must be a number |
      | -1    | must be >= 0     |
