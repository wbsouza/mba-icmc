Feature: algo-download architectural boundaries
  The download core owns source-agnostic application flow and contracts.
  Provider adapters own HTTP and provider-specific details.

  Rule: Core modules stay independent of adapter details
    Scenario: The application core has no provider or HTTP imports
      When I inspect the algo-download core modules
      Then no core module imports provider adapters
      And no core module imports HTTP client libraries
