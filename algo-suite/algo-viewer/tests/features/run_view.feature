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

  Rule: Every trade row shows the account equity after it closed

    Scenario: the equity column runs from the starting cash through the trades in closing order
      When I open the run page of "20260928T010000-fixture"
      Then the trades table has an "Realized equity" column explained as "cash plus the net P/L of the trades closed so far"
      And the trades table shows the equity after each trade:
        | trade_id | profit  | equity    |
        | 1        | 500.00  | 10,500.00 |
        | 5        | -100.00 | 10,400.00 |

    Scenario Outline: the equity accumulates net P/L (profit minus fees) in exit order, not row order
      Given trades closed as <closes> starting from cash <cash>
      Then the equity after each trade, in row order, is <balances>

      Examples:
        | cash  | closes                                              | balances                |
        | 10000 | A exit 2016-03-02 +500 fee 0, B exit 2016-03-10 -100 fee 0 | 10500, 10400            |
        | 10000 | A exit 2016-03-10 +300 fee 2, B exit 2016-03-02 -50 fee 1  | 10247, 9949             |
        | 5000  | A exit 2016-03-02 +0 fee 0                          | 5000                    |

  Rule: Positions still open at the end of the run are shown last, and reconcile realized with final equity

    Scenario: the open trades section is the last section of the page, after the trades table
      When I open the run page of "20260928T010000-fixture"
      Then the last two sections of the page are "Trades" and "Open trades"
      And the open trades section is titled "Open trades at the end of the run"

    Scenario: the open trades section lists the statement's open trades and the KPIs split realized from floating
      When I open the run page of "20260928T010000-fixture"
      Then the KPI "Final equity" reads "10,450.00"
      And the KPI "Realized" reads "10,400.00"
      And the KPI "Floating P/L" reads "+50.00 (1 open)"
      And the open trades section lists:
        | ticket | side | lots | opened           | open_price | stop    | targets                     | mark    | floating_pl |
        | 9      | buy  | 0.50 | 2016-04-29 10:00 | 1.13000    | 1.12500 | T1 1.14000 · T2 1.15000     | 1.13100 | 50.00       |

    Scenario: a run with nothing open says so instead of showing an empty table
      Given the fixture run had no open positions
      When I open the run page of "20260928T010000-fixture"
      Then the page says "No position was open at the end of the run: realized and final equity agree."
