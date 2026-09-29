Feature: F6 bar-count plan — the optional exit_after_bars horizon (story 21, T5)
  Proves the `capital_mgmt.exit_after_bars` extension of `chain/filters/f6_capital_mgmt.py`
  (spec CC-20, CC-21, CC-22; decisions D5, D6, D11). N is an optional positive integer:
  the number of completed signal bars a time-exit position is held. Absent (or `null`)
  means no time exit and the legacy plan byte for byte. When present, the plan carries
  `exit_after_bars` for the executor while everything else F6 already does — the ATR
  (or fixed/swing) stop, the shrink, the stop floors, the spread, the fixed-fractional
  lot and the margin veto — still applies (CC-21). The registered time arms use
  `targets: []` and `trail_stops: []`, so there is no target and no reward:risk veto;
  a target-based `min_reward_risk` with empty targets stays the existing configuration
  error. A boolean, fraction, zero, negative, string or list N is rejected with the fix
  (CC-22).

  Accepted timing contract (D5, user decision 2026-09-28; the lifecycle itself is T6):
  let t be the signal bar during which the entry filled. The exit is at the open of bar
  t+N. Expiry is due at the close of bar t+N-1, which is the open of t+N; the engine
  submits one market closure on the first tradable event at or after that open, after
  stop reconciliation, at the executor's actual fill price. N = 4 spans the four closes
  of the horizon check. The F6 module docstring records this contract next to the field.

  Rule: An omitted exit_after_bars leaves the legacy plan untouched (CC-20)

    Scenario: a five-key section resolves exit_after_bars to null and every other default as before
      Given a complete five-key capital_mgmt section
      When the capital-mgmt config is parsed for strategy "baseline"
      Then the parsed capital-mgmt config has exit_after_bars null
      And the capital-mgmt mapping has no key "exit_after_bars"
      And the capital-mgmt mapping records targets [{at_level_ratio: 2.0, close_fraction: 1.0}]
      And the capital-mgmt mapping records trail_stops []
      And the capital-mgmt mapping records min_reward_risk null
      And the capital-mgmt mapping records stop_distance_source fixed
      And the capital-mgmt mapping records atr_multiplier 2.0

    Scenario: the legacy mapping still parses back into an equal config and survives YAML
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to [{at_level_ratio: 4.0, close_fraction: 0.5}, {at_level_ratio: 6.0, close_fraction: 0.5}]
      And the capital_mgmt section sets trail_stops to [{at_level_ratio: 2.0, to_level_ratio: 0.1}]
      When the capital-mgmt config is parsed for strategy "baseline"
      Then parsing the capital-mgmt mapping again yields an equal config
      And the capital-mgmt mapping survives a YAML safe_dump round trip

    Scenario: an explicit null is the same as omitting the option
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets exit_after_bars to null
      When the capital-mgmt config is parsed for strategy "baseline"
      Then the parsed capital-mgmt config has exit_after_bars null

    Scenario: the legacy trade plan carries no exit_after_bars key
      Given a complete five-key capital_mgmt section
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000
      And an execution spread of 0 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's result does not veto
      And F6's trade plan has no key "exit_after_bars"
      And F6's trade plan has exactly the keys "lot_size, spread_pips, long, short"

  Rule: exit_after_bars is a positive integer or the section is rejected with the fix (CC-22)

    Scenario Outline: exit_after_bars <value> parses to <value> (<case>)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets exit_after_bars to <value>
      When the capital-mgmt config is parsed for strategy "confluence-a"
      Then the parsed capital-mgmt config has exit_after_bars <value>
      And the capital-mgmt mapping records exit_after_bars <value>

      Examples:
        | case                        | value |
        | the registered four bars    | 4     |
        | the shortest horizon        | 1     |
        | a long horizon              | 48    |

    Scenario Outline: exit_after_bars <value> is rejected (<case>)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets exit_after_bars to <value>
      When parsing the capital-mgmt config for strategy "confluence-a" fails
      Then the capital-mgmt config failure names "strategy 'confluence-a': capital_mgmt.exit_after_bars must be a positive integer"
      And the capital-mgmt config failure names "got <shown>"
      And the capital-mgmt config failure names "completed signal bars"

      Examples:
        | case            | value | shown |
        | a boolean true  | true  | True  |
        | a boolean false | false | False |
        | a fraction      | 4.5   | 4.5   |
        | a whole float   | 4.0   | 4.0   |
        | zero            | 0     | 0     |
        | negative        | -4    | -4    |
        | a string        | four  | 'four'|
        | a list          | [4]   | [4]   |

    Scenario: the rejection spells out the remediation in full
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets exit_after_bars to 0
      When parsing the capital-mgmt config for strategy "confluence-a" fails
      Then the capital-mgmt config failure is exactly "strategy 'confluence-a': capital_mgmt.exit_after_bars must be a positive integer (completed signal bars to hold; the exit is submitted at the open of bar t+N) or null to disable, got 0 — fix strategies/confluence-a/config.yaml"

  Rule: The registered time plan has no target and no target-based veto, and the rest of F6 still applies (CC-21)
    The registered arms: risk 3 %, ATR(14) × 2 base stop, empty targets and trail
    steps, N = 4, with the broker floors and OANDA spread still in force.

    Scenario Outline: the time plan sizes from the ATR stop and the floors (<case>)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets risk_per_trade to 0.03
      And the capital_mgmt section sets stop_distance_source to atr
      And the capital_mgmt section sets atr_multiplier to 2.0
      And the capital_mgmt section sets min_stop_pips to 5.0
      And the capital_mgmt section sets min_stop_factor to 1.2
      And the capital_mgmt section sets targets to []
      And the capital_mgmt section sets trail_stops to []
      And the capital_mgmt section sets exit_after_bars to 4
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin <available_margin>
      And market features atr_pips <atr_pips>, swing_low_pips -, swing_high_pips -
      And an execution spread of 1.5 pips and a broker stop level of <broker> pips
      When F6 applies to the state
      Then F6's result <veto>
      And F6's long plan has stop_pips <stop>
      And F6's short plan has stop_pips <stop>
      And F6's trade plan has lot_size <lot>
      And F6's trade plan has exit_after_bars 4
      And F6's trade plan has spread_pips 1.5
      And F6's long plan has no targets and no trail_stops
      And F6's short plan has no targets and no trail_stops
      And F6's long plan has reward_risk null
      And F6's reason mentions "atr"

      Examples:
        | case                                            | atr_pips | broker | available_margin | stop | lot | veto          |
        | 10-pip ATR at 2x is a 20-pip stop, 1.5 lots    | 10       | 5      | 10000            | 20   | 1.5 | does not veto |
        | a 1-pip ATR is floored at 1.2 x broker 5       | 1        | 5      | 10000            | 6    | 5   | vetoes        |
        | the same floor with margin to spare passes      | 1        | 5      | 20000            | 6    | 5   | does not veto |
        | no broker level: min_stop_pips 5 floors it     | 1        | 0      | 20000            | 5    | 6   | does not veto |

    Scenario: the margin veto on the time plan names the lot and the shortfall as before
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets risk_per_trade to 0.03
      And the capital_mgmt section sets stop_distance_source to atr
      And the capital_mgmt section sets targets to []
      And the capital_mgmt section sets trail_stops to []
      And the capital_mgmt section sets exit_after_bars to 4
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 1000
      And market features atr_pips 10, swing_low_pips -, swing_high_pips -
      And an execution spread of 1.5 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's result vetoes
      And F6's reason mentions "insufficient margin: proposed lot 1.5 needs 4500.0 but only 1000.0 is available"
      And F6's trade plan has exit_after_bars 4

    Scenario: a time plan with empty targets and a reward:risk floor is still the existing configuration error
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets targets to []
      And the capital_mgmt section sets exit_after_bars to 4
      And the capital_mgmt section sets min_reward_risk to 2.0
      When parsing the capital-mgmt config for strategy "confluence-a" fails
      Then the capital-mgmt config failure names "capital_mgmt.min_reward_risk needs at least one target to measure the reward against, but targets is empty"

    Scenario: a time exit may coexist with the default target (the lifecycle decides which fires first, T6)
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets exit_after_bars to 4
      And account features: balance 10000, pip value 10, margin per lot 3000, available margin 10000
      And an execution spread of 0 pips and a broker stop level of 0 pips
      When F6 applies to the state
      Then F6's result does not veto
      And F6's trade plan has exit_after_bars 4
      And F6's long plan has reward_risk 2.0

    Scenario: the time plan round-trips through the effective mapping and YAML
      Given a complete five-key capital_mgmt section
      And the capital_mgmt section sets stop_distance_source to atr
      And the capital_mgmt section sets targets to []
      And the capital_mgmt section sets trail_stops to []
      And the capital_mgmt section sets exit_after_bars to 4
      When the capital-mgmt config is parsed for strategy "confluence-a"
      Then parsing the capital-mgmt mapping again yields an equal config
      And the capital-mgmt mapping survives a YAML safe_dump round trip
      And the capital-mgmt mapping records exit_after_bars 4
      And the capital-mgmt mapping records targets []

  Rule: The accepted timing contract is recorded where the option is defined (D5)

    Scenario: the F6 module documentation states the bar-open timing contract
      Then the F6 module docstring mentions "exit_after_bars"
      And the F6 module docstring mentions "open of bar t+N"
      And the F6 module docstring mentions "close of bar t+N-1"
      And the F6 module docstring mentions "the bar during which the entry filled"
