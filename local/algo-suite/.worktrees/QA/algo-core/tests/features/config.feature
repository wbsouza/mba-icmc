Feature: Configuration loading policy
  The loader turns a strategy config into a validated parameter set under a hybrid
  policy: a missing trading-impactful parameter hard-stops; a missing operational
  parameter falls back to a logged default; an explicit null disables a nullable
  parameter; and a schema-version mismatch refuses to load. (SPEC.md §8;
  extends/inheritance is post-TCC and out of scope here.)

  Background:
    Given a baseline strategy config

  Scenario: a missing trading-impactful parameter is a hard stop
    Given the config omits "risk_math.risk_per_trade"
    When the loader validates it
    Then it fails to load
    And the error names "risk_per_trade", section "risk_math" and reference value 0.03
    And the error hints to run the config_generator

  Scenario: a missing operational parameter falls back to a logged default
    Given the config omits "operational.log_level"
    When the loader validates it
    Then it loads successfully
    And the provenance log contains "USING DEFAULT: log_level=INFO"

  Scenario: an explicit null disables a nullable parameter
    Given the config sets "risk_guard.max_leverage" to null
    When the loader validates it
    Then it loads successfully
    And the provenance log contains "EXPLICITLY DISABLED: max_leverage"

  Scenario: a missing nullable trading parameter is still a hard stop (missing is not null)
    Given the config omits "risk_guard.max_leverage"
    When the loader validates it
    Then it fails to load

  Scenario: a schema-version mismatch refuses to load with an upgrade hint
    Given the config sets schema_version to 1
    When the loader validates it
    Then it fails to load with exit code 3
    And the error hints to run "--upgrade"

  Scenario: a missing schema_version is rejected (fail fast, no silent default)
    Given the config omits "schema_version"
    When the loader validates it
    Then it fails to load with exit code 3

  Scenario: a null on a non-nullable parameter is rejected
    Given the config sets "risk_math.risk_per_trade" to null
    When the loader validates it
    Then it fails to load

  Scenario: an unknown parameter is rejected (fail fast, no silent ignore)
    Given the config has an unknown key "risk_math.bogus_param"
    When the loader validates it
    Then it fails to load
