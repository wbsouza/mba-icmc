Feature: Run page
  The run page shows the KPI cards, the equity curve, a month-by-month bar chart of the
  returns (green up, red down), the monthly table, the decision funnel, the parameters
  grouped by section and the trades table. Drawdown is a KPI (the maximum), not a second
  curve: a running-peak line reads like a second equity curve and hides the months.

  Background:
    Given the fixture results database is open

  Scenario: the run page plots equity and monthly returns, and no drawdown curve
    When I open the run page of "20260928T010000-fixture"
    Then the KPI "Max drawdown" reads "0.95%"
    And the charts on the page are "Equity" and "Monthly returns"
    And the monthly bars are 2016-03 +4.00% up, 2016-04 +0.48% up
    And there is no "Drawdown" heading

  Scenario Outline: monthly bars carry the sign as colour
    Given monthly returns of <returns>
    Then their bar colours are <colours>

    Examples:
      | returns          | colours        |
      | 2.0, -1.5, 0.0   | up, down, up   |
      | -0.1             | down           |

  Rule: Every trade row shows the account balance after it closed

    Scenario: the balance runs from the starting cash through the trades in closing order
      When I open the run page of "20260928T010000-fixture"
      Then the trades table shows the balance after each trade:
        | trade_id | profit  | balance   |
        | 1        | 500.00  | 10,500.00 |
        | 5        | -100.00 | 10,400.00 |

    Scenario Outline: the balance accumulates net P/L (profit minus fees) in exit order, not row order
      Given trades closed as <closes> starting from cash <cash>
      Then the balances after each trade, in row order, are <balances>

      Examples:
        | cash  | closes                                              | balances                |
        | 10000 | A exit 2016-03-02 +500 fee 0, B exit 2016-03-10 -100 fee 0 | 10500, 10400            |
        | 10000 | A exit 2016-03-10 +300 fee 2, B exit 2016-03-02 -50 fee 1  | 10247, 9949             |
        | 5000  | A exit 2016-03-02 +0 fee 0                          | 5000                    |
