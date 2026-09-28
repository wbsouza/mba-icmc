Feature: H4 evidence joins complete matrices to actual results and parameters
  Historical failures and unchanged prior snapshots remain separate.

  Scenario: All eight completed cells retain results and full configuration
    Given the real completed H4 snapshot
    Then both parents and all cell manifests pass the completion gate
    And each cell has matching configuration, model hashes, and actual trade count
    And every filter has archived parameters or an explicit absence

  Scenario: Parent success alone cannot certify a matrix
    Given the real completed H4 snapshot
    When the final integrity report is marked unsuccessful in memory
    Then the completion gate rejects the matrix

  Scenario: H4 charts preserve every recorded sample and parameter link
    Given the real completed H4 snapshot
    When both H4 family figures are rendered
    Then all eight series preserve equity and drawdown in two to one panels
    And every H4 legend links to its own complete parameter entry

  Scenario: Changed source bytes cannot replace H4 evidence
    Given the real completed H4 snapshot
    When the expected H4 equity hash is changed in memory
    Then H4 rendering rejects the stale evidence
