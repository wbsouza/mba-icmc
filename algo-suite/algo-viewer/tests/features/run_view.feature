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
