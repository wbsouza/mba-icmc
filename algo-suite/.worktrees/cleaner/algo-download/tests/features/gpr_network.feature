@network
Feature: GPR adapter against the live datafeed (opt-in)
  This smoke test hits the real Caldara & Iacoviello site, so it is excluded
  from the default offline gate. It validates the assumptions the offline
  tests mock: the canonical URL serves the index file directly (no mirror,
  no redirect to a different host), and resume is a filesystem no-op.

  # gpr-network-01
  Scenario: A real fetch and resume
    Given a GPR source against the live feed
    When I fetch the real GPR index
    Then the unit status is WRITTEN with a positive byte count
    And the raw path is "raw/gpr/data_gpr_export.xls"
    And the payload is a non-empty Excel file
    When I download gpr again
    Then the unit is now SKIPPED
