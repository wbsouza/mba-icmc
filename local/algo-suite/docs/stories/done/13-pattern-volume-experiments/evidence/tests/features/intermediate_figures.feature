Feature: Intermediate-result figures preserve real-run evidence
  Only successful runs with unchanged archived inputs may appear in a figure.

  Scenario: A completed run retains its recorded samples and parameter identity
    Given the real intermediate-results snapshot
    When the September execution figure is prepared
    Then the chart has equity and drawdown panels in a two to one ratio
    And every plotted sample equals its source equity and drawdown
    And both legend labels link to their own parameter appendix entries

  Scenario: An unfinished run cannot be plotted as a completed result
    Given the real intermediate-results snapshot
    When an unfinished run is selected for plotting
    Then plotting rejects the selection as incomplete

  Scenario: Changed source bytes cannot silently replace frozen evidence
    Given the real intermediate-results snapshot
    When a completed run is checked against a mismatched archived hash
    Then plotting rejects the source hash mismatch
