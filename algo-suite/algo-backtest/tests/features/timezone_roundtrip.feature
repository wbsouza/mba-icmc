@integration
Feature: Materialized UTC bars round-trip through LEAN as UTC
  Proves that bars written by the materializer are read back by the engine — with the
  algorithm timezone forced to UTC — at exactly their original UTC instants, observed
  via self.UtcTime (= the bar's UTC EndTime). Running a summer (EDT) and a winter (EST)
  date shows the result is correctly DST-invariant, since the data layer is UTC.

  Scenario Outline: <label> minute bars survive materialize then LEAN unchanged
    Given 5 one-minute QuoteBars starting at "<first_start>" UTC
    And they are materialized to lean-data in timezone "UTC"
    When the probe replays "<day>" to "<next_day>" in the LEAN container
    Then the backtest exits successfully
    And the algorithm timezone is UTC
    And each bar returns at its original UTC end with bid and ask intact
    And the probe reports 5 bars

    Examples:
      | label      | first_start         | day      | next_day |
      | summer_edt | 2014-07-15T12:00:00 | 20140715 | 20140716 |
      | winter_est | 2014-01-15T12:00:00 | 20140115 | 20140116 |
