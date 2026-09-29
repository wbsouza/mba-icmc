Feature: Runs table
  The Runs view lists every run of the database with its job, strategy, bar size, span,
  trade count, return, max drawdown and win rate. It filters by free text and bar size,
  sorts by any column, and lets a person tick runs to compare.

  Background:
    Given these runs:
      | run_id | job     | strategy    | bar_minutes | start      | end        | closed_trades | total_return | max_drawdown | win_rate |
      | r1     | broad   | h1-atr-stop | 60          | 2016-03-01 | 2016-11-30 | 10            | -0.0614      | 0.202        | 0.27     |
      | r2     | broad   | h4-hybrid   | 240         | 2016-03-01 | 2016-11-30 | 22            | 0.081        | 0.09         | 0.45     |
      | r3     | oneyear | baseline    | 15          | 2015-09-01 | 2016-08-31 | 140           | 0.012        | 0.15         | 0.40     |

  Scenario Outline: the text filter matches the job, strategy, symbol or run id
    When I filter the runs table by "<text>"
    Then the visible run ids are <ids>

    Examples:
      | text    | ids        |
      | hyb     | r2         |
      | oneyear | r3         |
      | r1      | r1         |
      | EURUSD  | r2, r3, r1 |
      | nothing |            |

  Scenario: the bar-size filter keeps one clock
    When I choose the bar size "H1"
    Then the visible run ids are r1

  Scenario Outline: any column sorts the table
    When I sort the runs by "<column>" <direction>
    Then the visible run ids are <ids>

    Examples:
      | column | direction  | ids        |
      | Return | descending | r2, r3, r1 |
      | Return | ascending  | r1, r3, r2 |
      | Trades | ascending  | r1, r2, r3 |
      | Max DD | descending | r1, r3, r2 |

  Scenario: ticking runs enables the comparison
    Then the compare button is disabled
    When I tick runs r1 and r2
    Then the compare button is enabled
    And the toolbar reads "2 selected"
