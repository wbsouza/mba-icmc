Feature: DuckDB helpers
  A connection factory and a Parquet reader, so tools query the canonical store
  without re-implementing DuckDB wiring.

  Scenario: a fresh connection runs a query
    When I open a DuckDB connection
    Then querying "SELECT 42" returns 42

  Scenario: reading a Parquet glob returns all rows
    Given a Parquet file with 3 rows in the data directory
    When I read every Parquet file in the data directory
    Then the row count is 3
