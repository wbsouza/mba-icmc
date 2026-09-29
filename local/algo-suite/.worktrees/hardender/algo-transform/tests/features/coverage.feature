Feature: Compute the per-source monthly coverage matrix and the training-window rule
  Pure functions, no I/O (the constitution keeps testable modules separate
  from the filesystem-scanning that counts units on disk; that scanning is
  covered elsewhere, not here). Schema per algo-transform SPEC.md Sec 6.2.

  # coverage-01
  Scenario Outline: A month's coverage ratio and backtestable flag are computed from expected vs present units
    Given source <source> resolution <resolution> expects <expected> units in month <month>
    And <present> units are present
    When the coverage matrix is computed
    Then the coverage_ratio for <source> <month> is <ratio>
    And backtestable is <backtestable>
    Examples:
      | source | resolution | month   | expected | present | ratio | backtestable |
      | gdelt  | daily      | 2020-01 | 2976     | 2976    | 1.0   | true         |
      | gdelt  | daily      | 2020-02 | 2784     | 2088    | 0.75  | false        |
      | gpr    | daily      | 2020-01 | 1        | 1       | 1.0   | true         |

  # coverage-02
  Scenario: A month covered only by the daily price fallback is not backtestable
    Given source "yfinance" resolution "daily" expects 1 unit in month 2020-01
    And 1 unit is present
    When the coverage matrix is computed
    Then backtestable for "yfinance" 2020-01 is false
    # SPEC.md Sec 6.2 price fallback: daily-only price months never synthesize minute bars

  # coverage-03
  Scenario: The training window is the largest contiguous span where GDELT covers at least 80% of months
    Given the GDELT monthly coverage_ratio series:
      | month   | ratio |
      | 2015-02 | 0.9   |
      | 2015-03 | 0.85  |
      | 2015-04 | 0.5   |
      | 2015-05 | 0.95  |
      | 2015-06 | 0.9   |
      | 2015-07 | 0.92  |
    When the training window is selected
    Then the window is 2015-05 to 2015-07
    # the gap at 2015-04 (below 80%) splits the series; the longer of the two
    # contiguous >=80% runs (2015-02..03 vs 2015-05..07) wins

  # coverage-04
  Scenario: A tie in contiguous-span length is resolved by preferring the later window
    Given the GDELT monthly coverage_ratio series:
      | month   | ratio |
      | 2015-02 | 0.9   |
      | 2015-03 | 0.9   |
      | 2015-04 | 0.5   |
      | 2015-05 | 0.9   |
      | 2015-06 | 0.9   |
    When the training window is selected
    Then the window is 2015-05 to 2015-06
    # a later window reflects a more recent, more representative market
    # regime; ties must not be resolved by scan order, an implementation
    # accident
