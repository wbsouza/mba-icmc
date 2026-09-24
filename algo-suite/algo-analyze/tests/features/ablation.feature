Feature: Build an ablation table from completed run metrics
  `build_ablation_table` compares completed run directories without recomputing metrics.
  It reads each run's persisted metrics artifact, returns one row per run, and computes
  a total-return delta against a designated baseline run.

  Rule: Completed runs compare against a named baseline

    Scenario: two runs produce a known delta against the baseline
      Given a completed run "baseline-ma" with total return 10.0
      And a completed run "baseline-meanrev" with total return 13.5
      When I build the ablation table with baseline "baseline-ma"
      Then the ablation table has 2 rows
      And run "baseline-ma" has total return delta 0.0
      And run "baseline-meanrev" has total return delta 3.5

  Rule: Broken inputs fail fast instead of silently changing the table

    Scenario: baseline identifier is not one of the provided runs
      Given a completed run "baseline-ma" with total return 10.0
      When I build the ablation table with baseline "hybrid" expecting failure
      Then ablation fails with ValueError naming "hybrid"

    Scenario: a run has no metrics artifact
      Given a run "baseline-ma" without metrics
      When I build the ablation table with baseline "baseline-ma" expecting failure
      Then ablation fails with FileNotFoundError naming "baseline-ma"

    Scenario: a run directory is missing
      Given a missing run "baseline-ma"
      When I build the ablation table with baseline "baseline-ma" expecting failure
      Then ablation fails with FileNotFoundError naming "baseline-ma"

    Scenario: a run has no manifest artifact
      Given a run "baseline-ma" with metrics but no manifest
      When I build the ablation table with baseline "baseline-ma" expecting failure
      Then ablation fails with FileNotFoundError naming "run manifest"

    Scenario: a run manifest is missing thesis metadata
      Given a run "baseline-ma" with metrics and incomplete manifest
      When I build the ablation table with baseline "baseline-ma" expecting failure
      Then ablation fails with ValueError naming "symbol"
