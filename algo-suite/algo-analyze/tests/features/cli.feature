Feature: algo-analyze CLI wires the library modules together
  `metrics`, `significance`, `ablation` and `figures` are the CLI surface `docs/
  experiments.md` §2/§3 specifies, each resolving the data root and reading run
  artifacts from `<data_root>/runs/<run-id>/`. This feature proves the wiring
  end to end through the CLI (not just that the underlying library function
  works in isolation, which is covered by each module's own feature file).

  Rule: metrics prints headline metrics plus the deflated Sharpe

    Scenario: enough closed trades deflates the headline Sharpe
      Given a completed run "r1" with sharpe 0.5 and trade returns 0.01, -0.02, 0.03, 0.01, -0.01
      When I run "algo-analyze metrics --run r1 --trials 50"
      Then the command exits 0
      And the metrics output has a numeric deflated_sharpe

    Scenario: fewer than two closed trades reports undeflated with a note
      Given a completed run "r2" with sharpe 1.0 and trade returns 0.01
      When I run "algo-analyze metrics --run r2"
      Then the command exits 0
      And the metrics output has a null deflated_sharpe with a note

    Scenario: an implausibly high deflated Sharpe is flagged, not silently reported
      Given a completed run "r3" with sharpe 5.87 and trade returns 0.01, -0.02, 0.03
      When I run "algo-analyze metrics --run r3 --trials 1"
      Then the command exits 0
      And the metrics output flags the deflated Sharpe for investigation

    Scenario: a run with no metrics artifact fails fast
      Given a run "r4" without a metrics artifact
      When I run "algo-analyze metrics --run r4"
      Then the command exits 2
      And the error names "r4"

  Rule: significance compares exactly two runs under a fixed, recorded seed

    Scenario: two runs produce a reproducible p-value
      Given a completed run "sig-a" with sharpe 0.1 and trade returns 0.01, 0.02, 0.03, -0.01, 0.02
      And a completed run "sig-b" with sharpe 0.9 and trade returns 0.05, 0.06, 0.04, 0.07, 0.05
      When I run "algo-analyze significance --runs sig-a --runs sig-b --permutations 200 --seed 7"
      Then the command exits 0
      And the significance output records seed 7

    Scenario: significance requires exactly two runs
      When I run "algo-analyze significance --runs sig-a"
      Then the command exits 2
      And the error names "exactly two"

  Rule: ablation prints a contribution table and can render a figure

    Scenario: two runs produce a known delta against the baseline
      Given a completed run "base" with total return 10.0
      And a completed run "hyb" with total return 13.5
      When I run "algo-analyze ablation --runs base --runs hyb"
      Then the command exits 0
      And the ablation output has delta_total_return 3.5 for "hyb"

    Scenario: --figure also renders an ablation bar-chart PDF
      Given a completed run "base" with total return 10.0
      And a completed run "hyb" with total return 13.5
      When I run "algo-analyze ablation --runs base --runs hyb --figure"
      Then the command exits 0
      And an ablation figure PDF is written

  Rule: figures renders the equity and drawdown curves for a run

    Scenario: a completed run renders both curve PDFs
      Given a completed run "r5" with sharpe 0.5 and trade returns 0.01, -0.02, 0.03
      When I run "algo-analyze figures --run r5"
      Then the command exits 0
      And both figure PDFs are written

    Scenario: a run with no trades artifact fails fast
      Given a run "r6" without a trades artifact
      When I run "algo-analyze figures --run r6"
      Then the command exits 2
      And the error names "r6"
