Feature: Materialize canonical Parquet into the lean-data store
  `algo-backtest materialize` reads a month of canonical minute QuoteBar Parquet and
  writes LEAN-native day-zips under lean-data/, using the config-resolved data
  timezone (UTC for OANDA). It builds the durable store once: re-running is
  idempotent (days already present are skipped), and a missing source fails fast.

  Background:
    Given a canonical EUR/USD minute Parquet for 2014-07 with 3 bars on the 15th

  Rule: A month of canonical Parquet becomes LEAN day-zips

    Scenario: materializing a month writes LEAN day-zips
      When I materialize EUR/USD for 2014-07
      Then the materialize status is WRITTEN
      And lean-data has "20140715_quote.zip" for EUR/USD
      And 1 day was written

    Scenario: a month spanning two days writes one zip per day
      Given a canonical EUR/USD minute Parquet for 2014-07 spanning the 15th and 16th
      When I materialize EUR/USD for 2014-07
      Then the materialize status is WRITTEN
      And lean-data has "20140715_quote.zip" for EUR/USD
      And lean-data has "20140716_quote.zip" for EUR/USD
      And 2 days were written

    Scenario: day-zips are written atomically (no temporary files remain)
      When I materialize EUR/USD for 2014-07
      Then the materialize status is WRITTEN
      And no temporary files remain in the lean-data store

    Scenario: the materialize CLI command writes the store and reports
      When I run "algo-backtest materialize --symbol EURUSD --year 2014 --month 7"
      Then the command exits successfully
      And lean-data has "20140715_quote.zip" for EUR/USD
      And the output reports "written"

  Rule: The store is built once — re-runs skip, bad sources fail fast

    Scenario: re-materializing the same month is idempotent
      Given EUR/USD 2014-07 has already been materialized
      When I materialize EUR/USD for 2014-07
      Then the materialize status is SKIPPED
      And 0 days were written

    Scenario: a missing canonical Parquet fails fast
      When I materialize EUR/USD for 2014-08
      Then materializing fails with a missing-source error

    Scenario: an empty canonical Parquet fails fast (not a silent skip)
      Given a canonical EUR/USD minute Parquet for 2014-09 with 0 bars
      When I materialize EUR/USD for 2014-09
      Then materializing fails with an empty-source error
