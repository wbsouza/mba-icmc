Feature: Compare runs
  The Compare view overlays the selected runs' equity curves, each re-based so its first
  sample equals 10,000 (raw equity is scaled by 10,000 / first sample, never shifted),
  and lines their monthly returns up month by month.

  Scenario Outline: a curve is re-based so its first sample equals 10,000
    Given an equity series of <values>
    When I re-base it
    Then the re-based series is <rebased>

    Examples:
      | values              | rebased             |
      | 5000, 5500, 4750    | 10000, 11000, 9500  |
      | 10000, 10200        | 10000, 10200        |
      | 20000, 21000, 19000 | 10000, 10500, 9500  |

  Scenario: a curve starting at zero cannot be re-based
    Given an equity series of 0, 100
    When I re-base it expecting failure
    Then the re-basing fails with "cannot re-base a curve that starts at equity 0"

  Scenario: the month-by-month table lines the runs up by month
    Given run "a" with monthly returns:
      | month   | return_pct |
      | 2016-03 | 2.0        |
      | 2016-04 | -1.0       |
    And run "b" with monthly returns:
      | month   | return_pct |
      | 2016-04 | 3.0        |
      | 2016-05 | 0.5        |
    When I pivot the monthly returns
    Then the pivot rows are:
      | month   | a    | b   |
      | 2016-03 | 2.0  |     |
      | 2016-04 | -1.0 | 3.0 |
      | 2016-05 |      | 0.5 |

  Scenario: the compare view renders the fixture run's months and legend
    Given the fixture results database is open
    When I compare the runs 20260928T010000-fixture
    Then the monthly table lists the months 2016-03, 2016-04
    And the legend names "hybrid · H1 · 2016-03-01"
