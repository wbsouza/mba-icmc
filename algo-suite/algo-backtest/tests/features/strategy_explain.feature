Feature: explain-strategy shows the resolved parameters and where each one came from
  `algo-backtest explain-strategy <name> [--strategies-dir DIR]` prints every resolved
  parameter of a strategy as `key = value  # <source>`, the source being the config.yaml
  in the extends chain that set it or `default` (2026-09-27, story 09). The same map is
  written next to every run as `strategy-provenance.json`.

  Scenario Outline: bundled strategies explain their inheritance (<name>: <key>)
    When I run "algo-backtest explain-strategy <name>"
    Then the explain command exits with code 0
    And the explanation lists "<key>" from "<source>"

    Examples:
      | name   | key                                          | source               |
      | hybrid | news_context.event_intensity_veto_threshold  | hybrid/config.yaml   |
      | hybrid | risk_guard.max_leverage                      | baseline/config.yaml |
      | hybrid | meta_learner.regime_gate                     | baseline/config.yaml |
      | hybrid | filters                                      | hybrid/config.yaml   |
      | hybrid | capital_mgmt.min_reward_risk                 | baseline/config.yaml |
      | hybrid | execution.spread_pips                        | baseline/config.yaml |
      | hybrid | capital_mgmt.risk_per_trade                  | baseline/config.yaml |
      | news-only | filters                                   | news-only/config.yaml |
      | news-only | meta_learner.families                     | news-only/config.yaml |
      | news-only | capital_mgmt.stop_loss_shrink             | news-only/config.yaml |
      | news-only | price_features.swing_lookback_bars        | baseline/config.yaml |
      | news-only-h4 | price_features.bar_minutes             | news-only-h4/config.yaml |
      | news-only-h4 | risk_guard.portfolio_at_risk_cap       | news-only/config.yaml |
      | news-rule | terminal_filter                           | news-rule/config.yaml |
      | news-rule | news_context.direction_source             | news-rule/config.yaml |
      | news-rule | news_context.intensity_buy_threshold      | news-rule/config.yaml |
      | news-rule | capital_mgmt.targets                      | news-only/config.yaml |
      | news-rule-h4 | price_features.bar_minutes             | news-rule-h4/config.yaml |
      | news-rule-h4 | news_context.intensity_sell_threshold  | news-rule/config.yaml |

  Scenario: an external variant explains both its own keys and the defaults it inherited
    Given an external strategies directory holding "tight" extending "baseline" with extra "{meta_learner: {theta_high: 0.6}}"
    When I run explain-strategy for "tight" with that directory
    Then the explain command exits with code 0
    And the explanation lists "meta_learner.theta_high" from "tight/config.yaml"
    And the explanation lists "meta_learner.theta_low" from "baseline/config.yaml"

  Scenario: an unknown strategy is a usage error naming what is available
    When I run "algo-backtest explain-strategy nope"
    Then the explain command exits with code 2
    And the explain output names "nope"
