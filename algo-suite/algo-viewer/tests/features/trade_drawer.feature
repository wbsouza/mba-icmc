Feature: Trade drawer
  Clicking a trade opens a drawer that explains why the chain entered it: the filters at
  the entry bar in order, F3's candlestick pattern with a plain-English description and
  direction, F7's probability against its thresholds, the plan, the exit and the P/L.

  Background:
    Given the fixture results database is open

  Scenario: the drawer explains the entry chain, names the pattern and the exit kind
    When I open trade "1" of run "20260928T010000-fixture"
    Then the drawer lists the chain steps in order:
      | step                     | recommendation |
      | F1 · Trend               | BUY            |
      | F2 · RSI / MACD          | BUY            |
      | F3 · Candlestick pattern | BUY            |
      | F4 · News context        | ABSTAIN        |
      | Activity ratio           | ABSTAIN        |
      | F5 · Risk guard          | ABSTAIN        |
      | F6 · Capital management  | ABSTAIN        |
      | F7 · Meta-learner        | BUY            |
    And the drawer names the pattern "Hammer"
    And the drawer describes the pattern with "closed near its high"
    And the drawer step "F7 · Meta-learner" reads "p̂ = 0.610, at or above θ_high 0.55 → BUY."
    And the drawer step "Activity ratio" reads "Tick activity 1.62× its recent average, at or above the 1.0 minimum."
    And the drawer shows the exit kind "Take profit"
    And the drawer shows the plan stop "1.09800 (20.0 pips)"
    And the drawer shows the realized P/L "500.00"
    And the drawer offers 5 entry bars

  Scenario: a trade without a pattern says F3 abstained and shows its trail moves
    When I open trade "5" of run "20260928T010000-fixture"
    Then the drawer step "F3 · Candlestick pattern" reads "No candlestick pattern on the decision bar; F3 abstained."
    And the drawer shows the exit kind "Trailing stop"
    And the drawer lists the trail move "2016-03-10 12:00: 1.12800 → 1.12700"

  Scenario Outline: each filter's reason becomes one plain-English line
    Given a filter row "<filter>" recommending <recommendation> with veto <veto> and reason "<reason>"
    Then its explanation summary is "<summary>"

    Examples:
      | filter          | recommendation | veto | reason                                                                       | summary                                                                                |
      | F1_trend        | SELL           | no   | trend_direction=-1.0, trend_strength=2.1, higher_tf_trend_direction=-1.0     | Primary trend down, higher-timeframe trend down → leaning SELL.                        |
      | F1_trend        | NEUTRAL        | yes  | direction conflict: primary trend_direction=1.0 vs. higher_tf_trend_direction=-1.0 | The primary trend (up) disagrees with the higher timeframe (down); the chain stood aside. |
      | F2_indicator    | SELL           | no   | rsi=41.8, macd_hist=-0.00012, rsi_midline=50.0, macd_hist_threshold=0.0      | RSI 41.8 below its 50 midline, MACD histogram negative → SELL.                         |
      | F3_pattern      | SELL           | no   | detected candlestick pattern 'shooting_star'                                 | Shooting star (bearish) → SELL.                                                        |
      | f7_meta_learner | HOLD           | no   | p_hat=0.5012, theta_high=0.55, theta_low=0.45, regime_gate=True, regime=bear | p̂ = 0.501, between the thresholds → HOLD.                                              |
      | f7_meta_learner | SELL           | no   | p_hat=0.41, theta_high=0.55, theta_low=0.45, regime_gate=False, regime=n/a   | p̂ = 0.410, at or below θ_low 0.45 → SELL.                                              |
      | volume_strength | ABSTAIN        | yes  | relative tick activity 0.74                                                  | Tick activity 0.74× its recent average, below the 1.0 minimum.                          |
      | f5_risk_guard   | ABSTAIN        | no   | no risk-guard caps breached                                                  | No risk-guard cap (daily/weekly drawdown, leverage, concurrent trades) was breached.    |
