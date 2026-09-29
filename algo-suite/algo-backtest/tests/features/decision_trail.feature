Feature: Trade decision drill-down in report.html
  report.html's Trade History expands every closed trade into how the filter chain reached
  it, built purely from the run directory: the chain's verdict at the entry bar
  (decisions.parquet — the first row whose trade_id is the trade's entry order id, or,
  failing that, the row timestamped at the entry), the plan the executor placed
  (trade-plans.json, joined by entry_order_id = trades.json orderIds[0]) and the exit (the
  trade's last order classified from LEAN's orders map — stop-market, limit target or a
  market order, "Liquidated" when the algorithm closed the position itself — plus the stop
  moves and cancel reasons the executor logged in log.txt). Nothing is invented: a trade
  without a plan or without a chain row fails fast naming the trade, and a run without the
  artifacts renders the drill-down as absent.

  Background:
    Given a chain run directory for strategy "hybrid" on "EURUSD" from "2016-03-01" to "2016-03-31"
    And the strategy config sets meta_learner theta_high 0.55, theta_low 0.45 and regime_gate false
    And the strategy config sets capital_mgmt.lot_notional_units to 100000

  Rule: A trail joins the ledger trade to its plan and to the chain row at the entry bar

    Scenario Outline: the trail carries the entry verdict, the plan, the exit and the holding time (<direction>)
      Given the chain decided "NO_TRADE" at "2016-03-22T13:00:00Z" for trade "none" with the filter results
        | filter        | recommendation | veto | reason                       | p_hat |
        | F1_trend      | SELL           | no   | trend_direction=-1.0         |       |
        | f5_risk_guard | ABSTAIN        | yes  | daily drawdown limit breached |       |
      And the chain decided "<decision>" at "2016-03-22T14:00:00Z" for trade "<entry_row_trade>" with the filter results
        | filter          | recommendation | veto | reason                       | p_hat   |
        | F1_trend        | <decision>     | no   | trend_direction=<trend>      |         |
        | F3_pattern      | ABSTAIN        | no   | no pattern detected this bar |         |
        | f7_meta_learner | <decision>     | no   | p_hat=<p_hat>                | <p_hat> |
      And the chain decided "HOLD" at "2016-03-22T15:00:00Z" for trade "<hold_row_trade>" with the filter results
        | filter          | recommendation | veto | reason       | p_hat |
        | f7_meta_learner | HOLD           | no   | p_hat=0.5000 | 0.5   |
      And the closed trades
        | orders | direction   | quantity | entry   | exit   | profit   | entry_time           | exit_time            |
        | 1,2    | <ledger>    | 53475    | 1.12254 | <exit> | <profit> | 2016-03-22T14:00:00Z | 2016-03-22T16:45:00Z |
      And the trade plans
        | entry_order_id | direction   | lots | quantity | entry_price | stop_loss | take_profits            | trail_stops                | spread_pips |
        | 1              | <direction> | 0.53 | 53475    | 1.12254     | <stop>    | 1.13026:0.5,1.13407:0.5 | 1.12645:2.17>1.12282:0.16 | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
      When I build the decision trails
      Then there is one trail per closed trade, for the tickets 1
      And the trail for ticket 1 has direction "<direction>", decision "<decision>", vetoed by "none" and p_hat <p_hat> against theta_high 0.55, theta_low 0.45, regime_gate false
      And the trail for ticket 1 lists the filters
        | filter          | recommendation | veto | reason                       |
        | F1_trend        | <decision>     | no   | trend_direction=<trend>      |
        | F3_pattern      | ABSTAIN        | no   | no pattern detected this bar |
        | f7_meta_learner | <decision>     | no   | p_hat=<p_hat>                |
      And the trail for ticket 1 plans lots 0.53, quantity 53475, entry 1.12254, stop <stop> at <stop_pips> pips, spread 1.0 pips
      And the trail for ticket 1 plans the targets "1.13026:0.5,1.13407:0.5" and the trail steps "1.12645:2.17>1.12282:0.16"
      And the trail for ticket 1 exits at "2016-03-22T16:45:00Z" price <exit> by "stop-market" via order 2 with profit <profit> after "2h 45m"

      Examples:
        | direction | ledger | decision | trend | entry_row_trade | hold_row_trade | p_hat  | stop    | stop_pips | exit    | profit  |
        | buy       | 0      | BUY      | 1.0   | 1               | 1              | 0.5525 | 1.12074 | 18.0      | 1.12053 | -107.48 |
        | sell      | 1      | SELL     | -1.0  | none            | none           | 0.41   | 1.12454 | 20.0      | 1.12300 | -24.60  |

    Scenario Outline: the exit is classified from the trade's last order and the executor's cancel reason (<label>)
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "1" with the filter results
        | filter          | recommendation | veto | reason     | p_hat |
        | f7_meta_learner | BUY            | no   | p_hat=0.60 | 0.60  |
      And the closed trades
        | orders   | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | <orders> | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits            | trail_stops               | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:0.5,1.13407:0.5 | 1.12645:2.17>1.12282:0.16 | 1.0         |
      And the engine order book
        | id | type | status | tag   |
        | 1  | 0    | 3      |       |
        | 2  | 2    | 3      |       |
        | 3  | 1    | 3      |       |
        | 4  | 1    | 3      |       |
        | 5  | 0    | 3      | <tag> |
      And the executor log records
        | time                | event      | entry   | from    | to      | reason   |
        | 2016-03-22 15:10:00 | TRAIL      | 1.12254 | 1.12074 | 1.12282 |          |
        | 2016-03-22 18:00:00 | OCO_CANCEL |         |         |         | <reason> |
      When I build the decision trails
      Then the trail for ticket 1 was closed by "<label>" via order <last>
      And the trail for ticket 1 records the trail moves "2016-03-22T15:10:00Z:1.12074>1.12282"

      Examples:
        | orders | last | tag        | reason   | label                         |
        | 1,2    | 2    |            | flat     | stop-market                   |
        | 1,3,4  | 4    |            | flat     | limit target                  |
        | 1,3,2  | 2    |            | flat     | stop-market                   |
        | 1,5    | 5    | Liquidated | reversal | market liquidation (reversal) |
        | 1,5    | 5    | Liquidated | veto     | market liquidation (veto)     |
        | 1,5    | 5    |            | flat     | market                        |

    Scenario: only stop moves inside the trade's window and at its entry price are attributed to it
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "1" with the filter results
        | filter          | recommendation | veto | reason     | p_hat |
        | f7_meta_learner | BUY            | no   | p_hat=0.60 | 0.60  |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits | trail_stops                                        | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:1.0  | 1.12645:2.17>1.12282:0.16,1.13000:4.14>1.12500:1.37 | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
      And the executor log records
        | time                | event | entry   | from    | to      | reason |
        | 2016-03-22 13:30:00 | TRAIL | 1.12254 | 1.12000 | 1.12100 |        |
        | 2016-03-22 15:10:00 | TRAIL | 1.12254 | 1.12074 | 1.12282 |        |
        | 2016-03-22 16:00:00 | TRAIL | 1.11000 | 1.10800 | 1.10900 |        |
        | 2016-03-22 17:20:00 | TRAIL | 1.12254 | 1.12282 | 1.12500 |        |
      When I build the decision trails
      Then the trail for ticket 1 records the trail moves "2016-03-22T15:10:00Z:1.12074>1.12282,2016-03-22T17:20:00Z:1.12282>1.12500"

    Scenario: without log.txt the trail states that no stop move was recorded
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "1" with the filter results
        | filter          | recommendation | veto | reason     | p_hat |
        | f7_meta_learner | BUY            | no   | p_hat=0.60 | 0.60  |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits | trail_stops | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:1.0  |             | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
      When I build the decision trails
      Then the trail for ticket 1 has no executor log

    Scenario Outline: holding time reads as days, hours and minutes
      When I format the holding time from "<entry>" to "<exit>"
      Then the holding time reads "<text>"

      Examples:
        | entry                | exit                 | text       |
        | 2016-03-22T14:00:00Z | 2016-03-22T16:45:00Z | 2h 45m     |
        | 2016-04-28T19:00:00Z | 2016-05-13T06:09:00Z | 14d 11h 9m |
        | 2016-03-22T14:00:00Z | 2016-03-22T14:38:00Z | 0h 38m     |

  Rule: A trade whose plan, chain row or closing order is missing fails fast naming it

    Scenario: a closed trade without a plan fails naming the trade
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "7" with the filter results
        | filter          | recommendation | veto | reason     | p_hat |
        | f7_meta_learner | BUY            | no   | p_hat=0.60 | 0.60  |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 7,8    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits | trail_stops | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:1.0  |             | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 7  | 0    | 3      |     |
        | 8  | 2    | 3      |     |
      When building the decision trails fails
      Then the failure reads "trade-plans.json has no plan with entry_order_id 7 for the closed trade entered at 2016-03-22T14:00:00+00:00; the executor records one per planned entry, so the run's artifacts are inconsistent — re-run the backtest"

    Scenario: a closed trade without a chain row at its entry fails naming the trade
      Given the chain decided "NO_TRADE" at "2016-03-22T13:00:00Z" for trade "none" with the filter results
        | filter   | recommendation | veto | reason               | p_hat |
        | F1_trend | SELL           | no   | trend_direction=-1.0 |       |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits | trail_stops | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:1.0  |             | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
      When building the decision trails fails
      Then the failure reads "decisions.parquet has no row for trade 1 entered at 2016-03-22T14:00:00+00:00: no row carries trade_id '1' and none is timestamped at the entry; the audit trail and trades.json disagree — re-run the backtest"

    Scenario: a closing order missing from the engine's order book fails naming the trade
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "1" with the filter results
        | filter          | recommendation | veto | reason     | p_hat |
        | f7_meta_learner | BUY            | no   | p_hat=0.60 | 0.60  |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits | trail_stops | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:1.0  |             | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
      When building the decision trails fails
      Then the failure reads "main.json orders has no order 2, the last order of closed trade 1 in trades.json; the run directory is inconsistent — re-run the backtest"

  Rule: report.html expands every closed trade into its trail without any script

    Scenario: each closed trade gets one details element naming its entry filters and its exit kind
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "1" with the filter results
        | filter          | recommendation | veto | reason             | p_hat  |
        | F1_trend        | BUY            | no   | trend_direction=1.0 |        |
        | f7_meta_learner | BUY            | no   | p_hat=0.5525       | 0.5525 |
      And the chain decided "SELL" at "2016-03-23T09:00:00Z" for trade "3" with the filter results
        | filter          | recommendation | veto | reason               | p_hat |
        | F1_trend        | SELL           | no   | trend_direction=-1.0 |       |
        | f7_meta_learner | SELL           | no   | p_hat=0.40           | 0.40  |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit  | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12053 | -107.48 | 2016-03-22T14:00:00Z | 2016-03-22T16:45:00Z |
        | 3,4    | 1         | 40000    | 1.12500 | 1.12000 | 200.00  | 2016-03-23T09:00:00Z | 2016-03-23T12:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits            | trail_stops               | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:0.5,1.13407:0.5 | 1.12645:2.17>1.12282:0.16 | 1.0         |
        | 3              | sell      | 0.40 | 40000    | 1.12500     | 1.12700   | 1.12000:1.0             |                           | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
        | 3  | 0    | 3      |     |
        | 4  | 1    | 3      |     |
      When I build the report with the decision trails
      Then the report has 2 details elements and no script element
      And the report legend names the sections "Decision at entry", "Plan" and "Exit"
      And the report trail for ticket 1 names the filters "F1_trend, f7_meta_learner" and the exit "stop-market"
      And the report trail for ticket 3 names the filters "F1_trend, f7_meta_learner" and the exit "limit target"
      And the report trail for ticket 1 shows "p̂ 0.5525 ≥ θ_high · θ_high 0.55 · θ_low 0.45 · regime gate off"
      And the report trail for ticket 3 shows "p̂ 0.4000 ≤ θ_low · θ_high 0.55 · θ_low 0.45 · regime gate off"
      And the report trail for ticket 1 shows "1.12074 (18.0 pips)"
      And the report still has the tab labels "Equity", "Drawdown", "Monthly Returns", "Trade History", "Parameters"

    Scenario: the statement command regenerates the drill-down for a run with the audit artifacts
      Given the chain decided "BUY" at "2016-03-22T14:00:00Z" for trade "1" with the filter results
        | filter          | recommendation | veto | reason     | p_hat |
        | f7_meta_learner | BUY            | no   | p_hat=0.60 | 0.60  |
      And the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the trade plans
        | entry_order_id | direction | lots | quantity | entry_price | stop_loss | take_profits | trail_stops | spread_pips |
        | 1              | buy       | 0.53 | 53475    | 1.12254     | 1.12074   | 1.13026:1.0  |             | 1.0         |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
      When I run the statement command on the run directory
      Then the statement command exits with code 0
      And the written report has 1 details elements and no script element
      And the written report states "closed by stop-market"

    Scenario: a run without the audit artifacts renders the drill-down as absent
      Given the closed trades
        | orders | direction | quantity | entry   | exit    | profit | entry_time           | exit_time            |
        | 1,2    | 0         | 53475    | 1.12254 | 1.12500 | 100.00 | 2016-03-22T14:00:00Z | 2016-03-22T18:00:00Z |
      And the engine order book
        | id | type | status | tag |
        | 1  | 0    | 3      |     |
        | 2  | 2    | 3      |     |
      When I run the statement command on the run directory
      Then the statement command exits with code 0
      And the written report has 0 details elements and no script element
      And the written report states "No decision trail: the run recorded no decisions.parquet / trade-plans.json"
