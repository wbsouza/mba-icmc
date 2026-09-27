Feature: Strategy-chain config loading (Spec 04h)
  `src/algo_backtest/strategies/<name>/config.yaml` declares one strategy's filter chain,
  meta-learner feature families and — since the 2026-09-27 amendment (story 09) — every
  configurable filter's own parameter section: `risk_guard` (F5), `capital_mgmt` (F6),
  `news_context` (F4) and `meta_learner.theta_high/theta_low/regime_gate` (F7). `hybrid`
  composes onto `baseline` via a single `extends:` level (docs/experiments.md §1,
  technical-debt.md TD-8).

  Rule: A strategy with no extends resolves its own config verbatim

    Scenario: baseline resolves its own filters and feature families
      Given a strategy config directory with "baseline" filters "f1_trend,f2_indicator,f7_meta_learner" and families "trend,indicator"
      When strategy "baseline" is loaded
      Then the loaded strategy's name is "baseline"
      And the loaded strategy's filters are "f1_trend,f2_indicator,f7_meta_learner"
      And the loaded strategy's meta-learner families are "trend,indicator"
      And the loaded strategy extends nothing

  Rule: extends composes the child's keys onto the base

    Scenario: hybrid extends baseline, adding F4 and the news family
      Given a strategy config directory with "baseline" filters "f1_trend,f5_risk_guard,f7_meta_learner" and families "trend"
      And "hybrid" extends "baseline" with filters "f1_trend,f4_news_context,f5_risk_guard,f7_meta_learner" and families "trend,news"
      When strategy "hybrid" is loaded
      Then the loaded strategy's filters are "f1_trend,f4_news_context,f5_risk_guard,f7_meta_learner"
      And the loaded strategy's meta-learner families are "trend,news"
      And the loaded strategy extends "baseline"

    Scenario: a base-only nested key survives the merge (deep-merge, not wholesale replace)
      Given a strategy config directory with "baseline" filters "f1_trend,f7_meta_learner" and families "trend"
      And "baseline" also declares meta_learner.theta_high 0.6
      And "hybrid" extends "baseline" with filters "f1_trend,f4_news_context,f7_meta_learner" and families "trend,news"
      When strategy "hybrid" is loaded
      Then the loaded strategy's raw meta_learner.theta_high is 0.6
      And the loaded strategy's F7 config has theta_high 0.6

    Scenario: a child overrides one key of an inherited filter section without restating the rest
      Given a strategy config directory with "baseline" filters "f1_trend,f5_risk_guard" and families "trend"
      And "hybrid" extends "baseline" with filters "f1_trend,f5_risk_guard" and families "trend"
      And "hybrid" also declares risk_guard.max_leverage 10
      When strategy "hybrid" is loaded
      Then the loaded strategy's risk-guard caps have max_leverage 10
      And the loaded strategy's risk-guard caps have daily_drawdown_limit -0.05

  Rule: Every configurable filter listed in filters has its own parameter section, and vice versa

    Scenario Outline: a strategy listing <filter> resolves a typed <section> config
      Given a strategy config directory with "typed" filters "<filter>" and families "trend"
      When strategy "typed" is loaded
      Then the loaded strategy has a typed "<section>" config

      Examples:
        | filter          | section      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |
        | f7_meta_learner | meta_learner |

    Scenario Outline: a strategy not listing <filter> resolves no <section> config
      Given a strategy config directory with "plain" filters "f1_trend" and families "trend"
      When strategy "plain" is loaded
      Then the loaded strategy has no "<section>" config

      Examples:
        | filter          | section      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |
        | f7_meta_learner | meta_learner |

    Scenario Outline: listing <filter> without its <section> section fails fast
      Given a strategy config directory with "gap" filters "<filter>" and families "trend"
      And "gap" drops its "<section>" section
      When loading strategy "gap" fails
      Then the failure names "<section>"
      And the failure names "<filter>"

      Examples:
        | filter          | section      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |

    Scenario: listing f7_meta_learner without its thresholds fails fast naming the missing key
      Given a strategy config directory with "gap" filters "f7_meta_learner" and families "trend"
      And "gap" drops meta_learner key "theta_high"
      When loading strategy "gap" fails
      Then the failure names "theta_high"

    Scenario Outline: a <section> section for a filter that is not listed fails fast
      Given a strategy config directory with "stray" filters "f1_trend" and families "trend"
      And "stray" adds a "<section>" section anyway
      When loading strategy "stray" fails
      Then the failure names "<section>"
      And the failure names "<filter>"

      Examples:
        | filter          | section      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |

    Scenario Outline: a <section> section that is not a mapping fails fast
      Given a strategy config directory with "odd" filters "<filter>" and families "trend"
      And "odd" replaces its "<section>" section with a scalar
      When loading strategy "odd" fails
      Then the failure names "<section>"

      Examples:
        | filter          | section      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |

  Rule: Only one level of extends is supported (TD-8)

    Scenario: a base that itself declares extends fails fast
      Given a strategy config directory with "core" filters "f1_trend" and families "trend"
      And "mid" extends "core" with filters "f1_trend,f2_indicator" and families "trend"
      And "leaf" extends "mid" with filters "f1_trend,f2_indicator,f3_pattern" and families "trend"
      When loading strategy "leaf" fails
      Then the failure names "only one level of extends"

  Rule: An unknown strategy fails fast, naming the missing config path

    Scenario: loading a strategy with no config.yaml fails fast
      Given an empty strategy config directory
      When loading strategy "nonexistent" fails
      Then the failure names "unknown strategy"

    Scenario: a config.yaml that is not a YAML mapping fails fast
      Given a strategy config directory with a non-mapping config for "listy"
      When loading strategy "listy" fails
      Then the failure names "must contain a YAML mapping"

  Rule: The real baseline/hybrid strategy configs resolve correctly (default root)

    Scenario: the real baseline strategy resolves its documented price-only chain
      When the real strategy "baseline" is loaded with the default root
      Then the real loaded strategy's filters end with "f6_capital_mgmt,f7_meta_learner"
      And the real loaded strategy's filters do not include "f4_news_context"
      And the real loaded strategy's meta-learner families are "trend,indicator,pattern"
      And the real loaded strategy has typed "risk_guard,capital_mgmt,meta_learner" configs
      And the real loaded strategy has no "news_context" config

    Scenario: the real hybrid strategy extends baseline, adding f4_news_context and news
      When the real strategy "hybrid" is loaded with the default root
      Then the real loaded strategy's filters include "f4_news_context"
      And the real loaded strategy's meta-learner families are "trend,indicator,pattern,news"
      And the real loaded strategy extends "baseline"
      And the real loaded strategy has typed "news_context,risk_guard,capital_mgmt,meta_learner" configs

    Scenario Outline: every bundled strategy resolves the same F7 thresholds and gate (<name>)
      When the real strategy "<name>" is loaded with the default root
      Then the real loaded strategy's F7 config has theta_high 0.55, theta_low 0.45 and the regime gate off

      Examples:
        | name          |
        | baseline      |
        | baseline-dsha |
        | hybrid        |

  Rule: An empty resolved filters list fails fast, whether absent or explicitly empty

    Scenario: a strategy config with an explicitly empty filters list fails fast
      Given a strategy config directory with an empty filters list for "empty"
      When loading strategy "empty" fails
      Then the failure names "empty filters list"

    Scenario: a strategy config with no filters key at all fails fast the same way
      Given a strategy config directory with no filters key at all for "nofilters"
      When loading strategy "nofilters" fails
      Then the failure names "empty filters list"

  Rule: An empty meta_learner mapping resolves to no feature families

    Scenario: a meta_learner dict with no families key resolves to no feature families
      Given a strategy config directory with "sparse" filters "f1_trend" and an empty meta_learner mapping
      When strategy "sparse" is loaded
      Then the loaded strategy has no meta-learner families

  Rule: A non-mapping meta_learner section fails fast rather than silently degrading

    Scenario: a scalar meta_learner value fails fast
      Given a strategy config directory with "odd" filters "f1_trend" and a scalar meta_learner
      When loading strategy "odd" fails
      Then the failure names "meta_learner"

    Scenario: a scalar meta_learner overriding a dict base still fails fast
      Given a strategy config directory with "baseline" filters "f1_trend" and families "trend"
      And "hybrid" extends "baseline" overriding meta_learner with a scalar value
      When loading strategy "hybrid" fails
      Then the failure names "meta_learner"

  Rule: A scalar meta_learner.families value fails fast instead of splitting into characters

    Scenario: meta_learner.families as a bare string fails fast, not "tuple(str)" char-splat
      Given a strategy config directory with "typo" filters "f1_trend" and meta_learner.families as the scalar "trend"
      When loading strategy "typo" fails
      Then the failure names "meta_learner.families"

    Scenario: meta_learner.families as a mapping fails fast, not "list(dict)" silent key-splat
      Given a strategy config directory with "oddmap" filters "f1_trend" and meta_learner.families as a mapping
      When loading strategy "oddmap" fails
      Then the failure names "meta_learner.families"

    Scenario: meta_learner.families with a non-string entry fails fast
      Given a strategy config directory with "badfamily" filters "f1_trend" and meta_learner.families containing a non-string entry
      When loading strategy "badfamily" fails
      Then the failure names "meta_learner.families"
