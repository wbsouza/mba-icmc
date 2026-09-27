Feature: End-of-run broker statement, equity chart and equity CSV
  Every simulation ends with a retail-FX-style account statement (statement.md), an
  equity chart (equity.png) and the chart's own series as equity.csv (time, equity,
  drawdown_pct — the input of `algo-analyze equity-curves`), all built purely from the
  run directory's artifacts: run.json,
  trades.json, LEAN's result JSON and its order-events sibling, plus strategy-config.json,
  strategy-provenance.json and trade-plans.json when present. Nothing is fabricated: a
  missing optional artifact is stated as absent, a missing required one fails fast
  naming the file and key.

  Background:
    Given a run directory for strategy "baseline" on "EURUSD" from "2015-09-01" to "2015-09-30"
    And the engine reports start equity 10000.00 and end equity 10000.00
    And the engine equity chart rows
      | unix_seconds | close    |
      | 1441065600   | 10000.00 |

  Rule: Closed transactions mirror the trade ledger, direction 0 = buy and 1 = sell

    Scenario Outline: a closed trade becomes one statement row
      Given the strategy config sets capital_mgmt.lot_notional_units to <lot_units>
      And a closed trade with orders 1,2 direction <direction> quantity <quantity> entry <entry> exit <exit> profit <profit> fees <fees>
      And order 1 filled as "<fill_side>" for <fill_quantity> units
      When I build the statement
      Then closed transaction 1 shows ticket 1, type "<type>", lots "<lots>", item "EURUSD"
      And closed transaction 1 shows open price <entry>, close price <exit>, commission "<commission>", swap "0.00", P/L "<pl>"
      And closed transaction 1 shows open time "2015.09.01 10:00" and close time "2015.09.01 10:10"

      Examples:
        | lot_units | direction | quantity | entry   | exit    | profit  | fees | fill_side | fill_quantity | type | lots | commission | pl      |
        | 100000    | 0         | 44094    | 1.13115 | 1.13129 | 6.17    | 0.0  | buy       | 44094         | buy  | 0.44 | 0.00       | 6.17    |
        | 100000    | 1         | 45896    | 1.08668 | 1.08645 | 10.56   | 0.0  | sell      | -45896        | sell | 0.46 | 0.00       | 10.56   |
        | 100000    | 0         | 250000   | 1.10007 | 1.09807 | -500.00 | 7.5  | buy       | 250000        | buy  | 2.50 | -7.50      | -500.00 |
        | absent    | 1         | 45896    | 1.08668 | 1.08645 | 10.56   | 0.0  | sell      | -45896        | sell | —    | 0.00       | 10.56   |

    Scenario Outline: lots are absent when the strategy config records no lot size (<case>)
      Given the strategy config sets <path> to <value>
      And a closed trade with orders 1,2 direction 0 quantity 44094 entry 1.13115 exit 1.13129 profit 6.17 fees 0.0
      And order 1 filled as "buy" for 44094 units
      When I build the statement
      Then closed transaction 1 shows ticket 1, type "buy", lots "—", item "EURUSD"

      Examples:
        | case                          | path                        | value |
        | no capital_mgmt section       | meta_learner.regime_gate    | false |
        | capital_mgmt without lot size | capital_mgmt.risk_per_trade | 0.03  |

    Scenario Outline: a non-positive lot size in the strategy config is rejected (<lot_units>)
      Given the strategy config sets capital_mgmt.lot_notional_units to <lot_units>
      And a closed trade with orders 1,2 direction 0 quantity 10000 entry 1.1 exit 1.2 profit 10 fees 0
      And order 1 filled as "buy" for 10000 units
      When I build the statement expecting failure
      Then the failure names both "lot_notional_units" and "<lot_units>"

      Examples:
        | lot_units |
        | 0         |
        | -100000   |

    Scenario Outline: a ledger trade whose entry order never filled is an inconsistent run (order <filled_order> filled)
      Given a closed trade with orders 1,2 direction 0 quantity 1000 entry 1.1 exit 1.2 profit 100 fees 0
      And order <filled_order> filled as "buy" for 1000 units
      When I build the statement expecting failure
      Then the failure names both "no fill event for order 1" and "main-order-events.json"

      Examples:
        | filled_order |
        | 2            |
        | 3            |

    Scenario Outline: a malformed ledger <field> is rejected naming it (<value>)
      Given a closed trade with orders 1,2 whose <field> is <value>
      When I build the statement expecting failure
      Then the failure names both "<field>" and "<value>"

      Examples:
        | field     | value         |
        | duration  | 14            |
        | duration  | 00:xx:00      |
        | entryTime | yesterday-ish |
        | exitTime  | 2015-13-45    |

    Scenario: a trade whose ledger direction contradicts its entry fill is rejected
      Given a closed trade with orders 1,2 direction 0 quantity 1000 entry 1.1 exit 1.2 profit 100 fees 0
      And order 1 filled as "sell" for -1000 units
      When I build the statement expecting failure
      Then the failure names both "trades.json" and "direction"

    Scenario: an unknown ledger direction is rejected, not guessed
      Given a closed trade with orders 1,2 direction 2 quantity 1000 entry 1.1 exit 1.2 profit 100 fees 0
      And order 1 filled as "buy" for 1000 units
      When I build the statement expecting failure
      Then the failure names both "trades.json" and "direction"

    Scenario: the totals row sums commission, swap and P/L over every closed trade
      Given the closed trades
        | orders | direction | quantity | entry   | exit    | profit  | fees |
        | 1,2    | 0         | 10000    | 1.10000 | 1.10100 | 10.00   | 1.0  |
        | 3,4    | 1         | 10000    | 1.10200 | 1.10300 | -10.00  | 1.0  |
        | 5,6    | 0         | 20000    | 1.10000 | 1.10500 | 100.00  | 2.0  |
      When I build the statement
      Then the statement lists 3 closed transactions
      And the totals row shows commission "-4.00", swap "0.00" and P/L "100.00"
      And the closed transactions section states "Deposit/Withdrawal: 0.00    Credit Facility: 0.00    Closed Trade P/L: 96.00"

    Scenario: closed transactions are listed in open-time order, whatever the ledger order
      Given the closed trades
        | orders | open_time            | direction | quantity | entry   | exit    | profit | fees |
        | 5,6    | 2015-09-03T09:00:00Z | 0         | 10000    | 1.10000 | 1.10100 | 10.00  | 0.0  |
        | 1,2    | 2015-09-01T09:00:00Z | 0         | 10000    | 1.10000 | 1.10100 | 10.00  | 0.0  |
        | 3,4    | 2015-09-02T09:00:00Z | 1         | 10000    | 1.10200 | 1.10300 | -10.00 | 0.0  |
      When I build the statement
      Then the closed transaction tickets are 1, 3, 5

    Scenario: the header line names the account, the strategy and the period end
      When I build the statement
      Then the header line is "A/C No: 20260927T000000-deadbeef   Name: baseline / EURUSD   2015.09.01 00:00"
      And the closed transactions table has the columns "Ticket | Open Time | Type | Lots | Item | Price | S / L | T / P | Close Time | Price | Commission | R/O Swap | Trade P/L"

    Scenario Outline: prices are printed at the quote precision the recorded prices carry
      When I derive the price precision of <prices>
      Then the price precision is <decimals>

      Examples:
        | prices                 | decimals |
        | 1.08668,1.1            | 5        |
        | 120.123,119.5          | 3        |
        | 100,101                | 0        |

  Rule: The A/C summary is arithmetic over the artifacts

    Scenario Outline: balance and equity follow from the start deposit, closed P/L and floating P/L
      Given the engine reports start equity <start> and end equity <end>
      And the closed trades
        | orders | direction | quantity | entry | exit | profit   | fees   |
        | 1,2    | 0         | 10000    | 1.1   | 1.2  | <profit> | <fees> |
      And the engine runtime statistics report holdings "<holdings>" and unrealized "<unrealized>"
      And order 1 filled as "buy" for 10000 units
      And order 2 filled as "sell" for <exit_units> units
      When I build the statement
      Then the A/C summary shows previous ledger balance "<start_fmt>", closed trade P/L "<closed>", balance "<balance>", floating P/L "<floating>" and equity "<equity>"
      And the A/C summary shows deposit/withdrawal "0.00" and total credit facility "0.00"

      Examples:
        | start    | end      | profit  | fees | holdings  | unrealized | exit_units | start_fmt | closed  | balance   | floating | equity    |
        | 10000.00 | 10250.00 | 250.00  | 0.0  | $0.00     | $0.00      | -10000     | 10,000.00 | 250.00  | 10,250.00 | 0.00     | 10,250.00 |
        | 10000.00 | 9700.00  | -295.00 | 5.0  | $0.00     | $0.00      | -10000     | 10,000.00 | -300.00 | 9,700.00  | 0.00     | 9,700.00  |
        | 100000   | 100011.9 | 11.93   | 0.0  | $5,000.00 | $-12.50    | -5000      | 100,000.00| 11.93   | 100,011.93| -12.50   | 99,999.43 |

    Scenario: the engine-reported equity is printed next to the computed one
      Given the engine runtime statistics report equity "$10,011.93"
      When I build the statement
      Then the A/C summary shows engine-reported equity "10,011.93"

    Scenario: the A/C summary is the broker's two-column block
      When I build the statement
      Then the A/C summary block rows are
        | Previous Ledger Balance | 10,000.00 | Floating P/L          | 0.00      |
        | Closed Trade P/L        | 0.00      | Total Credit Facility | 0.00      |
        | Deposit/Withdrawal      | 0.00      | Equity                | 10,000.00 |
        | Balance                 | 10,000.00 | Margin Requirement    | 0.00      |
        |                         |           | Available Margin      | 10,000.00 |

    Scenario Outline: margin requirement is zero when flat, else the engine's current sample or n/a
      Given the engine runtime statistics report holdings "<holdings>" and unrealized "<unrealized>"
      And <position>
      And the portfolio margin chart is <margin_chart>
      When I build the statement
      Then the A/C summary shows margin requirement "<requirement>" and available margin "<available>"

      Examples:
        | holdings  | unrealized | position                                | margin_chart                                 | requirement | available |
        | $0.00     | $0.00      | no order ever filled                    | at 12.5 percent sampled after the last fill  | 0.00        | 10,000.00 |
        | $5,433.40 | $-12.50    | order 7 filled as "sell" for -5000 units | absent                                       | n/a         | n/a       |
        | $5,433.40 | $-12.50    | order 7 filled as "sell" for -5000 units | empty                                        | n/a         | n/a       |
        | $5,433.40 | $-12.50    | order 7 filled as "sell" for -5000 units | at 12.5 percent sampled after the last fill  | 1,248.44    | 8,739.06  |
        | $5,433.40 | $-12.50    | order 7 filled as "sell" for -5000 units | at 12.5 percent sampled before the last fill | n/a         | n/a       |

    Scenario Outline: engine holdings with no open position are an inconsistent run (<holdings>)
      Given the engine runtime statistics report holdings "<holdings>" and unrealized "$0.00"
      And no order ever filled
      When I build the statement expecting failure
      Then the failure names both "Holdings" and "net to zero"

      Examples:
        | holdings   |
        | $5,000.00  |
        | $-5,000.00 |

  Rule: Trade plans are joined by entry order id and never fabricated

    Scenario: stop and target levels come from the recorded trade plan
      Given the closed trades
        | orders | direction | quantity | entry   | exit    | profit | fees |
        | 1,2    | 0         | 10000    | 1.10000 | 1.10100 | 10.00  | 0.0  |
        | 3,4    | 1         | 10000    | 1.10200 | 1.10300 | -10.00 | 0.0  |
      And the trade plans
        | entry_order_id | direction | stop_loss | take_profits    |
        | 1              | buy       | 1.09812   | 1.10234,1.10456 |
      When I build the statement
      Then closed transaction 1 shows S/L "1.09812" and T/P "1.10234 / 1.10456"
      And closed transaction 2 shows S/L "—" and T/P "—"
      And the statement does not say "no trade plan recorded for this run"

    Scenario: without trade-plans.json the S/L and T/P columns are explicitly absent
      Given a closed trade with orders 1,2 direction 0 quantity 10000 entry 1.1 exit 1.2 profit 10 fees 0
      And order 1 filled as "buy" for 10000 units
      When I build the statement
      Then closed transaction 1 shows S/L "—" and T/P "—"
      And the statement says "no trade plan recorded for this run"

  Rule: Open trades and working orders reflect the end-of-run position and order book

    Scenario: a flat account lists no open trades and no working orders
      When I build the statement
      Then the open trades section says "No transactions"
      And the working orders section says "No transactions"

    Scenario Outline: a position still open at the end is listed with its floating P/L
      Given the strategy config sets capital_mgmt.lot_notional_units to 100000
      And the engine account currency is "<account_currency>"
      And the engine runtime statistics report holdings "$5,433.40" and unrealized "$-12.50"
      And order 7 filled as "sell" for -5000 units at 1.10012
      When I build the statement
      Then the open trades section lists ticket 7 opened "2015.09.01 10:00" of type "sell", lots "0.05", price "1.10012", current price "<current>", P/L "-12.50"
      And the open trades section states "Floating P/L: -12.50"

      Examples:
        | account_currency | current |
        | USD              | 1.08668 |
        | EUR              | —       |

    Scenario: a stop order still pending at the end is a working order
      Given the strategy config sets capital_mgmt.lot_notional_units to 100000
      And order 9 was submitted as "sell" for -10000 units and never filled
      And the engine order book prices order 9 at stop 1.09512
      When I build the statement
      Then the working orders section lists ticket 9 opened "2015.09.01 10:00" of type "sell", lots "0.10", price "1.09512", market price "—"

    Scenario Outline: a working order's price is the engine's stop or limit, absent otherwise (<case>)
      Given the strategy config sets capital_mgmt.lot_notional_units to 100000
      And order 9 was submitted as "sell" for -10000 units and never filled
      And the engine order book <book>
      When I build the statement
      Then the working orders section lists ticket 9 opened "2015.09.01 10:00" of type "sell", lots "0.10", price "<price>", market price "—"

      Examples:
        | case                   | book                            | price   |
        | limit order            | prices order 9 at limit 1.10512 | 1.10512 |
        | market order, no price | records order 9 without a price | —       |
        | order not in the book  | records no order 9              | —       |

    Scenario: an order the engine rejected is not a working order
      Given order 9 was submitted as "sell" for -10000 units and then marked "invalid"
      When I build the statement
      Then the working orders section says "No transactions"

    Scenario: a run with closed trades but no order-events file is rejected
      Given a closed trade with orders 1,2 direction 0 quantity 10000 entry 1.1 exit 1.2 profit 10 fees 0
      And the order-events file is missing
      When I build the statement expecting failure
      Then the failure names "main-order-events.json"

  Rule: Equity and drawdown series are read from the engine's equity chart

    Scenario: the equity series keeps each candle's close in UTC order
      Given the engine equity chart rows
        | unix_seconds | close    |
        | 1441065600   | 10000.00 |
        | 1441065900   | 10010.00 |
        | 1441066200   | 9990.00  |
      When I read the equity series
      Then the equity series is
        | time                      | equity   |
        | 2015-09-01T00:00:00+00:00 | 10000.00 |
        | 2015-09-01T00:05:00+00:00 | 10010.00 |
        | 2015-09-01T00:10:00+00:00 | 9990.00  |

    Scenario Outline: drawdown is the percentage below the running peak
      When I compute drawdowns for the equity values <equity>
      Then the drawdowns are <drawdowns>

      Examples:
        | equity                        | drawdowns              |
        | 100,110,99,120,90             | 0,0,10,0,25            |
        | 100,100,100                   | 0,0,0                  |
        | 50,25                         | 0,50                   |

    Scenario Outline: a drawdown is undefined until equity is positive (<equity>)
      When computing drawdowns for the equity values <equity> fails
      Then the failure names "positive"

      Examples:
        | equity |
        | 0,10   |
        | -5,5   |

    Scenario: equity rows pair each sample's ISO-8601 UTC time with its equity and drawdown
      Given the engine equity chart rows
        | unix_seconds | close    |
        | 1441065600   | 10000.00 |
        | 1441065900   | 10100.00 |
        | 1441066200   | 9999.00  |
      When I build the equity rows
      Then the equity rows are
        | time                      | equity   | drawdown_pct |
        | 2015-09-01T00:00:00+00:00 | 10000.00 | 0.0          |
        | 2015-09-01T00:05:00+00:00 | 10100.00 | 0.0          |
        | 2015-09-01T00:10:00+00:00 | 9999.00  | 1.0          |
      And the equity CSV text is
        """
        time,equity,drawdown_pct
        2015-09-01T00:00:00+00:00,10000.0,0.0
        2015-09-01T00:05:00+00:00,10100.0,0.0
        2015-09-01T00:10:00+00:00,9999.0,1.0
        """

    Scenario: a result without the Strategy Equity chart is rejected
      Given the engine result has no equity chart
      When I build the statement expecting failure
      Then the failure names both "main.json" and "Strategy Equity"

  Rule: Performance and parameters are quoted with their provenance

    Scenario: median holding time is computed from the ledger durations
      Given the closed trades with durations
        | orders | duration   |
        | 1,2    | 00:14:00   |
        | 3,4    | 1.02:00:00 |
        | 5,6    | 00:09:00   |
      When I build the statement
      Then the performance section shows median holding "14.0" minutes and trades "3"

    Scenario: every strategy parameter is listed with the config.yaml that set it
      Given the strategy config sets capital_mgmt.lot_notional_units to 100000
      And the strategy config sets meta_learner.regime_gate to false
      And the strategy provenance maps "capital_mgmt.lot_notional_units" to "baseline/config.yaml"
      And the run params include "cash" = "10000"
      When I build the statement
      Then the parameters table has row "capital_mgmt.lot_notional_units" = "100000" from "baseline/config.yaml"
      And the parameters table has row "meta_learner.regime_gate" = "false" from "unknown"
      And the parameters table has row "cash" = "10000" from "--param"

    Scenario: a code-registered strategy without strategy-config.json says so
      Given the run params include "size" = "0.5"
      When I build the statement
      Then the statement says "no strategy-config.json recorded for this run"
      And the parameters table has row "size" = "0.5" from "--param"

  Rule: The statement command regenerates all three files for an existing run

    Scenario: the command writes statement.md, equity.png and equity.csv into the run directory
      Given a closed trade with orders 1,2 direction 0 quantity 10000 entry 1.1 exit 1.2 profit 10 fees 0
      And order 1 filled as "buy" for 10000 units
      When I run the statement command on that run directory
      Then the statement command exits with code 0
      And the run directory contains "statement.md" and "equity.png"
      And the run directory's "equity.csv" has the header "time,equity,drawdown_pct" and 1 data row
      And the output prints the A/C summary balance "10,010.00" and all three file paths

    Scenario: --out redirects all three files to another directory
      When I run the statement command on that run directory with an --out directory
      Then the statement command exits with code 0
      And the --out directory contains "statement.md" and "equity.png"
      And the --out directory contains "equity.csv" and "equity.png"

    Scenario Outline: a missing required artifact fails the command naming the file
      Given the run directory lacks "<artifact>"
      When I run the statement command on that run directory
      Then the statement command exits with code 2
      And the output names "<artifact>"

      Examples:
        | artifact    |
        | run.json    |
        | trades.json |
        | main.json   |

    Scenario: a corrupt artifact fails the command naming the file
      Given the run directory's "trades.json" is corrupt
      When I run the statement command on that run directory
      Then the statement command exits with code 2
      And the output names "trades.json"

  Rule: report.html is a self-contained dashboard of the same numbers

    Scenario Outline: the account KPI cards repeat the A/C summary
      Given the engine reports start equity <start> and end equity <start>
      And the strategy config sets capital_mgmt.lot_notional_units to 100000
      And the strategy config sets capital_mgmt.assumed_leverage to <leverage>
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit   | fees |
        | 1,2    | 0         | 10000    | 1.10000 | 1.10100 | <profit> | 0.0  |
      When I build the report
      Then the report KPI "Account Balance" is "<balance>"
      And the report KPI "Equity" is "<balance>" with note "<note>"
      And the report KPI "Floating P/L" is "0.00"
      And the report KPI "Margin Used" is "0.00" with note "0.00% of equity"
      And the report KPI "Free Margin" is "<balance>"
      And the report KPI "Leverage" is "<lev_label>"
      And the report KPI "Total Return %" is "<total_return>"

      Examples:
        | start    | leverage | profit  | balance   | note               | lev_label | total_return |
        | 10000.00 | 30       | 250.00  | 10,250.00 | +2.50% since start | 1:30      | +2.50%       |
        | 10000.00 | absent   | -100.00 | 9,900.00  | -1.00% since start | n/a       | -1.00%       |

    Scenario Outline: profit factor is gross profit over gross loss, n/a without a loss
      Given the closed trades
        | orders | direction | quantity | entry | exit | profit    | fees |
        | 1,2    | 0         | 10000    | 1.1   | 1.2  | <profit1> | 0.0  |
        | 3,4    | 0         | 10000    | 1.1   | 1.2  | <profit2> | 0.0  |
        | 5,6    | 0         | 10000    | 1.1   | 1.2  | <profit3> | 0.0  |
      When I build the report
      Then the report KPI "Profit Factor" is "<factor>"
      And the report KPI "Total Trades" is "3"

      Examples:
        | profit1 | profit2 | profit3 | factor |
        | 100.00  | -50.00  | 30.00   | 2.60   |
        | 100.00  | 50.00   | 30.00   | n/a    |
        | -100.00 | -50.00  | 0.00    | 0.00   |

    Scenario: monthly returns chain each month from the previous month's close
      Given the engine equity chart rows
        | unix_seconds | close    |
        | 1441065600   | 10000.00 |
        | 1443571200   | 10200.00 |
        | 1443657600   | 10100.00 |
        | 1446249600   | 10403.00 |
      And the closed trades
        | orders | open_time            | close_time           | direction | quantity | entry | exit | profit | fees |
        | 1,2    | 2015-09-05T09:00:00Z | 2015-09-05T10:00:00Z | 0         | 10000    | 1.1   | 1.2  | 100.00 | 0.0  |
        | 3,4    | 2015-09-20T09:00:00Z | 2015-09-20T10:00:00Z | 0         | 10000    | 1.1   | 1.2  | 100.00 | 0.0  |
        | 5,6    | 2015-10-10T09:00:00Z | 2015-10-10T10:00:00Z | 0         | 10000    | 1.1   | 1.2  | 203.00 | 0.0  |
      When I build the report
      Then the monthly returns are
        | month   | start_equity | end_equity | return_pct | trades |
        | 2015-09 | 10,000.00    | 10,200.00  | +2.00%     | 2      |
        | 2015-10 | 10,200.00    | 10,403.00  | +1.99%     | 1      |
      And the report KPI "Max Drawdown %" is "0.98%"

    Scenario Outline: the SVG path helper maps a series onto the chart box
      When I build the SVG path for the points <points> in a <width> by <height> box
      Then the SVG path is "<path>"

      Examples:
        | points           | width | height | path                            |
        | 0:100,1:110,2:90 | 100   | 50     | M0.0,25.0 L50.0,0.0 L100.0,50.0 |
        | 0:100,1:100      | 100   | 50     | M0.0,25.0 L100.0,25.0           |
        | 5:42             | 100   | 50     | M0.0,25.0                       |

    Scenario: the statement command writes report.html with the five tabs and no external resource
      Given a closed trade with orders 1,2 direction 0 quantity 10000 entry 1.1 exit 1.2 profit 10 fees 0
      And order 1 filled as "buy" for 10000 units
      When I run the statement command on that run directory
      Then the statement command exits with code 0
      And the run directory contains "report.html" and "statement.md"
      And the report contains the tab labels "Equity", "Drawdown", "Monthly Returns", "Trade History", "Parameters"
      And the report references no external resource
      And the output prints the report path
    Scenario Outline: an artifact of the wrong JSON shape fails the command naming the file (<artifact>)
      Given the run directory's "<artifact>" is replaced by the JSON document <document>
      When I run the statement command on that run directory
      Then the statement command exits with code 2
      And the output names "<artifact>"
      And the output names "must be a JSON <shape>"

      Examples:
        | artifact    | document | shape |
        | trades.json | {}       | list  |
        | run.json    | []       | dict  |
