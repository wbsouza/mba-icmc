Feature: F5 — RiskGuard filter
  Wires `rules/risk_guard.py` into the deterministic filter chain (`chain/model.py`'s
  `Filter` protocol). No upstream filter populates account/position state yet (Wave 2 is
  still landing F1-F4 in parallel — same situation Spec 04c documented for its own filter),
  so this filter defines and proves its own minimal `state.features` contract:

    - "account_portfolio_at_risk" (float): fraction of balance currently at risk
    - "account_daily_pnl_fraction" (float): today's signed P&L as a fraction of balance
    - "account_weekly_pnl_fraction" (float): this week's signed P&L as a fraction of balance
    - "account_open_trade_count" (int): currently open trades on this account
    - "account_leverage" (float): currently employed leverage

  F5 never proposes a direction (ABSTAIN always) — it only gates: VETO if any configured
  cap is breached, PASS otherwise.

  Rule: F5 vetoes when RiskGuard reports a breach, and passes otherwise

    Scenario: a clean account state passes with no veto
      Given synthetic account features: portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, open trades 1, leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When F5 applies to the state
      Then F5's result does not veto
      And F5's recommendation is "ABSTAIN"
      And F5's filter name is "f5_risk_guard"
      And F5's reason mentions "no risk-guard caps breached"

    Scenario: a breached cap causes F5 to veto
      Given synthetic account features: portfolio-at-risk 0.2, daily P&L -0.01, weekly P&L -0.02, open trades 1, leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When F5 applies to the state
      Then F5's result vetoes
      And F5's recommendation is "ABSTAIN"
      And F5's filter name is "f5_risk_guard"
      And F5's reason mentions "portfolio_at_risk"

    Scenario: two simultaneous breaches are both joined into F5's reason
      Given synthetic account features: portfolio-at-risk 0.2, daily P&L -0.08, weekly P&L -0.02, open trades 1, leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When F5 applies to the state
      Then F5's result vetoes
      And F5's reason mentions "portfolio_at_risk"
      And F5's reason mentions "daily_pnl_fraction"
      And F5's reason joins breaches with "; "

  Rule: A missing required feature key fails fast, naming the missing key

    Scenario: account_leverage missing from state.features fails fast
      Given synthetic account features missing "account_leverage"
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When F5 applies to the state
      Then applying F5 fails naming "account_leverage"

  Rule: A fractional open-trade-count is rejected, never silently truncated

    Scenario: a non-integer account_open_trade_count fails fast
      Given synthetic account features with a fractional open trade count 2.9
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When F5 applies to the state
      Then applying F5 fails naming "account_open_trade_count"
