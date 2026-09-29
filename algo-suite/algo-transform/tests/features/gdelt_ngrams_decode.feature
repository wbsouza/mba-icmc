Feature: Decode a raw GDELT Web News NGrams minute payload into reconstructed article rows
  Consumes raw/gdelt_ngrams/... minute payloads (algo-download SPEC.md
  Sec 7a.3, technical-debt.md TD-28) via the gdeltnews package's n-gram-based
  text reconstruction -- a local, deterministic operation over the
  already-downloaded bytes, no network fetch. Produces one row per URL
  present in the minute payload: url, publish timestamp, reconstructed text.
  This is the only source of article text for algo-score's FinBERT/LM
  sentiment scorer (algo-score/SPEC.md Sec 2).

  # gdelt-ngrams-decode-01
  Scenario: A real-format NGrams minute payload decodes to one row per URL
    Given a GDELT NGrams payload for minute 2020-01-02 14:34 containing 3 URLs with ngram data
    When I decode it
    Then 3 canonical news rows are produced
    And each row carries a url, a publish timestamp, and reconstructed text

  # gdelt-ngrams-decode-02
  Scenario: A 0-byte MISSING marker decodes to zero rows, not an error
    Given an empty raw payload (the download no-data marker for an out-of-coverage or unpublished minute)
    When I decode it
    Then it yields zero news rows
    And no error is raised

  # gdelt-ngrams-decode-03
  Scenario: A non-gzip payload is a decode error naming the minute
    Given a non-empty payload that is not valid gzip
    When I decode it
    Then a DecodeError is raised naming the minute's raw path

  # gdelt-ngrams-decode-04
  # gdeltnews' own reconstruction is resilient to per-line data problems (verified
  # against the real library, not assumed): a malformed JSON line or a line missing
  # a required ngram field is silently skipped, not raised as an error -- only a
  # payload that isn't gzip at all fails the decode.
  Scenario Outline: A malformed reconstructed line is silently skipped, not an error
    Given <bad_payload>
    When I decode it
    Then it yields zero news rows
    And no error is raised
    Examples:
      | bad_payload                                                   |
      | a gzip payload whose line is not valid JSON                  |
      | a gzip payload whose JSON line is missing a required ngram field |
