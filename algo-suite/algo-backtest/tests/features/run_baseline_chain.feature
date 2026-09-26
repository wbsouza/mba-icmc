Feature: Run the F1-F7 baseline chain via the run CLI (wiring smoke test)
  `algo-backtest run --strategy baseline` wires the config.yaml-driven F1+F2+F3+F5+F6+F7
  chain (no F4/news) into a real LEAN algorithm for the first time (2026-09-26). This is
  a wiring smoke test, not a methodology result -- see technical-debt.md's TD-51 and
  docs/stories/planned/04h-algo-backtest-hybrid-integration/progress.md: F3's
  candlestick-pattern feature is never populated (no real detector), F5/F6's
  account-risk features use fixed placeholder economics (no real ATR/margin model), and
  F7's meta-learner is trained on a short window by
  scripts/train_baseline_meta_learner.py, not a statistically meaningful model.

  Rule: Inputs are validated before any container starts

    Scenario: a size outside (0, 1] is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=2"
      Then the run command exits with code 2
      And the error says size must be in range

    Scenario: an unknown param is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param bogus=1"
      Then the run command exits with code 2

  Rule: A validated run executes the full F1-F7 chain on the engine without crashing

    @integration
    Scenario: the baseline chain runs to completion against a price swing
      Given materialized EUR/USD minute data with a price swing in 2014-05
      When I run baseline over 2014-05-07 to 2014-05-09 with size 0.5
      Then the strategy run exits successfully
      And a metrics summary is reported
      And the run artifacts are written under the data root
      And the container log shows the F1-F7 chain actually evaluated a decision
