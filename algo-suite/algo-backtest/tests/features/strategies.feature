Feature: Strategy-chain config loading (Spec 04h)
  `src/algo_backtest/strategies/<name>/config.yaml` declares one strategy's filter chain +
  meta-learner feature families; `hybrid` composes onto `baseline` via a single
  `extends:` level (docs/experiments.md §1, technical-debt.md TD-8).

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
      Given a strategy config directory with "baseline" filters "f1_trend" and families "trend"
      And "baseline" also declares meta_learner.theta_high 0.55
      And "hybrid" extends "baseline" with filters "f1_trend,f4_news_context" and families "trend,news"
      When strategy "hybrid" is loaded
      Then the loaded strategy's raw meta_learner.theta_high is 0.55

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

    Scenario: the real hybrid strategy extends baseline, adding f4_news_context and news
      When the real strategy "hybrid" is loaded with the default root
      Then the real loaded strategy's filters include "f4_news_context"
      And the real loaded strategy's meta-learner families are "trend,indicator,pattern,news"
      And the real loaded strategy extends "baseline"

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
