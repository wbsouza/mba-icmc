Feature: F7 — threshold-rule (meta-learner) filter
  Proves the terminal rule (`monografia/chapters/03-methodology.tex`,
  "Phase two: deterministic execution as a filter chain"):

      BUY  if p_hat > theta_high and regime = bull
      SELL if p_hat < theta_low  and regime = bear
      HOLD otherwise

  plus the walk-forward data-splitting policy (PRD.md §4) and the meta-learner's
  reproducibility guarantee (every LightGBM `Booster`/`LogisticRegression` fit pins
  `random_state`).

  Rule: walk_forward_split partitions rows into chronological, non-overlapping spans

    Scenario: rows split into train, validation and test by date boundary
      Given training rows on 2020-01-01, 2020-01-02, 2020-01-10, 2020-01-11, 2020-01-20, 2020-01-21
      When the rows are walk-forward split at train_end 2020-01-05, validation_end 2020-01-15, test_end 2020-01-25
      Then the train span has 2 rows
      And the validation span has 2 rows
      And the test span has 2 rows

    Scenario: out-of-order boundaries fail fast
      Given training rows on 2020-01-01, 2020-01-02, 2020-01-10, 2020-01-11, 2020-01-20, 2020-01-21
      When the rows are walk-forward split at train_end 2020-01-15, validation_end 2020-01-05, test_end 2020-01-25 expecting failure
      Then the split fails naming "strictly increasing"

    Scenario: an empty span fails fast
      Given training rows on 2020-01-01, 2020-01-02, 2020-01-10, 2020-01-11, 2020-01-20, 2020-01-21
      When the rows are walk-forward split at train_end 2020-01-05, validation_end 2020-01-06, test_end 2020-01-25 expecting failure
      Then the split fails naming "empty"

  Rule: train_meta_learner is reproducible given a fixed random_state

    Scenario: training twice on identical inputs yields identical predictions
      Given a synthetic walk-forward training split with 40 labeled rows
      When the meta-learner is trained twice with random_state 42 on the trend and indicator families
      Then both trained meta-learners predict the same p_hat for the same held-out row

  Rule: F7 applies the terminal BUY/SELL/HOLD rule from p_hat and the trend regime

    Scenario: p_hat above theta_high with a bull regime recommends BUY
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45
      And trend_score 0.5 in state.features
      When F7 applies to the state
      Then F7 recommends "BUY"
      And F7's result does not veto
      And F7's filter_name is "f7_meta_learner"
      And F7's reason mentions "p_hat=0.8000"
      And F7's confidence is 0.8
      And F7 enriches "p_hat" with value 0.8
      And the meta-learner was called with the state's own features

    Scenario: p_hat below theta_low with a bear regime recommends SELL
      Given a stub meta-learner predicting p_hat 0.2
      And theta_high 0.55 and theta_low 0.45
      And trend_score -0.5 in state.features
      When F7 applies to the state
      Then F7 recommends "SELL"

    Scenario: a high p_hat with a bear regime HOLDs — the regime must agree
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45
      And trend_score -0.5 in state.features
      When F7 applies to the state
      Then F7 recommends "HOLD"
      And F7's result does not veto

    Scenario: a p_hat between the thresholds HOLDs regardless of regime
      Given a stub meta-learner predicting p_hat 0.5
      And theta_high 0.55 and theta_low 0.45
      And trend_score 0.5 in state.features
      When F7 applies to the state
      Then F7 recommends "HOLD"

    Scenario: p_hat exactly at theta_high HOLDs — the rule is strictly greater-than
      Given a stub meta-learner predicting p_hat 0.55
      And theta_high 0.55 and theta_low 0.45
      And trend_score 0.5 in state.features
      When F7 applies to the state
      Then F7 recommends "HOLD"

    Scenario: p_hat exactly at theta_low HOLDs — the rule is strictly less-than
      Given a stub meta-learner predicting p_hat 0.45
      And theta_high 0.55 and theta_low 0.45
      And trend_score -0.5 in state.features
      When F7 applies to the state
      Then F7 recommends "HOLD"

    Scenario: a zero trend_score is a neutral regime, so a high p_hat still HOLDs (not bull)
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45
      And trend_score 0 in state.features
      When F7 applies to the state
      Then F7 recommends "HOLD"

    Scenario: a zero trend_score is a neutral regime, so a low p_hat still HOLDs (not bear)
      Given a stub meta-learner predicting p_hat 0.2
      And theta_high 0.55 and theta_low 0.45
      And trend_score 0 in state.features
      When F7 applies to the state
      Then F7 recommends "HOLD"

  Rule: meta_learner.theta_{high,low} resolve via the shared algo_core.config loader

    Scenario: a configured meta_learner section resolves both thresholds
      Given a meta_learner config with theta_high=0.6, theta_low=0.4
      When the F7 config is loaded
      Then the loaded F7 config has theta_high 0.6
      And the loaded F7 config has theta_low 0.4

    Scenario: a missing meta_learner section fails fast
      Given a meta_learner config missing "theta_high"
      When the F7 config is loaded
      Then loading the F7 config fails naming "theta_high"

  Rule: F7 requires the upstream trend_score enrichment (F1 must run first)

    Scenario: trend_score missing from state.features fails fast
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45
      When F7 applies to a state missing "trend_score"
      Then applying F7 fails naming "trend_score"
