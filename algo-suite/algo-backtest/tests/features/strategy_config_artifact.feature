Feature: Resolved strategy configuration is a durable run artifact
  The engine snapshots the fully resolved `StrategyChainConfig.raw` next to the run
  twice, from the same mapping: `strategy-config.json` (read by the QA scripts and the
  ablation-provenance tooling) and, since story 12, `strategy-config.yaml` — the same
  document in the form a `strategies/<name>/config.yaml` is written in, so a run's exact
  parameters can be copied into a new variant without hand-translating JSON. Both are
  published through the shared atomic writer; the JSON check runs first, so a value JSON
  rejects never reaches either file.

  Scenario Outline: The <sidecar> sidecar atomically replaces the previous complete document
    Given a resolved baseline-dsha config and existing config sidecars
    When the resolved config sidecars are written
    Then the <sidecar> replacement publishes the full resolved config atomically

    Examples:
      | sidecar              |
      | strategy-config.json |
      | strategy-config.yaml |

  Scenario: The YAML sidecar loads back as the same resolved strategy
    Given a resolved baseline-dsha config and existing config sidecars
    When the resolved config sidecars are written
    Then strategy-config.yaml loads back as the resolved "baseline-dsha" strategy
    And strategy-config.json and strategy-config.yaml hold the same document

  Scenario Outline: Invalid JSON values never replace a valid sidecar
    Given a resolved baseline-dsha config and existing config sidecars
    And its raw config contains <invalid> data
    When writing the config sidecars fails
    Then the prior config sidecars are unchanged
    And the error explains how to fix the strategy config

    Examples:
      | invalid       |
      | non-JSON      |
      | non-finite    |

  Scenario: Failed atomic replacement preserves the existing sidecars
    Given a resolved baseline-dsha config and existing config sidecars
    And the filesystem rejects the sidecar replacement
    When writing the config sidecars fails
    Then the prior config sidecars are unchanged
    And no temporary config file remains
