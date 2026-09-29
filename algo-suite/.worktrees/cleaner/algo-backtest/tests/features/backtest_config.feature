Feature: algo-backtest configuration
  algo-backtest resolves its effective configuration through the shared algo-core
  loader (env > conf/backtest.yaml > conf/algo.yaml > defaults). The per-market data
  timezone is the value the lean-data materializer needs; it is config-driven, never
  hard-coded, and exposed to the tool as a typed ZoneInfo. OANDA forex is UTC by
  convention (empirically confirmed against the LEAN engine).

  Scenario: zero-config resolves the OANDA data timezone to UTC
    Given no config files and no ALGO_ overrides
    When I load the algo-backtest config
    Then the OANDA data timezone is "UTC"
    And it is a ZoneInfo instance
    And the provenance trail includes the data root

  Scenario: the data timezone is overridable via the environment
    Given the environment sets "ALGO_MARKETS__OANDA__DATA_TZ" to "America/New_York"
    When I load the algo-backtest config
    Then the OANDA data timezone is "America/New_York"
    And it is a ZoneInfo instance

  Scenario: an unknown timezone fails fast
    Given the environment sets "ALGO_MARKETS__OANDA__DATA_TZ" to "Mars/Phobos"
    When I load the algo-backtest config
    Then loading fails with a timezone error
