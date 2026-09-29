Feature: Extract the first Chapter-4 metrics from a run
  E2 reads the four headline metrics — total return, Sharpe, max drawdown, hit rate —
  from LEAN's own portfolio statistics, deterministically from a run's artifacts.

  Rule: The four headline metrics come from LEAN's portfolio statistics

    Scenario: the four metrics are extracted from a result
      Given a LEAN result with portfolio statistics 0.02, 1.5, 0.1, 0.6
      When I extract the metrics
      Then total return is 0.02
      And the Sharpe ratio is 1.5
      And the max drawdown is 0.1
      And the hit rate is 0.6

    Scenario: the metrics command reports them from a run directory
      Given a LEAN result with portfolio statistics 0.02, 1.5, 0.1, 0.6
      When I run the metrics command on that run directory
      Then the output reports total_return 0.02 and sharpe 1.5

  Rule: A result with no portfolio statistics fails fast with an actionable error

    Scenario: extracting metrics from an unfinished run is rejected
      Given a LEAN result with no portfolio statistics
      When I extract the metrics expecting failure
      Then extraction fails telling me the backtest may not have finished

    Scenario: a non-numeric statistic is rejected, not coerced
      Given a LEAN result whose total net profit is not a number
      When I extract the metrics expecting failure
      Then extraction fails telling me the backtest may not have finished

  Rule: A malformed metrics.json artifact is rejected, not a raw traceback

    Scenario: the metrics command rejects a corrupt metrics.json
      Given a run directory whose metrics.json is corrupt
      When I run the metrics command on that run directory
      Then the metrics command exits with code 2
      And the error tells me the metrics artifact is invalid
