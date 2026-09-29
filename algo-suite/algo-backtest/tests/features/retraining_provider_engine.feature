Feature: The on-demand provider loads a published bundle through the live engine
  Story 19 (T11/T12), minimum-viable slice for today's delivery (2026-09-28): the
  provider's boundary-based selection, cache/eviction and mid-replay retraining
  triggers remain future T11/T12 work (see progress.md's "Integration handoff notes
  for Phase 3"); this proves only that `ChainAlgorithm` can load its F7 model from a
  single pre-published retraining bundle (`retraining.bundle`/`retraining.provider`)
  and run a real native backtest without error, in place of a single model.json file.
  Needs the project's real EUR/USD data root (ALGO_DATA_ROOT) — the same one
  scripts/train_baseline_meta_learner.py already requires — to fit one real T9 epoch.

  Rule: A chain strategy can load its F7 model from a published bundle instead of model_path

    @integration
    Scenario: baseline runs a real backtest with an F7 model loaded from a published bundle
      Given one real T9 epoch bundle fitted for policy U deploying 2016-01, published to a fresh registry
      When the baseline chain runs natively over the bundle's deployment window with that bundle as its F7 model
      Then the strategy run exits successfully
      And the container log shows the algorithm loaded the published bundle
      And the container log shows the F1-F7 chain actually evaluated a decision
      And a metrics summary is reported
