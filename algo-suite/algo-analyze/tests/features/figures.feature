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

  Rule: Cross-run ablation summaries render as valid vector PDFs

    Scenario: ablation rows render a bars PDF
      Given ablation rows:
        | run_id       | delta_total_return |
        | baseline-ma  | 0.00               |
        | hybrid-news  | 0.04               |
        | hybrid-full  | 0.07               |
      When I render the ablation bars figure
      Then the figure PDF is valid and non-empty
