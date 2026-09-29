Feature: Transform a GDELT NGrams month into a canonical news Parquet partition
  Mirrors the GDELT events completeness-gated orchestrator
  (gdelt_transform.feature): a month is written only when every expected
  UTC-minute unit is present as data or a durable MISSING marker (per
  raw/gdelt_ngrams's own MISSING-marker convention, algo-download SPEC.md
  Sec 7a.3); an incomplete or corrupt month writes nothing. Output lands at
  parquet/news/gdelt (algo-score/SPEC.md Sec 2's news Parquet contract), not
  parquet/events/gdelt (Spec 02's separate GDELT-events dataset) -- same
  provider, two distinct output datasets.

  Background:
    Given a writable data root

  # gdelt-ngrams-transform-01
  Scenario: A complete raw month is transformed to a news Parquet partition
    Given a complete raw GDELT NGrams month for 2020-01 with article data in minute 2020-01-02 14:34
    When I transform "gdelt_ngrams" for "2020-01"
    Then a news Parquet partition exists at parquet/news/gdelt for 2020-01
    And it contains at least one news row
    And its rows validate as algo-score NewsArticle records
    And the run exits 0

  # gdelt-ngrams-transform-02
  Scenario: An incomplete raw month is not transformed
    Given a complete raw GDELT NGrams month for 2020-01 with article data in minute 2020-01-02 14:34
    And the raw minute 2020-01-05 09:00 is removed
    When I transform "gdelt_ngrams" for "2020-01"
    Then no news Parquet partition exists at parquet/news/gdelt for 2020-01
    And the report says the month is incomplete

  # gdelt-ngrams-transform-03
  Scenario: A complete month with a corrupt raw minute is not transformed
    Given a complete raw GDELT NGrams month for 2020-01 with article data in minute 2020-01-02 14:34
    And the raw minute 2020-01-05 09:00 is corrupt
    When I transform "gdelt_ngrams" for "2020-01"
    Then no news Parquet partition exists at parquet/news/gdelt for 2020-01
    And the report says the month is corrupt
    And the report names the corrupt minute's raw path

  # gdelt-ngrams-transform-04
  Scenario: An already-written month is skipped unless --rebuild
    Given a prior complete news partition exists for gdelt_ngrams 2020-01
    When I transform "gdelt_ngrams" for "2020-01"
    Then the report status is SKIPPED

  # gdelt-ngrams-transform-05
  Scenario: A month where every minute is a durable MISSING marker is written as an empty partition, not an error
    Given a complete raw GDELT NGrams month for 2020-01 where every minute is a durable MISSING marker
    When I transform "gdelt_ngrams" for "2020-01"
    Then a news Parquet partition exists at parquet/news/gdelt for 2020-01
    And it contains zero news rows
    And it has the id, text, and publish_ts columns
    And the run exits 0

  # gdelt-ngrams-transform-06
  Scenario Outline: expected_minutes covers every minute of the month, through its last day
    When I compute expected minutes for <year>-<month>
    Then there are <count> expected minutes
    And the last expected day is <last_day>

    Examples:
      | year | month | count | last_day |
      | 2020 | 1     | 44640 | 31       |
      | 2020 | 2     | 41760 | 29       |
