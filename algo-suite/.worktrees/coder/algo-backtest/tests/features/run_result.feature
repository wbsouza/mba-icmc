Feature: Parse a LEAN /Results directory into a minimal RunResult
  Slice C needs only enough of LEAN's output to prove the run path worked: whether the
  run succeeded and how many round-trip trades closed (from totalPerformance.closedTrades).
  Richer metrics are deferred to Slice E. A results directory with no parseable result
  fails fast.

  Rule: The result file is parsed into success + closed-trade count

    Scenario: a result reporting one closed trade is parsed
      Given a LEAN results directory reporting 1 closed trade
      When I parse it as a successful run
      Then the run is reported successful
      And it reports 1 closed trade
      And the raw results path points at the result JSON

    Scenario: the full result file is chosen over its summary sibling
      Given a LEAN results directory reporting 1 closed trade
      And a summary sibling is also present
      When I parse it as a successful run
      Then it reports 1 closed trade
      And the raw results path points at the result JSON

    Scenario: a failed run is reported as not successful
      Given a LEAN results directory reporting 0 closed trades
      When I parse it as a failed run
      Then the run is reported unsuccessful
      And it reports 0 closed trades

  Rule: An absent or ambiguous result fails fast

    Scenario: two competing primary result files are ambiguous and fail fast
      Given a LEAN results directory reporting 1 closed trade
      And a second, differently-named primary result file is also present
      When I parse it as a successful run
      Then parsing fails with an ambiguous-result error

    Scenario: a results directory with no parseable result fails fast
      Given an empty LEAN results directory
      When I parse it as a successful run
      Then parsing fails with a missing-result error
