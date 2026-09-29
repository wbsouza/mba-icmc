Feature: Orchestrate a download run (source-agnostic)
  The synchronous orchestrator plans units, skips those already on disk, fetches
  the rest, and aggregates a normalized report. MISSING is not a failure; a
  FAILED unit does not stop the run but makes the exit code non-zero.

  Scenario: Done units are skipped, the rest are fetched
    Given a source planning 3 units
    And unit 1 is already on disk
    And unit 2 fetches "written"
    And unit 3 fetches "written"
    When I run the download
    Then the report is written=2 skipped=1 missing=0 failed=0
    And the exit code is 0

  Scenario: A no-data unit is MISSING, not a failure
    Given a source planning 3 units
    And unit 1 fetches "missing"
    And unit 2 fetches "written"
    And unit 3 fetches "written"
    When I run the download
    Then the report is written=2 skipped=0 missing=1 failed=0
    And the exit code is 0

  Scenario: A failed unit continues the run but flips the exit code
    Given a source planning 3 units
    And unit 1 fetches "written"
    And unit 2 fetches "failed"
    And unit 3 fetches "written"
    When I run the download
    Then the report is written=2 skipped=0 missing=0 failed=1
    And every planned unit was visited
    And the exit code is non-zero

  Scenario: An unexpected error in one unit is contained as FAILED
    Given a source planning 3 units
    And unit 1 fetches "written"
    And unit 2 raises an unexpected error
    And unit 3 fetches "written"
    When I run the download
    Then the report is written=2 skipped=0 missing=0 failed=1
    And every planned unit was visited
    And the exit code is non-zero
