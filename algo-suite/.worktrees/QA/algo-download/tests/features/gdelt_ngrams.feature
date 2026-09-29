Feature: Download GDELT Web News NGrams 3.0 (raw only)
  The gdelt_ngrams adapter writes provider-native NGrams JSON-lines
  (.webngrams.json.gz) bytes under raw/gdelt_ngrams/ and nothing else. A unit
  is one UTC-minute file. Resume is filesystem-only; a minute the provider
  never published is MISSING and durable; a minute whose fetch never
  completes writes nothing and flips the exit code. There is no symbol
  dimension — this is a global feed, not per-instrument. This adapter does
  not reconstruct article text (that is algo-transform's job, out of scope
  here) — it writes the raw gzipped JSON-lines payload verbatim, same
  raw-only stage boundary as every other adapter.

  Background:
    Given a writable data root
    And the GDELT NGrams datafeed returns gzip bytes by default

  # gdelt-ngrams-01
  Scenario: Planning performs no I/O
    When I plan gdelt_ngrams for "2020-01"
    Then the plan lists 44640 minute units
    And no HTTP request was made
    And no file was written under the data root

  # gdelt-ngrams-02
  Scenario: Happy path writes raw payloads at the canonical path
    When I download gdelt_ngrams for "2020-01"
    Then a raw payload exists at "raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz"
    And no file is written outside the raw store
    And no unit is FAILED
    And the run exits 0
    And the written unit's recorded byte count matches the payload

  # gdelt-ngrams-03
  Scenario: Resume is a filesystem no-op
    Given gdelt_ngrams "2020-01" is already downloaded
    When I download gdelt_ngrams for "2020-01"
    Then no HTTP request was made
    And every unit is SKIPPED
    And the run exits 0

  # gdelt-ngrams-04
  Scenario: A minute the provider never published is MISSING and durable, not FAILED
    Given the GDELT NGrams datafeed has no data for minute 2020-01-02 14:34
    When I download gdelt_ngrams for "2020-01"
    Then "raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz" exists as an empty payload
    And that minute is counted MISSING
    And the run exits 0

  # gdelt-ngrams-05
  Scenario: A minute fetch that never completes writes nothing and flips the exit code
    Given the GDELT NGrams datafeed always errors for minute 2020-01-02 14:34
    When I download gdelt_ngrams for "2020-01"
    Then no file exists at "raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz"
    And that minute is counted FAILED
    And the run exits non-zero
    And the failure is logged once as "fetch_failed" with the unit, url, and error

  # gdelt-ngrams-06
  Scenario: A single failing fetch retries through the throttle before giving up
    Given the GDELT NGrams datafeed always errors for minute 2020-01-02 14:34
    When I fetch gdelt_ngrams minute 2020-01-02 14:34 directly
    Then the direct fetch result is FAILED with zero bytes
    And the request throttle waited before every attempt

  # gdelt-ngrams-07
  Scenario: The minute URL is directly guessable from its timestamp, no master list needed
    When I build the GDELT NGrams URL for minute 2020-01-02 14:34
    Then the URL is "https://data.gdeltproject.org/gdeltv3/webngrams/20200102143400.webngrams.json.gz"

  # gdelt-ngrams-08
  Scenario: Constructor overrides are honored, and unset ones fall back to defaults
    When I construct a GdeltNgramsSource with an explicit client, backoff, sleep, and min interval
    Then the source uses the explicit client, backoff, sleep, and min interval
    When I construct a GdeltNgramsSource with no overrides
    Then the source builds its own client at the default timeout

  # gdelt-ngrams-09
  Scenario Outline: The raw path is day-partitioned and round-trips to the same minute
    When I round-trip the raw path under "/data" for minute <minute>
    Then the parsed minute equals <minute>

    Examples:
      | minute              |
      | 2020-01-02 14:34    |
      | 2020-12-25 23:59    |
