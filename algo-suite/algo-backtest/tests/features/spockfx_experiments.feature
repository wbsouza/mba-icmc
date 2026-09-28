Feature: Bounded exploratory SpockFX signal experiments
  The H4 matrix is prepared without launching training or LEAN.
  Each invocation uses a new output directory and leaves market inputs untouched.

  Scenario: Four explicit H4 variants differ only in detector and volume gate
    Given the tracked SpockFX experiment setup
    When all four H4 strategy variants are resolved
    Then the variants form the disabled or talib by absent or present volume matrix
    And each variant preserves the Dragon08 risk and exit mapping
    And every variant declares the research assumptions and exploratory windows

  Scenario: Hybrid counterparts preserve all shared baseline assumptions
    Given the tracked SpockFX experiment setup
    When baseline and hybrid counterparts are resolved
    Then each hybrid differs only by F4 news context and the F7 news family

  Scenario: Explicit hybrid mode prepares only four hybrid runs
    Given the tracked SpockFX experiment setup
    And explicit temporary input and SpockFX source directories
    And all required hybrid news sources
    When a fresh hybrid experiment output directory is prepared
    Then exactly four hybrid runs use the hybrid trainer and exhaustive source archives
    And no training or backtest process was launched
    And the input files are unchanged

  Scenario: Missing hybrid news prevents preparation
    Given the tracked SpockFX experiment setup
    And explicit temporary input and SpockFX source directories
    When hybrid preparation is requested without news sources
    Then preparation fails before launching a process

  Scenario: An automatic combined sweep is not a supported mode
    Given the tracked SpockFX experiment setup
    When combined experiment mode is requested
    Then preparation fails before launching a process

  Scenario: Resource budgets are explicit and archived before any child
    Given a prepared temporary SpockFX experiment
    Then the archived environment declares six LEAN slots with four CPUs and eight gigabytes each
    And training stays on the existing CPU backend with four numeric threads

  Scenario: Two workers run only a bounded pair of independent cells
    Given a temporary SpockFX experiment prepared for two workers
    When two-worker execution is observed with controlled independent cells
    Then no more than two cells overlap and all four are individually recorded

  Scenario: Parallel failure drains the current pair and skips the remaining cells
    Given a temporary SpockFX experiment prepared for two workers
    When one cell in the first pair fails with code 17
    Then both started cells finish and no second pair starts

  Scenario: Execute cannot silently alter a frozen resource plan
    Given a prepared temporary SpockFX experiment
    When execution requests two workers against the one-worker plan
    Then execution rejects the changed worker budget before launching a process

  Scenario Outline: Reject unsupported worker budgets before preparing output
    Given the tracked SpockFX experiment setup
    And explicit temporary input and SpockFX source directories
    When preparation requests worker count <workers>
    Then preparation fails before launching a process

    Examples:
      | workers |
      | 0       |
      | 3       |
      | true    |

  Scenario: Preparation archives settings before any process can launch
    Given the tracked SpockFX experiment setup
    And explicit temporary input and SpockFX source directories
    When a fresh experiment output directory is prepared
    Then each run already has resolved settings provenance hashes parameters and pending status
    And the archived commands use explicit strategy directory model output and September dates
    And no training or backtest process was launched
    And the input files are unchanged

  Scenario Outline: Refuse unsafe or incomplete preparation
    Given the tracked SpockFX experiment setup
    And explicit temporary input and SpockFX source directories
    When preparation is requested with <problem>
    Then preparation fails before launching a process

    Examples:
      | problem                 |
      | an existing output      |
      | output inside inputs    |
      | inputs inside output    |
      | missing market inputs   |
      | missing XML source      |
      | a dangling output link  |

  Scenario: Successful execution records every child exit and model hash before backtesting
    Given a prepared temporary SpockFX experiment
    When all training and backtest children succeed in the runner harness
    Then exactly four training and four backtest children ran sequentially
    And every run records success and the exact model hash
    And the input files are unchanged
    And the final immutable check passes with archived source and input hashes

  Scenario Outline: A failed child stops the experiment and preserves its exit status
    Given a prepared temporary SpockFX experiment
    When the first <stage> child exits with code 17 in the runner harness
    Then the experiment exits with code 17 and launches no later run
    And the failed run retains its settings and failure status
    And the final immutable check passes with archived source and input hashes

    Examples:
      | stage    |
      | training |
      | backtest |

  Scenario: A timed out child is a recorded failure
    Given a prepared temporary SpockFX experiment
    When the first training child times out in the runner harness
    Then the experiment exits with code 124 and launches no later run
    And the failed run retains its settings and failure status
    And the final immutable check passes with archived source and input hashes

  Scenario Outline: Mutation during a child overrides its exit and prevents later cells
    Given a prepared temporary SpockFX experiment
    When the first backtest child changes <target> and exits with code <code>
    Then the experiment exits with code 1 and launches no later run
    And the final immutable check names the changed file and both hashes

    Examples:
      | target | code |
      | input  | 0    |
      | input  | 17   |
      | source | 0    |
      | model  | 0    |

  Scenario: Each batch is checked before and after its children complete
    Given a temporary SpockFX experiment prepared for two workers
    When two-worker execution is observed with controlled independent cells
    Then each pair has parent-owned before and after immutable checks
    And the final immutable check passes with archived source and input hashes

  Scenario: A child that cannot start is a recorded failure
    Given a prepared temporary SpockFX experiment
    When the first training child cannot start in the runner harness
    Then the experiment exits with code 127 and launches no later run
    And the failed run retains its settings and failure status

  Scenario: A successful trainer must actually produce a model
    Given a prepared temporary SpockFX experiment
    When the trainer exits successfully without a model in the runner harness
    Then the experiment exits with code 1 and launches no later run
    And the failed run retains its settings and failure status

  Scenario Outline: The backtest worker separates input and output roots
    Given a prepared temporary SpockFX experiment
    When the backtest worker receives engine success <success> in the runner harness
    Then the worker passes the explicit inputs and isolated results to the production API
    And the worker reports engine success <success>
    And the input files are unchanged

    Examples:
      | success |
      | true    |
      | false   |

  Scenario: Prepared code or configuration cannot drift unnoticed
    Given a prepared temporary SpockFX experiment
    When an archived strategy is changed before execution
    Then execution refuses the changed snapshot before launching a process

  Scenario: Isolated code fingerprints still detect source changes
    Given a prepared temporary SpockFX experiment
    When a fingerprinted fixture source changes before execution
    Then execution refuses the changed snapshot before launching a process

  Scenario: Unrelated edits cannot destabilize an isolated runner scenario
    Given a prepared temporary SpockFX experiment
    When an unrelated fixture document changes after preparation
    Then the prepared fingerprint still verifies

  Scenario: Output directories cannot be executed twice
    Given a prepared temporary SpockFX experiment
    When all training and backtest children succeed in the runner harness
    And execution is requested again
    Then the second execution is rejected before launching a process
