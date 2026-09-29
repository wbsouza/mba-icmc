Feature: Download GDELT event data (raw only)
  The GDELT adapter writes provider-native Events-table (.export.CSV.zip) bytes
  under raw/gdelt/ and nothing else. A unit is one 15-minute slot. Resume is
  filesystem-only; a slot the provider never published is MISSING and durable;
  a slot whose fetch never completes writes nothing and flips the exit code.
  There is no symbol dimension — GDELT is a global feed, not per-instrument.

  Background:
    Given a writable data root
    And the GDELT datafeed returns zip bytes by default

  # gdelt-01
  Scenario: Planning performs no I/O
    When I plan gdelt for "2020-01"
    Then the plan lists 2976 slot units
    And no HTTP request was made
    And no file was written under the data root

  # gdelt-02
  Scenario: Happy path writes raw payloads at the canonical path
    When I download gdelt for "2020-01"
    Then a raw payload exists at "raw/gdelt/2020/01/02/20200102143000.export.CSV.zip"
    And no file is written outside the raw store
    And no unit is FAILED
    And the run exits 0

  # gdelt-03
  Scenario: Resume is a filesystem no-op
    Given gdelt "2020-01" is already downloaded
    When I download gdelt for "2020-01"
    Then no HTTP request was made
    And every unit is SKIPPED
    And the run exits 0

  # gdelt-04
  Scenario: A slot the provider never published is MISSING and durable, not FAILED
    Given the GDELT datafeed has no data for slot 2020-01-02 14:30
    When I download gdelt for "2020-01"
    Then "raw/gdelt/2020/01/02/20200102143000.export.CSV.zip" exists as an empty payload
    And that slot is counted MISSING
    And the run exits 0

  # gdelt-05
  Scenario: A slot fetch that never completes writes nothing and flips the exit code
    Given the GDELT datafeed always errors for slot 2020-01-02 14:30
    When I download gdelt for "2020-01"
    Then no file exists at "raw/gdelt/2020/01/02/20200102143000.export.CSV.zip"
    And that slot is counted FAILED
    And the run exits non-zero

  # gdelt-06
  Scenario: The slot URL is directly guessable from its timestamp, no master list needed
    When I build the GDELT Events URL for slot 2020-01-02 14:30
    Then the URL is "https://data.gdeltproject.org/gdeltv2/20200102143000.export.CSV.zip"

  # gdelt-07
  Scenario: The raw path is day-partitioned and round-trips to the same slot
    When I round-trip the raw path under "/data" for slot 2020-01-02 14:30
    Then the parsed slot equals the original slot
