@integration
Feature: The pinned LEAN engine runs under the testcontainers harness
  Proves the container wiring (mounts + secret-free config + default launcher entrypoint)
  before any materializer or timezone assertions layer on top.

  Scenario: A trivial no-data backtest runs to completion
    Given the smoke algorithm
    When I run it in the LEAN container
    Then the backtest exits successfully
    And the logs contain "SMOKE_END_OK"
