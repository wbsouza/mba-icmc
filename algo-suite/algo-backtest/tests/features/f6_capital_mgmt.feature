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

  `risk_per_trade` (specs.md §14.7: 3% for Strategy A05) is F6's own config parameter,
  never hardcoded, resolved the same way `rules/risk_guard.py` resolves its caps.

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

  Rule: Loading risk_per_trade from config is fail-fast on a missing trading-impactful parameter

    Scenario: risk_per_trade present in config loads cleanly
      Given a risk_math config with risk_per_trade=0.03
      When I load the capital-mgmt config
      Then the loaded risk_per_trade is 0.03

    Scenario: a config missing risk_per_trade entirely hard-stops
      Given a risk_math config missing risk_per_trade
      When I load the capital-mgmt config
      Then loading fails with a missing-trading-parameter error naming "risk_per_trade"
