Feature: Run the F1-F7 baseline chain via the run CLI (wiring smoke test)
  `algo-backtest run --strategy baseline` wires the config.yaml-driven F1+F2+F3+F5+F6+F7
  chain (no F4/news) into a real LEAN algorithm for the first time (2026-09-26). This is
  a wiring smoke test, not a methodology result -- see technical-debt.md's TD-51 and
  docs/stories/done/2026-09-26-04h-algo-backtest-hybrid-integration/progress.md: F3's
  candlestick-pattern feature is never populated (no real detector), F5/F6's
  account-risk features use fixed placeholder economics (no real ATR/margin model), and
  F7's meta-learner is trained on a short window by
  scripts/train_baseline_meta_learner.py, not a statistically meaningful model.

  Rule: Inputs are validated before any container starts

    Scenario: a size outside (0, 1] is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=2 --param cash=10000"
      Then the run command exits with code 2
      And the error says size must be in range

    Scenario: a non-positive starting cash is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param cash=0"
      Then the run command exits with code 2
      And the error says cash must be positive

    Scenario: a model trained for hybrid is rejected for baseline before any container starts
      When I run baseline with the bundled hybrid model as --model
      Then the run command exits with code 2
      And the error names the model's families and the strategy's declared families

    Scenario: an unknown param is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param cash=10000 --param bogus=1"
      Then the run command exits with code 2
      And the error says params must be exactly

  Rule: The execution bootstrap prints every strategy parameter and its source

    Scenario Outline: parameters are printed with their provenance before any data check (<key>)
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the bootstrap output lists strategy parameter "<key>" = <value> from "<source>"

      Examples:
        | key                       | value | source               |
        | meta_learner.regime_gate  | false | baseline/config.yaml |
        | capital_mgmt.risk_per_trade | 0.03 | baseline/config.yaml |
        | price_features.ema_fast   | 3     | baseline/config.yaml |

  Rule: A validated run executes the full F1-F7 chain on the engine without crashing

    @integration
    Scenario: the baseline chain trades a sine cycle and every decision joins its LEAN trade
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      When I run baseline over the 2014-05-08 to 2014-05-09 test span with size 0.5, cash 10000 and that model
      Then the strategy run exits successfully
      And the container log shows the algorithm loaded the fixture model
      And a metrics summary is reported
      And the run artifacts are written under the data root
      And the container log shows the F1-F7 chain actually evaluated a decision
      And decisions.parquet is written under the run's results directory
      And every decisions.parquet row's trade_id names the LEAN trade open at that row's instant
      And at least one decisions.parquet row is joined to a trades.json trade

  Rule: A YAML variant in --strategies-dir runs without a code change

    @integration
    Scenario: an external variant runs on the same engine and records its own parameters
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      And an external strategies directory with "probe-tight" extending baseline with theta_high 0.52 and theta_low 0.48
      When I run probe-tight from that directory over the 2014-05-08 to 2014-05-09 test span with size 0.5, cash 10000 and that model
      Then the strategy run exits successfully
      And the run's strategy-config.json under "probe-tight" records theta_high 0.52 and theta_low 0.48
      And the run's strategy-provenance.json under "probe-tight" attributes "meta_learner.theta_high" to "probe-tight/config.yaml" and "risk_guard.max_leverage" to "baseline/config.yaml"
