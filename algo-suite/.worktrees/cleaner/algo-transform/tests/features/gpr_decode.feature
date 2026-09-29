Feature: Decode the raw GPR index file into canonical index rows
  algo-transform mirrors the raw GPR file's own periods and values verbatim.
  algo-download confirmed only the URL and file format (SPEC.md Sec 7a.2), not
  the internal column layout or the series' time resolution, so this decoder
  reads whatever periods the source file actually contains -- it does not
  assume monthly or daily and does not forward-fill (algo-score SPEC.md Sec
  6.2 owns forward-fill onto the minute grid).

  # gpr-decode-01
  Scenario Outline: A GPR index row decodes to a typed period and index value
    Given a raw GPR file row for period <period> with index value <value>
    When I decode it
    Then a canonical GPR row exists for period <period> with index <value>
    And no value is forward-filled or interpolated
    Examples:
      | period  | value |
      | 2015-02 | 91.4  |
      | 2020-03 | 145.2 |

  # gpr-decode-02
  Scenario: An empty raw file is a decode error, not a silent empty series
    Given a 0-byte raw GPR file
    When I decode it
    Then a DecodeError is raised naming the file
    # GPR's raw fetch is a single whole-window unit (algo-download SPEC.md
    # Sec 7a.2): an empty payload here means the fetch never got the file,
    # not a per-period no-data gap the way GDELT's MISSING marker works.

  # gpr-decode-03
  Scenario: A malformed raw file is a decode error naming the file
    Given a raw GPR file that is not a valid spreadsheet
    When I decode it
    Then a DecodeError is raised naming the file

  # gpr-decode-04
  Scenario: A real binary XLS export decodes its Excel-typed period and value cells
    Given a binary XLS GPR file for period 2019-05 with index value 123.4
    When I decode it
    Then a canonical GPR row exists for period 2019-05 with index 123.4
