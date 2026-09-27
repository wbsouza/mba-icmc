Feature: Filter-chain mechanics with stub filters
  Proves FilterChain.run()'s accumulate / veto-short-circuit / abstain-does-not-veto
  loop (specs.md §11.3.1) ahead of any real F1-F7 filter, using trivial stub filters
  that always PASS, always VETO, or always ABSTAIN.

  Rule: Non-veto filters accumulate into state.features and state.filter_results

    Scenario: Multiple non-veto filters run in order and contribute to the state
      Given a chain of PASS filters "trend" and "indicator" each enriching a distinct feature
      And a terminal decision-maker that reports "BUY"
      When the chain runs
      Then both filters ran in order
      And state.features holds both filters' enrichment
      And state.filter_results holds both filters' results in order
      And the chain outcome decision is "BUY"
      And every filter received the running state
      And the terminal decision-maker observed the accumulated state

  Rule: A veto short-circuits the chain

    Scenario: A vetoing filter stops the chain before downstream filters run
      Given a chain of a PASS filter "trend", a VETO filter "risk_guard" that also enriches, and a PASS filter "capital"
      And a terminal decision-maker that reports "BUY"
      When the chain runs
      Then the filter "capital" was never called
      And the chain outcome decision is "NO_TRADE"
      And state.features holds the enrichment from filters that ran
      And state.features holds the vetoing filter's own enrichment
      And state.filter_results holds results for filters that ran

  Rule: FilterResult.confidence must be in [0, 1], or absent

    Scenario Outline: an out-of-range confidence is rejected at construction
      When a FilterResult is built with confidence <confidence>
      Then it is rejected for an out-of-range confidence

      Examples:
        | confidence |
        | 1.5        |
        | -0.1       |

    Scenario: an absent confidence is accepted
      When a FilterResult is built with confidence absent
      Then it is accepted

    Scenario Outline: a boundary confidence value is accepted
      When a FilterResult is built with confidence <confidence>
      Then it is accepted

      Examples:
        | confidence |
        | 0.0        |
        | 1.0        |

  Rule: ExecutionState.timestamp must be timezone-aware UTC

    Scenario: a naive timestamp is rejected at construction
      When an ExecutionState is built with a naive timestamp
      Then it is rejected for a non-UTC timestamp

    Scenario: a non-UTC timezone-aware timestamp is rejected at construction
      When an ExecutionState is built with a timestamp in a non-UTC timezone
      Then it is rejected for a non-UTC timestamp

  Rule: An ABSTAIN carries no veto and does not stop the chain

    Scenario: An abstaining filter does not veto and the chain reaches the terminal
      Given a chain of a PASS filter "trend", an ABSTAIN filter "pattern", and a PASS filter "capital"
      And a terminal decision-maker that reports "HOLD"
      When the chain runs
      Then the filter "capital" was called
      And state.filter_results holds a result with recommendation "ABSTAIN" and no veto
      And the chain outcome decision is "HOLD"

  Rule: The real F1-F7 chain reaches a decision via F7TerminalDecision (Spec 04h)
    The chain is built from a strategy config.yaml written in the scenario itself, through
    the same loader and wiring the LEAN algorithm uses, so every threshold and cap is the
    YAML's, not a test constant — and the YAML → engine path is exercised on the way.

    Scenario Outline: <case>
      Given a strategy "probe" whose config.yaml is:
        """
        schema_version: 2
        filters:
          - f1_trend
          - f2_indicator
          - f3_pattern
          - f4_news_context
          - f5_risk_guard
          - f6_capital_mgmt
          - f7_meta_learner
        news_context:
          event_intensity_veto_threshold: -0.5
          sentiment_direction_threshold: 0.15
        risk_guard:
          portfolio_at_risk_cap: 0.10
          daily_drawdown_limit: -0.05
          weekly_drawdown_limit: -0.15
          max_concurrent_trades_per_account: 5
          max_leverage: 30
        capital_mgmt:
          risk_per_trade: 0.03
          stop_loss_pips: 20.0
          pip_value_per_lot: 10.0
          lot_notional_units: 100000
          assumed_leverage: 30
        meta_learner:
          families: [trend, indicator, pattern, news]
          theta_high: 0.55
          theta_low: 0.45
          regime_gate: false
        """
      And the real F1..F7 chain built from the "probe" strategy config, terminated by F7TerminalDecision
      And a bar whose features are:
        | feature                   | value  |
        | trend_direction           | 0.8    |
        | trend_strength            | 40.0   |
        | higher_tf_trend_direction | 0.3    |
        | rsi                       | 70.0   |
        | macd_hist                 | 0.5    |
        | candlestick_pattern       | hammer |
        | account_daily_pnl_fraction  | -0.01 |
        | account_weekly_pnl_fraction | -0.02 |
        | account_open_trade_count  | 1      |
        | account_leverage          | 5.0    |
        | account_balance           | 10000  |
        | pip_value                 | 1.0    |
        | margin_per_lot            | 50.0   |
        | available_margin          | 10000  |
      And the account portfolio-at-risk is <portfolio_at_risk>
      And the day's GDELT event_intensity is <event_intensity>
      And the meta-learner predicts p_hat <p_hat>
      When the real chain runs
      Then the real chain outcome decision is "<decision>"
      And the real chain was vetoed by "<vetoed_by>"
      And every real filter ran in order "<filters_ran>"

      Examples: every filter passes and F7 decides
        | case                                     | portfolio_at_risk | event_intensity | p_hat | decision | vetoed_by | filters_ran                                                                                           |
        | clean bullish bar buys                   | 0.05              | 0.5             | 0.8   | BUY      | none      | F1_trend, F2_indicator, F3_pattern, f4_news_context, f5_risk_guard, f6_capital_mgmt, f7_meta_learner |
        | p_hat inside the band holds              | 0.05              | 0.5             | 0.5   | HOLD     | none      | F1_trend, F2_indicator, F3_pattern, f4_news_context, f5_risk_guard, f6_capital_mgmt, f7_meta_learner |
        | low p_hat sells despite the bull regime  | 0.05              | 0.5             | 0.2   | SELL     | none      | F1_trend, F2_indicator, F3_pattern, f4_news_context, f5_risk_guard, f6_capital_mgmt, f7_meta_learner |

      Examples: a veto short-circuits before the later filters run
        | case                                     | portfolio_at_risk | event_intensity | p_hat | decision | vetoed_by       | filters_ran                                                            |
        | risk-guard breach stops before F6 and F7 | 0.5               | 0.5             | 0.8   | NO_TRADE | f5_risk_guard   | F1_trend, F2_indicator, F3_pattern, f4_news_context, f5_risk_guard     |
        | high-risk news stops before F5, F6, F7   | 0.05              | -5.0            | 0.8   | NO_TRADE | f4_news_context | F1_trend, F2_indicator, F3_pattern, f4_news_context                    |

    Scenario: F7TerminalDecision fails fast if F7 did not run last
      Given a chain of a PASS filter "trend" only, terminated by F7TerminalDecision
      When the real chain runs expecting failure
      Then the real chain fails naming "f7_meta_learner"

    Scenario: F7TerminalDecision fails fast on an empty chain (no filters at all)
      Given an empty chain terminated by F7TerminalDecision
      When the real chain runs expecting failure
      Then the real chain fails naming "state.filter_results is empty"

  Rule: decision_to_order_action classifies every chain Decision (Spec 04h)

    Scenario Outline: a Decision maps to the right order action
      When chain Decision "<decision>" is classified
      Then the order action is "<action>"

      Examples:
        | decision | action      |
        | BUY      | execute     |
        | SELL     | execute     |
        | HOLD     | manage      |
        | NO_TRADE | stand_aside |
