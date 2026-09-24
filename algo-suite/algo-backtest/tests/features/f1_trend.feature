Feature: F1 trend-regime filter
  Proves the F1 trend filter (specs.md §11.3.2: "Recommends BUY/SELL aligned with the
  multi-timeframe trend; vetoes if direction conflicts"), ahead of any real LEAN-native
  ADX/EMA feature wiring (that is future 04a/04h integration work).

  Feature-key contract (documented again in `f1_trend.py`'s module docstring):
    - state.features["trend_direction"]: float, signed slope of the primary-timeframe
      EMA. Positive = uptrend, negative = downtrend, zero = flat.
    - state.features["trend_strength"]: float in [0, 100], an ADX-style trend-strength
      reading for the primary timeframe.
    - state.features["higher_tf_trend_direction"]: float, same sign convention as
      trend_direction, computed on a coarser timeframe (multi-timeframe confirmation).

  A "direction conflict" is trend_direction and higher_tf_trend_direction disagreeing
  in sign (both nonzero, opposite signs) — the primary timeframe wants to trade against
  the higher timeframe's regime.

  Rule: A direction conflict between timeframes vetoes the chain

    Scenario: Primary uptrend conflicts with a higher-timeframe downtrend
      Given trend_direction 0.8, trend_strength 30.0 and higher_tf_trend_direction -0.5
      When F1 is applied
      Then F1 vetoes with reason mentioning "conflict"
      And F1's filter_name is "F1_trend"
      And F1 recommends "NEUTRAL" with veto

    Scenario: Primary downtrend conflicts with a higher-timeframe uptrend
      Given trend_direction -0.6, trend_strength 25.0 and higher_tf_trend_direction 0.4
      When F1 is applied
      Then F1 vetoes with reason mentioning "conflict"
      And F1's filter_name is "F1_trend"
      And F1 recommends "NEUTRAL" with veto

  Rule: Aligned timeframes produce a directional recommendation and a trend_score enrichment

    Scenario: Both timeframes agree on an uptrend
      Given trend_direction 0.8, trend_strength 40.0 and higher_tf_trend_direction 0.3
      When F1 is applied
      Then F1 recommends "BUY" with no veto
      And F1's filter_name is "F1_trend"
      And F1's reason is non-empty
      And F1 enriches "trend_score" with value 0.32

    Scenario: Both timeframes agree on a downtrend
      Given trend_direction -0.5, trend_strength 60.0 and higher_tf_trend_direction -0.2
      When F1 is applied
      Then F1 recommends "SELL" with no veto
      And F1's filter_name is "F1_trend"
      And F1's reason is non-empty
      And F1 enriches "trend_score" with value -0.3

    Scenario: A flat higher timeframe never conflicts with a trending primary timeframe
      Given trend_direction 0.6, trend_strength 20.0 and higher_tf_trend_direction 0.0
      When F1 is applied
      Then F1 recommends "BUY" with no veto

  Rule: A flat primary trend is neither a conflict nor a directional call

    Scenario: No slope on the primary timeframe
      Given trend_direction 0.0, trend_strength 10.0 and higher_tf_trend_direction 0.5
      When F1 is applied
      Then F1 recommends "NEUTRAL" with no veto

  Rule: A missing required feature is a hard, explained failure (fail-fast)

    Scenario: trend_direction is absent from state.features
      Given a state missing "trend_direction"
      When F1 is applied
      Then F1 raises an error naming "trend_direction"
