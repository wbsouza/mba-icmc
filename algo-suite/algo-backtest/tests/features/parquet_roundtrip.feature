@integration
Feature: Canonical Parquet round-trips through the materializer into LEAN
  Unlike the timezone feature (which feeds synthetic QuoteBars straight to the
  materializer), this persists them to canonical Parquet via the same repository
  algo-transform writes with, reads them back, and only then materializes and replays
  them — proving the Parquet -> QuoteBar read leg (schema, precision, UTC survive).

  Scenario: QuoteBars persisted to Parquet, read back, and replayed arrive unchanged
    Given 5 one-minute QuoteBars starting at "2014-07-15T12:00:00" UTC
    And they are written to canonical Parquet and read back
    And the read-back bars equal the originals
    And they are materialized to lean-data in timezone "UTC"
    When the probe replays "20140715" to "20140716" in the LEAN container
    Then the backtest exits successfully
    And the algorithm timezone is UTC
    And each bar returns at its original UTC end with bid and ask intact
    And the probe reports 5 bars
