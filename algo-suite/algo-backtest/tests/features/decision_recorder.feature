Feature: DecisionRecorder — per-run trade_id bookkeeping for decisions.parquet
  `chain/audit.py` (Spec 04f) converts one ChainOutcome into a DecisionRow given a
  trade_id, but holds no state across bars. DecisionRecorder is the per-run
  bookkeeping every chain-driven LEAN algorithm needs (Spec 04h): remember which
  trade_id is "currently open" so a HOLD row is still joined to the trade it is
  managing, forget it once the position closes, and write the whole batch once at
  end of algorithm.

  Rule: A trade opened via open_trade is attached to every row recorded until closed

    Scenario: A BUY decision recorded after open_trade carries that trade_id
      Given a decision recorder
      When trade "order-1" is opened
      And a "BUY" decision for pair "EURUSD" is recorded
      Then the last recorded row's trade_id is "order-1"

    Scenario: A HOLD decision recorded while a trade is open still carries its trade_id
      Given a decision recorder
      When trade "order-1" is opened
      And a "BUY" decision for pair "EURUSD" is recorded
      And a "HOLD" decision for pair "EURUSD" is recorded
      Then the last recorded row's trade_id is "order-1"

  Rule: Closing a trade clears the id for every row recorded afterward

    Scenario: A NO_TRADE decision recorded after close_trade carries no trade_id
      Given a decision recorder
      When trade "order-1" is opened
      And trade "order-1" is closed
      And a "NO_TRADE" decision for pair "EURUSD" is recorded
      Then the last recorded row's trade_id is absent

    Scenario: A decision recorded before any trade is opened carries no trade_id
      Given a decision recorder
      When a "NO_TRADE" decision for pair "EURUSD" is recorded
      Then the last recorded row's trade_id is absent

    Scenario: A HOLD decision recorded before any trade is opened carries no trade_id
      Given a decision recorder
      When a "HOLD" decision for pair "EURUSD" is recorded
      Then the last recorded row's trade_id is absent

    Scenario: A HOLD decision recorded after close_trade carries no trade_id
      Given a decision recorder
      When trade "order-1" is opened
      And trade "order-1" is closed
      And a "HOLD" decision for pair "EURUSD" is recorded
      Then the last recorded row's trade_id is absent

  Rule: Consecutive trades never bleed their ids into each other

    Scenario: A second trade's id does not leak into the row that closed the first
      Given a decision recorder
      When trade "order-1" is opened
      And a "BUY" decision for pair "EURUSD" is recorded
      And trade "order-1" is closed
      And a "NO_TRADE" decision for pair "EURUSD" is recorded
      And trade "order-5" is opened
      And a "BUY" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "order-1"
      And recorded row 2's trade_id is absent
      And recorded row 3's trade_id is "order-5"

  Rule: The accumulated batch persists to and round-trips from decisions.parquet

    Scenario: Every recorded row is written and reads back unchanged
      Given a decision recorder
      When trade "order-1" is opened
      And a "BUY" decision for pair "EURUSD" is recorded
      And trade "order-1" is closed
      And a "NO_TRADE" decision for pair "GBPUSD" is recorded
      And the recorder is written to "decisions.parquet"
      Then the Parquet file exists on disk
      And it contains 2 rows
      And row 1 read back has trade_id "order-1" and pair "EURUSD"
      And row 2 read back has trade_id absent and pair "GBPUSD"
