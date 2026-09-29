Feature: DownloadRequest value-object validation
  A DownloadRequest validates its months on construction: an impossible month
  is rejected, valid months are preserved verbatim.

  Scenario: An impossible month is rejected
    When I build a request for "EURUSD" with months "2020-13"
    Then request construction fails validation

  Scenario: Valid months are accepted and preserved
    When I build a request for "EURUSD" with months "2020-01, 2020-12"
    Then the request months are "2020-01, 2020-12"
