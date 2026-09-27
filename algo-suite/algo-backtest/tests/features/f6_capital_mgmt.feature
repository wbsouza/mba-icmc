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
  never code constants.

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
      Then the capital-mgmt config failure names "<key>"
      And the capital-mgmt config failure names "baseline"

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
      Then the capital-mgmt config failure names "<names>"

      Examples:
        | case                        | risk | stop | pip  | lot    | lev | names              |
        | zero risk                   | 0    | 20   | 10   | 100000 | 30  | risk_per_trade     |
        | risk above 1                | 1.5  | 20   | 10   | 100000 | 30  | risk_per_trade     |
        | zero stop distance          | 0.03 | 0    | 10   | 100000 | 30  | stop_loss_pips     |
        | negative pip value          | 0.03 | 20   | -10  | 100000 | 30  | pip_value_per_lot  |
        | zero lot notional           | 0.03 | 20   | 10   | 0      | 30  | lot_notional_units |
        | zero leverage               | 0.03 | 20   | 10   | 100000 | 0   | assumed_leverage   |
        | non-numeric stop distance   | 0.03 | wide | 10   | 100000 | 30  | stop_loss_pips     |
