@network
Feature: Dukascopy adapter against the live datafeed (opt-in)
  This smoke test hits the real Dukascopy datafeed, so it is excluded from the
  default offline gate. It validates the assumptions the offline tests mock: the
  public URL format, that a real payload is a valid LZMA-compressed bi5 of
  20-byte tick records, that a weekend hour yields a durable MISSING, and that
  resume is a filesystem no-op.

  Scenario: A real data hour, a weekend gap, and resume
    Given a Dukascopy source against the live feed
    When I fetch the real EURUSD hour 2020-01-02 14h
    Then the hour status is WRITTEN with a positive byte count
    And the raw path is "raw/dukascopy/EURUSD/2020/01/02/14h.bi5"
    And the payload decompresses to whole 20-byte tick records
    And the first record has a plausible EURUSD level with bid no greater than ask
    When I fetch the weekend EURUSD hour 2020-01-04 12h
    Then the hour status is MISSING with an empty marker persisted
    And both hours are now done on disk
