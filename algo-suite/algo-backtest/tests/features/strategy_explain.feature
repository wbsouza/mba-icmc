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
