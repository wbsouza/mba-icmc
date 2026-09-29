Feature: algo-transform CLI wiring
  The Typer CLI fails fast on bad input (unsupported source, unknown symbol,
  impossible/badly-formatted month, missing or inverted range, invalid
  timeframe) and reports an incomplete month with a non-zero exit code.

  Scenario: version prints the package version
    When I invoke the CLI with "version"
    Then the run exits 0
    And the output is non-empty

  # cli-01
  Scenario: an unsupported source fails fast naming the known sources
    Given a writable data root
    When I run "--source nope --symbol EURUSD --month 2020-01"
    Then the run exits non-zero
    And the output contains "dukascopy"

  Scenario: an unknown symbol fails fast
    Given a writable data root
    When I run "--source dukascopy --symbol XXXYYY --month 2020-01"
    Then the run exits non-zero
    And the output contains case-insensitively "catalog"

  Scenario: an impossible month fails fast
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --month 2020-13"
    Then the run exits non-zero
    And the output mentions a valid month range "01-12" or "1-12"

  Scenario: a run requires a month or a range
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD"
    Then the run exits non-zero

  Scenario: the timeframe option is accepted (and an empty month is incomplete)
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --month 2020-01 --timeframe h4"
    Then the run exits non-zero
    And the output contains case-insensitively "incomplete"

  Scenario: an invalid timeframe is rejected
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --month 2020-01 --timeframe w1"
    Then the run exits non-zero

  Scenario: a badly-formatted month fails fast
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --month 2020/01"
    Then the run exits non-zero
    And the output contains "YYYY-MM"

  Scenario: a range whose start is after its end fails fast
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --from 2020-03 --to 2020-01"
    Then the run exits non-zero

  # cli-range-01: only one end of a --from/--to range given falls through to the
  # "provide --month, or both --from and --to" usage error, not a crash
  Scenario Outline: only one end of a range is given fails fast with the usage message
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD <flag>"
    Then the run exits non-zero
    And the output contains "both --from and --to"
    Examples:
      | flag             |
      | --from 2020-01   |
      | --to 2020-01     |

  Scenario: an incomplete month reports and exits non-zero
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --month 2020-01"
    Then the run exits non-zero
    And the output contains case-insensitively "incomplete"

  Scenario: a range over incomplete months exits non-zero with one line per month
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --from 2020-01 --to 2020-02"
    Then the run exits non-zero
    And the output reports "incomplete" exactly 2 times

  # cli-range-02: a range spanning a year boundary must roll year and month
  # together (Nov 2019 .. Feb 2020 is 4 months: Nov, Dec, Jan, Feb)
  Scenario: a range spanning a year boundary exits non-zero with one line per month
    Given a writable data root
    When I run "--source dukascopy --symbol EURUSD --from 2019-11 --to 2020-02"
    Then the run exits non-zero
    And the output reports "incomplete" exactly 4 times

  # cli-gdelt-01
  Scenario: gdelt (no symbol) rejects --symbol
    Given a writable data root
    When I run "--source gdelt --symbol EURUSD --month 2020-01"
    Then the run exits non-zero
    And the output contains "--symbol"

  # cli-gdelt-02
  Scenario: gdelt runs without --symbol
    Given a writable data root
    When I run "--source gdelt --month 2020-01"
    Then the run exits non-zero
    And the output contains case-insensitively "incomplete"
    # empty raw input -> INCOMPLETE, the same fail-fast contract as dukascopy;
    # confirms the CLI accepts gdelt without --symbol rather than rejecting it

  # cli-gdelt-ngrams-01
  Scenario: gdelt_ngrams (no symbol) rejects --symbol
    Given a writable data root
    When I run "--source gdelt_ngrams --symbol EURUSD --month 2020-01"
    Then the run exits non-zero
    And the output contains "--symbol"

  # cli-gdelt-ngrams-02
  Scenario: gdelt_ngrams runs without --symbol
    Given a writable data root
    When I run "--source gdelt_ngrams --month 2020-01"
    Then the run exits non-zero
    And the output contains case-insensitively "incomplete"
    # empty raw input -> INCOMPLETE, the same fail-fast contract as gdelt;
    # confirms the CLI accepts gdelt_ngrams without --symbol rather than rejecting it

  # cli-gpr-01
  Scenario Outline: gpr (whole window) rejects a per-instrument or date-range flag
    Given a writable data root
    When I run "--source gpr <flags>"
    Then the run exits non-zero
    And the output contains "<rejected_flag>"
    Examples:
      | flags                        | rejected_flag |
      | --symbol EURUSD              | --symbol      |
      | --month 2020-01              | --month       |
      | --from 2020-01 --to 2020-02  | --from        |
      | --from 2020-01               | --from        |
      | --to 2020-01                 | --to          |

  # cli-gpr-02
  Scenario: gpr runs with none of --symbol/--month/--from/--to
    Given a writable data root
    When I run "--source gpr"
    Then the run exits non-zero
    And the output contains case-insensitively "missing"
    # no raw GPR file on disk in this scenario -> reported missing, not a flag error

  # cli-coverage-01
  Scenario: coverage runs over the data root and prints the selected window
    Given a writable data root
    And a GDELT coverage series where 2015-05 through 2015-07 each cover at least 80% of the month
    When I invoke the CLI with "coverage"
    Then the run exits 0
    And the output states the selected window "2015-05 to 2015-07"
    And the output contains "coverage-matrix.pdf"
    And the coverage matrix is written to parquet/_meta/coverage.parquet
    And a coverage-matrix figure is written
