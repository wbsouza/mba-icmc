Feature: Chain wiring shared by the chain-driven LEAN algorithms and F7 training
  `algo_backtest.chain.wiring` is the LEAN-free half of `engine/chain_algorithm.py`:
  it builds a strategy's filter chain from its resolved config.yaml (filter list plus
  each filter's own parameter section), turns indicator and portfolio readings into the
  ExecutionState.features contract, and tracks day/week PnL anchors. The F7 training scripts build their rows through the same
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

    Scenario Outline: The ATR reading is carried under atr_pips exactly as given (<case>)
      When price features are built for price 1.1000, fast EMA 1.1000, slow EMA 1.1000, HTF EMA 1.1000 with atr_pips <atr_pips>
      Then feature "atr_pips" is <atr_pips>
      And feature "trend_direction" is 0

      Examples:
        | case          | atr_pips |
        | quiet market  | 3.25     |
        | volatile bar  | 42       |

    Scenario: Without an ATR reading the features carry no atr_pips key rather than an invented one
      When price features are built for price 1.1000, fast EMA 1.1000, slow EMA 1.1000, HTF EMA 1.1000
      Then the features carry none of "atr_pips, swing_low_pips, swing_high_pips"

    Scenario Outline: The swing distances are carried under swing_low_pips / swing_high_pips exactly as given (<case>)
      When price features are built for price 1.1000, fast EMA 1.1000, slow EMA 1.1000, HTF EMA 1.1000 with swing_low_pips <low> and swing_high_pips <high>
      Then feature "swing_low_pips" is <low>
      And feature "swing_high_pips" is <high>
      And the features carry none of "atr_pips"

      Examples:
        | case               | low  | high |
        | price near the low | 2.5  | 38   |
        | price at the high  | 40   | 0    |

  Rule: The pip is the instrument's price-movement unit, never a literal
    Live, LEAN's symbol properties give the minimum price variation (the 5-digit
    "pipette"); the pip is ten of those by the FX quoting convention. Offline, the
    Instrument's unit_size is the same pip.

    Scenario Outline: A pip is ten times LEAN's minimum price variation (<pair>)
      When the pip size is derived from a minimum price variation of <variation>
      Then the pip size is <pip>
      And it equals the unit_size of instrument "<pair>"

      Examples:
        | pair   | variation | pip    |
        | EURUSD | 0.00001   | 0.0001 |
        | USDJPY | 0.001     | 0.01   |

    Scenario: A non-positive minimum price variation fails fast
      When deriving the pip size from a minimum price variation of 0 fails
      Then building fails naming "minimum price variation"

  Rule: Account features follow the F5/F6 contract

    Scenario: A net-short portfolio's leverage is its unsigned holdings over equity
      Given an invested account worth 10000 holding -50000 with unrealized profit -200
      When account features are built at price 1.1000 with the real baseline capital_mgmt section
      Then feature "account_leverage" is 5
      And feature "account_portfolio_at_risk" is 0.02
      And feature "account_open_trade_count" is 1

    Scenario: A flat account has no portfolio at risk
      Given a flat account worth 10000
      When account features are built at price 1.1000 with the real baseline capital_mgmt section
      Then feature "account_portfolio_at_risk" is 0
      And feature "account_open_trade_count" is 0

    Scenario: An invested account with no equity left reports zero at-risk and leverage instead of dividing by zero
      Given an invested account worth 0 holding -50000 with unrealized profit -200
      When account features are built at price 1.1000 with the real baseline capital_mgmt section
      Then feature "account_portfolio_at_risk" is 0
      And feature "account_leverage" is 0
      And feature "account_open_trade_count" is 1

    Scenario Outline: Every F5/F6 account reading is carried under its contract key (<case>)
      Given a flat account worth 10000 with cash <cash>, margin remaining <margin>, daily PnL fraction <daily> and weekly PnL fraction <weekly>
      When account features are built at price 1.1000 without a capital_mgmt section
      Then feature "account_balance" is <cash>
      And feature "available_margin" is <margin>
      And feature "account_daily_pnl_fraction" is <daily>
      And feature "account_weekly_pnl_fraction" is <weekly>

      Examples:
        | case               | cash  | margin | daily | weekly |
        | mixed day and week | 8000  | 6000   | 0.01  | -0.02  |
        | losing week        | 9500  | 9500   | -0.03 | -0.05  |

    Scenario Outline: The F6 sizing inputs come from the capital_mgmt section, not constants (<case>)
      Given a flat account worth 10000
      When account features are built at price <price> with capital_mgmt stop_loss_pips <stop>, pip_value_per_lot <pip>, lot_notional_units <lot>, assumed_leverage <lev>
      Then feature "pip_value" is <pip>
      And feature "margin_per_lot" is <margin>

      Examples:
        | case                 | price | stop | pip | lot    | lev | margin |
        | standard lot at 30x  | 1.1   | 20   | 10  | 100000 | 30  | 3666.6666667 |
        | mini lot at 50x      | 1.25  | 15   | 1   | 10000  | 50  | 250    |
        | unlevered            | 2.0   | 5    | 10  | 100000 | 1   | 200000 |
        | zero price           | 0     | 20   | 10  | 100000 | 30  | 0      |

    Scenario: A strategy without F6 gets no sizing inputs rather than invented ones
      Given a flat account worth 10000
      When account features are built at price 1.1000 without a capital_mgmt section
      Then feature "account_balance" is 10000
      And the features carry none of "pip_value, margin_per_lot"

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

  Rule: A strategy's resolved config builds the chain in declared order with each filter's own parameters

    Scenario: The hybrid config builds all seven filters in order when a news index is given
      When the hybrid config's filters are built with a news index
      Then the chain's filters are "f1_trend, f2_indicator, f3_pattern, f4_news_context, f5_risk_guard, f6_capital_mgmt, f7_meta_learner"
      And the built F7 filter carries the hybrid config's thresholds and regime gate
      And the built F5 filter carries the hybrid config's risk-guard caps
      And the built F6 filter carries the hybrid config's capital_mgmt section and execution spread
      And the built F4 filter carries the hybrid config's news-context thresholds

    Scenario: F4 without a news index fails fast
      When the hybrid config's filters are built without a news index
      Then building fails naming "needs_news_data"

    Scenario: An unknown filter name fails fast
      When filters "f1_trend, f9_bogus" are built
      Then building fails naming "unknown filter 'f9_bogus'"

    Scenario Outline: A configurable filter whose section was never parsed fails fast (<filter>)
      When filters "f1_trend, <filter>" are built
      Then building fails naming "has no parsed '<section>' section"
      And building fails naming "load_strategy_chain_config"

      Examples:
        | filter          | section      |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |
        | f7_meta_learner | meta_learner |

    Scenario: F4 whose section was never parsed fails fast even when a news index is given
      When filters "f1_trend, f4_news_context" are built with an empty news index
      Then building fails naming "has no parsed 'news_context' section"
      And building fails naming "load_strategy_chain_config"

  Rule: The bundled risk caps follow RiskGuard's sign contract

    Scenario: A flat account at break-even passes F5 under the real baseline risk_guard caps
      Given a flat account worth 10000
      When F5 evaluates the account under the real baseline risk_guard caps
      Then F5 does not veto

    Scenario: A positive (sign-flipped) drawdown limit is rejected at construction
      When risk-guard caps are built with daily_drawdown_limit 0.05
      Then building fails naming "must be <= 0"
