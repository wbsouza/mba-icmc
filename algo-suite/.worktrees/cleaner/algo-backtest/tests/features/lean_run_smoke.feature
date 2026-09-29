@integration
Feature: lean-smoke proves the run path end to end
  The full path — materialized EUR/USD lean-data -> LEAN run -> /Results parsed ->
  one closed round-trip trade — works. The bundled smoke-trade algorithm enters and
  exits explicitly (not relying on the engine to close at end), so the assertion is
  stable. This is plumbing proof, not a strategy.

  Scenario: a materialized month yields one closed trade through lean-smoke
    Given materialized EUR/USD minute data for 2014-05
    When I run the lean-smoke CLI command
    Then the command exits successfully
    And it reports exactly one closed trade

  Scenario: a run whose window has no bars never enters and closes no trade
    Given materialized EUR/USD minute data outside the smoke-trade window
    When I run the smoke-trade algorithm directly
    Then the algorithm reports it never entered
    And it reports zero closed trades
