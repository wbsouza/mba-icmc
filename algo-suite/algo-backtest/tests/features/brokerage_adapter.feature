Feature: Brokerage-adapter registry
  Brokerage simulation is a config-selected adapter, not a hardcoded call
  (Spec 04a). Adapters self-register by name; the factory builds one by name
  and fails fast on an unknown name (no silent default), since the brokerage
  model changes fill economics.

  Scenario: Build the registered "oanda" adapter by name
    When I build the brokerage adapter "oanda"
    Then I get a BrokerageAdapter whose name is "oanda"

  Scenario: An unknown adapter name fails fast
    When I build the brokerage adapter "nope"
    Then an UnknownBrokerageAdapterError is raised naming the known adapters

  Scenario: Registering a clashing name fails fast
    Given a registered adapter named "demo"
    When I register another adapter also named "demo"
    Then a registration error is raised

  Scenario: The oanda adapter applies LEAN's OANDA margin brokerage model
    Given a fake QCAlgorithm
    When I apply the "oanda" brokerage adapter to it
    Then the algorithm's brokerage model is set to OANDA margin
