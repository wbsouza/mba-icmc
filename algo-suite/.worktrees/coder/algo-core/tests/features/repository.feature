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
