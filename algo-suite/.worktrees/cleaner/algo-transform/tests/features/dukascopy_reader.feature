Feature: Read a Dukascopy month from raw .bi5 hours
  Expected-hour enumeration is the single definition shared by completeness and
  loading. Loading decodes data hours, skips 0-byte no-data markers and absent
  hours, and quarantines corrupt hours.

  Scenario: Expected hours cover every hour of the month
    When I enumerate the expected hours for EURUSD 2020-01
    Then there are 744 expected hours
    And the first expected hour is EURUSD 2020-01-01 00h
    And the last expected hour is EURUSD 2020-01-31 23h

  Scenario: A month is incomplete when one hour is absent
    Given a writable data root
    And the EURUSD 2020-01 month is filled with no-data markers
    Then the month EURUSD 2020-01 is complete
    When the hour EURUSD 2020-01-02 14h is removed
    Then the month EURUSD 2020-01 is incomplete

  Scenario: Load decodes data, skips markers, and quarantines corrupt hours
    Given a writable data root
    And the EURUSD 2020-01 month is filled with no-data markers
    And a data hour at EURUSD 2020-01-02 14h with one EUR/USD tick
    And a corrupt hour at EURUSD 2020-01-03 10h
    When I load ticks for EURUSD 2020-01
    Then it loads 1 tick
    And the first loaded tick has ask 1.11966
    And 1 hour is quarantined

  Scenario: Load skips absent hours
    Given a writable data root
    And a data hour at EURUSD 2020-01-02 14h with one EUR/USD tick
    When I load ticks for EURUSD 2020-01
    Then it loads 1 tick
    And nothing is quarantined
