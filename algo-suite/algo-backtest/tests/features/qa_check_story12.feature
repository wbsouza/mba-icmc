Feature: Story-12 QA check script over a finished run directory
  docs/stories/done/12-execution-realism/evidence/qa_check.py is the deterministic
  gate of the story-12 QA procedure: one PASS/FAIL line per check, exit 0 only when every
  check passes. It reads a run directory's artifacts alone (no LEAN import) and proves the
  execution-realism machinery — every trade plan traces to the resolved capital_mgmt and
  execution sections, every planned entry to an order LEAN booked, position risk stays
  within risk_per_trade, the statement/equity/report artifacts exist and are self-contained.
  The run directories here are synthetic, written from the tables below.

  Background:
    Given a finished run directory for strategy "baseline" on "EURUSD" from "2015-09-01" to "2015-09-30" with cash 10000
    And the resolved "capital_mgmt" section
      | key                  | value                                                |
      | risk_per_trade       | 0.03                                                 |
      | stop_loss_pips       | 20.0                                                 |
      | pip_value_per_lot    | 10.0                                                 |
      | lot_notional_units   | 100000                                               |
      | assumed_leverage     | 30                                                   |
      | stop_loss_shrink     | 0.20                                                 |
      | min_stop_pips        | 5.0                                                  |
      | min_stop_factor      | 1.2                                                  |
      | targets              | [{"at_level_ratio": 2.0, "close_fraction": 0.5}]     |
      | trail_stops          | [{"at_level_ratio": 0.5, "to_level_ratio": -0.66}]   |
      | min_reward_risk      | 2.0                                                  |
      | stop_distance_source | "fixed"                                              |
      | atr_multiplier       | 2.0                                                  |
    And the resolved "execution" section
      | key                    | value |
      | spread_pips            | 1.0   |
      | commission_per_lot     | 0.0   |
      | min_hold_bars          | 0     |
      | broker_stop_level_pips | 0.0   |
      | close_on_veto          | false |
    And the resolved "risk_guard" section
      | key                               | value |
      | max_concurrent_trades_per_account | 2     |
    And every resolved parameter is attributed to "baseline/config.yaml"
    And the equity samples
      | time                      | equity   |
      | 2015-09-01T00:00:00+00:00 | 10000.00 |
      | 2015-09-02T00:00:00+00:00 | 10120.50 |
    And a planned trade
      | field          | value                                                                                              |
      | entry_order_id | 1                                                                                                  |
      | entry_time     | "2015-09-01T10:00:00"                                                                              |
      | direction      | "buy"                                                                                              |
      | lots           | 1.875                                                                                              |
      | quantity       | 187500.0                                                                                           |
      | entry_price    | 1.13115                                                                                            |
      | stop_loss      | 1.12955                                                                                            |
      | take_profits   | [{"price": 1.13465, "close_fraction": 0.5, "quantity": -93750.0}]                                  |
      | trail_stops    | [{"at_level_ratio": 0.59375, "to_level_ratio": -0.5975, "at_price": 1.1321, "to_price": 1.130194}] |
      | spread_pips    | 1.0                                                                                                |
    And LEAN booked order 1 for 187500.0 units
    And the trade entered by order 1 closed by order 2 at "2015-09-01T10:10:00Z" with profit 120.5 and fees 0.0

  Rule: A consistent run passes every check and exits 0

    Scenario: the synthetic run passes as written
      When I run the QA check on the run directory
      Then every check reports PASS
      And the QA exit code is 0

    Scenario: a run without planned entries passes the plan checks vacuously
      Given the artifact "trade-plans.json" is replaced by []
      When I run the QA check on the run directory
      Then check "position risk within risk_per_trade" reports PASS
      And check "concurrent positions within risk_guard cap" reports PASS
      And the QA exit code is 0

  Rule: One deviation in an artifact flips exactly the check that guards it

    Scenario Outline: one deviation flips its check (<case>)
      Given the artifact "<artifact>" field "<path>" is set to <value>
      When I run the QA check on the run directory
      Then check "<check>" reports <verdict>
      And the QA exit code is <exit>

      Examples: trade plan against the resolved config
        | case                          | artifact           | path                          | value   | check                                        | verdict | exit |
        | stop below the floor          | trade-plans.json   | 0.stop_loss                   | 1.13100 | plan stop distance within capital_mgmt bounds | FAIL    | 1    |
        | stop not shrunk               | trade-plans.json   | 0.stop_loss                   | 1.12915 | plan stop distance within capital_mgmt bounds | FAIL    | 1    |
        | stop on the profit side       | trade-plans.json   | 0.stop_loss                   | 1.13275 | plan stop distance within capital_mgmt bounds | FAIL    | 1    |
        | no take-profit placed         | trade-plans.json   | 0.take_profits                | []      | plan targets match capital_mgmt.targets       | FAIL    | 1    |
        | take-profit off the formula   | trade-plans.json   | 0.take_profits.0.price        | 1.13400 | plan targets match capital_mgmt.targets       | FAIL    | 1    |
        | take-profit closes too much   | trade-plans.json   | 0.take_profits.0.close_fraction | 1.0   | plan targets match capital_mgmt.targets       | FAIL    | 1    |
        | no trail step planned         | trade-plans.json   | 0.trail_stops                 | []      | plan trail steps match capital_mgmt.trail_stops | FAIL  | 1    |
        | trail destination off formula | trade-plans.json   | 0.trail_stops.0.to_price      | 1.13000 | plan trail steps match capital_mgmt.trail_stops | FAIL  | 1    |
        | spread differs from execution | trade-plans.json   | 0.spread_pips                 | 2.0     | plan spread equals execution.spread_pips      | FAIL    | 1    |
        | entry order unknown to LEAN   | trade-plans.json   | 0.entry_order_id              | 9       | plan entry orders join the LEAN result        | FAIL    | 1    |
        | LEAN booked another quantity  | main.json          | orders.1.quantity             | 100000  | plan entry orders join the LEAN result        | FAIL    | 1    |
        | lots do not match quantity    | trade-plans.json   | 0.lots                        | 2.0     | plan lots match quantity                      | FAIL    | 1    |
        | quantity contradicts side     | trade-plans.json   | 0.quantity                    | -187500.0 | plan lots match quantity                    | FAIL    | 1    |
        | risk budget lowered           | strategy-config    | capital_mgmt.risk_per_trade   | 0.02    | position risk within risk_per_trade           | FAIL    | 1    |
        | risk budget lowered, lots ok  | strategy-config    | capital_mgmt.risk_per_trade   | 0.02    | plan lots match quantity                      | PASS    | 1    |

      Examples: config, provenance and run manifest
        | case                          | artifact                 | path                        | value                | check                                              | verdict | exit |
        | provenance from a stray file  | strategy-provenance.json | capital_mgmt.risk_per_trade | "conf/backtest.yaml" | provenance sources are config.yaml or default      | FAIL    | 1    |
        | provenance default is allowed | strategy-provenance.json | capital_mgmt.risk_per_trade | "default"            | provenance sources are config.yaml or default      | PASS    | 0    |
        | YAML drifted from JSON        | strategy-config.json     | execution.min_hold_bars     | 3                    | strategy-config.yaml matches strategy-config.json  | FAIL    | 1    |
        | cash differs from first equity | run.json                | params.cash                 | "9000"               | equity.csv starts at cash                          | FAIL    | 1    |
        | no cap on concurrent trades   | strategy-config          | risk_guard.max_concurrent_trades_per_account | null | concurrent positions within risk_guard cap       | PASS    | 0    |

    Scenario Outline: a text artifact that breaks its contract fails (<case>)
      Given the artifact "<artifact>" contains "<text>"
      When I run the QA check on the run directory
      Then check "<check>" reports FAIL
      And the QA exit code is 1

      Examples:
        | case                        | artifact    | text                                                        | check                        |
        | report carries a script     | report.html | <!doctype html><html><body><script>alert(1)</script></body></html>               | report.html self-contained |
        | report loads a CDN resource | report.html | <!doctype html><html><head><link href='https://cdn.example/x.css'></head></html> | report.html self-contained |
        | equity csv header renamed   | equity.csv  | date,equity,dd\n2015-09-01T00:00:00+00:00,10000.0,0.0                            | equity.csv starts at cash  |

  Rule: A missing artifact fails its own check

    Scenario Outline: <artifact> absent
      Given the artifact "<artifact>" is absent
      When I run the QA check on the run directory
      Then check "<check>" reports FAIL
      And the QA exit code is 1

      Examples:
        | artifact                 | check                                             |
        | strategy-config.yaml     | strategy-config.yaml matches strategy-config.json |
        | strategy-provenance.json | provenance sources are config.yaml or default     |
        | trade-plans.json         | trade-plans.json present                          |
        | statement.md             | statement.md present                              |
        | equity.png               | equity.png present                                |
        | equity.csv               | equity.csv starts at cash                         |
        | report.html              | report.html present                               |

  Rule: Concurrent planned positions are counted against the risk-guard cap

    Scenario Outline: concurrent positions against the cap (<case>)
      Given a second planned trade entered by order 3 at "<entry>" and closed by order 4 at "<exit>"
      And the artifact "strategy-config" field "risk_guard.max_concurrent_trades_per_account" is set to <cap>
      When I run the QA check on the run directory
      Then check "concurrent positions within risk_guard cap" reports <verdict>

      Examples:
        | case                              | entry                | exit                 | cap  | verdict |
        | two overlapping trades under cap 2 | 2015-09-01T10:05:00 | 2015-09-01T10:20:00Z | 2    | PASS    |
        | two overlapping trades over cap 1  | 2015-09-01T10:05:00 | 2015-09-01T10:20:00Z | 1    | FAIL    |
        | back-to-back trades under cap 1    | 2015-09-01T10:10:00 | 2015-09-01T10:20:00Z | 1    | PASS    |
        | still-open second trade over cap 1 | 2015-09-01T10:05:00 | open                 | 1    | FAIL    |
        | overlapping trades without a cap   | 2015-09-01T10:05:00 | 2015-09-01T10:20:00Z | null | PASS    |

  Rule: Two or more run directories are consolidated through algo-analyze equity-curves

    Scenario Outline: two run directories are consolidated (<case>)
      Given a second finished run "<run_id>" of the same strategy from "<start>" to "<end>"
      And the second run's artifact "<absent>" is absent
      When I run the QA check on both run directories
      Then check "equity-curves consolidates the runs" reports <verdict>
      And the QA exit code is <exit>

      Examples:
        | case                                | run_id                   | start      | end        | absent     | verdict | exit |
        | consecutive windows consolidate     | 20260927T010000-cafebabe | 2015-10-01 | 2015-10-31 | none       | PASS    | 0    |
        | a run without equity.csv cannot     | 20260927T010000-cafebabe | 2015-10-01 | 2015-10-31 | equity.csv | FAIL    | 1    |
