Feature: Results database from run directories
  `algo-analyze results-db build --runs-root [LABEL=]DIR ... --out results.sqlite` loads
  every finished run directory (`<runs-root>/<strategy>/<stamp>/`, finished = it has a
  run.json) into one SQLite file the browser viewer opens with sql.js. Every number comes
  from the run's own artifacts (run.json, metrics.json, trades.json, trade-plans.json,
  equity.csv, strategy-config.yaml, strategy-provenance.json, main.json's orders,
  decisions.parquet and the tagged engine log); nothing is estimated. Re-running the build
  upserts by run id, a broken artifact stops the build naming the file, and with
  --bars-root the bars from before each entry to after its exit come from the M1 bid/ask mid.

  Background:
    Given a runs root labelled "broad" under a job directory "2026-09-28-broad-window-h4/data/runs"

  Rule: Every finished run directory becomes rows in every table

    Scenario: a run with two trades fills the run, parameter, equity, monthly, trade and plan tables
      Given a finished run "20260928T010000-aaaa" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-04-30 with cash 10000
      And its metrics are total_return 0.05, sharpe 1.2, max_drawdown 0.03, hit_rate 0.5
      And its config sets:
        | key                             | value  | source               |
        | price_features.bar_minutes      | 60     | hybrid/config.yaml   |
        | meta_learner.theta_high         | 0.55   | h4-base/config.yaml |
        | capital_mgmt.lot_notional_units | 100000 | h4-base/config.yaml |
      And its engine log names model sha256 "4220696d32cfd2c60f9821a2c5944f406b7f391b68fccd155ab498459a124d9a"
      And its equity samples are:
        | time                      | equity |
        | 2016-03-01T00:00:00+00:00 | 10000  |
        | 2016-03-20T00:00:00+00:00 | 10300  |
        | 2016-03-31T00:00:00+00:00 | 10200  |
        | 2016-04-30T00:00:00+00:00 | 10500  |
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
        | 5     | sell      | 50000    | 2016-04-10T08:00:00Z | 1.12000     | 2016-04-11T08:30:00Z | 1.12500    | -250   | stop          |
      And its trade plans are:
        | order | lots | stop_loss | stop_pips | targets                 | trail_steps | spread_pips |
        | 1     | 1.0  | 1.09800   | 20        | 1.10500:0.5,1.11000:0.5 | 40:5        | 1.0         |
      When I build the results database
      Then table "runs" has 1 row
      And the run "20260928T010000-aaaa" has:
        | column        | value                                                            |
        | job           | broad                                                            |
        | strategy      | hybrid                                                           |
        | symbol        | EURUSD                                                           |
        | start         | 2016-03-01                                                       |
        | end           | 2016-04-30                                                       |
        | bar_minutes   | 60                                                               |
        | cash          | 10000.0                                                          |
        | model_sha256  | 4220696d32cfd2c60f9821a2c5944f406b7f391b68fccd155ab498459a124d9a |
        | closed_trades | 2                                                                |
        | total_return  | 0.05                                                             |
        | sharpe        | 1.2                                                              |
        | max_drawdown  | 0.03                                                             |
        | hit_rate      | 0.5                                                              |
      And the run's run_dir, statement_path and report_path point into its directory
      And table "run_parameters" has 4 rows
      And the parameter "meta_learner.theta_high" of the run is "0.55" from "h4-base/config.yaml"
      And the parameter "cash" of the run is "\"10000\"" from "--param"
      And table "equity_samples" has 4 rows
      And the monthly returns of the run are:
        | month   | start_equity | end_equity | return_pct | trades |
        | 2016-03 | 10000        | 10200      | 2.0        | 1      |
        | 2016-04 | 10200        | 10500      | 2.9411764706 | 1    |
      And the trades of the run are:
        | trade_id | direction | lots | exit_kind | holding_minutes | is_win | exit_order_type |
        | 1        | buy       | 1.0  | target    | 300             | 1      | limit           |
        | 5        | sell      | 0.5  | stop      | 1470            | 0      | stop            |
      And the trade plan of trade "1" has stop_loss 1.098, stop_pips 20, 2 targets and 1 trail step
      And table "trade_plans" has 1 row

    Scenario: the positions still open at the end of the run and the account summary come from the statement
      Given a finished run "20260928T010000-open" of strategy "news-rule" on EURUSD from 2016-03-01 to 2017-02-28 with cash 10000
      And its statement lists the open trades:
        | ticket | open_time        | type | lots | price   | stop    | targets           | mark    | profit |
        | 157    | 2016.11.10 00:00 | sell | 0.17 | 1.09191 | 1.11091 | 1.01542 / 0.97722 | 1.05693 | 587.18 |
        | 161    | 2017.02.20 08:00 | buy  | 0.10 | 1.06000 | —       | —                 | 1.05693 | -30.70 |
      And its statement's account summary is balance 10,633.10, floating P/L 556.48 and equity 11,189.58
      When I build the results database
      Then table "open_positions" has 2 rows
      And the open positions of the run are:
        | ticket | open_time                 | direction | lots | open_price | stop_loss | take_profits_json | mark_price | floating_pl |
        | 157    | 2016-11-10T00:00:00+00:00 | sell      | 0.17 | 1.09191    | 1.11091   | [1.01542, 0.97722] | 1.05693    | 587.18      |
        | 161    | 2017-02-20T08:00:00+00:00 | buy       | 0.1  | 1.06       | none      | []                | 1.05693    | -30.7       |
      And the run "20260928T010000-open" has:
        | column      | value    |
        | balance     | 10633.10 |
        | floating_pl | 556.48   |
        | equity_end  | 11189.58 |

    Scenario: a statement without an Open Trades table leaves the run with no open positions and no summary
      Given a finished run "20260928T010000-flat" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-04-30 with cash 10000
      When I build the results database
      Then table "open_positions" has 0 rows
      And the run "20260928T010000-flat" has:
        | column      | value |
        | balance     | none  |
        | floating_pl | none  |
        | equity_end  | none  |

    Scenario: an Open Trades row with a non-numeric floating P/L stops the build naming the statement
      Given a finished run "20260928T010000-bad" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-04-30 with cash 10000
      And its statement lists the open trades:
        | ticket | open_time        | type | lots | price   | stop | targets | mark    | profit |
        | 9      | 2016.04.29 00:00 | buy  | 0.10 | 1.10000 | —    | —       | 1.10100 | ten    |
      When I build the results database expecting failure
      Then the failure message contains "statement.md"

    Scenario: a plan without a recorded stop distance gets it from its entry price and the pip
      Given a finished run "20260928T010000-aaab" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
      And its trade plans are:
        | order | lots | stop_loss | stop_pips | targets     | trail_steps | spread_pips |
        | 1     | 1.0  | 1.09750   | -         | 1.10500:1.0 | 40:5        | 1.0         |
      When I build the results database
      Then the trade plan of trade "1" has stop_loss 1.0975, stop_pips 25, 1 targets and 1 trail step

    Scenario: a run without a strategy config records only the --param values and the default bar size
      Given a finished run "20260928T010000-bbbb" of strategy "baseline" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And it has no strategy config
      When I build the results database
      Then the run "20260928T010000-bbbb" has:
        | column      | value |
        | bar_minutes | 1     |
      And table "run_parameters" has 1 row

  Rule: Every decision is kept; the first BUY/SELL row of a trade is its entry decision

    Scenario: decisions, their filters, the entry flag, F7's probability and F3's pattern
      Given a finished run "20260928T010000-cccc" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
      And its decisions are:
        | timestamp            | final_decision | trade_id | vetoed_by       |
        | 2016-03-02T09:00:00Z | NO_TRADE       |          | volume_strength |
        | 2016-03-02T10:00:00Z | BUY            | 1        |                 |
        | 2016-03-02T11:00:00Z | HOLD           | 1        |                 |
        | 2016-03-02T12:00:00Z | BUY            | 1        |                 |
      And the decision at 2016-03-02T09:00:00Z ran the filters:
        | filter          | recommendation | veto | reason                                                                 | p_hat |
        | F1_trend        | BUY            | no   | trend_direction=1.0, trend_strength=3.0, higher_tf_trend_direction=1.0 |       |
        | volume_strength | ABSTAIN        | yes  | relative tick activity 0.5                                             |       |
      And the decision at 2016-03-02T10:00:00Z ran the filters:
        | filter          | recommendation | veto | reason                                                                     | p_hat |
        | F1_trend        | BUY            | no   | trend_direction=1.0, trend_strength=3.0, higher_tf_trend_direction=1.0     |       |
        | F3_pattern      | BUY            | no   | detected candlestick pattern 'hammer'                                      |       |
        | f7_meta_learner | BUY            | no   | p_hat=0.61, theta_high=0.55, theta_low=0.45, regime_gate=False, regime=n/a | 0.61  |
      When I build the results database
      Then table "decisions" has 4 rows
      And table "decision_filters" has 5 rows
      And the entry decision of trade "1" is at 2016-03-02T10:00:00+00:00 with p_hat 0.61
      And the decision at 2016-03-02T09:00:00+00:00 is not an entry and was vetoed by "volume_strength"
      And the decision at 2016-03-02T12:00:00+00:00 is a same-side repeat, not an entry
      And the decision summary of the run is:
        | final_decision | vetoed_by       | count |
        | BUY            |                 | 2     |
        | HOLD           |                 | 1     |
        | NO_TRADE       | volume_strength | 1     |
      And the filters of the entry decision of trade "1" are, in order:
        | position | filter_name     | recommendation | veto | pattern_name |
        | 0        | F1_trend        | BUY            | 0    |              |
        | 1        | F3_pattern      | BUY            | 0    | hammer       |
        | 2        | f7_meta_learner | BUY            | 0    |              |

    Scenario: the entries mode keeps only the entry decisions but still the whole funnel
      Given a finished run "20260928T010000-cccd" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its decisions are:
        | timestamp            | final_decision | trade_id | vetoed_by |
        | 2016-03-02T09:00:00Z | NO_TRADE       |          | F1_trend  |
        | 2016-03-02T10:00:00Z | SELL           | 1        |           |
        | 2016-03-02T11:00:00Z | HOLD           | 1        |           |
      When I build the results database keeping only the entry decisions
      Then table "decisions" has 1 row
      And table "decision_summary" has 3 rows

    Scenario Outline: F3's pattern name is extracted from its reason text
      Then the pattern extracted from "<reason>" is <pattern>

      Examples:
        | reason                                           | pattern           |
        | detected candlestick pattern 'bullish_engulfing' | bullish_engulfing |
        | detected candlestick pattern 'evening_star'      | evening_star      |
        | pattern=hammer                                   | hammer            |
        | no pattern detected this bar                     | none              |

  Rule: The exit kind follows the closing order and the tagged engine log

    Scenario Outline: stop, target, trailed stop, reversal and liquidation exits
      Given a finished run "20260928T010000-dddd" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order   |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | <closing_order> |
      And its engine log records "<log_line>" at <log_time>
      When I build the results database
      Then the exit kind of trade "1" is "<exit_kind>"

      Examples:
        | closing_order | log_time             | log_line                                                    | exit_kind   |
        | limit         | -                    | -                                                           | target      |
        | stop          | -                    | -                                                           | stop        |
        | stop          | 2016-03-02T12:00:00Z | HYBRID_TRAIL\|entry=1.1\|from=1.098\|to=1.101\|steps=[0]     | trail_stop  |
        | stop          | 2016-03-02T12:00:00Z | HYBRID_TRAIL\|entry=1.2\|from=1.198\|to=1.201\|steps=[0]     | stop        |
        | stop          | 2016-03-02T16:00:00Z | HYBRID_TRAIL\|entry=1.1\|from=1.098\|to=1.101\|steps=[0]     | stop        |
        | market        | 2016-03-02T15:00:00Z | HYBRID_OCO_CANCEL\|reason=reversal\|orders=[2, 3]           | reversal    |
        | market        | 2016-03-02T15:00:00Z | HYBRID_OCO_CANCEL\|reason=veto\|orders=[2, 3]               | liquidation |
        | market        | 2016-03-02T15:00:00Z | HYBRID_OCO_CANCEL\|reason=flat\|orders=[2, 3]               | unknown     |
        | market        | -                    | -                                                           | unknown     |

    Scenario: every trail move is stored and joined to the trade it moved
      Given a finished run "20260928T010000-eeee" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10300    | 300    | stop          |
      And its engine log records "HYBRID_TRAIL|entry=1.1|from=1.098|to=1.101|steps=[0]" at 2016-03-02T12:00:00Z
      And its engine log records "HYBRID_TRAIL|entry=1.1|from=1.101|to=1.103|steps=[0, 1]" at 2016-03-02T14:00:00Z
      And its engine log records "HYBRID_TRAIL|entry=1.3|from=1.298|to=1.301|steps=[0]" at 2016-03-20T14:00:00Z
      When I build the results database
      Then the trail moves of trade "1" are:
        | time                      | from_stop | to_stop |
        | 2016-03-02T12:00:00+00:00 | 1.098     | 1.101   |
        | 2016-03-02T14:00:00+00:00 | 1.101     | 1.103   |
      And table "trail_moves" has 3 rows
      And the exit kind of trade "1" is "trail_stop"

  Rule: Re-running the build upserts by run id

    Scenario: a rebuild replaces a run's rows instead of duplicating them
      Given a finished run "20260928T010000-ffff" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its equity samples are:
        | time                      | equity |
        | 2016-03-01T00:00:00+00:00 | 10000  |
        | 2016-03-31T00:00:00+00:00 | 10100  |
      When I build the results database
      And its metrics change to total_return 0.09, sharpe 2.0, max_drawdown 0.01, hit_rate 1.0
      And I build the results database again
      Then table "runs" has 1 row
      And the run "20260928T010000-ffff" has:
        | column       | value |
        | total_return | 0.09  |
      And table "equity_samples" has 2 rows
      And table "monthly_returns" has 1 row

    Scenario: a database of another schema version is refused
      Given a finished run "20260928T010000-gggg" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And the output file already holds schema version 99
      When I build the results database expecting failure
      Then the failure message contains "schema version [99]"

  Rule: Directories still running are skipped; broken finished runs stop the build naming the file

    Scenario: a directory without run.json is in progress and is skipped, counted
      Given a finished run "20260928T010000-hhhh" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And an unfinished run directory "20260928T020000-iiii" of strategy "hybrid" holding only main.json
      When I build the results database through the CLI
      Then the CLI reports "results-db: 1 run(s) ingested"
      And the CLI reports "results-db: skipped 1 unfinished run directory (no run.json)"
      And table "runs" has 1 row

    Scenario: a runs root with no run directories is refused
      Given an empty runs root
      When I build the results database expecting failure
      Then the failure message contains "holds no <strategy>/<stamp>/ run directories"

    Scenario Outline: a finished run with a missing or broken artifact is refused naming the file
      Given a finished run "20260928T010000-jjjj" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
      And its file "<file>" is <damage>
      When I build the results database expecting failure
      Then the failure message is "<message>"

      Examples:
        | file              | damage               | message                                                                                                                  |
        | trades.json       | missing              | trades.json is missing from {run_dir}; LEAN's closed-trade ledger is required                                            |
        | metrics.json      | missing              | metrics.json is missing from {run_dir}; the run has no metrics — re-run `algo-backtest run`                              |
        | metrics.json      | not valid JSON       | metrics.json in {run_dir} is not valid JSON (Expecting value: line 1 column 1 (char 0))                                  |
        | metrics.json      | lacking key hit_rate | metrics.json in {run_dir} lacks key 'hit_rate'                                                                           |
        | equity.csv        | missing              | equity.csv is missing from {run_dir}; regenerate it with `algo-backtest statement --run {run_dir}`                       |
        | equity.csv        | headed wrongly       | equity.csv in {run_dir} must start with the header time,equity,drawdown_pct; regenerate it with `algo-backtest statement --run` |
        | main.json         | missing              | main.json is missing from {run_dir}; LEAN's result JSON is required for the orders                                       |
        | decisions.parquet | missing              | decisions.parquet is missing from {run_dir}; the chain writes the audit trail at the end of a run — re-run it            |
        | log.txt           | missing              | log.txt is missing from {run_dir}; trades.json lists 1 closed trade(s) and exit kinds are classified from the engine log |
        | main.json         | lacking order 2      | main.json in {run_dir} has no order 2, the closing order of a trade in trades.json; the run directory is inconsistent    |

  Rule: The job label of a runs root names the experiment

    Scenario Outline: the label is given explicitly or derived from the path
      When I parse the runs root argument "<argument>"
      Then its job label is "<job>" and its path ends with "<tail>"

      Examples:
        | argument                                    | job                        | tail |
        | /x/2026-09-28-broad-window-h4/data/runs     | 2026-09-28-broad-window-h4 | runs |
        | /x/jobs/oneyear/runs                        | oneyear                    | runs |
        | lab=/x/anything/data/runs                   | lab                        | runs |
        | /x/pilot                                    | pilot                      | pilot |

  Rule: With --bars-root the bars of each trade's chart window come from the M1 bid/ask mid

    The window runs from --bars-before ahead of the decision bar (offset 0, the last bar
    closed at or before the entry) to --bars-after past the bar holding the exit, so the
    exit is always on the chart; --bars-max-after caps how far past the entry it may reach.

    Scenario: the decision bar is offset 0 and the neighbours are complete buckets of the run's bar size
      Given a finished run "20260928T010000-kkkk" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its config sets:
        | key                        | value | source             |
        | price_features.bar_minutes | 60    | hybrid/config.yaml |
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T10:30:00Z | 1.10500    | 500    | limit         |
      And M1 bars for EURUSD on 2016-03-02 from 06:00 to 12:00 with bid 1.10000 rising 0.00010 per minute and a 0.00020 spread
      When I build the results database with 2 bars before and 1 after each entry
      Then the entry bars of trade "1" are:
        | offset | time                      | open    | high    | low     | close   |
        | -2     | 2016-03-02T07:00:00+00:00 | 1.10610 | 1.11200 | 1.10610 | 1.11200 |
        | -1     | 2016-03-02T08:00:00+00:00 | 1.11210 | 1.11800 | 1.11210 | 1.11800 |
        | 0      | 2016-03-02T09:00:00+00:00 | 1.11810 | 1.12400 | 1.11810 | 1.12400 |
        | 1      | 2016-03-02T10:00:00+00:00 | 1.12410 | 1.13000 | 1.12410 | 1.13000 |
        | 2      | 2016-03-02T11:00:00+00:00 | 1.13010 | 1.13600 | 1.13010 | 1.13600 |
      And the build reports 0 capped trade windows

    Scenario: a trade held past --bars-after keeps its bars up to --bars-after past the exit bar
      Given a finished run "20260928T010000-kkkl" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its config sets:
        | key                        | value | source             |
        | price_features.bar_minutes | 60    | hybrid/config.yaml |
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
      And M1 bars for EURUSD on 2016-03-02 from 06:00 to 18:00 with bid 1.10000 rising 0.00010 per minute and a 0.00020 spread
      When I build the results database with 2 bars before and 1 after each entry
      Then the entry bars of trade "1" are:
        | offset | time                      | open    | high    | low     | close   |
        | -2     | 2016-03-02T07:00:00+00:00 | 1.10610 | 1.11200 | 1.10610 | 1.11200 |
        | -1     | 2016-03-02T08:00:00+00:00 | 1.11210 | 1.11800 | 1.11210 | 1.11800 |
        | 0      | 2016-03-02T09:00:00+00:00 | 1.11810 | 1.12400 | 1.11810 | 1.12400 |
        | 1      | 2016-03-02T10:00:00+00:00 | 1.12410 | 1.13000 | 1.12410 | 1.13000 |
        | 2      | 2016-03-02T11:00:00+00:00 | 1.13010 | 1.13600 | 1.13010 | 1.13600 |
        | 3      | 2016-03-02T12:00:00+00:00 | 1.13610 | 1.14200 | 1.13610 | 1.14200 |
        | 4      | 2016-03-02T13:00:00+00:00 | 1.14210 | 1.14800 | 1.14210 | 1.14800 |
        | 5      | 2016-03-02T14:00:00+00:00 | 1.14810 | 1.15400 | 1.14810 | 1.15400 |
        | 6      | 2016-03-02T15:00:00+00:00 | 1.15410 | 1.16000 | 1.15410 | 1.16000 |
        | 7      | 2016-03-02T16:00:00+00:00 | 1.16010 | 1.16600 | 1.16010 | 1.16600 |
      And the build reports 0 capped trade windows

    Scenario: a trade held past --bars-max-after stops at the cap and the build counts it
      Given a finished run "20260928T010000-kkkm" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its config sets:
        | key                        | value | source             |
        | price_features.bar_minutes | 60    | hybrid/config.yaml |
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
      And M1 bars for EURUSD on 2016-03-02 from 06:00 to 18:00 with bid 1.10000 rising 0.00010 per minute and a 0.00020 spread
      When I build the results database with 2 bars before and 1 after each entry, at most 3 after the entry
      Then the entry bars of trade "1" are:
        | offset | time                      | open    | high    | low     | close   |
        | -2     | 2016-03-02T07:00:00+00:00 | 1.10610 | 1.11200 | 1.10610 | 1.11200 |
        | -1     | 2016-03-02T08:00:00+00:00 | 1.11210 | 1.11800 | 1.11210 | 1.11800 |
        | 0      | 2016-03-02T09:00:00+00:00 | 1.11810 | 1.12400 | 1.11810 | 1.12400 |
        | 1      | 2016-03-02T10:00:00+00:00 | 1.12410 | 1.13000 | 1.12410 | 1.13000 |
        | 2      | 2016-03-02T11:00:00+00:00 | 1.13010 | 1.13600 | 1.13010 | 1.13600 |
        | 3      | 2016-03-02T12:00:00+00:00 | 1.13610 | 1.14200 | 1.13610 | 1.14200 |
      And the build reports 1 capped trade window

    Scenario: an entry outside the M1 partitions stops the build naming the partition
      Given a finished run "20260928T010000-llll" of strategy "hybrid" on EURUSD from 2016-03-01 to 2016-03-31 with cash 10000
      And its closed trades are:
        | order | direction | quantity | entry_time           | entry_price | exit_time            | exit_price | profit | closing_order |
        | 1     | buy       | 100000   | 2016-03-02T10:00:00Z | 1.10000     | 2016-03-02T15:00:00Z | 1.10500    | 500    | limit         |
      When I build the results database with 2 bars before and 1 after each entry expecting failure
      Then the failure message contains "M1 partition"
      And the failure message contains "year=2016/month=03/data.parquet is missing"
