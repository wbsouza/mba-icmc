Feature: Transform a GDELT month into a canonical event Parquet partition
  Mirrors the Dukascopy completeness-gated orchestrator (transform.feature): a
  month is written only when every expected 15-minute slot is present as data
  or a durable MISSING marker; an incomplete or corrupt month writes nothing.
  GDELT has no --symbol (algo-download SPEC.md Sec 7.1 / cli-11).

  Background:
    Given a writable data root

  # gdelt-transform-01
  Scenario: A complete raw month is transformed to an event partition
    Given a complete raw GDELT month for 2020-01 with event data in slot 2020-01-02 14:30
    When I transform "gdelt" for "2020-01"
    Then an event Parquet partition exists at parquet/events/gdelt for 2020-01
    And it contains at least one event row
    And the run exits 0

  # gdelt-transform-02
  Scenario: An incomplete raw month is not transformed
    Given a complete raw GDELT month for 2020-01 with event data in slot 2020-01-02 14:30
    And the raw slot 2020-01-05 09:00 is removed
    When I transform "gdelt" for "2020-01"
    Then no event Parquet partition exists at parquet/events/gdelt for 2020-01
    And the report says the month is incomplete

  # gdelt-transform-03
  Scenario: A complete month with a corrupt raw slot is not transformed
    Given a complete raw GDELT month for 2020-01 with event data in slot 2020-01-02 14:30
    And the raw slot 2020-01-05 09:00 is corrupt
    When I transform "gdelt" for "2020-01"
    Then no event Parquet partition exists at parquet/events/gdelt for 2020-01
    And the report says the month is corrupt
    And the report names the corrupt slot's raw path

  # gdelt-transform-04
  Scenario: An already-written month is skipped unless --rebuild
    Given a prior complete event partition exists for gdelt 2020-01
    When I transform "gdelt" for "2020-01"
    Then the report status is SKIPPED
