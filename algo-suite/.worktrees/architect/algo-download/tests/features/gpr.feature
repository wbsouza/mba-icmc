Feature: Download the GPR index (raw only)
  The GPR adapter writes the Caldara & Iacoviello Geopolitical Risk index —
  one provider-native file, the full window, no per-month partitioning — under
  raw/gpr/ and nothing else. There is exactly one unit; resume is filesystem-
  only; a failed fetch writes nothing and flips the exit code. There is no
  symbol dimension and no month dimension.

  Background:
    Given a writable data root
    And the GPR datafeed returns index bytes by default

  # gpr-01
  Scenario: Planning yields exactly one unit, no I/O
    When I plan gpr
    Then the plan lists 1 unit
    And no HTTP request was made
    And no file was written under the data root

  # gpr-02
  Scenario: Happy path writes the raw index file at the canonical path
    When I download gpr
    Then a raw payload exists at "raw/gpr/data_gpr_export.xls"
    And no file is written outside the raw store
    And no unit is FAILED
    And the run exits 0

  # gpr-03
  Scenario: Resume is a filesystem no-op
    Given gpr is already downloaded
    When I download gpr
    Then no HTTP request was made
    And every unit is SKIPPED
    And the run exits 0

  # gpr-04
  Scenario: A failed fetch writes nothing and flips the exit code
    Given the GPR datafeed always errors
    When I download gpr
    Then no file exists at "raw/gpr/data_gpr_export.xls"
    And the unit is counted FAILED
    And the run exits non-zero

  # gpr-05
  Scenario: The canonical GPR URL is the authors' own site, not a mirror
    When I build the GPR URL
    Then the URL is "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"
