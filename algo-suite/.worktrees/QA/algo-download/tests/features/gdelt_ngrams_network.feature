@network
Feature: GDELT NGrams adapter against the live datafeed (opt-in)
  This smoke test hits the real Web News NGrams 3.0 feed, so it is excluded
  from the default offline gate. It validates the assumptions the offline
  tests mock: the minute URL is directly guessable from a timestamp (no
  master-list fetch required), a real file is gzip-compressed JSON-lines, and
  a minute before the dataset's coverage start (2020-01-01) is a durable
  MISSING via an empty 404 body. Fixed, already-settled timestamps are used
  throughout (never "now" or a recent minute) because the provider publishes
  each minute's file with an observed lag of up to roughly an hour — a 404 on
  a just-elapsed minute does not yet prove the minute is MISSING (see
  algo-download/SPEC.md §7a.3 and technical-debt.md TD-30).

  # gdelt-ngrams-network-01
  Scenario: A real minute, an out-of-coverage minute, and resume
    Given a GDELT NGrams source against the live feed
    When I fetch the real minute 2020-01-01 00:01
    Then the minute status is WRITTEN with a positive byte count
    And the raw path is "raw/gdelt_ngrams/2020/01/01/20200101000100.webngrams.json.gz"
    And the payload is gzip-compressed JSON-lines with fields "date, ngram, lang, type, pos, pre, post, url"
    When I fetch the out-of-coverage minute 2019-12-31 23:59
    Then the minute status is MISSING with an empty marker persisted
    And both minutes are now done on disk
