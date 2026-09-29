Feature: Run a single strategy via the run CLI
  `algo-backtest run` runs one strategy over a window on the proven LEAN path: one symbol,
  minute resolution, long-only, single position, fixed sizing. Parameters are strategy-
  specific, passed as repeated `--param key=value` and validated by the strategy; every
  strategy takes `cash`, the account's starting deposit (story 12, TD-65). Exercised
  here with the baseline-ma crossover; multi-strategy comparison lives in `experiment run`.

  Rule: Inputs are validated before any container starts

    Scenario: an unknown strategy is rejected
      When I run "algo-backtest run --strategy bogus --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error names the unknown strategy

    Scenario: a non-positive fast period is rejected
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param fast=0 --param slow=5 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error says the fast period must be positive

    Scenario: a fast period not below the slow period is rejected
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param fast=10 --param slow=10 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error says fast must be below slow

    Scenario Outline: a size outside (0, 1] is rejected (long-only, no leverage)
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param fast=3 --param slow=8 --param size=<size> --param cash=10000"
      Then the run command exits with code 2
      And the error says size must be in range

      Examples:
        | size |
        | -0.5 |
        | 2    |

    Scenario Outline: a non-positive starting cash is rejected (cash=<cash>)
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param fast=3 --param slow=8 --param size=0.5 --param cash=<cash>"
      Then the run command exits with code 2
      And the error says cash must be positive

      Examples:
        | cash |
        | 0    |
        | -1   |

    Scenario: a from-date after the to-date is rejected
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-09 --to 2014-05-07 --param fast=3 --param slow=8 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error says from must not be after to

    Scenario: a --param without an "=" is rejected
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param fast3"
      Then the run command exits with code 2
      And the error says the param must be key=value

  Rule: A run requires materialized data covering its window

    Scenario: no materialized data fails fast before launching the engine
      Given no materialized EUR/USD lean-data
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param fast=3 --param slow=8 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error tells me to run materialize first

    Scenario: data present but not covering the requested window fails fast
      Given materialized EUR/USD minute data with a price swing in 2014-05
      When I run "algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-06-07 --to 2014-06-09 --param fast=3 --param slow=8 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error tells me to run materialize first

  Rule: A validated run executes on the engine and reports its trades

    @integration
    Scenario: baseline-ma generates at least one closed trade on a price swing
      Given materialized EUR/USD minute data with a price swing in 2014-05
      When I run baseline-ma over 2014-05-07 to 2014-05-09 with fast 3, slow 8 and cash 10000
      Then the strategy run exits successfully
      And the parsed result has at least one closed trade
      And a metrics summary is reported
      And the run artifacts are written under the data root

    @integration
    Scenario: a flat market yields no trades but is still a successful run (exit 0)
      Given materialized EUR/USD minute data with a flat price in 2014-05
      When I run baseline-ma over 2014-05-07 to 2014-05-09 with fast 3, slow 8 and cash 10000
      Then the strategy run exits successfully
      And the parsed result has zero closed trades
      And the reported metrics show zero total return and zero max drawdown
