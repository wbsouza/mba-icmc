Feature: Aggregate experiments into the Chapter-4 summary table
  `algo-analyze summary` unions every successful experiment manifest under the data root
  into one deterministic CSV — one row per run, fixed auditable columns — the table the
  thesis cites. It reads experiment.json only; failed experiments are excluded. No deltas,
  ranking, or plots (Stage F2).

  Rule: Every successful experiment contributes one CSV row per run

    Scenario: two experiments aggregate into one table sorted by experiment then run
      Given a successful experiment "beta" with runs "b2, b1"
      And a successful experiment "alpha" with runs "a2, a1"
      When I aggregate the experiments
      Then the summary has 4 rows
      And the summary columns are exactly the canonical set
      And the rows are ordered alpha/a1, alpha/a2, beta/b1, beta/b2

    Scenario: two price-only strategies sit side by side, ready for comparison
      Given a successful experiment "compare" with a baseline-ma and a baseline-meanrev run
      When I aggregate the experiments
      Then the summary has 2 rows
      And the summary has both a "baseline-ma" and a "baseline-meanrev" strategy row

  Rule: Failed experiments are excluded, never silently corrupting the table

    Scenario: a failed-only experiment is skipped while successful rows remain
      Given a successful experiment "alpha" with runs "a1"
      And a failed experiment "beta"
      When I aggregate the experiments
      Then the summary has 1 row
      And the summary contains run "a1"

  Rule: Aggregation fails fast on a broken or ambiguous experiment state

    Scenario: no experiments have run
      Given no experiments have run
      When I aggregate the experiments expecting failure
      Then aggregation fails telling me to run an experiment first

    Scenario: an experiment with both a manifest and an error artifact is rejected
      Given an experiment "alpha" with both a manifest and an error artifact
      When I aggregate the experiments expecting failure
      Then aggregation fails naming the inconsistent experiment

    Scenario: a corrupt manifest is rejected
      Given a successful experiment "alpha" whose manifest is corrupt
      When I aggregate the experiments expecting failure
      Then aggregation fails naming the corrupt manifest

    Scenario: a manifest row with an unknown column is rejected
      Given a successful experiment "alpha" whose row has an unknown column
      When I aggregate the experiments expecting failure
      Then aggregation fails naming the wrong columns

    Scenario: a row whose experiment label disagrees with the manifest is rejected
      Given a successful experiment "alpha" whose row is labeled experiment "beta"
      When I aggregate the experiments expecting failure
      Then aggregation fails naming the mismatched experiment label

    Scenario: a failed run in a manifest is rejected (only successful runs are aggregated)
      Given a successful experiment "alpha" with a failed run
      When I aggregate the experiments expecting failure
      Then aggregation fails saying only successful runs are aggregated

    Scenario: a duplicate run identity is rejected
      Given a successful experiment "alpha" with runs "a1, a1"
      When I aggregate the experiments expecting failure
      Then aggregation fails naming the duplicate run identity

  Rule: The summary CSV is deterministic and thesis-stable

    Scenario: re-running without data changes yields a byte-identical CSV
      Given a successful experiment "alpha" with runs "a1, a2"
      When I write the summary twice
      Then both CSV files are byte-identical
