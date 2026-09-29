Feature: Decode a raw GDELT Events slot into canonical event rows
  algo-transform mirrors the raw GDELT Events-table facts (algo-download
  SPEC.md Sec 7a.1: Events table only, no article text) into typed rows, one
  row per event, verbatim. No text field is produced here: SOURCEURL is
  carried through so a future text-fetch adapter (technical-debt.md TD-28,
  GDELT Web News NGrams 3.0) can join on it later, but this decoder does not
  fetch or fabricate article text -- that would be a different raw source.

  # gdelt-decode-01
  Scenario: A real-format Events zip decodes to one row per event
    Given a GDELT Events zip for slot 2020-01-02 14:30 containing 3 tab-delimited event rows
    When I decode it
    Then 3 canonical event rows are produced
    And each row keeps its GLOBALEVENTID, event date, EventCode, GoldsteinScale, AvgTone and SOURCEURL verbatim
    And no row has an article-text field

  # gdelt-decode-02
  Scenario: A 0-byte MISSING marker decodes to zero events, not an error
    Given an empty raw payload (the download no-data marker for an out-of-coverage or unpublished slot)
    When I decode it
    Then it yields zero event rows
    And no error is raised

  # gdelt-decode-03
  Scenario Outline: A corrupt payload is a decode error naming the slot
    Given <bad_payload>
    When I decode it
    Then a DecodeError is raised naming the slot's raw path
    Examples:
      | bad_payload                                                  |
      | a non-empty payload that is not a valid zip                  |
      | a zip whose CSV row has a mismatched column count             |
      | a zip whose CSV row has an invalid numeric field              |
