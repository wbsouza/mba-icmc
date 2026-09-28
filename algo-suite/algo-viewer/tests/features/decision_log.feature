Feature: Decision log
  The run page lists every chain evaluation of the run, one row per bar, and says why a bar
  was vetoed as "parameter: observed vs limit" (`risk_guard.daily_drawdown_limit: -0.074 <
  -0.05`). Consecutive bars with the same outcome, vetoing filter and breached parameter
  collapse into one row ("×14 bars, first → last") so a long drawdown lock does not flood the
  page. Vetoed rows are salmon; clicking a row expands that bar's full chain, where the step
  that vetoed is salmon too and carries the same why line. Modes: vetoes (default), entries,
  every bar; pages of 200 rows.

  Background:
    Given the fixture results database is open

  Scenario: the vetoes mode lists the vetoed bars, collapsed, with why each was vetoed
    When I open the run page of "20260928T010000-fixture"
    Then the decision log summary reads "5 bar(s) in 4 row(s) · page 1 of 1"
    And the decision log rows are:
      | when                                          | decision | vetoed_by       | why                                                           | vetoed |
      | 2016-03-02 09:00                              | NO_TRADE | volume_strength | volume_strength.min_relative_activity: 0.74 < 1               | yes    |
      | 2016-03-02 11:00                              | NO_TRADE | f5_risk_guard   | risk_guard.max_concurrent_trades_per_account: 1 ≥ 1           | yes    |
      | ×2 bars, 2016-03-03 09:00 → 2016-03-03 10:00  | NO_TRADE | f5_risk_guard   | risk_guard.daily_drawdown_limit: -0.0744 < -0.05              | yes    |
      | 2016-03-04 09:00                              | NO_TRADE | f4_news_context | news_context.event_intensity_veto_threshold: -0.731 ≤ -0.5    | yes    |

  Scenario: the entries mode lists the two entries and the every-bar mode every evaluation
    When I open the run page of "20260928T010000-fixture"
    And I switch the decision log to "Entries"
    Then the decision log summary reads "2 bar(s) in 2 row(s) · page 1 of 1"
    And the decision log rows are:
      | when             | decision | vetoed_by | why | vetoed |
      | 2016-03-02 10:00 | BUY      |           |     | no     |
      | 2016-03-10 08:00 | SELL     |           |     | no     |
    When I switch the decision log to "Every bar"
    Then the decision log summary reads "7 bar(s) in 6 row(s) · page 1 of 1"

  Scenario: clicking a vetoed row expands that bar's chain with the vetoing step marked and explained
    When I open the run page of "20260928T010000-fixture"
    And I click the decision log row at "2016-03-04 09:00"
    Then the expanded chain has 4 steps
    And the expanded chain step "f4_news_context" is vetoed with why "news_context.event_intensity_veto_threshold: -0.731 ≤ -0.5"
    And the expanded chain step "F1_trend" is not vetoed

  Scenario Outline: a veto reason becomes "parameter: observed vs limit" (<filter>)
    Given the run parameter "volume_strength.min_relative_activity" is "1.0"
    When the filter "<filter>" vetoed with reason "<reason>"
    Then the why line is "<why>" naming the parameter "<parameter>"

    Examples:
      | filter          | reason                                                                                              | why                                                                                                 | parameter                                    |
      | f5_risk_guard   | daily_pnl_fraction -0.0744 is below limit -0.05                                                     | risk_guard.daily_drawdown_limit: -0.0744 < -0.05                                                    | risk_guard.daily_drawdown_limit              |
      | f5_risk_guard   | weekly_pnl_fraction -0.1612 is below limit -0.15                                                    | risk_guard.weekly_drawdown_limit: -0.161 < -0.15                                                    | risk_guard.weekly_drawdown_limit             |
      | f5_risk_guard   | portfolio_at_risk 0.2103 exceeds cap 0.18                                                           | risk_guard.portfolio_at_risk_cap: 0.21 > 0.18                                                       | risk_guard.portfolio_at_risk_cap             |
      | f5_risk_guard   | open_trade_count 2 has reached the cap 2                                                            | risk_guard.max_concurrent_trades_per_account: 2 ≥ 2                                                 | risk_guard.max_concurrent_trades_per_account |
      | f5_risk_guard   | leverage 31.4 exceeds cap 30                                                                        | risk_guard.max_leverage: 31.4 > 30                                                                  | risk_guard.max_leverage                      |
      | f5_risk_guard   | daily_pnl_fraction -0.06 is below limit -0.05; open_trade_count 2 has reached the cap 2             | risk_guard.daily_drawdown_limit: -0.06 < -0.05; risk_guard.max_concurrent_trades_per_account: 2 ≥ 2 | risk_guard.daily_drawdown_limit              |
      | f4_news_context | active high-risk event: event_intensity=-0.7312 <= veto threshold -0.5000                           | news_context.event_intensity_veto_threshold: -0.731 ≤ -0.5                                          | news_context.event_intensity_veto_threshold  |
      | volume_strength | relative tick activity 0.74                                                                         | volume_strength.min_relative_activity: 0.74 < 1                                                     | volume_strength.min_relative_activity        |
      | volume_strength | tick activity unavailable (warm-up or zero baseline)                                                | tick activity unavailable (warm-up or zero baseline)                                                |                                              |
      | f6_capital_mgmt | reward:risk below capital_mgmt.min_reward_risk 2.0: long 1.5, short 1.5; trade plan from swing stop | capital_mgmt.min_reward_risk: long 1.5, short 1.5 < 2                                               | capital_mgmt.min_reward_risk                 |
      | f6_capital_mgmt | insufficient margin: proposed lot 3.0 needs 10000.0 but only 9500.0 is available; trade plan        | capital_mgmt.assumed_leverage: lot 3 needs margin 10000 > available 9500                            | capital_mgmt.assumed_leverage                |
      | F1_trend        | direction conflict: primary trend_direction=1.0 vs. higher_tf_trend_direction=-1.0                  | price_features.ema_higher_tf: primary trend 1 vs higher timeframe -1                                | price_features.ema_higher_tf                 |
      | f9_unknown      | something new the viewer does not parse                                                             | something new the viewer does not parse                                                             |                                              |

  Scenario Outline: consecutive bars collapse only when outcome, vetoing filter and parameter agree
    Given the log rows:
      | time             | decision | vetoed_by     | reason                                            | trade |
      | 2016-03-03 09:00 | NO_TRADE | f5_risk_guard | daily_pnl_fraction -0.0744 is below limit -0.05   |       |
      | 2016-03-03 10:00 | NO_TRADE | f5_risk_guard | daily_pnl_fraction -0.0712 is below limit -0.05   |       |
      | 2016-03-03 11:00 | NO_TRADE | f5_risk_guard | open_trade_count 1 has reached the cap 1          | 1     |
      | 2016-03-03 12:00 | BUY      |               |                                                   | 2     |
      | 2016-03-03 13:00 | BUY      |               |                                                   | 2     |
    Then the grouped log is <groups>

    Examples:
      | groups                                                                                                   |
      | ×2 daily_drawdown_limit @2016-03-03 09:00→10:00; ×1 max_concurrent_trades_per_account @2016-03-03 11:00→11:00; ×2 BUY @2016-03-03 12:00→13:00 |
