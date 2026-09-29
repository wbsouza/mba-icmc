Feature: Layered configuration resolution
  The suite runs zero-config: every setting has a convention default. Optional files
  override defaults and the environment overrides files. Precedence, highest first:
  environment (ALGO_*) > conf/<tool>.yaml > conf/algo.yaml > defaults. The resolved
  values are validated by the loader policy (SPEC.md §8) and every value records its
  source in the provenance log. (paths.py fixed the conventions; this is the missing
  layered read + merge.)

  Background:
    Given a schema with operational defaults log_level "INFO" and oanda data_tz "UTC"
    And the current schema version is 1

  Scenario: zero-config uses the convention defaults
    Given no config files and no ALGO_ environment overrides
    When I resolve the "backtest" config
    Then it resolves successfully
    And "operational.log_level" is "INFO"
    And "markets.oanda.data_tz" is "UTC"
    And the provenance log contains "USING DEFAULT: log_level=INFO"

  Scenario: a global config file overrides a default
    Given conf/algo.yaml sets "operational.log_level" to "DEBUG"
    When I resolve the "backtest" config
    Then it resolves successfully
    And "operational.log_level" is "DEBUG"
    And the provenance log contains "FROM CONFIG: log_level='DEBUG'"

  Scenario: a tool config file overrides the global file
    Given conf/algo.yaml sets "operational.log_level" to "DEBUG"
    And conf/backtest.yaml sets "operational.log_level" to "WARNING"
    When I resolve the "backtest" config
    Then it resolves successfully
    And "operational.log_level" is "WARNING"

  Scenario: an environment variable overrides the config files
    Given conf/backtest.yaml sets "operational.log_level" to "WARNING"
    And the environment sets "ALGO_OPERATIONAL__LOG_LEVEL" to "ERROR"
    When I resolve the "backtest" config
    Then it resolves successfully
    And "operational.log_level" is "ERROR"

  Scenario: a nested setting is overridable via a __-delimited env var
    Given the environment sets "ALGO_MARKETS__OANDA__DATA_TZ" to "America/New_York"
    When I resolve the "backtest" config
    Then it resolves successfully
    And "markets.oanda.data_tz" is "America/New_York"

  Scenario: a present config file lacking schema_version fails fast
    Given conf/algo.yaml without a schema_version sets "operational.log_level" to "DEBUG"
    When I resolve the "backtest" config
    Then it fails to resolve
    And the error mentions "schema_version"
