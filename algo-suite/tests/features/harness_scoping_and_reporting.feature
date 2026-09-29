# Scenario: harness_scoping-01 default scope walks src/<package> and excludes __init__.py
# Scenario: harness_scoping-02 default scope excludes spikes/algos/mutants subtrees
# Scenario: harness_scoping-03 extra_paths accepts a single file
# Scenario: harness_scoping-04 extra_paths accepts a directory
# Scenario: harness_scoping-05 a tool with no src directory yields nothing
# Scenario: harness_scoping-06 MutationReport.summary scores killed/survived/errored verdicts
# Scenario: harness_scoping-07 revert_pending restores the file and clears pending state
# Scenario: harness_scoping-08 a termination signal reverts the pending file before exiting
Feature: Target-file scoping, report scoring, and interrupt-safety

  Background:
    Given an isolated fake workspace root

  Scenario: default scope walks src/<package> and excludes __init__.py
    Given a tool "widget" with source files:
      | path                    |
      | src/widget/__init__.py  |
      | src/widget/thing.py     |
      | src/widget/sub/deep.py  |
    When target files are listed for tool "widget"
    Then the listed files are:
      | path                    |
      | src/widget/sub/deep.py  |
      | src/widget/thing.py     |

  Scenario: default scope excludes spikes/algos/mutants subtrees
    Given a tool "widget" with source files:
      | path                          |
      | src/widget/thing.py           |
      | src/widget/spikes/explore.py  |
      | src/widget/algos/strategy.py  |
      | src/widget/mutants/thing.py   |
    When target files are listed for tool "widget"
    Then the listed files are:
      | path                 |
      | src/widget/thing.py  |

  Scenario: extra_paths accepts a single file
    Given a tool "widget" with source files:
      | path                  |
      | src/widget/thing.py   |
      | other/main.py         |
    When target files are listed for tool "widget" with paths "other/main.py"
    Then the listed files are:
      | path           |
      | other/main.py  |

  Scenario: extra_paths accepts a directory
    Given a tool "widget" with source files:
      | path                  |
      | src/widget/thing.py   |
      | other/main.py         |
      | other/helper.py       |
    When target files are listed for tool "widget" with paths "other"
    Then the listed files are:
      | path             |
      | other/helper.py  |
      | other/main.py    |

  Scenario: a tool with no src directory yields nothing
    Given a tool "empty" with no source directory
    When target files are listed for tool "empty"
    Then the listed files are:
      | path |

  Scenario Outline: MutationReport.summary scores killed/survived/errored verdicts
    Given a mutation report with verdicts "<verdicts>"
    When the report is summarized
    Then the summary score is <score> percent
    And the summary killed count is <killed>
    And the summary survived count is <survived>
    And the summary errored count is <errored>

    Examples:
      | verdicts                    | score | killed | survived | errored |
      | killed,killed                | 100.0 | 2      | 0        | 0       |
      | survived,survived             | 0.0   | 0      | 2        | 0       |
      | killed,killed,survived        | 66.7  | 2      | 1        | 0       |
      | killed,error,error            | 100.0 | 1      | 0        | 2       |
      |                               | 100.0 | 0      | 0        | 0       |

  Scenario: revert_pending restores the file and clears pending state
    Given a file "mod.py" containing "mutated"
    And a pending revert for "mod.py" back to "original"
    When the pending revert is applied
    Then "mod.py" contains "original"
    And no revert is pending

  Scenario: revert_pending is a no-op when nothing is pending
    Given no revert is pending
    When the pending revert is applied
    Then no revert is pending

  Scenario: a termination signal reverts the pending file before exiting
    Given a file "mod.py" containing "mutated"
    And a pending revert for "mod.py" back to "original"
    When a termination signal is handled
    Then "mod.py" contains "original"
    And the process would exit with the signal's exit code
