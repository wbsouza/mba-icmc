Feature: F2 indicator filter
  Proves the F2 indicator filter (specs.md §11.3.2: "Recommends direction confirmed by
  oscillators; ABSTAIN on no-information bars"), ahead of any real LEAN-native
  RSI/MACD feature wiring (future 04a/04h integration work).

  Feature-key contract (documented again in `f2_indicator.py`'s module docstring):
    - state.features["rsi"]: float | None in [0, 100], or None on a no-information bar
      (e.g. still warming up). Above 50 is a bullish bias, below 50 bearish.
    - state.features["macd_hist"]: float | None, the MACD histogram (signal-line
      distance), or None on a no-information bar. Positive is bullish momentum,
      negative bearish.

  A "no-information bar" is either oscillator being absent/None — F2 needs both to
  confirm a direction, so it abstains rather than guess. F2 never vetoes.

  Rule: A missing oscillator reading is a no-information bar (ABSTAIN)

    Scenario: rsi has not warmed up yet
      Given rsi is absent and macd_hist 0.4
      When F2 is applied
      Then F2 abstains with reason mentioning "no-information"
      And F2's filter_name is "F2_indicator"

    Scenario: macd_hist has not warmed up yet
      Given rsi 62.0 and macd_hist is absent
      When F2 is applied
      Then F2 abstains with reason mentioning "no-information"
      And F2's filter_name is "F2_indicator"

  Rule: Both oscillators confirming the same direction produce a directional recommendation

    Scenario: RSI above 50 and a positive MACD histogram confirm an uptrend
      Given rsi 62.0 and macd_hist 0.4
      When F2 is applied
      Then F2 recommends "BUY"
      And F2's filter_name is "F2_indicator"
      And F2's reason is non-empty

    Scenario: RSI below 50 and a negative MACD histogram confirm a downtrend
      Given rsi 38.0 and macd_hist -0.4
      When F2 is applied
      Then F2 recommends "SELL"
      And F2's filter_name is "F2_indicator"
      And F2's reason is non-empty

  Rule: Disagreeing oscillators produce no confirmed direction

    Scenario: RSI bullish but MACD histogram bearish
      Given rsi 62.0 and macd_hist -0.1
      When F2 is applied
      Then F2 recommends "NEUTRAL"

  Rule: Oscillator readings must strictly cross their neutral threshold to confirm a direction

    Scenario: RSI exactly at 50 is not bullish
      Given rsi 50.0 and macd_hist 0.4
      When F2 is applied
      Then F2 recommends "NEUTRAL"

    Scenario: RSI just above 50 is bullish
      Given rsi 51.0 and macd_hist 0.4
      When F2 is applied
      Then F2 recommends "BUY"

    Scenario: A zero MACD histogram is not bullish momentum
      Given rsi 62.0 and macd_hist 0.0
      When F2 is applied
      Then F2 recommends "NEUTRAL"

    Scenario: RSI exactly at 50 is not bearish
      Given rsi 50.0 and macd_hist -0.4
      When F2 is applied
      Then F2 recommends "NEUTRAL"

    Scenario: RSI just above 50 is not bearish
      Given rsi 50.5 and macd_hist -0.4
      When F2 is applied
      Then F2 recommends "NEUTRAL"

    Scenario: A zero MACD histogram is not bearish momentum
      Given rsi 38.0 and macd_hist 0.0
      When F2 is applied
      Then F2 recommends "NEUTRAL"

    Scenario: A positive MACD histogram is not bearish momentum, even with a low RSI
      Given rsi 38.0 and macd_hist 0.5
      When F2 is applied
      Then F2 recommends "NEUTRAL"

  Rule: rsi outside [0, 100] fails fast

    Scenario Outline: an out-of-range rsi is rejected
      Given rsi <rsi> and macd_hist 0.4
      When F2 is applied
      Then F2 raises an error naming "rsi"

      Examples:
        | rsi   |
        | -1.0  |
        | 101.0 |
        | 150.0 |

    Scenario Outline: a boundary rsi is accepted
      Given rsi <rsi> and macd_hist 0.4
      When F2 is applied
      Then F2's filter_name is "F2_indicator"

      Examples:
        | rsi   |
        | 0.0   |
        | 100.0 |

  Rule: F2's thresholds come from the strategy config.yaml indicator section (2026-09-27)

    Scenario Outline: the indicator section parses with defaults for what it omits (<case>)
      Given an indicator section <section>
      When the indicator config is parsed for strategy "baseline"
      Then the parsed indicator config has rsi_midline <midline> and macd_hist_threshold <threshold>

      Examples:
        | case                  | section                                          | midline | threshold |
        | empty: all defaults   | {}                                               | 50      | 0         |
        | custom midline        | {rsi_midline: 55}                                | 55      | 0         |
        | both overridden       | {rsi_midline: 45, macd_hist_threshold: 0.0001}   | 45      | 0.0001    |
        | midline just above 0  | {rsi_midline: 0.5}                               | 0.5     | 0         |
        | midline just below 100| {rsi_midline: 99.5}                              | 99.5    | 0         |

    Scenario Outline: an invalid indicator section fails fast (<case>)
      Given an indicator section <section>
      When parsing the indicator config for strategy "baseline" fails
      Then the indicator config failure names "<failure>"

      Examples:
        | case                     | section                       | failure                                                                        |
        | midline at 0             | {rsi_midline: 0}              | strategy 'baseline': indicator.rsi_midline must be strictly inside (0, 100), got 0.0   |
        | midline at 100           | {rsi_midline: 100}            | strategy 'baseline': indicator.rsi_midline must be strictly inside (0, 100), got 100.0 |
        | midline as a string      | {rsi_midline: mid}            | strategy 'baseline': indicator.rsi_midline must be a number, got 'mid'         |
        | threshold as a string    | {macd_hist_threshold: thin}   | strategy 'baseline': indicator.macd_hist_threshold must be a number, got 'thin' |
        | negative threshold       | {macd_hist_threshold: -0.1}   | strategy 'baseline': indicator.macd_hist_threshold must be >= 0                |
        | unknown key              | {stochastic_period: 14}       | strategy 'baseline': indicator has unknown keys ['stochastic_period']          |

    Scenario Outline: the configured midline decides bullish vs bearish (<case>)
      Given an indicator section <section>
      And rsi <rsi> and macd_hist <macd_hist>
      When F2 is applied with that indicator config
      Then F2 recommends "<recommendation>"

      Examples:
        | case                                    | section                        | rsi | macd_hist | recommendation |
        | 52 is bullish against the default 50    | {}                             | 52  | 0.4       | BUY            |
        | 52 is not bullish against midline 55    | {rsi_midline: 55}              | 52  | 0.4       | NEUTRAL        |
        | 56 clears midline 55                    | {rsi_midline: 55}              | 56  | 0.4       | BUY            |
        | 48 is bearish against the default 50    | {}                             | 48  | -0.4      | SELL           |
        | 48 is not bearish against midline 45    | {rsi_midline: 45}              | 48  | -0.4      | NEUTRAL        |
        | histogram inside the threshold band     | {macd_hist_threshold: 0.5}     | 60  | 0.4       | NEUTRAL        |
        | histogram beyond the threshold band     | {macd_hist_threshold: 0.5}     | 60  | 0.6       | BUY            |
        | negative histogram inside the band      | {macd_hist_threshold: 0.5}     | 40  | -0.4      | NEUTRAL        |
        | negative histogram beyond the band      | {macd_hist_threshold: 0.5}     | 40  | -0.6      | SELL           |
