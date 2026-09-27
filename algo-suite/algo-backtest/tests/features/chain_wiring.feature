Feature: Chain wiring shared by the chain-driven LEAN algorithms and F7 training
  `algo_backtest.chain.wiring` is the LEAN-free half of `engine/chain_algorithm.py`:
  it builds a strategy's filter chain from its config.yaml list, turns indicator and
  portfolio readings into the ExecutionState.features contract, and tracks day/week
  PnL anchors. The F7 training scripts build their rows through the same
  price_features(), so train and serve share one feature definition.

  Rule: Price features follow the F1/F2/F3 contract

    Scenario: A fast EMA above the slow EMA is an up-trend, price below the HTF EMA a down HTF trend
      When price features are built for price 1.1000, fast EMA 1.1010, slow EMA 1.1000, HTF EMA 1.1050
      Then feature "trend_direction" is 1
      And feature "higher_tf_trend_direction" is -1
      And feature "candlestick_pattern" is missing

    Scenario: The EMA-gap trend strength is clamped to F1's [0, 100] range
      When price features are built for price 1.0000, fast EMA 1.0200, slow EMA 1.0000, HTF EMA 1.0000
      Then feature "trend_strength" is 100

    Scenario: Equal EMAs are no trend
      When price features are built for price 1.1000, fast EMA 1.1000, slow EMA 1.1000, HTF EMA 1.1000
      Then feature "trend_direction" is 0
      And feature "trend_strength" is 0

  Rule: Account features follow the F5/F6 contract

    Scenario: A net-short portfolio's leverage is its unsigned holdings over equity
      Given an invested account worth 10000 holding -50000 with unrealized profit -200
      When account features are built at price 1.1000
      Then feature "account_leverage" is 5
      And feature "account_portfolio_at_risk" is 0.02
      And feature "account_open_trade_count" is 1

    Scenario: A flat account has no portfolio at risk
      Given a flat account worth 10000
      When account features are built at price 1.1000
      Then feature "account_portfolio_at_risk" is 0
      And feature "account_open_trade_count" is 0

  Rule: PnL anchors reset at each new UTC day and ISO week

    Scenario: The daily anchor resets on a new day but the weekly anchor carries over
      Given PnL windows anchored at equity 10000 on "2024-01-02T10:00:00+00:00"
      When equity 10100 is observed on "2024-01-02T15:00:00+00:00"
      Then the daily PnL fraction is 0.01 and the weekly PnL fraction is 0.01
      When equity 10200 is observed on "2024-01-03T00:00:00+00:00"
      Then the daily PnL fraction is 0 and the weekly PnL fraction is 0.02

    Scenario: The weekly anchor resets on a new ISO week
      Given PnL windows anchored at equity 10000 on "2024-01-07T23:59:00+00:00"
      When equity 10500 is observed on "2024-01-08T00:00:00+00:00"
      Then the daily PnL fraction is 0 and the weekly PnL fraction is 0

  Rule: A strategy's filter list builds the chain in declared order, failing fast on gaps

    Scenario: The hybrid filter list builds all seven filters in order when a news index is given
      When the hybrid config's filters are built with a news index
      Then the chain's filters are "f1_trend, f2_indicator, f3_pattern, f4_news_context, f5_risk_guard, f6_capital_mgmt, f7_meta_learner"

    Scenario: F4 without a news index fails fast
      When the hybrid config's filters are built without a news index
      Then building fails naming "needs_news_data"

    Scenario: An unknown filter name fails fast
      When filters "f1_trend, f9_bogus" are built
      Then building fails naming "unknown filter 'f9_bogus'"

  Rule: The smoke-test risk caps follow RiskGuard's sign contract

    Scenario: A flat account at break-even passes F5 under the wiring's placeholder caps
      Given a flat account worth 10000
      When F5 evaluates the account under the wiring's placeholder caps
      Then F5 does not veto

    Scenario: A positive (sign-flipped) drawdown limit is rejected at construction
      When risk-guard caps are built with daily_drawdown_limit 0.05
      Then building fails naming "must be <= 0"
