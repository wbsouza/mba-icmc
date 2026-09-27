Feature: F6 — capital-management filter
  Wires `rules/risk_math.py`'s fixed-fractional lot-size formula into the deterministic
  filter chain, enriching `state.features` with the proposed lot size (specs.md §11.3.1's
  enrichment example) and vetoing if the position would require more margin than is
  available. No upstream filter populates ATR/balance state yet, so this module defines
  and proves its own minimal `state.features` contract:

    - "account_balance" (float): current account balance
    - "pip_value" (float): monetary value of one pip per 1.0 lot
    - "stop_loss_pips" (float): ATR-derived stop-loss distance, in pips
    - "margin_per_lot" (float): margin required per 1.0 lot at the current instrument/leverage
    - "available_margin" (float): currently free margin in the account

  `risk_per_trade` (specs.md §14.7: 3% for Strategy A05) and the sizing economics the
  chain feeds F6 (stop distance, pip value, lot notional, assumed leverage) are F6's own
  `capital_mgmt` section of the strategy config.yaml (2026-09-27 amendment, story 09),
  never code constants. Story 12 (execution realism) grows the same section with the
  fx-manager A05 trade-plan keys (specs.md §14.5–14.7): `stop_loss_shrink`,
  `min_stop_pips`, `targets[]`, `trail_stops[]`, `min_reward_risk`, `stop_distance_source`
  and `atr_multiplier`. Each has a default so a pre-story-12 section keeps loading; the
  effective values are written back into the resolved config via `capital_mgmt_mapping`.

  Rule: F6 enriches state with the proposed lot size and passes when margin is sufficient

    Scenario: a well-margined account computes and passes its proposed lot size
      Given synthetic capital-mgmt features: balance 10000.0, pip value 1.0, stop-loss 20.0 pips, margin per lot 100.0, available margin 2000.0
      And a risk per trade of 0.03
      When F6 applies to the state
      Then F6's result does not veto
      And F6's filter name is "f6_capital_mgmt"
      And F6's recommendation is "ABSTAIN"
      And F6's reason mentions "sufficient margin"
      And F6 enriches "proposed_lot_size" with 15.0

    Scenario: available margin exactly equal to required margin does not veto
      Given synthetic capital-mgmt features: balance 10000.0, pip value 1.0, stop-loss 20.0 pips, margin per lot 100.0, available margin 1500.0
      And a risk per trade of 0.03
      When F6 applies to the state
      Then F6's result does not veto
      And F6 enriches "proposed_lot_size" with 15.0

  Rule: F6 vetoes when the proposed lot size would need more margin than is available

    Scenario: an under-margined account vetoes despite computing a lot size
      Given synthetic capital-mgmt features: balance 10000.0, pip value 1.0, stop-loss 20.0 pips, margin per lot 100.0, available margin 1000.0
      And a risk per trade of 0.03
      When F6 applies to the state
      Then F6's result vetoes
      And F6's filter name is "f6_capital_mgmt"
      And F6's recommendation is "ABSTAIN"
      And F6's reason mentions "margin"
      And F6 enriches "proposed_lot_size" with 15.0

  Rule: A missing required feature key fails fast, naming the missing key

    Scenario: available_margin missing from state.features fails fast
      Given synthetic capital-mgmt features missing "available_margin"
      And a risk per trade of 0.03
      When F6 applies to the state
      Then applying F6 fails naming "available_margin"

  Rule: F6's parameters come from the strategy config.yaml capital_mgmt section

    Scenario Outline: a complete capital_mgmt section parses into a CapitalMgmtConfig (<case>)
      Given a capital_mgmt section with risk_per_trade=<risk>, stop_loss_pips=<stop>, pip_value_per_lot=<pip>, lot_notional_units=<lot>, assumed_leverage=<lev>
      When the capital-mgmt config is parsed for strategy "baseline"
      Then the parsed capital-mgmt config has risk_per_trade <risk>, stop_loss_pips <stop>, pip_value_per_lot <pip>, lot_notional_units <lot> and assumed_leverage <lev>

      Examples:
        | case                    | risk | stop | pip  | lot    | lev |
        | smoke-test economics    | 0.03 | 20   | 10   | 100000 | 30  |
        | tighter stop, mini lots | 0.01 | 10.5 | 1    | 10000  | 50  |
        | all-in risk             | 1    | 5    | 10   | 100000 | 1   |

    Scenario Outline: a capital_mgmt section missing <key> fails fast naming the key and the strategy
      Given a capital_mgmt section missing "<key>"
      When parsing the capital-mgmt config for strategy "baseline" fails
      Then the capital-mgmt config failure names "strategy 'baseline': capital_mgmt.<key> is missing"

      Examples:
        | key                |
        | risk_per_trade     |
        | stop_loss_pips     |
        | pip_value_per_lot  |
        | lot_notional_units |
        | assumed_leverage   |

    Scenario Outline: an out-of-range or non-numeric capital_mgmt value fails fast (<case>)
      Given a capital_mgmt section with risk_per_trade=<risk>, stop_loss_pips=<stop>, pip_value_per_lot=<pip>, lot_notional_units=<lot>, assumed_leverage=<lev>
      When parsing the capital-mgmt config for strategy "baseline" fails
      Then the capital-mgmt config failure names "<failure>"

      Examples:
        | case                        | risk | stop | pip  | lot    | lev | failure                                                                      |
        | zero risk                   | 0    | 20   | 10   | 100000 | 30  | strategy 'baseline': capital_mgmt.risk_per_trade must be > 0                 |
        | risk above 1                | 1.5  | 20   | 10   | 100000 | 30  | strategy 'baseline': capital_mgmt.risk_per_trade must be a fraction in (0, 1] |
        | zero stop distance          | 0.03 | 0    | 10   | 100000 | 30  | strategy 'baseline': capital_mgmt.stop_loss_pips must be > 0                 |
        | negative pip value          | 0.03 | 20   | -10  | 100000 | 30  | strategy 'baseline': capital_mgmt.pip_value_per_lot must be > 0              |
        | zero lot notional           | 0.03 | 20   | 10   | 0      | 30  | strategy 'baseline': capital_mgmt.lot_notional_units must be > 0             |
        | zero leverage               | 0.03 | 20   | 10   | 100000 | 0   | strategy 'baseline': capital_mgmt.assumed_leverage must be > 0               |
        | non-numeric stop distance   | 0.03 | wide | 10   | 100000 | 30  | strategy 'baseline': capital_mgmt.stop_loss_pips must be a number            |

  Rule: The trade-plan keys default when omitted, so a five-key section still loads

    Scenario Outline: a section with only the five sizing keys resolves the plan default for <key>
      Given a complete five-key capital_mgmt section
      When the capital-mgmt config is parsed for strategy "baseline"
      Then the capital-mgmt mapping records <key> <default>

      Examples:
        | key                  | default                                       |
        | stop_loss_shrink     | 0.0                                           |
        | min_stop_pips        | 0.0                                           |
        | targets              | [{at_level_ratio: 2.0, close_fraction: 1.0}]  |
        | trail_stops          | []                                            |
        | min_reward_risk      | null                                          |
        | stop_distance_source | fixed                                         |
        | atr_multiplier       | 2.0                                           |
        | risk_per_trade       | 0.03                                          |

    Scenario Outline: a plan key set explicitly overrides only itself (<case>)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets <key> to <value>
      When the capital-mgmt config is parsed for strategy "baseline"
      Then the capital-mgmt mapping records <key> <value>
      And the capital-mgmt mapping records <other> <other_default>

      Examples:
        | case                        | key                  | value                                                                                   | other            | other_default |
        | A05 stop shrink             | stop_loss_shrink     | 0.2                                                                                     | min_stop_pips    | 0.0           |
        | five-pip stop floor         | min_stop_pips        | 5.0                                                                                     | stop_loss_shrink | 0.0           |
        | two targets, half each      | targets              | [{at_level_ratio: 1.0, close_fraction: 0.5}, {at_level_ratio: 2.0, close_fraction: 0.5}] | trail_stops      | []            |
        | no target at all            | targets              | []                                                                                      | min_reward_risk  | null          |
        | A05 trail to breakeven side | trail_stops          | [{at_level_ratio: 0.5, to_level_ratio: -0.66}]                                          | atr_multiplier   | 2.0           |
        | two trail steps             | trail_stops          | [{at_level_ratio: 0.5, to_level_ratio: -0.66}, {at_level_ratio: 1.0, to_level_ratio: 0.0}] | targets       | [{at_level_ratio: 2.0, close_fraction: 1.0}] |
        | reward:risk floor           | min_reward_risk      | 2.0                                                                                     | stop_loss_shrink | 0.0           |
        | reward:risk explicitly off  | min_reward_risk      | null                                                                                    | atr_multiplier   | 2.0           |
        | ATR-derived stop            | stop_distance_source | atr                                                                                     | atr_multiplier   | 2.0           |
        | wider ATR multiple          | atr_multiplier       | 3.5                                                                                     | min_stop_pips    | 0.0           |

    Scenario: the effective mapping parses back into the same config (YAML-safe lists, not tuples)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to [{at_level_ratio: 1.0, close_fraction: 0.5}, {at_level_ratio: 2.0, close_fraction: 0.5}]
      And the capital_mgmt section sets trail_stops to [{at_level_ratio: 0.5, to_level_ratio: -0.66}]
      When the capital-mgmt config is parsed for strategy "baseline"
      Then parsing the capital-mgmt mapping again yields an equal config
      And the capital-mgmt mapping survives a YAML safe_dump round trip

  Rule: An invalid or unknown trade-plan value fails fast naming the strategy, section and key

    Scenario Outline: <case>
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets <key> to <value>
      When parsing the capital-mgmt config for strategy "baseline" fails
      Then the capital-mgmt config failure names "<failure>"
      And the capital-mgmt config failure names "strategy 'baseline'"

      Examples:
        | case                                   | key                  | value                                                                                   | failure                                                       |
        | shrink of 100% leaves no stop          | stop_loss_shrink     | 1                                                                                       | capital_mgmt.stop_loss_shrink must be a fraction in [0, 1)    |
        | negative shrink                        | stop_loss_shrink     | -0.1                                                                                    | capital_mgmt.stop_loss_shrink must be a fraction in [0, 1)    |
        | non-numeric shrink                     | stop_loss_shrink     | some                                                                                    | capital_mgmt.stop_loss_shrink must be a number                |
        | negative stop floor                    | min_stop_pips        | -1                                                                                      | capital_mgmt.min_stop_pips must be >= 0                       |
        | targets not a list                     | targets              | {at_level_ratio: 2.0, close_fraction: 1.0}                                              | capital_mgmt.targets must be a list of mappings               |
        | target entry not a mapping             | targets              | [2.0]                                                                                   | capital_mgmt.targets[0] must be a mapping                     |
        | target missing close_fraction          | targets              | [{at_level_ratio: 2.0}]                                                                 | capital_mgmt.targets[0].close_fraction is missing             |
        | target with unknown key                | targets              | [{at_level_ratio: 2.0, close_fraction: 1.0, lots: 1}]                                   | capital_mgmt.targets[0] has unknown keys ['lots']             |
        | target level not positive              | targets              | [{at_level_ratio: 0, close_fraction: 1.0}]                                              | capital_mgmt.targets[0].at_level_ratio must be > 0            |
        | close fraction of zero                 | targets              | [{at_level_ratio: 2.0, close_fraction: 0}]                                              | capital_mgmt.targets[0].close_fraction must be a fraction in (0, 1] |
        | close fraction above one               | targets              | [{at_level_ratio: 2.0, close_fraction: 1.5}]                                            | capital_mgmt.targets[0].close_fraction must be a fraction in (0, 1] |
        | close fractions summing past the lot   | targets              | [{at_level_ratio: 1.0, close_fraction: 0.6}, {at_level_ratio: 2.0, close_fraction: 0.6}] | capital_mgmt.targets close_fraction values sum to 1.2        |
        | target levels not increasing           | targets              | [{at_level_ratio: 2.0, close_fraction: 0.5}, {at_level_ratio: 2.0, close_fraction: 0.5}] | capital_mgmt.targets[1].at_level_ratio must exceed           |
        | trail_stops not a list                 | trail_stops          | {at_level_ratio: 0.5, to_level_ratio: -0.66}                                            | capital_mgmt.trail_stops must be a list of mappings           |
        | trail missing to_level_ratio           | trail_stops          | [{at_level_ratio: 0.5}]                                                                 | capital_mgmt.trail_stops[0].to_level_ratio is missing         |
        | trail arming level not positive        | trail_stops          | [{at_level_ratio: -0.5, to_level_ratio: -0.66}]                                         | capital_mgmt.trail_stops[0].at_level_ratio must be > 0        |
        | trail destination not a number         | trail_stops          | [{at_level_ratio: 0.5, to_level_ratio: entry}]                                          | capital_mgmt.trail_stops[0].to_level_ratio must be a number   |
        | trail levels not increasing            | trail_stops          | [{at_level_ratio: 1.0, to_level_ratio: 0.0}, {at_level_ratio: 0.5, to_level_ratio: -0.66}] | capital_mgmt.trail_stops[1].at_level_ratio must exceed     |
        | reward:risk of zero                    | min_reward_risk      | 0                                                                                       | capital_mgmt.min_reward_risk must be > 0                      |
        | reward:risk not a number               | min_reward_risk      | two                                                                                     | capital_mgmt.min_reward_risk must be a number                 |
        | unknown stop source                    | stop_distance_source | swing                                                                                   | capital_mgmt.stop_distance_source must be one of ['atr', 'fixed'] |
        | ATR multiplier of zero                 | atr_multiplier       | 0                                                                                       | capital_mgmt.atr_multiplier must be > 0                       |
        | unknown key                            | take_profit_pips     | 40                                                                                      | capital_mgmt has unknown keys ['take_profit_pips']            |

    Scenario: a reward:risk floor with no target to measure it against fails fast
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to []
      And the capital_mgmt section sets min_reward_risk to 2.0
      When parsing the capital-mgmt config for strategy "baseline" fails
      Then the capital-mgmt config failure names "capital_mgmt.min_reward_risk needs at least one target"
