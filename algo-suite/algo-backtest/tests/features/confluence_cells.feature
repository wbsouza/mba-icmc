Feature: Fourteen-cell manifest generator — the fixed confluence-chain study grid (story 21, T10)
  Proves `experiments/confluence-chain/make_cells.py`, the deterministic generator of the
  seven registered arms times two clocks (spec CC-21, CC-23, CC-28; decisions D3, D7, D9,
  D11). The arms are A, B, A-plan, T-only, M-only, always-short and always-long; the
  clocks are H1 (60 minutes, momentum L=480) and H4 (240 minutes, momentum L=120). No
  other arm, clock, threshold search or confirmatory dataset is ever produced — Story 22's
  candlestick/support-resistance arms and Story 19's F7/adaptive-model integration are out
  of scope for these 14 cells (CC-23). Every cell shares EUR/USD, a USD 10,000 account,
  the pinned OANDA cost/broker-floor settings, F5 caps (portfolio-at-risk 0.18, daily
  drawdown -0.05, weekly drawdown -0.15, max concurrent 2, leverage 30) and the window
  2016-03-01..2017-02-28 inclusive. Six of the seven arms use the time-exit plan (targets
  and trail_stops empty, `exit_after_bars: 4`, `min_hold_bars: 4`); A-plan instead pins
  every inherited stop/target/trail setting of the existing Heikin-Ashi H4 reference
  strategy, disclosing that it compares complete exit policies rather than isolating the
  trigger (D11). The generator writes one config.yaml per cell plus a manifest recording
  each cell's effective configuration hash, under a caller-selected job directory.

  Background:
    Given a caller-selected job directory

  Rule: The manifest contains exactly 14 unique cells: 7 arms times 2 clocks (CC-23, CC-28)

    Scenario: generating the manifest produces exactly 14 unique cell IDs
      When the fourteen-cell manifest is generated
      Then the manifest lists exactly 14 cells
      And every cell ID in the manifest is unique
      And the manifest's arms are exactly "A, B, A-plan, T-only, M-only, always-short, always-long"
      And each arm appears exactly once on clock 60 minutes and once on clock 240 minutes
      And the "A" cell on clock 60 minutes has cell ID "a-h1"
      And the "A-plan" cell on clock 240 minutes has cell ID "a-plan-h4"
      And the "always-long" cell on clock 60 minutes has cell ID "always-long-h1"

    Scenario Outline: each cell's clock carries the registered momentum lookback (<clock_label>) (CC-28)
      When the fourteen-cell manifest is generated
      Then every "<clock_label>" cell has clock_minutes <clock_minutes>
      And every "<clock_label>" cell has momentum lookback_bars <lookback>

      Examples:
        | clock_label | clock_minutes | lookback |
        | H1          | 60            | 480      |
        | H4          | 240           | 120      |

  Rule: Each arm's required-voter list matches the registered design (CC-23)

    Scenario Outline: the "<arm>" arm requires exactly "<required_voters>" (<case>)
      When the fourteen-cell manifest is generated
      Then every "<arm>" cell requires exactly the voters "<required_voters>"

      Examples:
        | case                                   | arm           | required_voters                       |
        | A requires momentum and relative trigger | A            | f1_trend, f4_news_context             |
        | B adds the F2 indicator                 | B             | f1_trend, f4_news_context, f2_indicator |
        | A-plan requires the same voters as A     | A-plan        | f1_trend, f4_news_context             |
        | T-only requires only the trigger         | T-only        | f4_news_context                       |
        | M-only requires only the context         | M-only        | f1_trend                              |
        | always-short requires only its own vote  | always-short  | constant_direction                    |
        | always-long requires only its own vote   | always-long   | constant_direction                    |

  Rule: Controls and M-only carry no news dependency; A/B/T-only do (CC-23, D9)

    Scenario Outline: the "<arm>" arm's manifest entry has no news_context section (<case>)
      When the fourteen-cell manifest is generated
      Then no "<arm>" cell's config declares a "news_context" section

      Examples:
        | case                        | arm           |
        | M-only has no news section  | M-only        |
        | always-short has no news    | always-short  |
        | always-long has no news     | always-long   |

    Scenario Outline: the "<arm>" arm's manifest entry declares a news_context section with direction_source intensity_relative (<case>)
      When the fourteen-cell manifest is generated
      Then every "<arm>" cell's config declares a "news_context" section with direction_source "intensity_relative" and intensity_sign -1

      Examples:
        | case             | arm     |
        | A uses the trigger | A     |
        | B uses the trigger | B     |
        | T-only is the trigger | T-only |

  Rule: Six of the seven arms use the registered time-exit plan on both clocks (CC-21)

    Scenario Outline: the "<arm>" arm's time plan has empty targets/trail_stops, exit_after_bars 4 and min_hold_bars 4 (<case>)
      When the fourteen-cell manifest is generated
      Then every "<arm>" cell's config has capital_mgmt targets []
      And every "<arm>" cell's config has capital_mgmt trail_stops []
      And every "<arm>" cell's config has capital_mgmt exit_after_bars 4
      And every "<arm>" cell's config has execution min_hold_bars 4
      And every "<arm>" cell's config has capital_mgmt risk_per_trade 0.03
      And every "<arm>" cell's config has capital_mgmt stop_distance_source "atr"
      And every "<arm>" cell's config has capital_mgmt atr_multiplier 2.0

      Examples:
        | case                       | arm          |
        | A uses the time exit       | A            |
        | B uses the time exit       | B            |
        | T-only uses the time exit  | T-only       |
        | M-only uses the time exit  | M-only       |
        | always-short uses the time exit | always-short |
        | always-long uses the time exit  | always-long  |

  Rule: A-plan pins every inherited exit setting from the existing Heikin-Ashi H4 reference plan (D11)
    A-plan uses the same required voters as A but a different, fully pinned exit policy —
    the deliberate exit-policy comparison the design discloses, not an oversight.

    Scenario: the A-plan cell's config pins the reference plan's stop, target and trail settings
      When the fourteen-cell manifest is generated
      Then every "A-plan" cell's config has capital_mgmt stop_distance_source "swing"
      And every "A-plan" cell's config has capital_mgmt stop_loss_shrink 0.50
      And every "A-plan" cell's config has capital_mgmt min_stop_pips 5.0
      And every "A-plan" cell's config has capital_mgmt min_stop_factor 1.2
      And every "A-plan" cell's config has capital_mgmt targets [{at_level_ratio: 4.0, close_fraction: 0.5}, {at_level_ratio: 6.0, close_fraction: 0.5}]
      And every "A-plan" cell's config has capital_mgmt trail_stops [{at_level_ratio: 2.0, to_level_ratio: 0.1}]
      And every "A-plan" cell's config has capital_mgmt min_reward_risk 2.0
      And every "A-plan" cell's config has capital_mgmt atr_multiplier 2.0
      And every "A-plan" cell's config has capital_mgmt risk_per_trade 0.03
      And no "A-plan" cell's config declares capital_mgmt exit_after_bars

    Scenario: A-plan's pinned plan differs from A's time-exit plan even though both share the same voters
      When the fourteen-cell manifest is generated
      Then the "A" and "A-plan" cells on clock 60 minutes require the same voters
      And the "A" and "A-plan" cells on clock 60 minutes have different capital_mgmt sections

  Rule: Costs, caps and instrument/window are invariant across all 14 cells (CC-23)

    Scenario: every cell shares the same instrument, account, costs, risk caps and study window
      When the fourteen-cell manifest is generated
      Then every cell's config has pair "EURUSD"
      And every cell's config has account_balance 10000
      And every cell's config has execution spread/commission matching the pinned OANDA costs
      And every cell's config has risk_guard portfolio_at_risk_cap 0.18
      And every cell's config has risk_guard daily_drawdown_limit -0.05
      And every cell's config has risk_guard weekly_drawdown_limit -0.15
      And every cell's config has risk_guard max_concurrent_trades_per_account 2
      And every cell's config has risk_guard max_leverage 30
      And every cell's study window is "2016-03-01".."2017-02-28"

  Rule: No disallowed arm, clock or filter can enter the manifest (CC-23)

    Scenario Outline: <case> cannot enter the manifest
      When the fourteen-cell manifest is generated
      Then no cell's config declares filter "<disallowed_filter>"

      Examples:
        | case                                    | disallowed_filter    |
        | F3 candlestick pattern confirmation is excluded | f3_pattern    |
        | F7 meta-learner is excluded                     | f7_meta_learner |
        | the volume-strength gate is excluded            | volume_strength |

    Scenario Outline: requesting an unregistered arm or clock is refused (<case>)
      When the fourteen-cell manifest is generated with an extra arm "<arm>" and it fails
      Then the cell-manifest failure names "<fragment>"

      Examples:
        | case                                | arm                | fragment                                   |
        | a Story 22 candlestick arm is refused | candlestick-context | 'candlestick-context' is not a registered arm |
        | a Story 22 support-resistance arm is refused | support-resistance | 'support-resistance' is not a registered arm |
        | a Story 19 adaptive-model arm is refused | adaptive-recency   | 'adaptive-recency' is not a registered arm  |

    Scenario: requesting a clock other than H1 or H4 is refused
      When the fourteen-cell manifest is generated with an extra clock 15 and it fails
      Then the cell-manifest failure names "15 is not a registered clock (H1=60, H4=240)"

  Rule: Every manifest row records a config hash, and the manifest is deterministic (CC-23)

    Scenario: every manifest row carries a config hash and none collide
      When the fourteen-cell manifest is generated
      Then every manifest row has a non-empty config_hash
      And no two manifest rows share the same config_hash
      And every manifest row's config_hash is a 64-character hex SHA-256 digest

    Scenario: regenerating the manifest from the same inputs yields identical hashes and cell IDs
      When the fourteen-cell manifest is generated
      And the fourteen-cell manifest is generated again into a second job directory
      Then the two manifests list the same 14 cell IDs in the same order
      And every cell's config_hash is identical between the two manifests

    Scenario: the job directory holds one config.yaml per cell plus the manifest
      When the fourteen-cell manifest is generated
      Then the job directory has exactly 14 config.yaml files, one per cell
      And the job directory has one manifest file listing all 14 rows
