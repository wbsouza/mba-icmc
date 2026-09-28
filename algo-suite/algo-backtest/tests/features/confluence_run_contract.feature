Feature: Confluence run contract — the bounded fourteen-cell launch harness (story 21, T17)
  Proves `experiments/confluence-chain/run_cells.py`, the explicit-run-ID harness that
  enforces the registration (T16's README, the fourteen registered cell ids), data
  (T9's preflight, reused here) and integration (the disclosed GDELT-availability gap)
  gates before any registered cell's backtest is launched (spec CC-23, CC-24, CC-32).
  Every scenario below launches through a fake runner — a stub standing in for the
  real `algo-backtest run` child process — and never starts a real LEAN run.

  Rule: Exactly the fourteen registered ids are ever accepted (CC-23)

    Scenario: the harness recognizes exactly the fourteen registered cell ids
      Given a fresh job directory
      Then the harness's registered cell ids are exactly the fourteen from the README

    Scenario: an unregistered cell id is refused before anything is written
      Given a fresh job directory
      When the harness is launched for cell id "zzz-h1" with a fake runner that always succeeds
      Then the launch is refused naming the unregistered id "zzz-h1"
      And no attempt file exists for any cell

  Rule: Each cell gets its own distinct output root

    Scenario: two different cells never share an output root
      Given a fresh job directory
      When the harness is launched for cells "m-only-h1" and "always-short-h1" with a fake runner that always succeeds
      Then "m-only-h1" and "always-short-h1" each have their own status.json under the job directory
      And "m-only-h1"'s status.json path differs from "always-short-h1"'s status.json path

  Rule: No cell in this study ever launches with a model (README, "No model dependency")

    Scenario Outline: the constructed launch command never carries --model
      Given a fresh job directory
      When the harness is launched for cell id "<cell_id>" with a fake runner that always succeeds
      Then the recorded command for "<cell_id>" does not contain "--model"

      Examples:
        | cell_id          |
        | m-only-h1        |
        | always-short-h4  |

  Rule: A failed preflight launches zero cells (CC-24)

    Scenario: a population preflight failure aborts before any cell is attempted
      Given a fresh job directory
      And a population preflight that always fails
      When the harness is launched for cells "m-only-h1" and "m-only-h4" with a fake runner that always succeeds
      Then the launch raises a preflight error
      And no attempt file exists for any cell
      And the fake runner was never called

  Rule: News-dependent cells are recorded unavailable and never launched (CC-13, CC-32, D9)

    Scenario Outline: an arm blocked on GDELT availability is recorded unavailable, not launched
      Given a fresh job directory
      When the harness is launched for cell id "<cell_id>" with a fake runner that always succeeds
      Then "<cell_id>"'s status is "unavailable"
      And the fake runner was never called for "<cell_id>"

      Examples:
        | cell_id     |
        | a-h1        |
        | b-h4        |
        | t-only-h1   |

    Scenario: A-plan resolves to unavailable through A's arm ledger, never raising unknown arm
      Given a fresh job directory
      When the harness is launched for cell id "a-plan-h1" with a fake runner that always succeeds
      Then "a-plan-h1"'s status is "unavailable"
      And the launch does not raise

    Scenario: a news-independent arm is not blocked by the availability gate
      Given a fresh job directory
      When the harness is launched for cell id "always-long-h1" with a fake runner that always succeeds
      Then "always-long-h1"'s status is "succeeded"

  Rule: A nonzero child exit persists as a failure record, never raised (CC-32)

    Scenario: a fake runner exiting nonzero is recorded as a failure, not an exception
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that always exits 1
      Then "m-only-h1"'s status is "failed"
      And "m-only-h1"'s recorded exit code is 1
      And the launch does not raise

  Rule: Bounded attempts — one initial attempt per cell, no automatic retry loop

    Scenario: resume never overwrites an existing attempt
      Given a fresh job directory
      And the harness has already launched cell id "m-only-h1" with a fake runner that always succeeds
      When the harness is launched again for cell id "m-only-h1" with a fake runner that always exits 1
      Then "m-only-h1"'s status is still "succeeded"
      And the fake runner was never called for "m-only-h1"

    Scenario: an explicit rerun is the only way to attempt a cell again
      Given a fresh job directory
      And the harness has already launched cell id "m-only-h1" with a fake runner that always exits 1
      When the harness reruns cell id "m-only-h1" with a fake runner that always succeeds
      Then "m-only-h1"'s status is "succeeded"

  Rule: Every recorded status carries its config and source hashes (CC-32)

    Scenario: a launched cell's status and command record its config hash and source revision
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then "m-only-h1"'s recorded config hash matches its generated manifest row
      And "m-only-h1"'s command record names a source revision or explicit None
