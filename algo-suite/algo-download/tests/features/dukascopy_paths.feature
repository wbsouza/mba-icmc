Feature: Dukascopy URL and raw-path mapping
  The Dukascopy datafeed indexes the month from zero in its URL (00 = January)
  while the on-disk store keeps the month 1-indexed. Build and parse of the raw
  path are inverses.

  Scenario: The bi5 URL is zero-indexed by month
    When I build the bi5 URL for "EURUSD" 2020-01-02 14h
    Then the URL is "https://datafeed.dukascopy.com/datafeed/EURUSD/2020/00/02/14h_ticks.bi5"

  Scenario: The raw path is one-indexed on disk
    When I build the raw path under "/data" for "EURUSD" 2020-01-02 14h
    Then the raw path is "/data/raw/dukascopy/EURUSD/2020/01/02/14h.bi5"

  Scenario: Parsing the raw path inverts building it
    When I round-trip the raw path under "/data" for "USDJPY" 2024-12-31 23h
    Then the parsed tick equals the original tick
