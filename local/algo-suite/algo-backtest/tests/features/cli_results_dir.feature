Feature: A run's results directory is fresh, unique, and correctly nested
  `run` and `lean-smoke` derive their results directory from the data root, the
  run's label, and a fresh timestamp+monotonic stamp, so two invocations never
  collide and results always land under the label's own subtree.

  Scenario: the results directory nests under runs/<label>/<stamp> and is created
    Given a data root
    When a fresh results directory is built for label "baseline-ma"
    Then the directory is under "runs/baseline-ma" in the data root
    And the directory exists on disk

  Scenario: two results directories built back to back never collide
    Given a data root
    When two fresh results directories are built for label "baseline-ma"
    Then the two directories are different paths
