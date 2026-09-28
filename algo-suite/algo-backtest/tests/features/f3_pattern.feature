Feature: F3 pattern filter
  Proves the F3 pattern filter (specs.md §11.3.2: "Recommends BUY/SELL on detected
  pattern; ABSTAIN if no pattern at current bar"), ahead of any real TA-Lib CDL*
  feature wiring (future 04a/04h integration work).

  Feature-key contract (documented again in `f3_pattern.py`'s module docstring):
    - state.features["candlestick_pattern"]: str | None. `None`/absent means no
      pattern was detected this bar. A present value must be one of the recognized
      TA-Lib-style CDL* pattern names this filter knows (bullish or bearish); an
      unrecognized name is a data-contract violation and raises.

  Rule: No pattern detected this bar is a no-information bar (ABSTAIN)

    Scenario: candlestick_pattern is absent
      Given no candlestick pattern is present
      When F3 is applied
      Then F3 abstains with reason mentioning "no pattern"
      And F3's filter_name is "F3_pattern"

  Rule: A recognized bullish pattern recommends BUY

    Scenario Outline: bullish reversal/continuation patterns
      Given candlestick pattern "<pattern>"
      When F3 is applied
      Then F3 recommends "BUY" with reason mentioning "<pattern>"
      And F3's filter_name is "F3_pattern"

      Examples:
        | pattern            |
        | bullish_engulfing  |
        | hammer             |
        | morning_star       |

  Rule: A recognized bearish pattern recommends SELL

    Scenario Outline: bearish reversal/continuation patterns
      Given candlestick pattern "<pattern>"
      When F3 is applied
      Then F3 recommends "SELL" with reason mentioning "<pattern>"
      And F3's filter_name is "F3_pattern"

      Examples:
        | pattern            |
        | bearish_engulfing  |
        | shooting_star      |
        | evening_star       |

  Rule: An unrecognized pattern name is a hard, explained failure (fail-fast)

    Scenario: candlestick_pattern names a pattern F3 doesn't recognize
      Given candlestick pattern "not_a_real_pattern"
      When F3 is applied
      Then F3 raises an error naming "not_a_real_pattern"

  Rule: F3's pattern vocabulary comes from the strategy config.yaml pattern section (2026-09-27)

    Scenario Outline: the pattern section parses with the default vocabulary when empty (<case>)
      Given a pattern section <section>
      When the pattern config is parsed for strategy "baseline"
      Then the parsed bullish patterns are "<bullish>"
      And the parsed bearish patterns are "<bearish>"

      Examples:
        | case              | section                                                        | bullish                                 | bearish                                         |
        | empty: defaults   | {}                                                             | bullish_engulfing, hammer, morning_star | bearish_engulfing, shooting_star, evening_star  |
        | custom vocabulary | {bullish_patterns: [piercing_line], bearish_patterns: [dark_cloud]} | piercing_line                      | dark_cloud                                      |

    Scenario Outline: an invalid pattern section fails fast (<case>)
      Given a pattern section <section>
      When parsing the pattern config for strategy "baseline" fails
      Then the pattern config failure names "<failure>"

      Examples:
        | case                         | section                                                      | failure                                                                               |
        | a name in both lists         | {bullish_patterns: [hammer], bearish_patterns: [hammer]}     | strategy 'baseline': pattern lists ['hammer'] as both bullish and bearish             |
        | empty bullish list           | {bullish_patterns: []}                                       | strategy 'baseline': pattern.bullish_patterns must be a non-empty list of pattern names, got [] |
        | scalar instead of list       | {bearish_patterns: shooting_star}                            | strategy 'baseline': pattern.bearish_patterns must be a non-empty list of pattern names, got 'shooting_star' |
        | mapping instead of list      | {bullish_patterns: {hammer: true}}                           | strategy 'baseline': pattern.bullish_patterns must be a non-empty list of pattern names |
        | integer instead of list      | {bearish_patterns: 5}                                        | strategy 'baseline': pattern.bearish_patterns must be a non-empty list of pattern names, got 5 |
        | non-string entry             | {bullish_patterns: [hammer, 7]}                              | strategy 'baseline': pattern.bullish_patterns must contain only strings                |
        | unknown key                  | {neutral_patterns: [doji]}                                   | strategy 'baseline': pattern has unknown keys ['neutral_patterns']                   |

    Scenario Outline: the configured vocabulary drives the recommendation (<case>)
      Given a pattern section <section>
      And a detected candlestick pattern "<pattern>"
      When F3 is applied with that pattern config
      Then F3 recommends "<recommendation>" with reason mentioning "<pattern>"

      Examples:
        | case                              | section                                                             | pattern       | recommendation |
        | default hammer is bullish         | {}                                                                  | hammer        | BUY            |
        | custom piercing_line is bullish   | {bullish_patterns: [piercing_line], bearish_patterns: [dark_cloud]} | piercing_line | BUY            |
        | custom dark_cloud is bearish      | {bullish_patterns: [piercing_line], bearish_patterns: [dark_cloud]} | dark_cloud    | SELL           |
