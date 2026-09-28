Feature: Constant-direction control filter — the two drift-control votes (story 21, T7)
  Proves `chain/filters/constant_direction.py`'s `ConstantDirectionFilter`, the sole voter
  behind the always-short and always-long drift-control arms (spec CC-23, decision D9). It
  is configured once with a fixed direction, BUY or SELL, and emits that vote on every bar
  it is asked about, regardless of price, momentum, relative intensity, news or model
  state — it never abstains, never explicitly holds, and never vetoes on its own account.
  It reads no `news_event_intensity`, sentiment or F7 feature and requires none of them
  to be present in `ExecutionState.features`; the control isolates the confluence chain's
  trigger and context logic from its own vote, not from risk management (design: "both
  controls enter whenever flat and eligible after risk/warmup rules; they share costs and
  the time exit with A"). The two drift-control arms remain subject to the same real F5
  risk-guard and F6 capital-management vetoes, through the real `FilterChain.run`, as
  every other cell (CC-23).

  Rule: A constant-direction filter always votes its configured direction (CC-23)

    Scenario Outline: a filter configured for <direction> votes <direction> regardless of state (<case>)
      Given a constant-direction filter configured for "<direction>"
      And a bar whose features are:
        | feature               | value      |
        | f1_momentum_sign      | <momentum> |
        | news_event_intensity  | <intensity> |
      When the constant-direction filter applies
      Then the constant-direction result recommends "<direction>"
      And the constant-direction result does not veto
      And the constant-direction result has no enrichment

      Examples:
        | case                                                         | direction | momentum | intensity |
        | always-short votes SELL with bullish momentum and calm news  | SELL      | 1        | 0.0       |
        | always-short votes SELL with bearish momentum and a news shock | SELL    | -1       | -2.0      |
        | always-long votes BUY with bearish momentum and calm news    | BUY       | -1       | 0.0       |
        | always-long votes BUY with bullish momentum and a news shock | BUY       | 1        | -2.0      |

    Scenario: the same filter instance votes identically on two unrelated bars
      Given a constant-direction filter configured for "SELL"
      When the constant-direction filter applies to a bar at "2016-03-01T10:00:00Z"
      And the constant-direction filter applies to a bar at "2016-06-15T14:30:00Z"
      Then both constant-direction results recommend "SELL"

  Rule: The vote never depends on any news, sentiment or model feature being present (CC-23, D9)

    Scenario Outline: a filter configured for <direction> votes <direction> on a bar with no features at all
      Given a constant-direction filter configured for "<direction>"
      And a bar whose features are empty
      When the constant-direction filter applies
      Then the constant-direction result recommends "<direction>"
      And the constant-direction result does not veto

      Examples:
        | direction |
        | SELL      |
        | BUY       |

  Rule: Only BUY or SELL may be configured; anything else is refused with the fix (D9)

    Scenario Outline: a constant-direction filter configured for <case> is refused
      When a constant-direction filter configured for "<value>" is built and fails
      Then the constant-direction failure names "<fragment>"

      Examples:
        | case                       | value   | fragment                                          |
        | HOLD is not a trigger      | HOLD    | direction must be 'BUY' or 'SELL', got 'HOLD'     |
        | NEUTRAL is not a trigger   | NEUTRAL | direction must be 'BUY' or 'SELL', got 'NEUTRAL'  |
        | ABSTAIN is not a trigger   | ABSTAIN | direction must be 'BUY' or 'SELL', got 'ABSTAIN'  |
        | lower-case is not accepted | buy     | direction must be 'BUY' or 'SELL', got 'buy'      |
        | an unrelated word          | LONG    | direction must be 'BUY' or 'SELL', got 'LONG'     |
        | an empty string            |         | direction must be 'BUY' or 'SELL', got ''         |

  Rule: The constant vote is still subject to the real F5/F6 vetoes through the real chain (CC-23)
    The voter is the real `ConstantDirectionFilter`; the gates are the real
    `RiskGuardFilter` and `CapitalMgmtFilter` parsed from the sections below, proving the
    control is not a bypass of risk management (same real-gate pattern T1 uses for the
    agreement terminal).

    Scenario Outline: <case>
      Given the real F5 and F6 gates parsed from:
        """
        risk_guard:
          portfolio_at_risk_cap: 0.18
          daily_drawdown_limit: -0.05
          weekly_drawdown_limit: -0.15
          max_concurrent_trades_per_account: 2
          max_leverage: 30
        capital_mgmt:
          risk_per_trade: 0.03
          stop_loss_pips: 20.0
          pip_value_per_lot: 10.0
          lot_notional_units: 100000
          assumed_leverage: 30
          targets: []
          trail_stops: []
        """
      And a chain of a constant-direction voter "constant_direction" configured for "SELL", then the real F5 and F6 gates
      And the chain is closed by an agreement terminal requiring "constant_direction"
      And a bar whose features are:
        | feature                     | value               |
        | account_daily_pnl_fraction  | -0.01               |
        | account_weekly_pnl_fraction | -0.02               |
        | account_open_trade_count    | 1                   |
        | account_leverage            | 5.0                 |
        | account_balance             | 10000               |
        | pip_value                   | 10.0                |
        | margin_per_lot              | 3000.0              |
        | available_margin            | <available_margin>  |
        | account_portfolio_at_risk   | <portfolio_at_risk> |
      When the constant-direction chain runs
      Then the constant-direction chain outcome decision is "<decision>"
      And the constant-direction chain was vetoed by "<vetoed_by>"

      Examples:
        | case                                              | portfolio_at_risk | available_margin | decision | vetoed_by       |
        | the gates pass and the constant vote trades        | 0.05              | 10000             | SELL     | none            |
        | F5 vetoes the constant vote before the terminal     | 0.50              | 10000             | NO_TRADE | f5_risk_guard   |
        | F6 vetoes the constant vote on margin               | 0.05              | 100               | NO_TRADE | f6_capital_mgmt |
