Feature: The expanded candlestick catalog reaches native signal production
  Story 22/23 integration lane, T7 minimum viable slice: the shared
  candle_catalog/candle_context/candle_sequence producer (chain/market_signals.py)
  populates `candle_evidence` on every closed bar when `pattern.detector: expanded`
  is selected, and F3's required_entry mode reads it end to end inside a real LEAN
  run — proving the wiring, not a methodology result. `candles-expanded`
  (strategies/candles-expanded/config.yaml) is F1 + F3(required_entry, expanded) +
  F5 + F6 with no F7 model.

  @integration
  Scenario: the candles-expanded rule-only strategy runs a real backtest end to end
    Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
    When I run candles-expanded over the 2014-05-08 to 2014-05-09 test span with cash 10000
    Then the strategy run exits successfully
    And the run artifacts are written under the data root for "candles-expanded"
    And the container log shows the F1-F7 chain actually evaluated a decision for "candles-expanded"
