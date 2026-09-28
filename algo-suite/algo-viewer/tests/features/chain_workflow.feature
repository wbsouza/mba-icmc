Feature: Chain workflow
  The run page draws the strategy as the chain it is: the filters in the order the run's
  `filters` parameter lists them, each node showing how many bars it vetoed. Clicking a
  node opens a panel below with what the filter does, what it reads and emits, and the
  run's parameters for that filter with the config file that set each one.

  Background:
    Given the fixture results database is open

  Scenario: the workflow lists the run's filters in order with their veto counts
    When I open the run page of "20260928T010000-fixture"
    Then the chain workflow nodes are, in order:
      | node            | label               | vetoes |
      | f1_trend        | F1 Trend            | 0      |
      | f2_indicator    | F2 RSI / MACD       | 0      |
      | f3_pattern      | F3 Candlestick      | 0      |
      | f4_news_context | F4 News context     | 0      |
      | volume_strength | Activity ratio      | 1      |
      | f5_risk_guard   | F5 Risk guard       | 0      |
      | f6_capital_mgmt | F6 Capital mgmt     | 0      |
      | f7_meta_learner | F7 Meta-learner     | 0      |
    And no filter details are shown

  Scenario: clicking a node shows that filter's parameters with provenance
    When I open the run page of "20260928T010000-fixture"
    And I click the chain node "f3_pattern"
    Then the filter details are titled "F3 Candlestick pattern"
    And the filter details list the parameters:
      | key              | value   | source             |
      | pattern.detector | "talib" | hybrid/config.yaml |
    When I click the chain node "f7_meta_learner"
    Then the filter details are titled "F7 Meta-learner"
    And the filter details list the parameters:
      | key                      | value | source              |
      | meta_learner.regime_gate | false | hybrid/config.yaml  |
      | meta_learner.theta_high  | 0.55  | h4-base/config.yaml |
      | meta_learner.theta_low   | 0.45  | h4-base/config.yaml |
    When I click the chain node "f7_meta_learner"
    Then no filter details are shown

  Scenario Outline: every filter's parameters come from its own config sections
    Given the run parameters:
      | key                            | value |
      | price_features.ema_fast        | 3     |
      | price_features.rsi_period      | 14    |
      | price_features.atr_period      | 14    |
      | indicator.rsi_midline          | 50.0  |
      | pattern.detector               | talib |
      | volume_strength.lookback       | 20    |
      | risk_guard.max_leverage        | 30    |
      | capital_mgmt.risk_per_trade    | 0.03  |
      | execution.spread_pips          | 1.0   |
      | meta_learner.theta_high        | 0.55  |
      | news_context.sentiment_direction_threshold | 0.15 |
    Then the parameters of filter "<filter>" are <keys>

    Examples:
      | filter          | keys                                                   |
      | f1_trend        | price_features.ema_fast                                |
      | f2_indicator    | indicator.rsi_midline, price_features.rsi_period       |
      | f3_pattern      | pattern.detector                                       |
      | f4_news_context | news_context.sentiment_direction_threshold             |
      | volume_strength | volume_strength.lookback                               |
      | f5_risk_guard   | risk_guard.max_leverage                                |
      | f6_capital_mgmt | capital_mgmt.risk_per_trade, execution.spread_pips, price_features.atr_period |
      | f7_meta_learner | meta_learner.theta_high                                |
