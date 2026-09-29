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

  # --- Phase 3 hardening (mutation pass over run_cells.py and the registration README) ---

  Rule: The registered caps and the README agree (T16 registration, CC-23)

    Scenario: the harness's default caps are the README's 3 concurrent cells and 30 minutes
      Then the harness defaults to 1800 seconds per cell and 3 concurrent cells
      And the README states a cap of 3 concurrent containers and a 30-minute timeout per cell

    Scenario: the README's cell table lists exactly the fourteen registered cells
      Given a fresh job directory
      When the harness is launched for all fourteen registered cells with a fake runner that always succeeds
      Then the README's cell table names exactly the registered cell ids with their arm and clock

    Scenario: the README's launch-ready and blocked cells match what the harness does
      Given a fresh job directory
      When the harness is launched for all fourteen registered cells with a fake runner that always succeeds
      Then every cell the README calls launch-ready is "succeeded"
      And every cell the README calls blocked is "unavailable"

    Scenario: the README's pair, window and veto policy match every generated cell config
      Given a fresh job directory
      When the harness is launched for all fourteen registered cells with a fake runner that always succeeds
      Then every cell config has pair "EURUSD", window "2016-03-01" to "2017-02-28" and close_on_veto false
      And the README states pair "EUR/USD", window "2016-03-01..2017-02-28" and close_on_veto false
      And every time-exit cell config registers min_hold_bars 4 and the A-plan config registers 0
      And the README states a horizon of N=4 and min_hold_bars 4
      And the README's constant-direction rows and execution costs match every generated config

    Scenario: the job directory carries a byte-for-byte copy of the README
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then the job directory's README is a byte-for-byte copy of the registration README

  Rule: Selection semantics

    Scenario: no cell selection launches all fourteen registered cells, returned in sorted order
      Given a fresh job directory
      When the harness is launched for all fourteen registered cells with a fake runner that always succeeds
      Then the launch returned fourteen statuses in sorted cell id order
      And 6 cells are "succeeded" and 8 cells are "unavailable"

    Scenario: an empty cell selection launches nothing
      Given a fresh job directory
      When the harness is launched for no cells with a fake runner that always succeeds
      Then the launch returned no statuses
      And the fake runner was never called

    Scenario: the returned statuses follow sorted cell id order, not the request order
      Given a fresh job directory
      When the harness is launched for cells "m-only-h1" and "always-long-h1" with a fake runner that always succeeds
      Then the launch returned statuses for "always-long-h1" then "m-only-h1"

    Scenario: a rerun id outside the requested cells is refused before anything is written
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with rerun of "always-long-h1"
      Then the launch is refused naming the unregistered id "always-long-h1"
      And no attempt file exists for any cell

    Scenario: a rerun id that is not a registered cell is refused
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with rerun of "zzz-h1"
      Then the launch is refused naming the unregistered id "zzz-h1"

    Scenario: a concurrency cap below one is refused before anything is written
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a concurrency cap of 0
      Then the launch is refused with "--max-concurrent must be >= 1"
      And the job directory was not created

  Rule: A generator that drifts from the registration is refused

    Scenario: a generator emitting an unregistered cell id is refused
      Given a fresh job directory
      And a generator that also emits a cell "zzz-h1"
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then the launch is refused naming the unregistered id "zzz-h1"

    Scenario: a generator omitting a registered cell id is refused
      Given a fresh job directory
      And a generator that omits the cell "a-h1"
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then the launch is refused naming the unregistered id "a-h1"

    Scenario: a sibling script that cannot be loaded is refused
      Then loading the sibling script "notes.txt" is refused

  Rule: Bounded concurrency

    Scenario: the concurrency cap is both honoured and used
      Given a fresh job directory
      When the harness is launched for four news-free cells with a concurrency cap of 2 and a slow runner
      Then at most 2 cells ran at the same time and 2 ran together

  Rule: The data root is passed to the population gate

    Scenario: the data root defaults from the backtest config
      Given a fresh job directory
      And a recording population preflight
      And the backtest config names data root "/configured/root"
      When the harness is launched for cell id "m-only-h1" with the default data root
      Then the preflight was given data root "/configured/root"

    Scenario: an explicit data root wins over the backtest config
      Given a fresh job directory
      And a recording population preflight
      And the backtest config names data root "/configured/root"
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then the preflight was given the explicit data root

    Scenario: a resume with every cell already attempted asks the real gate about no cells
      Given a fresh job directory
      And the harness has already launched cell id "m-only-h1" with a fake runner that always succeeds
      And the real population preflight
      When the harness is launched again for cell id "m-only-h1" with a fake runner that always exits 1
      Then the launch does not raise
      And the fake runner was never called

  Rule: The real population gate checks every month of every requested clock (CC-24)

    Scenario: a gate over no cells passes
      Then the real population gate passes over no cells

    Scenario Outline: a missing monthly partition is a hard failure naming the clock and month
      Given a data root holding every M1 monthly partition except "<month>"
      Then the real population gate over both clocks fails naming clock 60 and month "<month>"

      Examples:
        | month   |
        | 2016-03 |
        | 2016-07 |
        | 2016-12 |
        | 2017-02 |

    Scenario: a gate over the H4 clock alone names clock 240 for a missing month
      Given a data root holding every M1 monthly partition except "2017-02"
      Then the real population gate over the H4 clock alone fails naming clock 240 and month "2017-02"

    Scenario: a data root holding every M1 monthly partition passes for both clocks
      Given a data root holding every M1 monthly partition except "none"
      Then the real population gate over both clocks passes
      And the real population gate over the H4 clock alone passes

    Scenario: an empty data root fails on the first study month
      Given a fresh job directory
      Then the real population gate over both clocks fails naming clock 60 and month "2016-03"

    Scenario Outline: the expected partition is the storage layout's real M1 price partition
      Then the partition expected for pair "<pair>", clock <clock> and month "<month>" is the layout's forex m1 price path

      Examples:
        | pair   | clock | month   |
        | EURUSD | 60    | 2016-03 |
        | EURUSD | 240   | 2017-02 |
        | GBPUSD | 60    | 2016-11 |

    Scenario Outline: cells that disagree on pair or window are a registration bug
      Then the real population gate refuses cells that differ in <difference>

      Examples:
        | difference   |
        | pair         |
        | window start |
        | window end   |

  Rule: Month enumeration for the population gate

    Scenario Outline: every calendar month touching the window is listed with its exact bounds
      Then the months between "<start>" and "<end>" are "<months>"

      Examples:
        | start      | end        | months                                                                                       |
        | 2016-03-01 | 2016-03-31 | 2016-03:2016-03-01:2016-03-31                                                                |
        | 2016-03-15 | 2016-05-02 | 2016-03:2016-03-01:2016-03-31,2016-04:2016-04-01:2016-04-30,2016-05:2016-05-01:2016-05-31    |
        | 2016-11-20 | 2017-02-01 | 2016-11:2016-11-01:2016-11-30,2016-12:2016-12-01:2016-12-31,2017-01:2017-01-01:2017-01-31,2017-02:2017-02-01:2017-02-28 |
        | 2020-02-10 | 2020-03-01 | 2020-02:2020-02-01:2020-02-29,2020-03:2020-03-01:2020-03-31                                  |

  Rule: The launch command is the exact algo-backtest run contract

    Scenario: the constructed argv, working directory and timeout are exactly the contract
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h4" with a timeout of 42 seconds
      Then the recorded command for "m-only-h4" is exactly the algo-backtest run contract with timeout 42
      And the fake runner was called from the suite directory with timeout 42

  Rule: Every attempt is recorded before, during and after the child runs (CC-32)

    Scenario: a running cell already has its command and a running status on disk
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that inspects its own record
      Then the runner saw a running status and a command record while the child was running
      And "m-only-h1"'s status is "succeeded"

    Scenario: a launched cell records the source revision, code hashes and timestamps
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then "m-only-h1"'s command and status both record the suite's git revision
      And "m-only-h1"'s command record holds the SHA-256 of the harness, generator and preflight sources
      And "m-only-h1"'s status has a start time and a later-or-equal finish time

    Scenario: the run log holds the child's combined output
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that always succeeds
      Then "m-only-h1"'s run log holds exactly "boom\n"

    Scenario Outline: the terminal status carries the exit code and the reason
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner exiting <code>
      Then "m-only-h1"'s status is "<state>"
      And "m-only-h1"'s recorded reason is <reason>

      Examples:
        | code | state     | reason             |
        | 0    | succeeded | null               |
        | 1    | failed    | child exited 1     |
        | -9   | failed    | child exited -9    |

    Scenario: a runner that raises is recorded as a failure with its output in the log
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner that raises "kaput"
      Then "m-only-h1"'s status is "failed"
      And "m-only-h1"'s recorded exit code is 1
      And "m-only-h1"'s run log mentions "runner raised RuntimeError('kaput')"

    Scenario Outline: the child's results directory is parsed from its own output
      Given a fresh job directory
      When the harness is launched for cell id "m-only-h1" with a fake runner printing "<output>"
      Then "m-only-h1"'s recorded results directory is <results>

      Examples:
        | output                                   | results        |
        | results=/runs/one                        | /runs/one      |
        | INFO done\nresults=/runs/two extra words | /runs/two      |
        | prefix results=/runs/three               | /runs/three    |
        | no marker here                           | null           |

    Scenario: an unavailable cell records why, with no start or finish time
      Given a fresh job directory
      When the harness is launched for cell id "a-h1" with a fake runner that always succeeds
      Then "a-h1"'s status is "unavailable"
      And "a-h1"'s recorded reason is no availability provenance sidecar for 2016-03
      And "a-h1" has no start time, no finish time and no source revision

    Scenario: a status file that is not a JSON object is refused on resume
      Given a fresh job directory
      And the harness has already launched cell id "m-only-h1" with a fake runner that always succeeds
      And the status file for "m-only-h1" holds a JSON list
      When the harness is launched again for cell id "m-only-h1" with a fake runner that always exits 1
      Then the launch is refused with "expected an object"

  Rule: The real child runner reports every outcome as a record, never an exception

    Scenario Outline: the real runner maps spawn, exit and timeout outcomes to exit codes
      Then the real runner running "<behaviour>" reports exit code <code> and output containing "<text>"

      Examples:
        | behaviour     | code | text                  |
        | prints both   | 0    | out-line              |
        | prints both   | 0    | err-line              |
        | exits 3       | 3    | none                  |
        | missing exe   | 127  | cannot start child    |
        | overruns      | 124  | exceeded 1s           |
        | shows cwd     | 0    | cwd-ok                |

  Rule: The source revision is None outside a git checkout

    Scenario Outline: the git revision helper is None when git cannot answer
      Then the git revision for <situation> is None

      Examples:
        | situation                 |
        | a directory outside git   |
        | a machine without git     |

  Rule: The command-line entry point

    Scenario: the CLI defaults to the registered caps and every cell
      Then running the CLI with "--job-dir some/job" forwards the defaults

    Scenario: the CLI forwards every explicit argument
      Then running the CLI with every explicit argument forwards each one

    Scenario Outline: the CLI exit code and output reflect the launch outcome
      Then the CLI against a launcher that <outcome> exits <code> and prints "<line>"

      Examples:
        | outcome                    | code | line                                  |
        | reports every cell success | 0    | m-only-h1: succeeded (exit_code=0)    |
        | reports one cell failed    | 1    | always-long-h1: failed (exit_code=1)  |
        | refuses the launch         | 2    | run_cells: kaput                      |
