Feature: lean-smoke guards against missing data
  lean-smoke fails fast with a clear message when no EUR/USD lean-data has been
  materialized, rather than launching the engine to hit an opaque "no data" error.
  The guard runs before any container, so this needs no Docker.

  Scenario: no materialized data fails fast before launching the engine
    Given a data root with no materialized EUR/USD lean-data
    When I run the lean-smoke command
    Then it exits with code 2
    And the error tells me to run materialize first
