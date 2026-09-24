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
