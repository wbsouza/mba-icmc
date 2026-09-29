Feature: Download Dukascopy tick data (raw only)
  The Dukascopy adapter writes provider-native .bi5 bytes under raw/dukascopy/
  and nothing else. Resume is filesystem-only; a no-data hour is MISSING and
  durable; a failed hour writes nothing and flips the exit code.

  Background:
    Given a writable data root
    And the Dukascopy datafeed returns tick bytes by default

  Scenario: Planning performs no I/O
    When I plan dukascopy "EURUSD" for "2020-01"
    Then the plan lists 744 hour units
    And no HTTP request was made
    And no file was written under the data root

  Scenario: Happy path writes raw .bi5 at the canonical path
    When I download dukascopy "EURUSD" for "2020-01"
    Then a raw payload exists at "raw/dukascopy/EURUSD/2020/01/02/14h.bi5"
    And no file is written outside the raw store
    And no unit is FAILED
    And the run exits 0

  Scenario: Resume is a filesystem no-op
    Given "EURUSD" "2020-01" is already downloaded
    When I download dukascopy "EURUSD" for "2020-01"
    Then no HTTP request was made
    And every unit is SKIPPED
    And the run exits 0

  Scenario: A no-data hour is MISSING and durable, not FAILED
    Given the datafeed has no data for "EURUSD" 2020-01-02 14h
    When I download dukascopy "EURUSD" for "2020-01"
    Then "raw/dukascopy/EURUSD/2020/01/02/14h.bi5" exists as an empty payload
    And that hour is counted MISSING
    And the run exits 0

  Scenario: A failed hour writes nothing and flips the exit code
    Given the datafeed always errors for "EURUSD" 2020-01-02 14h
    When I download dukascopy "EURUSD" for "2020-01"
    Then no file exists at "raw/dukascopy/EURUSD/2020/01/02/14h.bi5"
    And that hour is counted FAILED
    And the run exits non-zero

  Scenario: USDJPY keeps its own identity
    When I download dukascopy "USDJPY" for "2020-01"
    Then a raw payload exists at "raw/dukascopy/USDJPY/2020/01/02/14h.bi5"
    And the run exits 0
