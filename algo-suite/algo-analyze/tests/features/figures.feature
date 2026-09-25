Feature: Render thesis figures from analysis artifacts
  The figures lane renders importable vector PDFs without CLI integration.
  It reads completed run directories for equity and drawdown curves, and accepts
  ablation rows for cross-run contribution bars.

  Rule: Run-level curves render as valid vector PDFs

    Scenario: a completed run renders an equity curve PDF
      Given a run directory with trade returns 0.10, -0.05, 0.02
      When I render the equity curve figure
      Then the figure PDF is valid and non-empty

    Scenario: a completed run renders a drawdown curve PDF
      Given a run directory with trade returns 0.10, -0.05, 0.02
      When I render the drawdown curve figure
      Then the figure PDF is valid and non-empty

    Scenario: a run with zero closed trades still renders an empty equity curve PDF
      Given a run directory with zero closed trades
      When I render the equity curve figure
      Then the figure PDF is valid and non-empty

    Scenario: a run with zero closed trades still renders an empty drawdown curve PDF
      Given a run directory with zero closed trades
      When I render the drawdown curve figure
      Then the figure PDF is valid and non-empty

    Scenario: a missing trade ledger fails fast
      Given a run directory without trade artifacts
      When I render the equity curve figure expecting failure
      Then figure rendering fails with FileNotFoundError naming "trades.json"

    Scenario: a trade ledger without fractional returns fails fast
      Given a run directory with absolute PnL trades
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "fractional return"

    Scenario: a trade ledger with null returns fails fast
      Given a run directory with a null trade return
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "null"

    Scenario: a trade ledger with malformed JSON fails fast
      Given a run directory with malformed trades JSON
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "not valid JSON"

    Scenario: a trade ledger that is a JSON object instead of a list fails fast
      Given a run directory whose trades ledger is a JSON object
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "list of closed trades"

    Scenario: a trade ledger with a non-object trade element fails fast
      Given a run directory with a non-object trade element
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "is not an object"

    Scenario: a trade ledger with a non-finite return fails fast
      Given a run directory with a non-finite trade return
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "not finite"

    Scenario: a trade ledger with a return below -100% fails fast
      Given a run directory with a trade return of -1.5
      When I render the equity curve figure expecting failure
      Then figure rendering fails with ValueError naming "below -100%"

    Scenario: a run produced by write_run_artifacts renders an equity curve PDF
      Given a completed run written through write_run_artifacts with priced closed trades
      When I render the equity curve figure
      Then the figure PDF is valid and non-empty

    Scenario: a run produced by write_run_artifacts renders a drawdown curve PDF
      Given a completed run written through write_run_artifacts with priced closed trades
      When I render the drawdown curve figure
      Then the figure PDF is valid and non-empty

  Rule: Cross-run ablation summaries render as valid vector PDFs

    Scenario: ablation rows render a bars PDF
      Given ablation rows:
        | run_id       | delta_total_return |
        | baseline-ma  | 0.00               |
        | hybrid-news  | 0.04               |
        | hybrid-full  | 0.07               |
      When I render the ablation bars figure
      Then the figure PDF is valid and non-empty

    Scenario: empty ablation rows fail fast
      Given no ablation rows
      When I render the ablation bars figure expecting failure
      Then figure rendering fails with ValueError naming "at least one ablation row"
