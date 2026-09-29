Feature: Download source registry
  Sources self-register by name; the factory builds one by name and fails fast
  on an unknown name (no silent default), naming the known sources.

  Scenario: Build a registered source by name
    Given a registered source named "demo"
    When I build the source "demo"
    Then I get a DataSource whose name is "demo"

  Scenario: An unknown source name fails fast
    Given a registered source named "demo"
    When I build the source "nope"
    Then an UnknownSourceError is raised naming the known sources

  Scenario: Registering a clashing name fails fast
    Given a registered source named "demo"
    When I register another source also named "demo"
    Then a registration error is raised
