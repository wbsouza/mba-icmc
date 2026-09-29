@network
Feature: GDELT adapter against the live datafeed (opt-in)
  This smoke test hits the real GDELT feed, so it is excluded from the default
  offline gate. It validates the assumptions the offline tests mock: the slot
  URL is directly guessable from a timestamp (no master-list fetch required),
  a real Events-table zip contains exactly one CSV, and an out-of-coverage
  slot (before GDELT v2 began 2015-02-18) is a durable MISSING via an empty
  404 body.

  # gdelt-network-01
  Scenario: A real slot, an out-of-coverage slot, and resume
    Given a GDELT source against the live feed
    When I fetch the real Events slot 2026-09-22 09:45
    Then the slot status is WRITTEN with a positive byte count
    And the raw path is "raw/gdelt/2026/09/22/20260922094500.export.CSV.zip"
    And the payload is a zip containing exactly one CSV named "20260922094500.export.CSV"
    When I fetch the out-of-coverage slot 2015-02-17 00:00
    Then the slot status is MISSING with an empty marker persisted
    And both slots are now done on disk
