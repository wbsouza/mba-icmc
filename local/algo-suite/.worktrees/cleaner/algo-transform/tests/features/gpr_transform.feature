Feature: Transform the whole-window GPR file into a canonical event Parquet partition
  GPR is one raw file, the whole window (algo-download SPEC.md Sec 7.1 /
  cli-13..15) -- there is no per-month raw unit to gate on, so there is no
  INCOMPLETE state here: either the one raw file is present and decodes, or
  it is not.

  Background:
    Given a writable data root

  # gpr-transform-01
  Scenario: The raw GPR file transforms to a whole-window event partition
    Given a raw GPR file with rows for periods 2015-02 through 2015-04
    When I transform "gpr"
    Then an event Parquet partition exists at parquet/events/gpr
    And it contains one row per period in the raw file
    And the run exits 0

  # gpr-transform-02
  Scenario: A missing raw GPR file is reported, not silently skipped
    Given no raw GPR file on disk
    When I transform "gpr"
    Then no event Parquet partition exists at parquet/events/gpr
    And the report says the input is missing
    And the run exits non-zero

  # gpr-transform-03
  Scenario: An already-written partition is skipped unless --rebuild
    Given a raw GPR file with rows for periods 2015-02 through 2015-04
    And a prior event partition exists for gpr
    When I transform "gpr"
    Then the report status is SKIPPED

  # gpr-transform-04
  Scenario: A stale GPR partition does not hide a missing raw input
    Given a prior event partition exists for gpr
    When I transform "gpr"
    Then the report says the input is missing
    And the run exits non-zero
