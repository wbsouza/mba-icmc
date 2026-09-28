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

  Rule: A child drops an inherited top-level section by setting it to null

    Scenario: a variant that removes F2 and F3 from the chain drops their inherited sections
      Given a strategy config directory with "baseline" filters "f1_trend,f2_indicator,f3_pattern,f5_risk_guard" and families "trend"
      And "news-only" extends "baseline" with filters "f1_trend,f5_risk_guard" and families "trend"
      And "news-only" sets its "indicator" section to null
      And "news-only" sets its "pattern" section to null
      When strategy "news-only" is loaded
      Then the loaded strategy's filters are "f1_trend,f5_risk_guard"
      And the loaded strategy has no "indicator" config
      And the loaded strategy has no "pattern" config
      And the loaded strategy's raw config has no "pattern" section
      And the loaded strategy records no provenance under "pattern"
      And the loaded strategy's parameter "risk_guard.max_leverage" comes from "baseline/config.yaml"

    Scenario: an inherited section whose filter the child no longer lists is still a hard stop
      Given a strategy config directory with "baseline" filters "f1_trend,f3_pattern,f5_risk_guard" and families "trend"
      And "news-only" extends "baseline" with filters "f1_trend,f5_risk_guard" and families "trend"
      When loading strategy "news-only" fails
      Then the failure names "strategy 'news-only' declares a 'pattern:' section but does not list 'f3_pattern'"

    Scenario: a null inside a section keeps its per-key meaning rather than dropping the section
      Given a strategy config directory with "baseline" filters "f1_trend,f5_risk_guard" and families "trend"
      And "loose" extends "baseline" with filters "f1_trend,f5_risk_guard" and families "trend"
      And "loose" also declares risk_guard.max_leverage as null
      When strategy "loose" is loaded
      Then the loaded strategy has a typed "risk_guard" config
      And the loaded strategy's raw config records risk_guard.max_leverage null

  Rule: Every configurable filter listed in filters has its own parameter section, and vice versa

    Scenario Outline: a strategy listing <filter> resolves a typed <section> config
      Given a strategy config directory with "typed" filters "<filter>" and families "trend"
      When strategy "typed" is loaded
      Then the loaded strategy has a typed "<section>" config

      Examples:
        | filter          | section      |
        | f2_indicator    | indicator    |
        | f3_pattern      | pattern      |
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
        | f2_indicator    | indicator    |
        | f3_pattern      | pattern      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |
        | f7_meta_learner | meta_learner |

  Rule: Sections with defaults may be omitted; the effective values are recorded in the resolved config

    Scenario: price_features is always resolved, defaulting when the section is absent
      Given a strategy config directory with "plain" filters "f1_trend" and families "trend"
      When strategy "plain" is loaded
      Then the loaded strategy's price features are ema_fast 3, ema_slow 8, ema_higher_tf 60, rsi_period 14, macd_fast 12, macd_slow 26, macd_signal 9
      And the loaded strategy's raw config records price_features.ema_fast 3

    Scenario: a partial price_features section overrides and the rest defaults
      Given a strategy config directory with "custom" filters "f1_trend" and families "trend"
      And "custom" adds a "price_features" section {ema_higher_tf: 240}
      When strategy "custom" is loaded
      Then the loaded strategy's price features are ema_fast 3, ema_slow 8, ema_higher_tf 240, rsi_period 14, macd_fast 12, macd_slow 26, macd_signal 9
      And the loaded strategy's raw config records price_features.ema_higher_tf 240

    Scenario: execution is always resolved, defaulting when the section is absent (story 12)
      Given a strategy config directory with "plain" filters "f1_trend" and families "trend"
      When strategy "plain" is loaded
      Then the loaded strategy's execution config is spread_pips 0.0, commission_per_lot 0.0, min_hold_bars 0, broker_stop_level_pips 0.0
      And the loaded strategy's raw config records execution.spread_pips 0.0
      And the loaded strategy's parameter "execution.min_hold_bars" comes from "default"

    Scenario: a partial execution section overrides, the rest defaults, each with its provenance
      Given a strategy config directory with "custom" filters "f1_trend" and families "trend"
      And "custom" adds a "execution" section {spread_pips: 1.0}
      When strategy "custom" is loaded
      Then the loaded strategy's execution config is spread_pips 1.0, commission_per_lot 0.0, min_hold_bars 0, broker_stop_level_pips 0.0
      And the loaded strategy's raw config records execution.commission_per_lot 0.0
      And the loaded strategy's parameter "execution.spread_pips" comes from "custom/config.yaml"
      And the loaded strategy's parameter "execution.commission_per_lot" comes from "default"

    Scenario Outline: a five-key capital_mgmt section resolves the trade-plan default for <key> and records it
      Given a strategy config directory with "sized" filters "f1_trend,f6_capital_mgmt" and families "trend"
      When strategy "sized" is loaded
      Then the loaded strategy's raw config records capital_mgmt.<key> <value>
      And the loaded strategy's parameter "capital_mgmt.<key>" comes from "default"
      And the loaded strategy's parameter "capital_mgmt.risk_per_trade" comes from "sized/config.yaml"

      Examples:
        | key                  | value                                        |
        | stop_loss_shrink     | 0.0                                          |
        | targets              | [{at_level_ratio: 2.0, close_fraction: 1.0}] |
        | trail_stops          | []                                           |
        | min_reward_risk      | null                                         |
        | stop_distance_source | fixed                                        |
        | min_stop_factor      | 1.0                                          |

    Scenario: an explicit trade-plan key keeps its file as provenance
      Given a strategy config directory with "planned" filters "f1_trend,f6_capital_mgmt" and families "trend"
      And "planned" also declares capital_mgmt.min_reward_risk as 2.0
      When strategy "planned" is loaded
      Then the loaded strategy's raw config records capital_mgmt.min_reward_risk 2.0
      And the loaded strategy's parameter "capital_mgmt.min_reward_risk" comes from "planned/config.yaml"

    Scenario Outline: an invalid <section> trade-plan or execution value fails fast at load (<case>)
      Given a strategy config directory with "bad" filters "f1_trend,f6_capital_mgmt" and families "trend"
      And "bad" also declares <section>.<key> as <value>
      When loading strategy "bad" fails
      Then the failure names "<key>"
      And the failure names "bad"

      Examples:
        | case                     | section      | key                  | value |
        | stop shrink of 100%      | capital_mgmt | stop_loss_shrink     | 1.0   |
        | unknown stop source      | capital_mgmt | stop_distance_source | structural |
        | stop factor below one    | capital_mgmt | min_stop_factor      | 0.5   |
        | negative broker level    | execution    | broker_stop_level_pips | -1  |
        | negative spread          | execution    | spread_pips          | -1    |
        | fractional hold          | execution    | min_hold_bars        | 1.5   |

    Scenario: an execution section that is not a mapping fails fast
      Given a strategy config directory with "odd" filters "f1_trend" and families "trend"
      And "odd" replaces its "execution" section with a scalar
      When loading strategy "odd" fails
      Then the failure names "execution"

    Scenario Outline: <filter> listed without its optional <section> section resolves defaults and records them
      Given a strategy config directory with "defaulted" filters "<filter>" and families "trend"
      And "defaulted" drops its "<section>" section
      When strategy "defaulted" is loaded
      Then the loaded strategy has a typed "<section>" config
      And the loaded strategy's raw config records <section>.<key> <value>

      Examples:
        | filter       | section   | key              | value |
        | f2_indicator | indicator | rsi_midline      | 50    |
        | f3_pattern   | pattern   | bullish_patterns | [bullish_engulfing, hammer, morning_star] |

    Scenario Outline: an invalid <section> value fails fast at load (<case>)
      Given a strategy config directory with "bad" filters "f1_trend,f2_indicator,f3_pattern" and families "trend"
      And "bad" adds a "<section>" section <section_yaml>
      When loading strategy "bad" fails
      Then the failure names "<names>"
      And the failure names "strategy 'bad'"

      Examples:
        | case                        | section        | section_yaml                | names        |
        | fast EMA above slow EMA     | price_features | {ema_fast: 9}               | ema_fast     |
        | RSI midline out of range    | indicator      | {rsi_midline: 100}          | rsi_midline  |
        | pattern in both lists       | pattern        | {bullish_patterns: [hammer], bearish_patterns: [hammer]} | hammer |

    Scenario Outline: listing <filter> without its <section> section fails fast
      Given a strategy config directory with "gap" filters "<filter>" and families "trend"
      And "gap" drops its "<section>" section
      When loading strategy "gap" fails
      Then the failure names "strategy 'gap' lists '<filter>' but has no '<section>:' section"

      Examples:
        | filter          | section      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |

    Scenario: listing f7_meta_learner without its thresholds fails fast naming the missing key
      Given a strategy config directory with "gap" filters "f7_meta_learner" and families "trend"
      And "gap" drops meta_learner key "theta_high"
      When loading strategy "gap" fails
      Then the failure names "strategy 'gap': meta_learner.theta_high is missing"

    Scenario Outline: a listed filter's section missing <key> fails fast through the loader
      Given a strategy config directory with "gapkey" filters "<filter>" and families "trend"
      And "gapkey" drops "<section>" key "<key>"
      When loading strategy "gapkey" fails
      Then the failure names "strategy 'gapkey': <section>.<key> is missing"

      Examples:
        | filter          | section      | key                            |
        | f4_news_context | news_context | event_intensity_veto_threshold |
        | f5_risk_guard   | risk_guard   | max_leverage                   |
        | f6_capital_mgmt | capital_mgmt | risk_per_trade                 |

    Scenario Outline: a <section> section for a filter that is not listed fails fast
      Given a strategy config directory with "stray" filters "f1_trend" and families "trend"
      And "stray" adds a "<section>" section anyway
      When loading strategy "stray" fails
      Then the failure names "strategy 'stray' declares a '<section>:' section but does not list '<filter>'"

      Examples:
        | filter          | section      |
        | f2_indicator    | indicator    |
        | f3_pattern      | pattern      |
        | f4_news_context | news_context |
        | f5_risk_guard   | risk_guard   |
        | f6_capital_mgmt | capital_mgmt |

    Scenario Outline: a <section> section that is not a mapping fails fast
      Given a strategy config directory with "odd" filters "<filter>" and families "trend"
      And "odd" replaces its "<section>" section with a scalar
      When loading strategy "odd" fails
      Then the failure names "strategy 'odd': '<section>' must be a mapping (got 'str')"

      Examples:
        | filter          | section        |
        | f1_trend        | price_features |
        | f4_news_context | news_context   |
        | f5_risk_guard   | risk_guard     |
        | f6_capital_mgmt | capital_mgmt   |

    Scenario Outline: F7 keys in meta_learner without f7_meta_learner listed fail fast (<key>)
      Given a strategy config directory with "strayf7" filters "f1_trend" and families "trend"
      And "strayf7" adds meta_learner key "<key>" with value <value>
      When loading strategy "strayf7" fails
      Then the failure names "<key>"
      And the failure names "strategy 'strayf7': meta_learner declares"
      And the failure names "'f7_meta_learner' in filters"

      Examples:
        | key         | value |
        | theta_high  | 0.55  |
        | theta_low   | 0.45  |
        | regime_gate | false |

  Rule: Filter names are checked when the config is loaded, not when the chain is built

    Scenario Outline: an unknown filter name fails fast at load time (<filter>)
      Given a strategy config directory with "typo" filters "f1_trend,<filter>" and families "trend"
      When loading strategy "typo" fails
      Then the failure names "strategy 'typo': unknown filters ['<filter>'] in filters"
      And the failure names "known filters"

      Examples:
        | filter        |
        | f9_bogus      |
        | F1_trend      |
        | f7_metalearner |

  Rule: The config schema version is declared and current

    Scenario Outline: a config whose schema_version is not 2 fails fast (<case>)
      Given a strategy config directory with "old" filters "f1_trend" and families "trend"
      And "old" sets schema_version to <schema_version>
      When loading strategy "old" fails
      Then the failure names "strategy 'old': schema_version must be the integer 2 (got <got>)"

      Examples:
        | case            | schema_version | got  |
        | version 1       | 1              | 1    |
        | version 3       | 3              | 3    |
        | string "2"      | "2"            | '2'  |
        | boolean         | true           | True |
        | missing         | absent         | None |

  Rule: extends chains of any depth compose base-first, like compose override files (2026-09-27)

    Scenario: a three-level chain resolves with each level overriding its base
      Given a strategy config directory with "core" filters "f1_trend,f5_risk_guard" and families "trend"
      And "mid" extends "core" with filters "f1_trend,f2_indicator,f5_risk_guard" and families "trend"
      And "mid" also declares risk_guard.max_leverage 10
      And "leaf" extends "mid" with filters "f1_trend,f2_indicator,f3_pattern,f5_risk_guard" and families "trend"
      When strategy "leaf" is loaded
      Then the loaded strategy's filters are "f1_trend,f2_indicator,f3_pattern,f5_risk_guard"
      And the loaded strategy's risk-guard caps have max_leverage 10
      And the loaded strategy's risk-guard caps have daily_drawdown_limit -0.05
      And the loaded strategy extends "mid"

    Scenario: an extends cycle fails fast naming the chain
      Given a strategy config directory with "a" filters "f1_trend" and families "trend"
      And "b" extends "a" with filters "f1_trend" and families "trend"
      And "a" is changed to extend "b"
      When loading strategy "a" fails
      Then the failure names "extends cycle a -> b -> a"

    Scenario Outline: an extends value that is not a strategy name fails fast (<case>)
      Given a strategy config directory with "odd" filters "f1_trend" and families "trend"
      And "odd" sets extends to <value>
      When loading strategy "odd" fails
      Then the failure names "strategy 'odd': 'extends' must be a strategy name, got <got>"

      Examples:
        | case    | value      | got          |
        | integer | 7          | 7            |
        | list    | [baseline] | ['baseline'] |

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

    Scenario: the real news-only strategy runs the news family alone through F4, F5, F6 and F7
      When the real strategy "news-only" is loaded with the default root
      Then the loaded strategy's filters are "f4_news_context,f5_risk_guard,f6_capital_mgmt,f7_meta_learner"
      And the real loaded strategy's meta-learner families are "news"
      And the real loaded strategy extends "baseline"
      And the real loaded strategy has typed "news_context,risk_guard,capital_mgmt,meta_learner" configs
      And the real loaded strategy has no "indicator" config
      And the real loaded strategy has no "pattern" config
      And the loaded strategy's raw config has no "pattern" section
      And the loaded strategy's raw config records price_features.bar_minutes 60
      And the loaded strategy's raw config records meta_learner.label_horizon_minutes 60
      And the loaded strategy's raw config records meta_learner.regime_gate false

    Scenario: the real news-only-h4 strategy restates only the H4 clock over news-only
      When the real strategy "news-only-h4" is loaded with the default root
      Then the loaded strategy's filters are "f4_news_context,f5_risk_guard,f6_capital_mgmt,f7_meta_learner"
      And the real loaded strategy's meta-learner families are "news"
      And the real loaded strategy extends "news-only"
      And the loaded strategy's raw config records price_features.bar_minutes 240
      And the loaded strategy's raw config records meta_learner.label_horizon_minutes 240

    Scenario Outline: every bundled strategy resolves the same F7 thresholds and gate (<name>)
      When the real strategy "<name>" is loaded with the default root
      Then the real loaded strategy's F7 config has theta_high 0.55, theta_low 0.45 and the regime gate off

      Examples:
        | name          |
        | baseline      |
        | baseline-dsha |
        | hybrid        |
        | news-only     |
        | news-only-h4  |

    Scenario Outline: the news-only strategies carry the Heikin-Ashi H4 template's risk and exit plan (<name>: <section>.<key>)
      When the real strategy "<name>" is loaded with the default root
      Then the loaded strategy's raw config records <section>.<key> <value>
      And the loaded strategy's parameter "<section>.<key>" comes from "<source>"

      Examples:
        | name         | section        | key                               | value                                                                              | source                  |
        | news-only    | risk_guard     | portfolio_at_risk_cap             | 0.18                                                                               | news-only/config.yaml   |
        | news-only    | capital_mgmt   | stop_loss_shrink                  | 0.5                                                                                | news-only/config.yaml   |
        | news-only    | capital_mgmt   | targets                           | [{at_level_ratio: 4.0, close_fraction: 0.5}, {at_level_ratio: 6.0, close_fraction: 0.5}] | news-only/config.yaml   |
        | news-only    | capital_mgmt   | trail_stops                       | [{at_level_ratio: 2.0, to_level_ratio: 0.1}]                                       | news-only/config.yaml   |
        | news-only    | capital_mgmt   | stop_distance_source              | swing                                                                              | news-only/config.yaml   |
        | news-only    | news_context   | event_intensity_veto_threshold    | -0.5                                                                               | news-only/config.yaml   |
        | news-only    | price_features | swing_lookback_bars               | 60                                                                                 | baseline/config.yaml    |
        | news-only    | execution      | spread_pips                       | 1.0                                                                                | baseline/config.yaml    |
        | news-only-h4 | price_features | bar_minutes                       | 240                                                                                | news-only-h4/config.yaml |
        | news-only-h4 | meta_learner   | label_horizon_minutes             | 240                                                                                | news-only-h4/config.yaml |
        | news-only-h4 | capital_mgmt   | stop_loss_shrink                  | 0.5                                                                                | news-only/config.yaml   |
        | news-only-h4 | risk_guard     | max_concurrent_trades_per_account | 2                                                                                  | news-only/config.yaml   |
        | news-only-h4 | execution      | spread_pips                       | 1.0                                                                                | baseline/config.yaml    |

    Scenario Outline: every bundled strategy resolves the A05 trade plan and execution costs (<name>: <section>.<key>)
      When the real strategy "<name>" is loaded with the default root
      Then the loaded strategy's raw config records <section>.<key> <value>
      And the loaded strategy's parameter "<section>.<key>" comes from "baseline/config.yaml"

      Examples:
        | name          | section      | key                               | value                                          |
        | baseline      | capital_mgmt | stop_loss_shrink                  | 0.2                                            |
        | baseline      | capital_mgmt | min_stop_pips                     | 5.0                                            |
        | baseline      | capital_mgmt | targets                           | [{at_level_ratio: 2.0, close_fraction: 0.5}]   |
        | baseline      | capital_mgmt | trail_stops                       | [{at_level_ratio: 0.5, to_level_ratio: -0.66}] |
        | baseline      | capital_mgmt | min_reward_risk                   | 2.0                                            |
        | baseline      | capital_mgmt | stop_distance_source              | swing                                          |
        | baseline      | capital_mgmt | min_stop_factor                   | 1.2                                            |
        | baseline      | execution    | broker_stop_level_pips            | 0.0                                            |
        | hybrid        | capital_mgmt | min_stop_factor                   | 1.2                                            |
        | baseline      | capital_mgmt | atr_multiplier                    | 2.0                                            |
        | baseline      | risk_guard   | max_concurrent_trades_per_account | 2                                              |
        | baseline      | execution    | spread_pips                       | 1.0                                            |
        | baseline      | execution    | commission_per_lot                | 0.0                                            |
        | baseline      | execution    | min_hold_bars                     | 0                                              |
        | hybrid        | capital_mgmt | min_reward_risk                   | 2.0                                            |
        | hybrid        | capital_mgmt | trail_stops                       | [{at_level_ratio: 0.5, to_level_ratio: -0.66}] |
        | hybrid        | risk_guard   | max_concurrent_trades_per_account | 2                                              |
        | hybrid        | execution    | spread_pips                       | 1.0                                            |
        | baseline-dsha | capital_mgmt | stop_loss_shrink                  | 0.2                                            |
        | baseline-dsha | execution    | spread_pips                       | 1.0                                            |

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
      Then the failure names "strategy 'odd': 'meta_learner' must be a mapping (got 'str')"

    Scenario: a scalar meta_learner overriding a dict base still fails fast
      Given a strategy config directory with "baseline" filters "f1_trend" and families "trend"
      And "hybrid" extends "baseline" overriding meta_learner with a scalar value
      When loading strategy "hybrid" fails
      Then the failure names "meta_learner"

  Rule: A feature family F7 cannot fit fails fast at load time

    Scenario Outline: an unknown family name fails fast naming the known families (<families>)
      Given a strategy config directory with "typo" filters "f1_trend,f7_meta_learner" and families "<families>"
      When loading strategy "typo" fails
      Then the failure names "strategy 'typo': unknown meta_learner.families <unknown> — known families: ['trend', 'indicator', 'pattern', 'news']"

      Examples:
        | families      | unknown            |
        | trend,volume  | ['volume']         |
        | trends        | ['trends']         |
        | news,f4,f1    | ['f4', 'f1']       |

  Rule: A scalar meta_learner.families value fails fast instead of splitting into characters

    Scenario: meta_learner.families as a bare string fails fast, not "tuple(str)" char-splat
      Given a strategy config directory with "typo" filters "f1_trend" and meta_learner.families as the scalar "trend"
      When loading strategy "typo" fails
      Then the failure names "strategy 'typo': 'meta_learner.families' must be a list"

    Scenario: filters as a bare string fails fast, not "tuple(str)" char-splat
      Given a strategy config directory with "typo" filters as the scalar "f1_trend"
      When loading strategy "typo" fails
      Then the failure names "strategy 'typo': 'filters' must be a list"

    Scenario: meta_learner.families as a mapping fails fast, not "list(dict)" silent key-splat
      Given a strategy config directory with "oddmap" filters "f1_trend" and meta_learner.families as a mapping
      When loading strategy "oddmap" fails
      Then the failure names "meta_learner.families"

    Scenario: meta_learner.families with a non-string entry fails fast
      Given a strategy config directory with "badfamily" filters "f1_trend" and meta_learner.families containing a non-string entry
      When loading strategy "badfamily" fails
      Then the failure names "meta_learner.families"

  Rule: The resolved configuration travels as one self-contained YAML document

    Scenario: a resolved strategy dumps to YAML and loads back identically
      Given a strategy config directory with "baseline" filters "f1_trend,f5_risk_guard,f7_meta_learner" and families "trend"
      And "hybrid" extends "baseline" with filters "f1_trend,f4_news_context,f5_risk_guard,f7_meta_learner" and families "trend,news"
      When strategy "hybrid" is loaded
      And the loaded strategy is dumped to a resolved YAML file and loaded back as "hybrid"
      Then the reloaded strategy equals the loaded one apart from its extends provenance
      And the reloaded strategy's parameter "filters" comes from "strategy.yaml"
      And the reloaded strategy's parameter "risk_guard.max_leverage" comes from "strategy.yaml"

    Scenario: a resolved file still carrying extends is rejected
      Given a resolved strategy file for "leaf" that still declares extends
      When loading the resolved strategy file as "leaf" fails
      Then the failure names "extends"

  Rule: The F1 perception source is typed into the loaded config

    Scenario Outline: perception_source resolves to the declared source (<source>)
      Given a strategy config directory with "seen" filters "f1_trend" and families "trend"
      And "seen" sets perception_source to <source>
      When strategy "seen" is loaded
      Then the loaded strategy's perception source is "<source>"

      Examples:
        | source                      |
        | double_smoothed_heikin_ashi |
        | ema                         |

  Rule: A child in an external directory may extend a bundled base

    Scenario: an external variant resolves its base from the bundled strategies
      Given an external strategy config directory with "tight" extending bundled "baseline" and meta_learner theta_high 0.6
      When strategy "tight" is loaded from that external directory
      Then the loaded strategy's F7 config has theta_high 0.6
      And the loaded strategy's filters end with "f6_capital_mgmt,f7_meta_learner"

  Rule: Every resolved parameter records where it came from (2026-09-27)

    Scenario Outline: provenance names the config.yaml in the chain that set <key>, or default
      Given a strategy config directory with "core" filters "f1_trend,f2_indicator,f5_risk_guard,f7_meta_learner" and families "trend"
      And "core" drops its "indicator" section
      And "mid" extends "core" with filters "f1_trend,f2_indicator,f5_risk_guard,f7_meta_learner" and families "trend"
      And "mid" also declares risk_guard.max_leverage 10
      And "leaf" extends "mid" with filters "f1_trend,f2_indicator,f5_risk_guard,f7_meta_learner" and families "trend"
      And "leaf" also declares meta_learner.theta_high 0.6
      When strategy "leaf" is loaded
      Then the loaded strategy's parameter "<key>" comes from "<source>"

      Examples:
        | key                                | source           |
        | meta_learner.theta_high            | leaf/config.yaml |
        | meta_learner.theta_low             | core/config.yaml |
        | risk_guard.max_leverage            | mid/config.yaml  |
        | risk_guard.daily_drawdown_limit    | core/config.yaml |
        | indicator.rsi_midline              | default          |
        | price_features.ema_fast            | default          |
        | meta_learner.label_horizon_minutes | default          |
        | filters                            | leaf/config.yaml |
