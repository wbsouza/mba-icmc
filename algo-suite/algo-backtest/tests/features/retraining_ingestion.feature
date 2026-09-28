Feature: Incremental data and label-maturity adapter (Story 19, T2)
  The adaptive cycle consumes already-built training rows in keyed batches (one batch
  per source partition) and keeps a small ledger under a caller-given directory. The
  ledger records the availability watermark (the latest bar-close instant whose rows
  have been validated AND persisted, RWT-23) and, per row, whether its label is still
  pending or already mature (RWT-24). A completed month on disk never makes its later
  rows historically available: a row is visible only once the watermark reaches its
  close, and its label counts only once it reaches label_time.

  Every timestamp is a UTC instant (bar close = availability; label_time = the close
  of the horizon bar). Rows are keyed; a batch must be internally ordered by
  availability and unique by key; a batch that re-delivers identical rows is a no-op,
  a batch that re-delivers a key with different content is a conflict. Nothing in a
  rejected batch is persisted (atomic per batch), and consuming later batches never
  rewrites what earlier batches persisted (prefix invariance).

  Background:
    Given an empty ledger directory
    And the batch "jan-a" from partition "eurusd/h1/2016-01" carries the rows
      | key     | available_at         | label_time           | label |
      | bar-001 | 2016-01-04T09:00:00Z | 2016-01-04T10:00:00Z | 1     |
      | bar-002 | 2016-01-04T10:00:00Z | 2016-01-04T11:00:00Z | 0     |
      | bar-003 | 2016-01-04T11:00:00Z | 2016-01-04T14:00:00Z | 1     |
    And the batch "jan-b" from partition "eurusd/h1/2016-01" carries the rows
      | key     | available_at         | label_time           | label |
      | bar-004 | 2016-01-04T12:00:00Z | 2016-01-04T13:00:00Z | 0     |
      | bar-005 | 2016-01-04T14:00:00Z | 2016-01-04T15:00:00Z | 1     |

  Rule: Ordered batches advance the availability watermark only after validation and persistence (RWT-23)

    Scenario: Consuming two ordered batches advances the watermark to the last persisted close
      When the batch "jan-a" is consumed
      Then the ledger watermark is 2016-01-04T11:00:00Z
      And the ledger holds 3 rows
      When the batch "jan-b" is consumed
      Then the ledger watermark is 2016-01-04T14:00:00Z
      And the ledger holds 5 rows
      And the ledger directory contains a ledger file

    Scenario: A batch whose earliest new row precedes the watermark regresses it and is rejected
      Given the batch "jan-b" is consumed
      When consuming the batch "jan-a" fails
      Then the ingestion failure names "watermark"
      And the ingestion failure names "2016-01-04T14:00:00Z"
      And the ledger watermark is 2016-01-04T14:00:00Z
      And the ledger holds 2 rows

    Scenario: The persisted ledger reopens with the same watermark and row state
      Given the batch "jan-a" is consumed
      And the batch "jan-b" is consumed
      When the ledger is reopened from the same directory
      Then the ledger watermark is 2016-01-04T14:00:00Z
      And the ledger holds 5 rows
      And the row "bar-003" is mature
      And the row "bar-005" is pending

  Rule: Identical retry is idempotent; conflicting content is a failure

    Scenario: Re-consuming an identical batch changes nothing
      Given the batch "jan-a" is consumed
      And the ledger file bytes are remembered
      When the batch "jan-a" is consumed again
      Then the ledger watermark is 2016-01-04T11:00:00Z
      And the ledger holds 3 rows
      And the ledger file bytes are unchanged

    Scenario: A re-delivered key with a different label is a conflict and persists nothing
      Given the batch "jan-a" is consumed
      And the ledger file bytes are remembered
      And the batch "jan-a-conflict" from partition "eurusd/h1/2016-01" carries the rows
        | key     | available_at         | label_time           | label |
        | bar-003 | 2016-01-04T11:00:00Z | 2016-01-04T14:00:00Z | 0     |
        | bar-004 | 2016-01-04T12:00:00Z | 2016-01-04T13:00:00Z | 0     |
      When consuming the batch "jan-a-conflict" fails
      Then the ingestion failure names "bar-003"
      And the ingestion failure names "conflict"
      And the ledger holds 3 rows
      And the ledger file bytes are unchanged

    Scenario: A batch that repeats a key within itself is rejected before anything is persisted
      Given the batch "dup-inside" from partition "eurusd/h1/2016-01" carries the rows
        | key     | available_at         | label_time           | label |
        | bar-001 | 2016-01-04T09:00:00Z | 2016-01-04T10:00:00Z | 1     |
        | bar-001 | 2016-01-04T10:00:00Z | 2016-01-04T11:00:00Z | 0     |
      When consuming the batch "dup-inside" fails
      Then the ingestion failure names "bar-001"
      And the ingestion failure names "unique"
      And the ledger holds 0 rows
      And the ledger directory contains no ledger file

  Rule: Invalid rows are rejected before fitting or writing, and a rejected batch persists nothing (RWT-02)

    Scenario Outline: A row with an invalid timestamp is rejected (<case>)
      Given the batch "bad-time" from partition "eurusd/h1/2016-01" carries the rows
        | key     | available_at   | label_time   | label |
        | bar-001 | <available_at> | <label_time> | 1     |
      When consuming the batch "bad-time" fails
      Then the ingestion failure names "<fragment>"
      And the ledger holds 0 rows

      Examples:
        | case                                  | available_at              | label_time                | fragment     |
        | naive availability (no timezone)      | 2016-01-04T09:00:00       | 2016-01-04T10:00:00Z      | UTC          |
        | availability in a non-UTC offset      | 2016-01-04T09:00:00+01:00 | 2016-01-04T10:00:00Z      | UTC          |
        | naive label_time                      | 2016-01-04T09:00:00Z      | 2016-01-04T10:00:00       | UTC          |
        | label_time before availability        | 2016-01-04T09:00:00Z      | 2016-01-04T08:00:00Z      | label_time   |

    Scenario: A row with unknown label maturity (label_time None) is rejected in the adaptive path (RWT-24)
      Given the batch "unknown-maturity" from partition "eurusd/h1/2016-01" carries the rows
        | key     | available_at         | label_time | label |
        | bar-001 | 2016-01-04T09:00:00Z | None       | 1     |
      When consuming the batch "unknown-maturity" fails
      Then the ingestion failure names "label_time"
      And the ingestion failure names "bar-001"
      And the ledger holds 0 rows

    Scenario: Rows out of availability order inside a batch are rejected
      Given the batch "unordered" from partition "eurusd/h1/2016-01" carries the rows
        | key     | available_at         | label_time           | label |
        | bar-002 | 2016-01-04T10:00:00Z | 2016-01-04T11:00:00Z | 0     |
        | bar-001 | 2016-01-04T09:00:00Z | 2016-01-04T10:00:00Z | 1     |
      When consuming the batch "unordered" fails
      Then the ingestion failure names "ordered"
      And the ledger holds 0 rows

    Scenario: A partition that declares more bars than it delivers is rejected as a missing bar
      Given the batch "short" from partition "eurusd/h1/2016-01" declares 4 bars and carries the rows
        | key     | available_at         | label_time           | label |
        | bar-001 | 2016-01-04T09:00:00Z | 2016-01-04T10:00:00Z | 1     |
        | bar-002 | 2016-01-04T10:00:00Z | 2016-01-04T11:00:00Z | 0     |
        | bar-003 | 2016-01-04T11:00:00Z | 2016-01-04T14:00:00Z | 1     |
      When consuming the batch "short" fails
      Then the ingestion failure names "4"
      And the ingestion failure names "3"
      And the ledger holds 0 rows

    Scenario: An invalid row in the middle of a batch leaves the earlier valid rows unpersisted (partial persistence is impossible)
      Given the batch "jan-a" is consumed
      And the ledger file bytes are remembered
      And the batch "mixed" from partition "eurusd/h1/2016-01" carries the rows
        | key     | available_at         | label_time           | label |
        | bar-004 | 2016-01-04T12:00:00Z | 2016-01-04T13:00:00Z | 0     |
        | bar-005 | 2016-01-04T14:00:00Z | None                 | 1     |
      When consuming the batch "mixed" fails
      Then the ingestion failure names "bar-005"
      And the ledger holds 3 rows
      And the ledger watermark is 2016-01-04T11:00:00Z
      And the ledger file bytes are unchanged

  Rule: A label is pending until the watermark reaches its label_time, then mature (RWT-24)

    Scenario: A late outcome stays pending while its label_time is beyond the watermark
      When the batch "jan-a" is consumed
      Then the row "bar-001" is mature
      And the row "bar-002" is mature
      And the row "bar-003" is pending
      And the mature rows as of 2016-01-04T11:00:00Z are "bar-001, bar-002"

    Scenario: A pending label matures when a later batch carries the watermark to its label_time (label_time <= cutoff)
      Given the batch "jan-a" is consumed
      When the batch "jan-b" is consumed
      Then the row "bar-003" is mature
      And the row "bar-005" is pending
      And the mature rows as of 2016-01-04T14:00:00Z are "bar-001, bar-002, bar-003, bar-004"

    Scenario: Maturity is judged at the requested cutoff, not at the on-disk completion of the partition
      Given the batch "jan-a" is consumed
      And the batch "jan-b" is consumed
      Then the mature rows as of 2016-01-04T10:00:00Z are "bar-001"
      And the visible rows as of 2016-01-04T10:00:00Z are "bar-001, bar-002"
      And the mature rows as of 2016-01-04T13:59:00Z are "bar-001, bar-002, bar-004"

    Scenario: An as-of query with a naive cutoff is refused rather than read as local time (RWT-02)
      Given the batch "jan-a" is consumed
      When querying the mature rows as of 2016-01-04T11:00:00 fails
      Then the ingestion failure names "UTC"

  Rule: Later batches never change what earlier batches persisted (prefix invariance)

    Scenario: The persisted records of the first batch are identical with and without the second batch
      Given the batch "jan-a" is consumed
      And the persisted records of the keys "bar-001, bar-002, bar-003" are remembered
      When the batch "jan-b" is consumed
      Then the persisted records of the keys "bar-001, bar-002, bar-003" are unchanged
      And the ledger watermark is 2016-01-04T14:00:00Z

  Rule: Source partitions are identified by content so a silently rewritten file cannot masquerade as the same batch

    Scenario: A parquet partition written to disk is consumed with its path, sha256 and row count recorded
      Given the rows of the batch "jan-a" are written as a parquet partition file
      When the parquet partition is consumed
      Then the ledger records that partition's path, sha256 and 3 rows
      And the ledger watermark is 2016-01-04T11:00:00Z

    Scenario: The same partition path with different bytes and different rows is a conflict
      Given the rows of the batch "jan-a" are written as a parquet partition file
      And the parquet partition is consumed
      And the same partition file is rewritten with the label of "bar-002" flipped
      When consuming the parquet partition fails
      Then the ingestion failure names "bar-002"
      And the ledger holds 3 rows

    Scenario: The same partition path with different bytes but identical rows is still a conflict
      Given the rows of the batch "jan-a" are written as a parquet partition file
      And the parquet partition is consumed
      And the same partition file is rewritten with identical rows and different bytes
      When consuming the parquet partition fails
      Then the ingestion failure names "eurusd/h1/2016-01"
      And the ingestion failure names "sha256"
      And the ledger holds 3 rows
