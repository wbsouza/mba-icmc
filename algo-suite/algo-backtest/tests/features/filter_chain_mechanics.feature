Feature: Filter-chain mechanics with stub filters
  Proves FilterChain.run()'s accumulate / veto-short-circuit / abstain-does-not-veto
  loop (specs.md §11.3.1) ahead of any real F1-F7 filter, using trivial stub filters
  that always PASS, always VETO, or always ABSTAIN.

  Rule: Non-veto filters accumulate into state.features and state.filter_results

    Scenario: Multiple non-veto filters run in order and contribute to the state
      Given a chain of PASS filters "trend" and "indicator" each enriching a distinct feature
      And a terminal decision-maker that reports "BUY"
      When the chain runs
      Then both filters ran in order
      And state.features holds both filters' enrichment
      And state.filter_results holds both filters' results in order
      And the chain outcome decision is "BUY"
      And every filter received the running state
      And the terminal decision-maker observed the accumulated state

  Rule: A veto short-circuits the chain

    Scenario: A vetoing filter stops the chain before downstream filters run
      Given a chain of a PASS filter "trend", a VETO filter "risk_guard" that also enriches, and a PASS filter "capital"
      And a terminal decision-maker that reports "BUY"
      When the chain runs
      Then the filter "capital" was never called
      And the chain outcome decision is "NO_TRADE"
      And state.features holds the enrichment from filters that ran
      And state.features holds the vetoing filter's own enrichment
      And state.filter_results holds results for filters that ran

  Rule: FilterResult.confidence must be in [0, 1], or absent

    Scenario Outline: an out-of-range confidence is rejected at construction
      When a FilterResult is built with confidence <confidence>
      Then it is rejected for an out-of-range confidence

      Examples:
        | confidence |
        | 1.5        |
        | -0.1       |

    Scenario: an absent confidence is accepted
      When a FilterResult is built with confidence absent
      Then it is accepted

    Scenario Outline: a boundary confidence value is accepted
      When a FilterResult is built with confidence <confidence>
      Then it is accepted

      Examples:
        | confidence |
        | 0.0        |
        | 1.0        |

  Rule: ExecutionState.timestamp must be timezone-aware UTC

    Scenario: a naive timestamp is rejected at construction
      When an ExecutionState is built with a naive timestamp
      Then it is rejected for a non-UTC timestamp

    Scenario: a non-UTC timezone-aware timestamp is rejected at construction
      When an ExecutionState is built with a timestamp in a non-UTC timezone
      Then it is rejected for a non-UTC timestamp

  Rule: An ABSTAIN carries no veto and does not stop the chain

    Scenario: An abstaining filter does not veto and the chain reaches the terminal
      Given a chain of a PASS filter "trend", an ABSTAIN filter "pattern", and a PASS filter "capital"
      And a terminal decision-maker that reports "HOLD"
      When the chain runs
      Then the filter "capital" was called
      And state.filter_results holds a result with recommendation "ABSTAIN" and no veto
      And the chain outcome decision is "HOLD"
