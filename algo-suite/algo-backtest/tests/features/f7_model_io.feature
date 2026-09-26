Feature: Portable, pickle-free F7 model persistence
  F7 models are trained on the host but loaded inside the pinned LEAN container, whose
  scikit-learn/LightGBM/numpy are older than the workspace's — a pickled model breaks
  across that gap. f7_model_io stores the model as data (LightGBM text models plus the
  logistic combiner's coefficients) in one JSON document with its training provenance.

  Rule: A reloaded model predicts exactly what the trained model predicts

    Scenario: Round-tripping a trained hybrid-shaped model preserves every prediction
      Given a meta-learner trained on seeded synthetic rows with the trend, indicator, pattern and news families
      When the model is dumped to JSON and loaded back
      Then the loaded model's p_hat matches the trained model's on every test row
      And the loaded model carries no scikit-learn or pickled object

    Scenario: The embedded provenance round-trips
      Given a meta-learner trained on seeded synthetic rows with the trend, indicator, pattern and news families
      When the model is dumped to JSON with provenance strategy "hybrid" and loaded back
      Then the document's provenance strategy is "hybrid"

  Rule: Anything that is not an F7 model document of a supported version is rejected

    Scenario: A document of another format version fails fast with the retrain command
      Given a JSON file claiming F7 format version 99
      When loading it as an F7 model fails
      Then the model failure names "train_"

  Rule: A model only runs under a strategy whose declared families it was trained on

    Scenario: Every bundled chain model matches its strategy's declared families
      Then each F7-driven strategy's bundled model has exactly its config.yaml meta_learner families

    Scenario: A family mismatch fails fast naming both family sets
      When families "trend, indicator, pattern" are required to match "trend, indicator, pattern, news"
      Then the model failure names "meta_learner.families"
