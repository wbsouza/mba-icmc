Feature: RiskGuard — portfolio/drawdown/leverage caps
  Closes the risk gaps the fx-manager README documents as unenforced (specs.md §14.8):
  no portfolio-level capital cap, no daily/weekly drawdown limit, no per-account concurrent-
  trade cap, no leverage cap. Every cap is a config parameter (`risk_guard.*`), each
  independently `null`-disableable; a cap referenced by the schema but absent from config
  is a hard stop (CLAUDE.md fail-fast policy, specs.md §14.9.1), never a silent skip.

  Rule: Evaluating account state against caps reports every breached cap

    Scenario: no cap is breached
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports no breach

    Scenario: the portfolio-at-risk cap is breached
      Given an account with portfolio-at-risk 0.2, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "portfolio_at_risk_cap"

    Scenario: the daily drawdown limit is breached
      Given an account with portfolio-at-risk 0.05, daily P&L -0.08, weekly P&L -0.02, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "daily_drawdown_limit"

    Scenario: the weekly drawdown limit is breached
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.2, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "weekly_drawdown_limit"

    Scenario: the max-concurrent-trades cap is breached
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 3 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "max_concurrent_trades_per_account"

    Scenario: the max-leverage cap is breached
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 1 and leverage 20.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "max_leverage"

    Scenario: multiple caps breach at once and all are reported
      Given an account with portfolio-at-risk 0.2, daily P&L -0.08, weekly P&L -0.02, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "portfolio_at_risk_cap"
      And the risk guard reports a breach of "daily_drawdown_limit"

  Rule: A value exactly at its cap does not breach; the cap itself is the allowed limit

    Scenario: portfolio-at-risk exactly at its cap does not breach
      Given an account with portfolio-at-risk 0.1, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports no breach

    Scenario: daily P&L exactly at its drawdown limit does not breach
      Given an account with portfolio-at-risk 0.05, daily P&L -0.05, weekly P&L -0.02, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports no breach

    Scenario: weekly P&L exactly at its drawdown limit does not breach
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.1, an open-trade count of 1 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports no breach

    Scenario: leverage exactly at its cap does not breach
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 1 and leverage 10.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports no breach

    Scenario: open-trade count exactly at the concurrent-trades cap already breaches
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 2 and leverage 5.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I evaluate the risk guard
      Then the risk guard reports a breach of "max_concurrent_trades_per_account"

  Rule: A null-disabled cap never breaches, however extreme the account state

    Scenario: a null max_leverage cap is never breached
      Given an account with portfolio-at-risk 0.05, daily P&L -0.01, weekly P&L -0.02, an open-trade count of 1 and leverage 500.0
      And risk-guard caps: portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=null
      When I evaluate the risk guard
      Then the risk guard reports no breach

  Rule: Loading the caps from config is fail-fast on a missing trading-impactful parameter

    Scenario: all five caps present in config load cleanly
      Given a risk_guard config with portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=10.0
      When I load the risk-guard config
      Then the loaded caps have portfolio_at_risk_cap 0.1
      And the loaded caps have daily_drawdown_limit -0.05
      And the loaded caps have weekly_drawdown_limit -0.1
      And the loaded caps have max_concurrent_trades_per_account 2
      And the loaded caps have max_leverage 10.0

    Scenario: a config with an explicitly null cap loads it as disabled
      Given a risk_guard config with portfolio_at_risk_cap=0.1, daily_drawdown_limit=-0.05, weekly_drawdown_limit=-0.1, max_concurrent_trades_per_account=2, max_leverage=null
      When I load the risk-guard config
      Then the loaded caps have max_leverage disabled

    Scenario: a config missing the max_leverage cap entirely hard-stops
      Given a risk_guard config missing "max_leverage"
      When I load the risk-guard config
      Then loading fails with a missing-trading-parameter error naming "max_leverage"
