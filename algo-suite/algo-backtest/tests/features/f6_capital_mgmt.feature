Feature: F6 — capital-management filter
  Builds the fx-manager trade plan (specs.md §14.5–14.7, Strategy A05) for the bar and
  enriches `state.features` with it for the executor: the stop distance per side (fixed
  pips, ATR × multiplier or the structural swing level; shrunk toward entry by
  `stop_loss_shrink`; floored at `max(min_stop_pips, min_stop_factor × broker stop
  level)`), the fixed-fractional lot from `rules/risk_math.py`, every target and trailing
  step in pips with the spread added exactly as `rules/trail_stop.py` (the formulas
  confirmed against the fx-manager / spockfx-engine source), and the reward:risk ratio.
  It vetoes when the plan's reward:risk falls below `min_reward_risk` or the lot would
  need more margin than is available. Every number traces to a `capital_mgmt` or
  `execution` YAML key or to a market feature; nothing is a code constant.

  `state.features` contract (the account keys always; the market keys per source):

    - "account_balance" (float): current account balance
    - "pip_value" (float): monetary value of one pip per 1.0 lot
    - "margin_per_lot" (float): margin required per 1.0 lot at the current instrument/leverage
    - "available_margin" (float): currently free margin in the account
    - "atr_pips" (float): the bar's ATR in pips — `stop_distance_source: atr`
    - "swing_low_pips" / "swing_high_pips" (float): distance to the structural stop for a
      long / a short — `stop_distance_source: swing`

  Enrichment: `proposed_lot_size` (kept for compatibility) and `trade_plan`, a plain
  JSON-safe dict: {"lot_size", "spread_pips", "long": {"stop_pips", "targets": [{"pips",
  "close_fraction"}], "trail_stops": [{"at_pips", "to_pips"}], "reward_risk"}, "short":
  {…same…}}.

  `risk_per_trade` (specs.md §14.7: 3% for Strategy A05) and the sizing economics the
  chain feeds F6 (stop distance, pip value, lot notional, assumed leverage) are F6's own
  `capital_mgmt` section of the strategy config.yaml (2026-09-27 amendment, story 09),
  never code constants. Story 12 (execution realism) grows the same section with the
  fx-manager A05 trade-plan keys (specs.md §14.5–14.7): `stop_loss_shrink`,
  `min_stop_pips`, `min_stop_factor`, `targets[]`, `trail_stops[]`, `min_reward_risk`,
  `stop_distance_source` (`fixed`, `atr` or `swing`) and `atr_multiplier`. Each has a default so a pre-story-12 section keeps loading; the
  effective values are written back into the resolved config via `capital_mgmt_mapping`.

  Rule: The stop distance per side follows stop_distance_source, then shrinks, then floors

    Background:
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets risk_per_trade to 0.01
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000

    Scenario Outline: the stop distance and lot follow the source, the shrink and the floors (<case>)
      Given the capital_mgmt section sets stop_distance_source to <source>
      And the capital_mgmt section sets stop_loss_pips to <stop>
      And the capital_mgmt section sets stop_loss_shrink to <shrink>
      And the capital_mgmt section sets min_stop_pips to <min_stop>
      And the capital_mgmt section sets min_stop_factor to <min_factor>
      And the capital_mgmt section sets atr_multiplier to <atr_mult>
      And market features atr_pips <atr_pips>, swing_low_pips <swing_low>, swing_high_pips <swing_high>
      And an execution spread of 0 pips and a broker stop level of <broker> pips
      When F6 applies to the state
      Then F6's result does not veto
      And F6's long plan has stop_pips <long_stop>
      And F6's short plan has stop_pips <short_stop>
      And F6's trade plan has lot_size <lot>
      And F6 enriches "proposed_lot_size" with <lot>
      And F6's reason mentions "<source>"

      Examples: fixed source, shrunk toward entry and floored
        | case                                   | source | stop | shrink | min_stop | min_factor | broker | atr_mult | atr_pips | swing_low | swing_high | long_stop | short_stop | lot        |
        | A05 shrink of 20% above the floor      | fixed  | 20   | 0.2    | 5        | 1.0        | 0      | 2.0      | -        | -         | -          | 16        | 16         | 0.625      |
        | no shrink keeps the configured stop    | fixed  | 20   | 0      | 0        | 1.0        | 0      | 2.0      | -        | -         | -          | 20        | 20         | 0.5        |
        | min_stop_pips floors an over-shrunk stop | fixed | 20   | 0.8    | 5        | 1.0        | 0      | 2.0      | -        | -         | -          | 5         | 5          | 2          |
        | broker stop level × factor floors it   | fixed  | 20   | 0.8    | 0        | 1.2        | 5      | 2.0      | -        | -         | -          | 6         | 6          | 1.6666667  |
        | the higher of the two floors wins      | fixed  | 20   | 0.8    | 7        | 1.2        | 5      | 2.0      | -        | -         | -          | 7         | 7          | 1.4285714  |

      Examples: atr source, the bar's ATR times the multiplier
        | case                                   | source | stop | shrink | min_stop | min_factor | broker | atr_mult | atr_pips | swing_low | swing_high | long_stop | short_stop | lot        |
        | 12-pip ATR at 2× gives a 24-pip stop   | atr    | 20   | 0      | 0        | 1.0        | 0      | 2.0      | 12       | -         | -          | 24        | 24         | 0.4166667  |
        | ATR stop is shrunk like a fixed one    | atr    | 20   | 0.25   | 0        | 1.0        | 0      | 1.5      | 12       | -         | -          | 13.5      | 13.5       | 0.7407407  |
        | a tiny ATR is floored, not traded raw  | atr    | 20   | 0      | 5        | 1.0        | 0      | 2.0      | 1        | -         | -          | 5         | 5          | 2          |

      Examples: swing source, one structural level per side and the lot from the wider stop
        | case                                   | source | stop | shrink | min_stop | min_factor | broker | atr_mult | atr_pips | swing_low | swing_high | long_stop | short_stop | lot        |
        | far swing low, near swing high         | swing  | 20   | 0.2    | 5        | 1.0        | 0      | 2.0      | -        | 30        | 10         | 24        | 8          | 0.4166667  |
        | near swing low is floored, high is not | swing  | 20   | 0      | 5        | 1.0        | 0      | 2.0      | -        | 3         | 15         | 5         | 15         | 0.6666667  |

    Scenario: a sub-pip ATR stop is still a stop: only zero is refused
      Given the capital_mgmt section sets stop_distance_source to atr
      And the capital_mgmt section sets min_stop_pips to 0
      And market features atr_pips 0.4, swing_low_pips -, swing_high_pips -
      And an execution spread of 0 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's long plan has stop_pips 0.8
      And F6's short plan has stop_pips 0.8
      And F6's reason is exactly "insufficient margin: proposed lot 12.5 needs 37500.0 but only 10000.0 is available; trade plan from atr stop (long 0.8, short 0.8 pips), lot 12.5, spread 0.0 pips, reward:risk long 2.0, short 2.0"

    Scenario: a zero ATR with no floor cannot size a trade and fails fast naming the keys
      Given the capital_mgmt section sets stop_distance_source to atr
      And the capital_mgmt section sets min_stop_pips to 0
      And market features atr_pips 0, swing_low_pips -, swing_high_pips -
      And an execution spread of 0 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then applying F6 fails naming "stop_distance_source: atr"
      And applying F6 fails naming "min_stop_pips"

  Rule: Targets and trailing steps are pips from entry with the spread added as fx-manager does

    Background:
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets risk_per_trade to 0.01
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000

    Scenario Outline: targets and trailing steps carry the spread (<case>)
      Given the capital_mgmt section sets stop_loss_pips to <stop>
      And the capital_mgmt section sets stop_loss_shrink to <shrink>
      And the capital_mgmt section sets targets to [{at_level_ratio: <target>, close_fraction: <close>}]
      And the capital_mgmt section sets trail_stops to [{at_level_ratio: <trail_at>, to_level_ratio: <trail_to>}]
      And an execution spread of <spread> pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's result does not veto
      And F6's trade plan has spread_pips <spread>
      And F6's <side> plan target 1 is <target_pips> pips closing <close> of the position
      And F6's <side> plan trail 1 arms at <at_pips> pips and moves the stop to <to_pips> pips
      And F6's <side> plan has reward_risk <reward_risk>
      And F6's reason mentions "reward:risk"

      Examples: the spread widens the target, the arming level and the destination
        | case                                    | side  | stop | shrink | target | close | trail_at | trail_to | spread | target_pips | at_pips | to_pips | reward_risk |
        | no spread: pure multiples of the stop   | long  | 20   | 0      | 2.0    | 1.0   | 0.5      | 0.0      | 0      | 40          | 10      | 0       | 2.0         |
        | one pip of spread on a 20-pip stop      | long  | 20   | 0      | 2.0    | 1.0   | 0.5      | 0.0      | 1      | 43          | 11.5    | 1       | 2.15        |
        | 2.5 pips of spread, same plan           | short | 20   | 0      | 2.0    | 1.0   | 0.5      | 0.0      | 2.5    | 47.5        | 13.75   | 2.5     | 2.375       |
        | A05 plan on the shrunk 16-pip stop      | long  | 20   | 0.2    | 2.0    | 0.5   | 0.5      | -0.66    | 1      | 35          | 9.5     | -9.56   | 2.1875      |
        | A05 plan is symmetric for the short side| short | 20   | 0.2    | 2.0    | 0.5   | 0.5      | -0.66    | 1      | 35          | 9.5     | -9.56   | 2.1875      |
        | positive to-ratio locks in profit       | long  | 20   | 0      | 1.5    | 1.0   | 1.0      | 0.1      | 1      | 32.5        | 22      | 3       | 1.625       |

    Scenario: the reason digests the whole plan: source, per-side stops, lot, spread and reward:risk
      Given an execution spread of 1 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's reason is exactly "sufficient margin for proposed lot size 0.5; trade plan from fixed stop (long 20.0, short 20.0 pips), lot 0.5, spread 1.0 pips, reward:risk long 2.15, short 2.15"

    Scenario: a swing plan carries a different stop, target, trail and reward:risk per side
      Given the capital_mgmt section sets stop_distance_source to swing
      And the capital_mgmt section sets stop_loss_shrink to 0.2
      And the capital_mgmt section sets min_stop_pips to 5
      And the capital_mgmt section sets targets to [{at_level_ratio: 2.0, close_fraction: 0.5}]
      And the capital_mgmt section sets trail_stops to [{at_level_ratio: 0.5, to_level_ratio: -0.66}]
      And market features atr_pips -, swing_low_pips 30, swing_high_pips 10
      And an execution spread of 1 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's result does not veto
      And F6's long plan has stop_pips 24
      And F6's long plan target 1 is 51 pips closing 0.5 of the position
      And F6's long plan trail 1 arms at 13.5 pips and moves the stop to -14.84 pips
      And F6's long plan has reward_risk 2.125
      And F6's short plan has stop_pips 8
      And F6's short plan target 1 is 19 pips closing 0.5 of the position
      And F6's short plan trail 1 arms at 5.5 pips and moves the stop to -4.28 pips
      And F6's short plan has reward_risk 2.375
      And F6's trade plan has lot_size 0.4166667

    Scenario: a reward:risk floor names only the failing side, with the other side still in the digest
      Given the capital_mgmt section sets stop_distance_source to swing
      And the capital_mgmt section sets stop_loss_shrink to 0.2
      And the capital_mgmt section sets min_stop_pips to 5
      And the capital_mgmt section sets targets to [{at_level_ratio: 2.0, close_fraction: 0.5}]
      And the capital_mgmt section sets min_reward_risk to 2.2
      And market features atr_pips -, swing_low_pips 30, swing_high_pips 10
      And an execution spread of 1 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's veto flag is true
      And F6's reason is exactly "reward:risk below capital_mgmt.min_reward_risk 2.2: long 2.125; trade plan from swing stop (long 24.0, short 8.0 pips), lot 0.4166666666666667, spread 1.0 pips, reward:risk long 2.125, short 2.375"

    Scenario: two targets and two trailing steps are all carried, in order
      Given the capital_mgmt section sets targets to [{at_level_ratio: 1.0, close_fraction: 0.5}, {at_level_ratio: 2.0, close_fraction: 0.5}]
      And the capital_mgmt section sets trail_stops to [{at_level_ratio: 0.5, to_level_ratio: -0.66}, {at_level_ratio: 1.0, to_level_ratio: 0.0}]
      And an execution spread of 1 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's long plan target 1 is 22 pips closing 0.5 of the position
      And F6's long plan target 2 is 43 pips closing 0.5 of the position
      And F6's long plan trail 1 arms at 11.5 pips and moves the stop to -12.2 pips
      And F6's long plan trail 2 arms at 22 pips and moves the stop to 1 pips
      And F6's long plan has reward_risk 1.1
      And F6's trade plan is JSON-serialisable

    Scenario: no targets means no reward:risk to report
      Given the capital_mgmt section sets targets to []
      And an execution spread of 1 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's result does not veto
      And F6's long plan has reward_risk null
      And F6's short plan has reward_risk null
      And F6's trade plan is JSON-serialisable

  Rule: F6 vetoes when the first target's reward:risk falls below min_reward_risk

    Background:
      Given a complete five-key capital_mgmt section
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000
      And an execution spread of 0 pips and a broker stop level of 0 pips

    Scenario Outline: the reward:risk floor is enforced against the first target (<case>)
      Given the capital_mgmt section sets targets to [{at_level_ratio: <target>, close_fraction: 1.0}]
      And the capital_mgmt section sets min_reward_risk to <minimum>
      When F6 applies to the state
      Then F6's veto flag is <veto>
      And F6's long plan has reward_risk <reward_risk>
      And F6's reason mentions "<mentions>"

      Examples:
        | case                                  | target | minimum | reward_risk | veto  | mentions                                |
        | ratio equal to the floor passes       | 2.0    | 2.0     | 2.0         | false | sufficient margin                       |
        | ratio above the floor passes          | 2.0    | 1.5     | 2.0         | false | reward:risk                             |
        | ratio below the floor vetoes          | 2.0    | 2.5     | 2.0         | true  | capital_mgmt.min_reward_risk 2.5        |
        | a floor below one is still a floor    | 2.0    | 0.5     | 2.0         | false | sufficient margin                       |
        | the veto names the measured ratio     | 1.5    | 2.0     | 1.5         | true  | long 1.5                                |
        | no floor lets a poor ratio through    | 1.5    | null    | 1.5         | false | reward:risk                             |

    Scenario: both sides failing the floor are listed, then the plan digest follows
      Given the capital_mgmt section sets targets to [{at_level_ratio: 2.0, close_fraction: 1.0}]
      And the capital_mgmt section sets min_reward_risk to 2.5
      When F6 applies to the state
      Then F6's reason is exactly "reward:risk below capital_mgmt.min_reward_risk 2.5: long 2.0, short 2.0; trade plan from fixed stop (long 20.0, short 20.0 pips), lot 1.5, spread 0.0 pips, reward:risk long 2.0, short 2.0"

  Rule: F6 vetoes when the proposed lot size would need more margin than is available

    Background:
      Given a complete five-key capital_mgmt section
      And an execution spread of 0 pips and a broker stop level of 0 pips

    Scenario Outline: the margin veto is unchanged by the plan (<case>)
      Given account features: balance 10000, pip value 1, margin per lot 100, available margin <available>
      When F6 applies to the state
      Then F6's veto flag is <veto>
      And F6's filter name is "f6_capital_mgmt"
      And F6's recommendation is "ABSTAIN"
      And F6's reason mentions "<mentions>"
      And F6 enriches "proposed_lot_size" with 15.0
      And F6's trade plan has lot_size 15.0

      Examples:
        | case                                            | available | veto  | mentions            |
        | a well-margined account passes                  | 2000      | false | sufficient margin   |
        | available margin exactly equal to required passes | 1500    | false | sufficient margin   |
        | an under-margined account vetoes                | 1000      | true  | insufficient margin |

    Scenario: the margin veto states the lot, what it needs and what is available
      Given account features: balance 10000, pip value 1, margin per lot 100, available margin 1000
      When F6 applies to the state
      Then F6's reason is exactly "insufficient margin: proposed lot 15.0 needs 1500.0 but only 1000.0 is available; trade plan from fixed stop (long 20.0, short 20.0 pips), lot 15.0, spread 0.0 pips, reward:risk long 2.0, short 2.0"

  Rule: A missing feature fails fast, naming the key and the source that needs it

    Background:
      Given a complete five-key capital_mgmt section
      And an execution spread of 0 pips and a broker stop level of 0 pips

    Scenario Outline: a source-specific market feature is required (<case>)
      Given the capital_mgmt section sets stop_distance_source to <source>
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000
      And market features atr_pips <atr_pips>, swing_low_pips <swing_low>, swing_high_pips <swing_high>
      When F6 applies to the state
      Then applying F6 fails naming "<missing>"
      And applying F6 fails naming "stop_distance_source: <source>"

      Examples:
        | case                              | source | atr_pips | swing_low | swing_high | missing         |
        | atr source without atr_pips       | atr    | -        | -         | -          | atr_pips        |
        | swing source without swing_low    | swing  | -        | -         | 10         | swing_low_pips  |
        | swing source without swing_high   | swing  | -        | 30        | -          | swing_high_pips |

    Scenario: the fixed source needs no market feature at all
      Given account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000
      When F6 applies to the state
      Then F6's result does not veto

    Scenario: available_margin missing from state.features fails fast
      Given account features missing "available_margin"
      When F6 applies to the state
      Then applying F6 fails with exactly "f6_capital_mgmt: required state.features key 'available_margin' is missing — needed by the F6 account contract; see this module's docstring for the full contract"

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
        | min_stop_factor      | 1.0                                           |
        | targets              | [{at_level_ratio: 2.0, close_fraction: 1.0}]  |
        | trail_stops          | []                                            |
        | min_reward_risk      | null                                          |
        | stop_distance_source | fixed                                         |
        | atr_multiplier       | 2.0                                           |
        | min_stop_factor      | 1.0                                           |
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
        | reward:risk floor below one | min_reward_risk      | 0.5                                                                                     | stop_loss_shrink | 0.0           |
        | reward:risk explicitly off  | min_reward_risk      | null                                                                                    | atr_multiplier   | 2.0           |
        | ATR-derived stop            | stop_distance_source | atr                                                                                     | atr_multiplier   | 2.0           |
        | structural swing stop (A05) | stop_distance_source | swing                                                                                   | min_stop_factor  | 1.0           |
        | wider ATR multiple          | atr_multiplier       | 3.5                                                                                     | min_stop_pips    | 0.0           |

    Scenario: the effective mapping parses back into the same config (YAML-safe lists, not tuples)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to [{at_level_ratio: 1.0, close_fraction: 0.5}, {at_level_ratio: 2.0, close_fraction: 0.5}]
      And the capital_mgmt section sets trail_stops to [{at_level_ratio: 0.5, to_level_ratio: -0.66}]
      When the capital-mgmt config is parsed for strategy "baseline"
      Then parsing the capital-mgmt mapping again yields an equal config
      And the capital-mgmt mapping survives a YAML safe_dump round trip

  Rule: An invalid or unknown trade-plan value fails fast naming the strategy, section and key

    Scenario Outline: an invalid trade-plan value fails fast (<case>)
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
        | targets a bare number                  | targets              | 5                                                                                       | capital_mgmt.targets must be a list of mappings               |
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
        | unknown stop source                    | stop_distance_source | structural                                                                              | capital_mgmt.stop_distance_source must be one of ['atr', 'fixed', 'swing'] |
        | stop-level factor below one            | min_stop_factor      | 0.9                                                                                     | capital_mgmt.min_stop_factor must be >= 1                     |
        | stop-level factor not a number         | min_stop_factor      | broker                                                                                  | capital_mgmt.min_stop_factor must be a number                 |
        | ATR multiplier of zero                 | atr_multiplier       | 0                                                                                       | capital_mgmt.atr_multiplier must be > 0                       |
        | unknown key                            | take_profit_pips     | 40                                                                                      | capital_mgmt has unknown keys ['take_profit_pips']            |

    Scenario: a reward:risk floor with no target to measure it against fails fast
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to []
      And the capital_mgmt section sets min_reward_risk to 2.0
      When parsing the capital-mgmt config for strategy "baseline" fails
      Then the capital-mgmt config failure is exactly "strategy 'baseline': capital_mgmt.min_reward_risk needs at least one target to measure the reward against, but targets is empty — add a target or set min_reward_risk: null"

    Scenario Outline: the failure text spells out the fix in full (<case>)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to <value>
      When parsing the capital-mgmt config for strategy "baseline" fails
      Then the capital-mgmt config failure is exactly "<message>"

      Examples:
        | case                              | value                                                                                                                             | message                                                                                                                                                                  |
        | targets written as one mapping    | {at_level_ratio: 2.0, close_fraction: 1.0}                                                                                        | strategy 'baseline': capital_mgmt.targets must be a list of mappings, got {'at_level_ratio': 2.0, 'close_fraction': 1.0} — write `targets: [{at_level_ratio: <number>, close_fraction: <number>}]` |
        | the third level below the second  | [{at_level_ratio: 1.0, close_fraction: 0.3}, {at_level_ratio: 2.0, close_fraction: 0.3}, {at_level_ratio: 1.5, close_fraction: 0.3}] | strategy 'baseline': capital_mgmt.targets[2].at_level_ratio must exceed the previous entry's (2.0), got 1.5 — order the entries by at_level_ratio, strictly increasing |
        | fractions summing just past one   | [{at_level_ratio: 1.0, close_fraction: 0.7}, {at_level_ratio: 2.0, close_fraction: 0.50000000049}]                                | strategy 'baseline': capital_mgmt.targets close_fraction values sum to 1.2, more than the whole position (1.0) — lower them                                             |
