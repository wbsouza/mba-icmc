Feature: Consolidated equity curves across runs
  `algo-analyze equity-curves` overlays several finished runs on one time axis, like a
  robustness-testing chart: one line per strategy, and the consecutive windows of the
  same strategy (baseline 2015-09, 2015-10, 2015-11 run as three one-month backtests,
  each with a fresh starting deposit) chained into ONE continuous curve. Each run is a
  results directory holding run.json (strategy, window) and the equity.csv that
  `algo-backtest statement --run` writes (time, equity, drawdown_pct).

  Chaining re-bases every later window so it starts where the previous one ended: its
  raw equity is multiplied by previous_chained_end / this_raw_start. Nothing is
  fabricated — the un-chained raw equity is kept alongside in the long-format CSV.

  Background:
    Given an output directory for the consolidated curves

  Rule: Runs are grouped by the strategy run.json names and ordered by window start

    Scenario: runs given in any order come out grouped by strategy and sorted by start
      Given a run "hyb-oct" of strategy "hybrid" from "2015-10-01" to "2015-10-31" with equity 10000, 10200
      And a run "base-oct" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity 10000, 10100
      And a run "base-sep" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10050
      When I consolidate the runs
      Then the consolidated rows list the runs in the order base-sep, base-oct, hyb-oct
      And the strategies in the summary are baseline, hybrid

    Scenario: two runs of one strategy over overlapping windows cannot be chained
      Given a run "a" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10050
      And a run "b" of strategy "baseline" from "2015-09-15" to "2015-10-15" with equity 10000, 10100
      When I consolidate the runs expecting failure
      Then the failure names all of "baseline", "2015-09-15" and "overlap"

  Rule: Consecutive windows of a strategy are chained by re-basing each later window

    Scenario Outline: a later window is re-based to start where the previous one ended
      Given a run "a" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, <a_end>
      And a run "b" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity <b_start>, <b_end>
      When I consolidate the runs
      Then the chained equity of run "b" is <b_start_chained>, <b_end_chained>
      And the raw equity of run "b" is still <b_start>, <b_end>
      And the curve summary for "baseline" is first <first>, last <last>, net <net> percent, max drawdown <max_dd> percent

      Examples:
        | a_end | b_start | b_end | b_start_chained | b_end_chained | first | last    | net   | max_dd |
        | 10050 | 10000   | 10100 | 10050           | 10150.5       | 10000 | 10150.5 | 1.505 | 0.0    |
        | 9900  | 10000   | 10100 | 9900            | 9999          | 10000 | 9999    | -0.01 | 1.0    |
        | 10000 | 10000   | 10100 | 10000           | 10100         | 10000 | 10100   | 1.0   | 0.0    |
        | 10050 | 20000   | 20200 | 10050           | 10150.5       | 10000 | 10150.5 | 1.505 | 0.0    |

    Scenario: three consecutive months compound their re-basing factors
      Given a run "sep" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 11000
      And a run "oct" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity 10000, 11000
      And a run "nov" of strategy "baseline" from "2015-11-01" to "2015-11-30" with equity 10000, 11000
      When I consolidate the runs
      Then the chained equity of run "nov" is 12100, 13310

    Scenario: a single run is not re-based
      Given a run "only" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 9800, 10300
      When I consolidate the runs
      Then the chained equity of run "only" is 10000, 9800, 10300
      And the curve summary for "baseline" is first 10000, last 10300, net 3.0 percent, max drawdown 2.0 percent

    Scenario: the drawdown column follows the running peak of the chained curve
      Given a run "a" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10500
      And a run "b" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity 10000, 9600, 10000
      When I consolidate the runs
      Then the drawdown percent of run "b" is 0.0, 4.0, 0.0

  Rule: The long-format CSV and the PNG are written into the output directory

    Scenario: the long-format CSV has one row per sample of every run
      Given a run "a" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10050
      And a run "b" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity 10000, 10100
      When I consolidate the runs
      Then the consolidated CSV rows are
        | strategy | run_id | time                      | equity_raw | equity_chained | drawdown_pct |
        | baseline | a      | 2015-09-01T00:00:00+00:00 | 10000      | 10000          | 0.0          |
        | baseline | a      | 2015-09-02T00:00:00+00:00 | 10050      | 10050          | 0.0          |
        | baseline | b      | 2015-10-01T00:00:00+00:00 | 10000      | 10050          | 0.0          |
        | baseline | b      | 2015-10-02T00:00:00+00:00 | 10100      | 10150.5        | 0.0          |

    Scenario: two strategies over the same window share one chart and one CSV
      Given a run "base" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100, 10050
      And a run "hyb" of strategy "hybrid" from "2015-09-01" to "2015-09-30" with equity 10000, 9900, 10200
      When I consolidate the runs
      Then the consolidated CSV has 6 data rows covering the strategies baseline, hybrid
      And the consolidated PNG is written
      And the chart title names the window "2015-09-01 .. 2015-09-30"

    Scenario: the chart title spans the earliest start to the latest end
      Given a run "base" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And a run "hyb" of strategy "hybrid" from "2015-10-01" to "2015-11-30" with equity 10000, 9900
      When I consolidate the runs
      Then the chart title names the window "2015-09-01 .. 2015-11-30"

    Scenario: --label renames a strategy in the CSV, the legend and the summary
      Given a run "base" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And the label "baseline=Baseline (F1-F7)"
      When I consolidate the runs
      Then the strategies in the summary are Baseline (F1-F7)
      And the consolidated CSV has 2 data rows covering the strategies Baseline (F1-F7)

    Scenario Outline: the summary line per strategy states first, last, net and max drawdown
      Given a run "a" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And a run "b" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity 10000, <b_end>
      When I consolidate the runs
      Then the summary line for "baseline" is "<line>"

      Examples:
        | b_end | line                                                                                            |
        | 10100 | baseline: first 10,000.00 -> last 10,201.00, net +2.01%, max drawdown 0.00%, 2 run(s)          |
        | 9000  | baseline: first 10,000.00 -> last 9,090.00, net -9.10%, max drawdown 10.00%, 2 run(s)          |

  Rule: Missing or malformed inputs fail fast with the command that fixes them

    Scenario: a run without equity.csv names the run directory and the statement command
      Given a run "old" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And the run "old" lacks "equity.csv"
      When I consolidate the runs expecting failure
      Then the failure names the run directory of "old" and "algo-backtest statement --run"

    Scenario: a run without run.json names the file
      Given a run "old" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And the run "old" lacks "run.json"
      When I consolidate the runs expecting failure
      Then the failure names "run.json"

    Scenario: an equity.csv with a foreign header names the file and the expected columns
      Given a run "odd" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And the run "odd" equity.csv header is "timestamp,value"
      When I consolidate the runs expecting failure
      Then the failure names both "equity.csv" and "time,equity,drawdown_pct"

    Scenario: an empty equity.csv cannot be chained
      Given a run "flat" of strategy "baseline" from "2015-09-01" to "2015-09-30" with no equity samples
      When I consolidate the runs expecting failure
      Then the failure names both "equity.csv" and "no equity samples"

    Scenario Outline: a malformed --label is rejected
      Given a run "base" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And the label "<label>"
      When I consolidate the runs expecting failure
      Then the failure names "<named>"

      Examples:
        | label           | named                |
        | baseline        | strategy=Label       |
        | hybrid=Hybrid   | hybrid               |

    Scenario: no runs at all is an error, not an empty chart
      When I consolidate the runs expecting failure
      Then the failure names "--run"

  Rule: The CLI wires the consolidation end to end

    Scenario: the command writes both artifacts and prints one summary line per strategy
      Given a run "base-sep" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10050
      And a run "base-oct" of strategy "baseline" from "2015-10-01" to "2015-10-31" with equity 10000, 10100
      And a run "hyb-sep" of strategy "hybrid" from "2015-09-01" to "2015-09-30" with equity 10000, 10200
      When I run the equity-curves command on those runs
      Then the command exits with code 0
      And the output directory contains "equity-consolidated.csv" and "equity-consolidated.png"
      And the output prints "equity-curves: baseline: first 10,000.00 -> last 10,150.50"
      And the output prints "equity-curves: hybrid: first 10,000.00 -> last 10,200.00"
      And the output prints both artifact paths

    Scenario: a run without equity.csv exits 2 naming the remediation
      Given a run "old" of strategy "baseline" from "2015-09-01" to "2015-09-30" with equity 10000, 10100
      And the run "old" lacks "equity.csv"
      When I run the equity-curves command on those runs
      Then the command exits with code 2
      And the output prints "algo-backtest statement --run"
