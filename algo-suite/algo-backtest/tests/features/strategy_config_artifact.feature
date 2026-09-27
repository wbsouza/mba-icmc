Feature: Resolved strategy configuration is a durable run artifact
  Scenario: A config sidecar atomically replaces the previous complete document
    Given a resolved baseline-dsha config and an existing config sidecar
    When the resolved config sidecar is written
    Then the replacement publishes the full resolved config atomically

  Scenario Outline: Invalid JSON values never replace a valid sidecar
    Given a resolved baseline-dsha config and an existing config sidecar
    And its raw config contains <invalid> data
    When writing the config sidecar fails
    Then the prior config sidecar is unchanged
    And the error explains how to fix the strategy config

    Examples:
      | invalid       |
      | non-JSON      |
      | non-finite    |

  Scenario: Failed atomic replacement preserves the existing sidecar
    Given a resolved baseline-dsha config and an existing config sidecar
    And the filesystem rejects the sidecar replacement
    When writing the config sidecar fails
    Then the prior config sidecar is unchanged
    And no temporary config file remains
