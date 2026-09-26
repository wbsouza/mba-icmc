Feature: Partial-close ladder
  Ports fx-manager's `ClosePortionOrderFacadeBean` laddering rule logic (specs.md §14.5):
  an ordered sequence of rungs, each closing a fraction ("portion") of the *original* lot
  size. Strategy A05 (specs.md §14.7) uses a two-rung ladder — an intermediate 50% close,
  then a final-target 50% close — that together fully close the position; the ladder here
  is the general mechanic, with A05's specific percentages supplied by the caller/config,
  never hardcoded in this module.

  Rule: Each rung closes its portion of the original lot size, tracking what remains

    Scenario: Strategy A05's two-rung ladder (50% then 50%) fully closes a 1.0 lot
      Given an original lot size of 1.0
      And a close-portion ladder of 0.5, 0.5
      When I build the close ladder
      Then rung 1 closes 0.5 lots with 0.5 remaining
      And rung 2 closes 0.5 lots with 0.0 remaining

    Scenario: A three-rung ladder tracks the running remainder
      Given an original lot size of 2.0
      And a close-portion ladder of 0.25, 0.25, 0.5
      When I build the close ladder
      Then rung 1 closes 0.5 lots with 1.5 remaining
      And rung 2 closes 0.5 lots with 1.0 remaining
      And rung 3 closes 1.0 lots with 0.0 remaining

    Scenario: A single rung with portion exactly 1.0 fully closes in one step
      Given an original lot size of 1.0
      And a close-portion ladder of 1.0
      When I build the close ladder
      Then rung 1 closes 1.0 lots with 0.0 remaining

    Scenario: An uneven three-way split still fully closes with no rounding residue
      Given an original lot size of 1.0
      And a close-portion ladder of 0.33, 0.33, 0.34
      When I build the close ladder
      Then rung 3 closes with exactly 0.0 remaining
      And the ladder's rungs sum to exactly the original lot size

  Rule: A ladder that would close more than the original position fails fast

    Scenario: rung portions summing past 1.0 are rejected
      Given an original lot size of 1.0
      And a close-portion ladder of 0.6, 0.6
      When I build the close ladder
      Then building the ladder fails with an over-close error

    Scenario Outline: a rung portion outside (0, 1] is rejected
      Given an original lot size of 1.0
      And a close-portion ladder of <portion>
      When I build the close ladder
      Then building the ladder fails with an invalid-portion error

      Examples:
        | portion |
        | 0.0     |
        | -0.5    |
        | 1.5     |

  Rule: A non-positive original lot size fails fast

    Scenario: a zero original lot size is rejected
      Given an original lot size of 0.0
      And a close-portion ladder of 0.5, 0.5
      When I build the close ladder
      Then building the ladder fails with a non-positive-lot error
