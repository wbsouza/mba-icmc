Feature: F7 — threshold-rule (meta-learner) filter
  Proves the terminal rule (`monografia/chapters/03-methodology.tex`,
  "Phase two: deterministic execution as a filter chain"):

      BUY  if p_hat > theta_high and (regime = bull or the regime gate is off)
      SELL if p_hat < theta_low  and (regime = bear or the regime gate is off)
      HOLD otherwise

  theta_high, theta_low and regime_gate are strategy config.yaml `meta_learner` keys
  (2026-09-27 amendment, story 09), not code constants,

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

  Rule: train_meta_learner calibrates the combiner on validation, not train (regression proof)

    Scenario: a train/validation split with an inverted trend-label relationship proves validation is used
      Given a walk-forward split where trend_direction predicts UP in train but the true label is DOWN, and the reverse in validation
      When the meta-learner is trained on the trend family alone
      Then a held-out UP-trend row's p_hat is below 0.5

  Rule: F7 applies the terminal BUY/SELL/HOLD rule from p_hat, the thresholds and the regime gate

    Scenario Outline: <case>
      Given a stub meta-learner predicting p_hat <p_hat>
      And theta_high <theta_high> and theta_low <theta_low> with the regime gate <gate>
      And trend_score <trend_score> in state.features
      When F7 applies to the state
      Then F7 recommends "<recommendation>"
      And F7's result does not veto
      And F7's reason mentions "regime_gate=<gate_flag>"

      Examples: gate on — the thesis rule, the regime must agree with p_hat
        | case                                              | p_hat | theta_high | theta_low | gate | gate_flag | trend_score | recommendation |
        | high p_hat in a bull regime buys                  | 0.8   | 0.55       | 0.45      | on   | True      | 0.5         | BUY            |
        | low p_hat in a bear regime sells                  | 0.2   | 0.55       | 0.45      | on   | True      | -0.5        | SELL           |
        | high p_hat in a bear regime holds                 | 0.8   | 0.55       | 0.45      | on   | True      | -0.5        | HOLD           |
        | low p_hat in a bull regime holds                  | 0.2   | 0.55       | 0.45      | on   | True      | 0.5         | HOLD           |
        | p_hat inside the band holds                       | 0.5   | 0.55       | 0.45      | on   | True      | 0.5         | HOLD           |
        | p_hat exactly at theta_high holds (strict >)      | 0.55  | 0.55       | 0.45      | on   | True      | 0.5         | HOLD           |
        | p_hat exactly at theta_low holds (strict <)       | 0.45  | 0.55       | 0.45      | on   | True      | -0.5        | HOLD           |
        | neutral regime blocks a buy                       | 0.8   | 0.55       | 0.45      | on   | True      | 0           | HOLD           |
        | neutral regime blocks a sell                      | 0.2   | 0.55       | 0.45      | on   | True      | 0           | HOLD           |
        | wider band: 0.58 is inside 0.6/0.4 and holds      | 0.58  | 0.6        | 0.4       | on   | True      | 0.5         | HOLD           |
        | narrower band: 0.53 clears 0.52 and buys          | 0.53  | 0.52       | 0.48      | on   | True      | 0.5         | BUY            |

      Examples: gate off — p_hat alone decides (2026-09-27 pilot amendment, story 09)
        | case                                              | p_hat | theta_high | theta_low | gate | gate_flag | trend_score | recommendation |
        | high p_hat in a bear regime buys                  | 0.8   | 0.55       | 0.45      | off  | False     | -0.5        | BUY            |
        | low p_hat in a bull regime sells                  | 0.2   | 0.55       | 0.45      | off  | False     | 0.5         | SELL           |
        | neutral regime does not block a buy               | 0.8   | 0.55       | 0.45      | off  | False     | 0           | BUY            |
        | neutral regime does not block a sell              | 0.2   | 0.55       | 0.45      | off  | False     | 0           | SELL           |
        | p_hat inside the band still holds                 | 0.5   | 0.55       | 0.45      | off  | False     | 0.5         | HOLD           |
        | p_hat exactly at theta_high still holds           | 0.55  | 0.55       | 0.45      | off  | False     | -0.5        | HOLD           |
        | narrower band: 0.47 is below 0.48 and sells       | 0.47  | 0.52       | 0.48      | off  | False     | 0.5         | SELL           |

    Scenario: F7's result carries the audit fields and the meta-learner sees the state's own features
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45 with the regime gate on
      And trend_score 0.5 in state.features
      When F7 applies to the state
      Then F7's filter_name is "f7_meta_learner"
      And F7's reason mentions "p_hat=0.8000"
      And F7's confidence is 0.8
      And F7 enriches "p_hat" with value 0.8
      And the meta-learner was called with the state's own features

  Rule: Only the regime gate needs F1's trend_score enrichment

    Scenario: with the gate on, a missing trend_score fails fast (F1 must run first)
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45 with the regime gate on
      When F7 applies to a state missing "trend_score"
      Then applying F7 fails naming "trend_score"

    Scenario: with the gate off, a missing trend_score is not needed
      Given a stub meta-learner predicting p_hat 0.8
      And theta_high 0.55 and theta_low 0.45 with the regime gate off
      When F7 applies to a state missing "trend_score"
      Then F7 recommends "BUY"

  Rule: F7's thresholds and gate come from the strategy config.yaml meta_learner section

    Scenario Outline: a complete meta_learner section parses into an F7Config (<case>)
      Given a meta_learner section with theta_high <theta_high>, theta_low <theta_low> and regime_gate <regime_gate>
      When the F7 config is parsed for strategy "baseline"
      Then the parsed F7 config has theta_high <theta_high>
      And the parsed F7 config has theta_low <theta_low>
      And the parsed F7 config has the regime gate <gate>

      Examples:
        | case              | theta_high | theta_low | regime_gate | gate |
        | thesis defaults   | 0.55       | 0.45      | true        | on   |
        | gate off          | 0.55       | 0.45      | false       | off  |
        | wider band        | 0.6        | 0.4       | true        | on   |
        | asymmetric band   | 0.53       | 0.40      | false       | off  |

    Scenario Outline: an invalid meta_learner section fails fast naming the bad key and the strategy (<case>)
      Given a meta_learner section with theta_high <theta_high>, theta_low <theta_low> and regime_gate <regime_gate>
      When parsing the F7 config for strategy "baseline" fails
      Then the F7 config failure names "<names>"
      And the F7 config failure names "baseline"

      Examples:
        | case                              | theta_high | theta_low | regime_gate | names       |
        | theta_low above theta_high        | 0.45       | 0.55      | true        | theta_low   |
        | theta_low equal to theta_high     | 0.5        | 0.5       | true        | theta_low   |
        | theta_high above 1                | 1.5        | 0.45      | true        | theta_high  |
        | theta_low at 0                    | 0.55       | 0         | true        | theta_low   |
        | regime_gate as a string           | 0.55       | 0.45      | "yes"       | regime_gate |
        | regime_gate as an integer         | 0.55       | 0.45      | 1           | regime_gate |
        | theta_high as a string            | high       | 0.45      | true        | theta_high  |

    Scenario Outline: a missing meta_learner key fails fast naming the key and the strategy (<key>)
      Given a meta_learner section missing "<key>"
      When parsing the F7 config for strategy "baseline" fails
      Then the F7 config failure names "<key>"
      And the F7 config failure names "baseline"

      Examples:
        | key         |
        | theta_high  |
        | theta_low   |
        | regime_gate |
