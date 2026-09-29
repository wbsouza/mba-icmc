Feature: RiskGuard — portfolio/drawdown/leverage caps
  Closes the risk gaps the EJB version's README documents as unenforced (specs.md §14.8):
  no portfolio-level capital cap, no daily/weekly drawdown limit, no per-account concurrent-
  trade cap, no leverage cap. Every cap is a key of the strategy config.yaml `risk_guard`
  section (2026-09-27 amendment, story 09), each independently `null`-disableable; a cap
  absent from the section is a hard stop (CLAUDE.md fail-fast policy, specs.md §14.9.1),
  never a silent skip.

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

  Rule: F5's caps come from the strategy config.yaml risk_guard section

    Scenario Outline: a complete risk_guard section parses into RiskGuardCaps (<case>)
      Given a risk_guard section with portfolio_at_risk_cap=<par>, daily_drawdown_limit=<daily>, weekly_drawdown_limit=<weekly>, max_concurrent_trades_per_account=<trades>, max_leverage=<lev>
      When the risk-guard caps are parsed for strategy "baseline"
      Then the parsed caps have portfolio_at_risk_cap <par>, daily_drawdown_limit <daily>, weekly_drawdown_limit <weekly>, max_concurrent_trades_per_account <trades> and max_leverage <lev>

      Examples:
        | case                     | par  | daily | weekly | trades | lev  |
        | all five caps set        | 0.1  | -0.05 | -0.1   | 2      | 10.0 |
        | leverage cap disabled    | 0.1  | -0.05 | -0.1   | 2      | null |
        | every cap disabled       | null | null  | null   | null   | null |
        | zero drawdown floors     | 0.2  | 0     | 0      | 1      | 30   |

    Scenario Outline: a risk_guard section missing <key> fails fast naming the key and the strategy
      Given a risk_guard section missing "<key>"
      When parsing the risk-guard caps for strategy "baseline" fails
      Then the risk-guard config failure names "strategy 'baseline': risk_guard.<key> is missing"

      Examples:
        | key                               |
        | portfolio_at_risk_cap             |
        | daily_drawdown_limit              |
        | weekly_drawdown_limit             |
        | max_concurrent_trades_per_account |
        | max_leverage                      |

    Scenario Outline: an invalid risk_guard value fails fast (<case>)
      Given a risk_guard section with portfolio_at_risk_cap=<par>, daily_drawdown_limit=<daily>, weekly_drawdown_limit=<weekly>, max_concurrent_trades_per_account=<trades>, max_leverage=<lev>
      When parsing the risk-guard caps for strategy "baseline" fails
      Then the risk-guard config failure names "<failure>"

      Examples:
        | case                              | par  | daily | weekly | trades | lev  | failure                                                                                    |
        | positive daily drawdown limit     | 0.1  | 0.05  | -0.1   | 2      | 10.0 | risk_guard.daily_drawdown_limit must be <= 0                                               |
        | positive weekly drawdown limit    | 0.1  | -0.05 | 0.1    | 2      | 10.0 | risk_guard.weekly_drawdown_limit must be <= 0                                              |
        | fractional concurrent-trade cap   | 0.1  | -0.05 | -0.1   | 1.5    | 10.0 | strategy 'baseline': risk_guard.max_concurrent_trades_per_account must be an integer or null |
        | non-numeric leverage cap          | 0.1  | -0.05 | -0.1   | 2      | high | strategy 'baseline': risk_guard.max_leverage must be a number                              |
