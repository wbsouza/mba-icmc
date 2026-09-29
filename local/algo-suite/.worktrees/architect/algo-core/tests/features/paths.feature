Feature: Canonical storage path layout
  layout.py builds and parses the on-disk paths from one data root. Build and
  parse are inverses: parsing a built path returns the components it was built
  from, for every domain.

  Background:
    Given the data root "/data"

  Scenario: price Parquet path for an instrument month-partition
    When I build the price path for security_type "forex" symbol "EURUSD" resolution "minute" year 2024 month 3
    Then the path is "/data/parquet/forex/EURUSD/minute/year=2024/month=03/data.parquet"
    And parsing the price path yields security_type "forex" symbol "EURUSD" resolution "minute" year 2024 month 3

  Scenario: feature Parquet path for a dataset month-partition
    When I build the feature path for domain "sentiment" dataset "finbert" year 2024 month 12
    Then the path is "/data/parquet/sentiment/finbert/year=2024/month=12/data.parquet"
    And parsing the feature path yields domain "sentiment" dataset "finbert" year 2024 month 12

  Scenario: lean-data execution-store directory for an instrument
    When I build the lean-data dir for security_type "forex" market "dukascopy" resolution "minute" symbol "eurusd"
    Then the path is "/data/lean-data/forex/dukascopy/minute/eurusd"
    And parsing the lean-data dir yields security_type "forex" market "dukascopy" resolution "minute" symbol "eurusd"

  Scenario: price path derived from an Instrument (no caller-owned classification)
    When I build the price path from instrument "EURUSD" resolution "minute" year 2024 month 3
    Then the path is "/data/parquet/forex/EURUSD/minute/year=2024/month=03/data.parquet"

  Scenario: lean-data dir derived from an Instrument (LEAN-lowercased)
    When I build the lean-data dir from instrument "EURUSD" resolution "minute"
    Then the path is "/data/lean-data/forex/oanda/minute/eurusd"

  Scenario: raw store directory for a source (provider-native sub-path is the adapter's)
    When I build the raw dir for source "dukascopy"
    Then the path is "/data/raw/dukascopy"

  Scenario: Dukascopy raw hourly path builds and parses (inverse)
    When I build the dukascopy raw path for symbol "EURUSD" year 2020 month 1 day 2 hour 14
    Then the path is "/data/raw/dukascopy/EURUSD/2020/01/02/14h.bi5"
    And parsing the dukascopy raw path yields symbol "EURUSD" year 2020 month 1 day 2 hour 14
