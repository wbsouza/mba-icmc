Feature: DecisionRecorder — per-run trade_id bookkeeping for decisions.parquet
  `chain/audit.py` (Spec 04f) converts one ChainOutcome into a DecisionRow given a
  trade_id, but holds no state across bars. DecisionRecorder is the per-run
  bookkeeping every chain-driven LEAN algorithm needs (Spec 04h): from each *filled*
  order's position transition, track which LEAN trade is currently open — following
  LEAN's own flat-to-flat trade grouping, so trade_id stays a real foreign key into
  trades.json (each trade's first order id) — and write the whole batch at end of run.

  Rule: A fill that opens a position makes its order the current trade

    Scenario: An entry fill from flat opens a trade
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And a "BUY" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "1"

    Scenario: A HOLD decision while the trade is open still carries its trade_id
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And a "HOLD" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "1"

    Scenario: A reversal opens a new trade under the reversing order
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And order "2" fills taking the position from 1000 to -1000
      And a "SELL" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "2"

  Rule: A same-side fill stays inside the trade it scales

    Scenario: Scaling into an open long keeps the original trade_id
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And order "2" fills taking the position from 1000 to 1500
      And a "BUY" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "1"

    Scenario: Partially reducing an open short keeps the original trade_id
      Given a decision recorder
      When order "1" fills taking the position from 0 to -1000
      And order "2" fills taking the position from -1000 to -400
      And a "HOLD" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "1"

  Rule: Only a fill that flattens the position clears the trade

    Scenario: A closing fill clears the trade_id
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And order "2" fills taking the position from 1000 to 0
      And a "HOLD" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is absent

    Scenario: A decision recorded before any fill carries no trade_id
      Given a decision recorder
      When a "HOLD" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is absent

    Scenario: A NO_TRADE decision never carries a trade_id, even with a trade open
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And a "NO_TRADE" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is absent

  Rule: Consecutive trades never bleed their ids into each other

    Scenario: A second trade's id does not leak into rows of the first
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And a "BUY" decision for pair "EURUSD" is recorded
      And order "2" fills taking the position from 1000 to 0
      And a "NO_TRADE" decision for pair "EURUSD" is recorded
      And order "5" fills taking the position from 0 to 1000
      And a "BUY" decision for pair "EURUSD" is recorded
      Then recorded row 1's trade_id is "1"
      And recorded row 2's trade_id is absent
      And recorded row 3's trade_id is "5"

  Rule: The accumulated batch persists to and round-trips from decisions.parquet

    Scenario: Every recorded row is written and reads back unchanged, in order
      Given a decision recorder
      When order "1" fills taking the position from 0 to 1000
      And a "BUY" decision for pair "EURUSD" is recorded
      And order "2" fills taking the position from 1000 to 0
      And a "NO_TRADE" decision for pair "GBPUSD" is recorded
      And the recorder is written to "decisions.parquet"
      Then the Parquet file exists on disk
      And it contains 2 rows
      And row 1 read back has trade_id "1" and pair "EURUSD"
      And row 2 read back has trade_id absent and pair "GBPUSD"
