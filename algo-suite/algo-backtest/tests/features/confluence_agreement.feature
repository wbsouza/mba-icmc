Feature: Agreement terminal — named required votes close the confluence chain (story 21, T1)
  Proves `chain/terminal.py`'s `AgreementTerminalDecision`, the third terminal rule beside
  `F7TerminalDecision` and `LastFilterTerminalDecision` (spec CC-01..CC-05, decision D4).
  The rule: every *required* voter must have voted the same BUY or SELL; no other
  directional voter may disagree; an explicit HOLD from any voter blocks; optional
  ABSTAIN/NEUTRAL votes are ignored; anything else is HOLD. The terminal never vetoes:
  F5/F6 veto through `FilterChain.run` before it is ever consulted (CC-05).

  Configuration names voters by their canonical lower-case YAML ids (`f1_trend`,
  `f4_news_context`, ...) while `FilterResult.filter_name` carries each filter's runtime
  name (`F1_trend`, `F2_indicator`, `F3_pattern`, `f4_news_context`). The terminal is
  built with an explicit, closed `voter_name_map` from the first to the second; nothing is
  lower-cased or guessed (design: "do not silently lowercase arbitrary unknown names").
  Gates (`f5_risk_guard`, `f6_capital_mgmt`, `volume_strength`) emit no direction and can
  never be required voters (CC-04).

  Background:
    Given the canonical voter names map to runtime result names:
      | canonical       | runtime         |
      | f1_trend        | F1_trend        |
      | f2_indicator    | F2_indicator    |
      | f3_pattern      | F3_pattern      |
      | f4_news_context | f4_news_context |

  Rule: Unanimous required BUY or SELL votes are the decision (CC-01)

    Scenario Outline: every required voter agrees on <direction> and the terminal returns it (<case>)
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | <f1>           |
        | f4_news_context | <f4>           |
        | f5_risk_guard   | ABSTAIN        |
        | f6_capital_mgmt | ABSTAIN        |
      When the agreement terminal decides
      Then the agreement decision is "<direction>"

      Examples:
        | case                              | f1   | f4   | direction |
        | momentum up and intensity low buy | BUY  | BUY  | BUY       |
        | momentum down and intensity high  | SELL | SELL | SELL      |

    Scenario Outline: an optional voter that abstains or is neutral does not block agreement (<case>)
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | BUY            |
        | f4_news_context | BUY            |
        | F2_indicator    | <f2>           |
        | f5_risk_guard   | ABSTAIN        |
      When the agreement terminal decides
      Then the agreement decision is "BUY"

      Examples:
        | case                   | f2      |
        | F2 abstains            | ABSTAIN |
        | F2 is neutral          | NEUTRAL |
        | F2 agrees              | BUY     |

    Scenario Outline: a single required voter is enough (the T-only and M-only arms) (<case>)
      Given an agreement terminal requiring "<required>"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | <voter>         | <vote>         |
        | f5_risk_guard   | ABSTAIN        |
        | f6_capital_mgmt | ABSTAIN        |
      When the agreement terminal decides
      Then the agreement decision is "<decision>"

      Examples:
        | case                        | required        | voter           | vote | decision |
        | T-only: the trigger sells   | f4_news_context | f4_news_context | SELL | SELL     |
        | M-only: the context buys    | f1_trend        | F1_trend        | BUY  | BUY      |
        | T-only: the trigger neutral | f4_news_context | f4_news_context | NEUTRAL | HOLD  |

    Scenario: arm B requires all three voters and they agree
      Given an agreement terminal requiring "f1_trend, f4_news_context, f2_indicator"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | SELL           |
        | f4_news_context | SELL           |
        | F2_indicator    | SELL           |
        | f5_risk_guard   | ABSTAIN        |
        | f6_capital_mgmt | ABSTAIN        |
      When the agreement terminal decides
      Then the agreement decision is "SELL"

  Rule: A required voter that abstains, is neutral, holds or disagrees makes the decision HOLD (CC-02)

    Scenario Outline: required voters do not agree, so the chain holds (<case>)
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | <f1>           |
        | f4_news_context | <f4>           |
        | f5_risk_guard   | ABSTAIN        |
      When the agreement terminal decides
      Then the agreement decision is "HOLD"

      Examples:
        | case                                  | f1      | f4      |
        | the context abstains                  | ABSTAIN | BUY     |
        | the context is neutral (zero return)  | NEUTRAL | SELL    |
        | the context explicitly holds          | HOLD    | BUY     |
        | the trigger abstains                  | SELL    | ABSTAIN |
        | the trigger is neutral (interior)     | BUY     | NEUTRAL |
        | the trigger explicitly holds          | SELL    | HOLD    |
        | context up, trigger down              | BUY     | SELL    |
        | context down, trigger up              | SELL    | BUY     |

    Scenario Outline: an optional voter that disagrees or explicitly holds blocks agreement (<case>)
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | BUY            |
        | f4_news_context | BUY            |
        | <optional>      | <vote>         |
      When the agreement terminal decides
      Then the agreement decision is "HOLD"

      Examples:
        | case                                     | optional     | vote |
        | F2 votes against the required side       | F2_indicator | SELL |
        | F3 votes against the required side       | F3_pattern   | SELL |
        | F2 explicitly holds                      | F2_indicator | HOLD |
        | F3 explicitly holds                      | F3_pattern   | HOLD |

  Rule: When every vote abstains or is neutral, nothing is proposed: HOLD (CC-03)

    Scenario Outline: all voters abstain or are neutral (<case>)
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | <f1>           |
        | f4_news_context | <f4>           |
        | F2_indicator    | <f2>           |
        | f5_risk_guard   | ABSTAIN        |
        | f6_capital_mgmt | ABSTAIN        |
      When the agreement terminal decides
      Then the agreement decision is "HOLD"

      Examples:
        | case                        | f1      | f4      | f2      |
        | everything abstains         | ABSTAIN | ABSTAIN | ABSTAIN |
        | everything is neutral       | NEUTRAL | NEUTRAL | NEUTRAL |
        | a mix of abstain and neutral| NEUTRAL | ABSTAIN | NEUTRAL |

  Rule: An invalid required-voter list fails fast at construction, naming the offender and the fix (CC-04)

    Scenario Outline: building the terminal with <case> fails
      When an agreement terminal requiring "<required>" is built and fails
      Then the agreement failure names "<fragment>"
      And the agreement failure names "required_filters"

      Examples:
        | case                                   | required                        | fragment                                          |
        | an empty list                          |                                 | is empty — name at least one direction-emitting filter |
        | a duplicated name                      | f1_trend, f4_news_context, f1_trend | 'f1_trend' more than once                     |
        | an unknown name                        | f1_trend, f9_oracle             | 'f9_oracle' is not a known voter                  |
        | the runtime spelling instead of canonical | F1_trend                     | 'F1_trend' is not a known voter                   |
        | the F5 gate                            | f4_news_context, f5_risk_guard  | 'f5_risk_guard' is a gate, not a direction-emitting voter |
        | the F6 gate                            | f6_capital_mgmt                 | 'f6_capital_mgmt' is a gate, not a direction-emitting voter |

    Scenario: the unknown-name failure lists the known canonical voters so the typo is easy to fix
      When an agreement terminal requiring "f4_news_contxt" is built and fails
      Then the agreement failure names "known voters: ['f1_trend', 'f2_indicator', 'f3_pattern', 'f4_news_context']"

    Scenario: an empty voter name map is refused at construction
      Given the canonical voter names map to no runtime result names
      When an agreement terminal requiring "f1_trend" is built and fails
      Then the agreement failure names "voter_name_map is empty"

  Rule: A required result that is missing or duplicated in the chain state fails fast at decision time (CC-04)

    Scenario: a required voter that never ran is a chain misconfiguration, not a HOLD
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | BUY            |
        | f5_risk_guard   | ABSTAIN        |
      When the agreement terminal decides and fails
      Then the agreement failure names "required voter 'f4_news_context' (runtime name 'f4_news_context') did not run"
      And the agreement failure names "filters that ran: ['F1_trend', 'f5_risk_guard']"

    Scenario: a required voter with two results is a chain misconfiguration, not a majority
      Given an agreement terminal requiring "f1_trend, f4_news_context"
      And the chain state holds these filter results:
        | filter_name     | recommendation |
        | F1_trend        | BUY            |
        | F1_trend        | BUY            |
        | f4_news_context | BUY            |
      When the agreement terminal decides and fails
      Then the agreement failure names "required voter 'f1_trend' (runtime name 'F1_trend') ran 2 times"

    Scenario: an empty chain state fails naming the first required voter
      Given an agreement terminal requiring "f1_trend"
      And the chain state holds no filter results
      When the agreement terminal decides and fails
      Then the agreement failure names "required voter 'f1_trend' (runtime name 'F1_trend') did not run"
      And the agreement failure names "filters that ran: []"

  Rule: F5 and F6 vetoes short-circuit the real chain before the agreement terminal is consulted (CC-05)
    The gates are the real `RiskGuardFilter` and `CapitalMgmtFilter` parsed from the
    sections below; the voters are fixed-vote stubs standing in for the momentum context
    and the relative trigger, whose own behaviour T2/T4 prove. The terminal is the real
    `AgreementTerminalDecision`, wrapped only to count how often it is consulted.

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
      And a chain of a "<f1_vote>" voter "F1_trend", a "<f4_vote>" voter "f4_news_context", then the real F5 and F6 gates
      And the chain is closed by an agreement terminal requiring "f1_trend, f4_news_context"
      And a bar whose features are:
        | feature                     | value                |
        | account_daily_pnl_fraction  | -0.01                |
        | account_weekly_pnl_fraction | -0.02                |
        | account_open_trade_count    | 1                    |
        | account_leverage            | 5.0                  |
        | account_balance             | 10000                |
        | pip_value                   | 10.0                 |
        | margin_per_lot              | 3000.0               |
        | available_margin            | <available_margin>   |
        | account_portfolio_at_risk   | <portfolio_at_risk>  |
      When the agreement chain runs
      Then the agreement chain outcome decision is "<decision>"
      And the agreement chain was vetoed by "<vetoed_by>"
      And every agreement chain filter ran in order "<filters_ran>"
      And the agreement terminal was consulted <consulted> times

      Examples:
        | case                                           | f1_vote | f4_vote | portfolio_at_risk | available_margin | decision | vetoed_by       | filters_ran                                       | consulted |
        | the gates pass and the agreed side is traded   | SELL    | SELL    | 0.05              | 10000            | SELL     | none            | F1_trend, f4_news_context, f5_risk_guard, f6_capital_mgmt | 1 |
        | the gates pass but the voters disagree         | BUY     | SELL    | 0.05              | 10000            | HOLD     | none            | F1_trend, f4_news_context, f5_risk_guard, f6_capital_mgmt | 1 |
        | F5 vetoes an agreed side before the terminal   | SELL    | SELL    | 0.50              | 10000            | NO_TRADE | f5_risk_guard   | F1_trend, f4_news_context, f5_risk_guard          | 0         |
        | F6 vetoes on margin before the terminal        | BUY     | BUY     | 0.05              | 100              | NO_TRADE | f6_capital_mgmt | F1_trend, f4_news_context, f5_risk_guard, f6_capital_mgmt | 0 |

  Rule: The legacy terminals keep their behaviour beside the new one (CC-20)

    Scenario Outline: LastFilterTerminalDecision still maps its filter's <recommendation> to <decision>
      Given the chain state holds these filter results:
        | filter_name     | recommendation   |
        | f4_news_context | <recommendation> |
        | f5_risk_guard   | ABSTAIN          |
      When LastFilterTerminalDecision for "f4_news_context" decides
      Then the agreement decision is "<decision>"

      Examples:
        | recommendation | decision |
        | BUY            | BUY      |
        | SELL           | SELL     |
        | NEUTRAL        | HOLD     |
        | ABSTAIN        | HOLD     |

    Scenario: F7TerminalDecision still fails fast when F7 did not run last
      Given the chain state holds these filter results:
        | filter_name | recommendation |
        | F1_trend    | BUY            |
      When F7TerminalDecision decides and fails
      Then the agreement failure names "f7_meta_learner"

    Scenario: decision_to_order_action is unchanged for every decision the agreement terminal can emit
      Then decision_to_order_action maps "BUY" to "execute", "SELL" to "execute" and "HOLD" to "manage"
