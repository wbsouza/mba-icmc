Feature: Transform a Dukascopy month into a minute QuoteBar Parquet partition
  End to end: raw .bi5 hours -> decode -> resample -> canonical minute Parquet.
  A month is transformed only when its raw hours are all present; an incomplete
  month is reported, never written as a half-built partition.

  Background:
    Given a writable data root

  Scenario: A complete raw month is transformed to a minute partition
    Given a complete raw month for EURUSD 2020-01 with tick data in hour 2020-01-02 14h
    When I transform "dukascopy" "EURUSD" "2020-01"
    Then a minute Parquet partition exists for EURUSD 2020-01
    And it contains at least one QuoteBar
    And the run exits 0

  Scenario: An incomplete raw month is not transformed
    Given a complete raw month for EURUSD 2020-01 with tick data in hour 2020-01-02 14h
    And the raw hour 2020-01-05 09h is removed
    When I transform "dukascopy" "EURUSD" "2020-01"
    Then no minute Parquet partition exists for EURUSD 2020-01
    And the report says the month is incomplete

  Scenario: A complete month with a corrupt raw hour is not transformed
    Given a complete raw month for EURUSD 2020-01 with tick data in hour 2020-01-02 14h
    And the raw hour 2020-01-05 09h is corrupt
    When I transform "dukascopy" "EURUSD" "2020-01"
    Then no minute Parquet partition exists for EURUSD 2020-01
    And the report says the month is corrupt
