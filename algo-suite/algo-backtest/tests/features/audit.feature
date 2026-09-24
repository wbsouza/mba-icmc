Feature: decisions.parquet audit trail
  Converts a ChainOutcome (chain/model.py, Spec 04b) into a DecisionRow per specs.md
  §11.3.4's column contract, and persists a batch of rows as the decisions.parquet
  audit trail via algo-core's ParquetRepository. features_hash hashes
  ChainOutcome.state.features as it stands at chain completion — the accumulated
  feature set, not a separate pre-chain snapshot, since ChainOutcome keeps no such
  snapshot (see its own aliasing caveat in chain/model.py).

  Rule: A ChainOutcome converts to a DecisionRow with the full §11.3.4 column set

    Scenario: A non-vetoed chain outcome converts with vetoed_by absent
      Given a chain outcome for pair "EURUSD" at "2024-01-01T00:00:00+00:00" with filter results:
        | filter_name | recommendation | reason         | veto  | confidence |
        | trend       | BUY            | uptrend        | false | 0.8        |
        | risk_guard  | BUY            | within limits  | false |            |
      And the accumulated features are:
        | key      | value |
        | trend_ok | true  |
      And the chain decision is "BUY"
      When the outcome is converted to a decision row with trade_id "trade-001"
      Then the decision row's trade_id is "trade-001"
      And the decision row's timestamp is "2024-01-01T00:00:00+00:00"
      And the decision row's pair is "EURUSD"
      And the decision row's final_decision is "BUY"
      And the decision row's vetoed_by is absent
      And the decision row's filter_results mirrors the source filter results in order
      And the decision row's features_hash matches hashing the accumulated features

    Scenario: A vetoed chain outcome names the vetoing filter in vetoed_by
      Given a chain outcome for pair "EURUSD" at "2024-01-01T00:00:00+00:00" with filter results:
        | filter_name | recommendation | reason  | veto  | confidence |
        | trend       | BUY            | uptrend | false | 0.8        |
        | risk_guard  | HOLD           | breach  | true  |            |
      And the accumulated features are:
        | key      | value |
        | trend_ok | true  |
      And the chain decision is "NO_TRADE"
      When the outcome is converted to a decision row with trade_id "trade-002"
      Then the decision row's vetoed_by is "risk_guard"
      And the decision row's final_decision is "NO_TRADE"
      And the decision row's trade_id is absent

  Rule: A NO_TRADE decision row's trade_id is always null, even if the caller supplies one

    Scenario: A NO_TRADE row with no veto still forces trade_id to null
      Given a chain outcome for pair "EURUSD" at "2024-01-01T00:00:00+00:00" with filter results:
        | filter_name | recommendation | reason      | veto  | confidence |
        | trend       | NEUTRAL        | no signal   | false |            |
      And the accumulated features are:
        | key      | value |
        | trend_ok | false |
      And the chain decision is "NO_TRADE"
      When the outcome is converted to a decision row with trade_id "trade-fabricated"
      Then the decision row's trade_id is absent

  Rule: A batch of decision rows persists to and round-trips from decisions.parquet

    Scenario: Writing decision rows produces a real Parquet file that round-trips
      Given two decision rows for trade_ids "trade-001" and "trade-002"
      When the decision rows are written to "decisions.parquet"
      Then the Parquet file exists on disk
      And reading it back yields the same decision rows

    Scenario: A NO_TRADE row's null trade_id round-trips through decisions.parquet
      Given a single NO_TRADE decision row
      When the decision rows are written to "decisions.parquet"
      Then the Parquet file exists on disk
      And reading it back yields the same decision rows
      And the read-back row's trade_id is absent

  Rule: Every decision row carries a trade_id, making the table join-ready by trade_id

    Scenario: Two decision rows both carry their own distinct trade_id
      Given two decision rows for trade_ids "trade-001" and "trade-002"
      Then each decision row's trade_id matches the trade_id it was built with

  Rule: features_hash is deterministic and sensitive to feature content

    Scenario: Same feature content in a different key order hashes identically
      When two equal-content feature dicts built in a different key order are hashed
      Then their features_hash values are equal

    Scenario: Different feature content hashes differently
      When two feature dicts with different values are hashed
      Then their features_hash values differ

    Scenario: A feature value that isn't natively JSON-serializable still hashes safely
      When a feature dict containing a non-JSON-native value is hashed
      Then hashing succeeds and produces a features_hash
