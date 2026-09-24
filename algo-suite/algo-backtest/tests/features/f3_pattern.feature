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
