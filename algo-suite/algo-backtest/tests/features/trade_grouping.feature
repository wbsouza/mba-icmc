@integration
Feature: decisions.parquet trade ids identify the LEAN trade open at each moment
  The chain algorithms configure LEAN's trade ledger flat-to-flat (FIFO) — one trade
  per position episode — and DecisionRecorder.on_fill follows the same policy, so the
  trade_id recorded after any fill is the ledger trade actually open at that instant,
  through scale-ins, partial exits and reversals (LEAN's default fill-to-fill grouping
  would split those into overlapping trades).

  Scenario: Scale-in, partial exits and a reversal keep the recorder aligned with the ledger
    Given 12 one-minute QuoteBars starting at "2014-05-07T13:00:00" UTC
    And they are materialized to lean-data in timezone "UTC"
    When the trade-grouping probe replays "20140507" in the LEAN container
    Then the backtest exits successfully
    And the ledger has trades with order ids "1,2,3,4", "5,6" and "6,7"
    And after every fill the recorder's trade id is the first order of the ledger trade open at that instant
