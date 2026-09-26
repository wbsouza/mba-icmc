Feature: Run the F1-F7 hybrid chain (with F4/news) via the run CLI (wiring smoke test)
  `algo-backtest run --strategy hybrid` wires the config.yaml-driven F1+F2+F3+F4+F5+F6+F7
  chain (baseline's chain plus F4/news) into a real LEAN algorithm (Spec 04h). This is a
  wiring smoke test, not a methodology result -- see technical-debt.md's TD-51 and
  docs/stories/planned/04h-algo-backtest-hybrid-integration/progress.md: F3's
  candlestick-pattern feature is never populated (no real detector), F5/F6's
  account-risk features use fixed placeholder economics (no real ATR/margin model),
  F7's meta-learner is trained on a short window by
  scripts/train_hybrid_meta_learner.py, and F4's per-symbol sentiment is best-effort
  pending TD-48 -- only its GDELT event-intensity veto input is real.

  Rule: Inputs are validated before any container starts

    Scenario: a size outside (0, 1] is rejected
      When I run "algo-backtest run --strategy hybrid --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=2"
      Then the run command exits with code 2
      And the error says size must be in range

    Scenario: an unknown param is rejected
      When I run "algo-backtest run --strategy hybrid --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param bogus=1"
      Then the run command exits with code 2
      And the error says params must be exactly

    Scenario: a missing required param is rejected
      When I run "algo-backtest run --strategy hybrid --symbol EURUSD --from 2014-05-07 --to 2014-05-08"
      Then the run command exits with code 2
      And the error says params must be exactly

  Rule: A validated run executes the full F1-F7 chain, including F4/news, without crashing

    @integration
    Scenario: the hybrid chain runs to completion against a price swing with no active news veto
      Given materialized EUR/USD minute data with a price swing in 2014-05
      And a synthetic GDELT event-feature Parquet for 2014-05 with no active high-risk event
      When I run hybrid over 2014-05-07 to 2014-05-09 with size 0.5
      Then the strategy run exits successfully
      And a metrics summary is reported
      And the run artifacts are written under the data root
      And the container log shows the F1-F7 hybrid chain actually evaluated a decision
      And decisions.parquet is written under the run's results directory
      And every decisions.parquet row's trade_id is null or a real trades.json entry order id

    @integration
    Scenario: an active high-risk event vetoes every bar
      Given materialized EUR/USD minute data with a price swing in 2014-05
      And a synthetic GDELT event-feature Parquet for 2014-05 with an active high-risk event
      When I run hybrid over 2014-05-07 to 2014-05-09 with size 0.5
      Then the strategy run exits successfully
      And no trade was ever opened
