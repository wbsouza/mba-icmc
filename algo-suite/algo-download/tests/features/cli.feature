Feature: algo-download CLI wiring
  The typer CLI plans and runs downloads. Argument validation fails fast with a
  helpful message; a dry run performs no I/O; a real run (with the datafeed
  mocked) reports written payloads and exits zero.

  Background:
    Given ALGO_DATA_ROOT points at a writable temp directory

  Scenario: A dry run lists the plan without I/O
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD --month 2020-01 --dry-run"
    Then the CLI exits 0
    And the output contains "EURUSD 2020-01-02 14h"
    And no .bi5 file was written under the data root

  Scenario: An unknown source fails fast naming the known sources
    When I invoke the CLI with "run --source nope --symbol EURUSD --month 2020-01"
    Then the CLI exits non-zero
    And the output contains "dukascopy"

  Scenario: A run with neither a month nor a range fails fast
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD"
    Then the CLI exits non-zero

  Scenario: The version command prints the package version
    When I invoke the CLI with "version"
    Then the CLI exits 0
    And the output is non-empty

  Scenario: A badly formatted month fails fast
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD --month 2020/01"
    Then the CLI exits non-zero
    And the output contains "YYYY-MM"

  Scenario: An impossible month fails fast with a friendly range
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD --month 2020-13"
    Then the CLI exits non-zero
    And the output contains either "1-12" or "01-12"

  Scenario: An unknown symbol fails fast mentioning the catalog
    When I invoke the CLI with "run --source dukascopy --symbol XXXYYY --month 2020-01"
    Then the CLI exits non-zero
    And the lowercased output contains "catalog"

  Scenario: A from-month after the to-month fails fast
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD --from 2020-03 --to 2020-01"
    Then the CLI exits non-zero

  Scenario: A mocked run reports written payloads and exits zero
    Given the datafeed returns 200 with "TICKS" and no throttle
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD --month 2020-01"
    Then the CLI exits 0
    And the lowercased output contains "written"
    And at least one .bi5 file was written under the data root

  Scenario: A mocked range downloads each month and exits zero
    Given the datafeed returns 200 with "TICKS" and no throttle
    When I invoke the CLI with "run --source dukascopy --symbol EURUSD --from 2020-01 --to 2020-02"
    Then the CLI exits 0
    And the directory "raw/dukascopy/EURUSD/2020/01" exists under the data root
    And the directory "raw/dukascopy/EURUSD/2020/02" exists under the data root

  # cli-11
  Scenario: A global source (no symbol) rejects --symbol
    When I invoke the CLI with "run --source gdelt --symbol EURUSD --month 2020-01"
    Then the CLI exits non-zero
    And the output contains "--symbol"

  # cli-12
  Scenario: A global source (no symbol) runs without --symbol
    Given the GDELT datafeed returns 200 with "ZIP" and no throttle
    When I invoke the CLI with "run --source gdelt --month 2020-01 --dry-run"
    Then the CLI exits 0

  # cli-13
  Scenario: A whole-window source (no date partitioning) rejects --month
    When I invoke the CLI with "run --source gpr --month 2020-01"
    Then the CLI exits non-zero
    And the output contains "--month"

  # cli-14
  Scenario: A whole-window source (no date partitioning) rejects --from/--to
    When I invoke the CLI with "run --source gpr --from 2020-01 --to 2020-02"
    Then the CLI exits non-zero
    And the output contains "--from"

  # cli-15
  Scenario: A whole-window source runs with neither --symbol nor a date flag
    Given the GPR datafeed returns 200 with "XLS" and no throttle
    When I invoke the CLI with "run --source gpr"
    Then the CLI exits 0
    And the lowercased output contains "written"

  # cli-16
  Scenario: A second global source (no symbol) rejects --symbol
    When I invoke the CLI with "run --source gdelt_ngrams --symbol EURUSD --month 2020-01"
    Then the CLI exits non-zero
    And the output contains "--symbol"
    And the output contains "gdelt_ngrams"

  # cli-17
  Scenario: A second global source (no symbol) runs without --symbol
    Given the GDELT NGrams datafeed returns 200 with "GZIP" and no throttle
    When I invoke the CLI with "run --source gdelt_ngrams --month 2020-01 --dry-run"
    Then the CLI exits 0

  # cli-18
  Scenario: A global source range spans every requested month
    When I invoke the CLI with "run --source gdelt --from 2020-01 --to 2020-02 --dry-run"
    Then the CLI exits 0
    And the output contains "gdelt 2020-02-01 00:00"

  # cli-19
  Scenario Outline: A whole-window source rejects a lone --from or --to flag too
    When I invoke the CLI with "run --source gpr <flag>"
    Then the CLI exits non-zero
    And the output contains "--from"

    Examples:
      | flag           |
      | --from 2020-01 |
      | --to 2020-02   |

  # cli-20
  Scenario: A whole-window source checks --symbol before --month
    When I invoke the CLI with "run --source gpr --symbol EURUSD --month 2020-01"
    Then the CLI exits non-zero
    And the output contains "--symbol"
