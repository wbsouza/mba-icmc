Feature: Run a backtest experiment
  `algo-backtest experiment run` executes each run in a spec on the proven run path,
  writing one deterministic directory per run plus an experiment manifest with one metrics
  row per run — the reproducible seed for the Chapter-4 comparison table. No CPCV, no
  parameter sweeps, no parallelism (Stage F1).

  Rule: An experiment writes a deterministic tree and a manifest with one row per run

    Scenario: a two-run experiment produces per-run dirs and a manifest
      Given an experiment of 2 runs over covered EUR/USD data
      When I run the experiment
      Then each run has its own directory under runs/experiments/<experiment>
      And each run directory holds run.json, trades.json and metrics.json
      And the experiment manifest lists 2 runs each with a metrics row

    Scenario: rerunning the experiment keeps the same deterministic layout
      Given an experiment of 2 runs over covered EUR/USD data
      When I run the experiment
      And I run the experiment again
      Then the run directories are the same paths as the first run
      And the experiment manifest still lists 2 runs each with a metrics row

    Scenario: re-running a shrunk spec removes the dropped run's directory
      Given an experiment of 2 runs over covered EUR/USD data
      When I run the experiment
      And I re-run the experiment with only its first run
      Then only the first run's directory remains under runs/experiments/<experiment>

  Rule: A run is validated and its data coverage checked before the engine starts

    Scenario: a run whose window has no materialized data fails fast
      Given an experiment of 1 run over a window with no materialized data
      When I run the experiment expecting failure
      Then the experiment fails telling me to materialize that window first

  Rule: A failed run aborts the experiment and records an error artifact (no manifest)

    Scenario: the first run failing aborts the experiment and writes an error artifact
      Given an experiment of 2 runs over covered EUR/USD data whose first run fails
      When I run the experiment expecting failure
      Then no experiment manifest is written
      And an experiment error artifact names the failed run

    Scenario: a later failure records the earlier runs as completed
      Given an experiment of 2 runs over covered EUR/USD data whose second run fails
      When I run the experiment expecting failure
      Then no experiment manifest is written
      And the experiment error names the failed run and lists the completed ones

  Rule: A validated experiment runs on the real engine end to end

    @integration
    Scenario: a one-run baseline experiment yields a manifest with real metrics
      Given materialized EUR/USD minute data with a flat price in 2014-05
      And a baseline experiment spec for that data
      When I run the experiment on the engine
      Then the experiment manifest has 1 run row
      And that run reports zero total return and zero max drawdown

    @integration
    Scenario: a second strategy (baseline-meanrev) runs through the same path
      Given materialized EUR/USD minute data with a flat price in 2014-05
      And a baseline-meanrev experiment spec for that data
      When I run the experiment on the engine
      Then the experiment manifest has 1 run row
      And that run reports zero total return and zero max drawdown
