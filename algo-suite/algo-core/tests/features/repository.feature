Feature: Repository data-access pattern
  Value objects are persisted and read through a Repository port, never touching
  the storage engine directly. Two backends implement the same port, a Parquet
  writer and a DuckDB analytical reader, so swapping the backend touches no
  caller (SPEC.md §13.5, no DB lock-in).

  Scenario Outline: a repository round-trips value objects
    Given a "<backend>" repository for bars in the data directory
    When I put 2 bars
    And I read all bars
    Then I get the 2 bars back with the same values
    And the repository reports it exists

    Examples:
      | backend |
      | parquet |
      | duckdb  |

  Scenario: an unwritten repository reports it does not exist
    Given a "parquet" repository for bars in the data directory
    Then the repository reports it does not exist

  Scenario: writing an empty batch with an explicit schema keeps the real columns
    Given a "parquet" repository for bars in the data directory
    When I put 0 bars with the bar schema
    Then the written file has the ts and close columns
    And it has 0 rows

  Rule: ParquetRepository does not require duckdb to be installed

    A pyarrow-only consumer (e.g. a chain-driven LEAN algorithm inside the pinned
    container, which ships pyarrow but not duckdb) must be able to import and use
    ParquetRepository without duckdb present at all.

    Scenario: Importing algo_core.repository.parquet succeeds without duckdb
      Given duckdb is not installed
      When algo_core.repository.parquet is imported fresh
      Then ParquetRepository is importable and duckdb was never imported

    Scenario: Accessing DuckDBRepository still fails clearly when duckdb truly is absent
      Given duckdb is not installed
      When algo_core.repository is imported fresh
      Then accessing DuckDBRepository on it raises ImportError
