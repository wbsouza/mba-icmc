Feature: Materialize canonical QuoteBars into LEAN-native minute files
  The materializer writes LEAN forex-minute day-zips from UTC QuoteBars, START-indexed
  in the configured data timezone, and fails fast on malformed or colliding input.

  Rule: ms is the bar START since midnight in the configured data timezone

    Scenario Outline: ms encodes the bar START in the data timezone
      Given a QuoteBar starting at "<utc_start>" UTC
      When I compute the lean-data rows in timezone "<data_tz>"
      Then the file day is "<file_day>"
      And the first row ms is <ms>

      Examples:
        | utc_start           | data_tz          | file_day   | ms       |
        | 2014-05-07T00:00:00 | UTC              | 2014-05-07 | 0        |
        | 2014-05-07T23:59:00 | UTC              | 2014-05-07 | 86340000 |
        | 2014-07-15T12:00:00 | America/New_York | 2014-07-15 | 28800000 |
        | 2014-01-15T12:00:00 | America/New_York | 2014-01-15 | 25200000 |
        | 2014-03-09T07:00:00 | America/New_York | 2014-03-09 | 10800000 |

    Scenario: A row carries bid/ask OHLC with zero volumes at the pair's precision
      Given a QuoteBar starting at "2014-05-07T00:00:00" UTC
      When I compute the lean-data rows in timezone "UTC"
      Then the row has 11 columns
      And both volume columns are "0"
      And the bid-open column is "1.10000"
      And the ask-open column is "1.10010"

    Scenario: A day's bars become one named zip with a named CSV
      Given QuoteBars starting at:
        | utc_start           |
        | 2014-05-07T00:00:00 |
        | 2014-05-07T00:01:00 |
      When I write lean-data minute files in timezone "UTC"
      Then one file "20140507_quote.zip" is written
      And it contains the CSV "20140507_eurusd_minute_quote.csv"
      And the CSV row ms values are "0,60000"

    Scenario: Bars on different START days are written to separate files
      Given QuoteBars starting at:
        | utc_start           |
        | 2014-05-07T23:59:00 |
        | 2014-05-08T00:00:00 |
      When I write lean-data minute files in timezone "UTC"
      Then the written files are "20140507_quote.zip,20140508_quote.zip"

    Scenario: The autumn fall-back instants are distinct minutes in UTC
      Given QuoteBars starting at:
        | utc_start           |
        | 2014-11-02T05:30:00 |
        | 2014-11-02T06:30:00 |
      When I compute the lean-data rows in timezone "UTC"
      Then the row ms values are "19800000,23400000"

  Rule: Malformed or colliding input fails fast (one bar per minute slot)

    Scenario: A non-minute-aligned bar is rejected
      Given a QuoteBar starting at "2014-05-07T00:00:30" UTC
      When I compute the lean-data rows in timezone "UTC"
      Then it fails with "minute-aligned"

    Scenario: Two bars in the same slot are rejected
      Given QuoteBars starting at:
        | utc_start           |
        | 2014-05-07T00:00:00 |
        | 2014-05-07T00:00:00 |
      When I compute the lean-data rows in timezone "UTC"
      Then it fails with "duplicate lean-data slot"

    Scenario: The DST fall-back hour collides in a non-UTC timezone
      Given QuoteBars starting at:
        | utc_start           |
        | 2014-11-02T05:30:00 |
        | 2014-11-02T06:30:00 |
      When I compute the lean-data rows in timezone "America/New_York"
      Then it fails with "duplicate lean-data slot"
