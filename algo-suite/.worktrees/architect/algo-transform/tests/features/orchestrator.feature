Feature: Orchestrate a completeness-gated, idempotent month transform
  transform_month writes a canonical partition only when the raw month is
  complete and decodes cleanly. A pre-existing partition is skipped; an
  incomplete or corrupt month writes nothing.

  Scenario: An already-existing partition is skipped
    Given a writable data root
    And a prior complete m1 partition exists for EURUSD 2020-01
    When I transform_month EURUSD 2020-01
    Then the report status is SKIPPED
    And the report exit code is 0

  Scenario: An incomplete raw month writes nothing
    Given a writable data root
    When I transform_month EURUSD 2020-01
    Then the report status is INCOMPLETE
    And the report exit code is non-zero
    And no m1 partition exists for EURUSD 2020-01

  Scenario: A complete month is written to the chosen timeframe partition
    Given a writable data root
    And the EURUSD 2020-01 month is filled with no-data markers
    And a data hour at EURUSD 2020-01-02 14h with one EUR/USD tick
    When I transform_month EURUSD 2020-01 at timeframe H4
    Then the report status is WRITTEN
    And an h4 partition exists for EURUSD 2020-01
    And no m1 partition exists for EURUSD 2020-01

  Scenario: A corrupt raw hour blocks the write
    Given a writable data root
    And the EURUSD 2020-01 month is filled with no-data markers
    And a corrupt hour at EURUSD 2020-01-02 14h
    When I transform_month EURUSD 2020-01
    Then the report status is CORRUPT
    And the report quarantined count is 1
    And the report exit code is non-zero
    And no m1 partition exists for EURUSD 2020-01
