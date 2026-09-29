Feature: Strategy runs bind canonical quote activity to their result artifacts
  An external strategy with volume enabled records exact canonical m1 file hashes
  before starting LEAN and rejects a run if those inputs change during execution.
  Only the container call is mocked; configuration, Parquet and manifests use real IO.

  Background:
    Given an external volume-enabled strategy with canonical May and June quotes
    And a mocked LEAN runner that produces a successful result

  Scenario: The activity manifest is written before the container starts
    When the external volume strategy is run across May and June
    Then the container saw the complete schema-1 quote activity manifest before starting
    And the activity data mount and resolved strategy enable canonical tick lookup
    And the run succeeds with the original activity manifest preserved
    And both canonical input files are unchanged

  Scenario Outline: A tick-count mutation during execution invalidates the run
    Given the mocked container changes only the <month> tick count during execution
    When the external volume strategy is run expecting rejection
    Then the container was called exactly once
    And the run error reports changed canonical tick activity and says to discard the run
    And the saved activity manifest still records the original input bytes
    And only the <month> canonical digest changed
    Examples:
      | month |
      | May   |
      | June  |

  Scenario Outline: A missing canonical month fails before container startup
    Given the <month> canonical partition is missing but materialized quotes remain
    When the external volume strategy is run expecting rejection
    Then the container was never called
    And the run error identifies the missing <month> partition and download remediation
    And no activity manifest or engine result was written
    Examples:
      | month |
      | May   |
      | June  |
