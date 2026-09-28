Feature: F7 combiner fitting accepts independent row-aligned stage weights (Story 19, T6)
  `train_meta_learner` gains a second optional keyword, `combiner_weights`, a sequence of
  one finite non-negative float per `split.validation` row, in `split.validation` order.
  When given, the logistic combiner's `LogisticRegression.fit` receives it as
  `sample_weight` (RWT-08). The family stage keeps its own `family_weights` (T5): the two
  vectors are produced and mean-one normalized independently by the retraining weights
  module (RWT-05); F7 validates each one against its own stage's row count and forwards
  it to that stage only. Both vectors are validated before any family is fitted
  (fail fast, RWT-02). When `combiner_weights` is omitted the combiner fit is
  bit-identical to today's (RWT-17) and the public signature
  `train_meta_learner(families, split, *, random_state)` keeps working unchanged.

  The combiner is still fitted only on the families' out-of-sample predictions for
  `split.validation`; weights never change which rows it sees, and `split.test` is
  never consumed (future-data independence).

  The "real effect" fixture has forty validation rows with identical features, half
  labeled UP and half DOWN: every family predicts one constant P(up) for them, so an
  unweighted combiner cannot prefer either class and its p_hat is exactly 0.5;
  weighting one half to ~0 must move it.

  Background:
    Given a synthetic walk-forward training split with 40 train rows, 8 validation rows and 4 test rows

  Rule: Omitted combiner weights reproduce today's combiner fit exactly (RWT-17, backward-compatible API)

    Scenario: Training with the legacy call and with combiner_weights omitted fit identical combiners
      When the meta-learner is trained with the legacy call on the trend and indicator families
      And the meta-learner is trained with combiner_weights omitted on the trend and indicator families
      Then both trained meta-learners predict the same p_hat for the same held-out row
      And both trained meta-learners have identical combiner coefficients and intercept

    Scenario: Uniform combiner weights of 1.0 reproduce the unweighted combiner bit for bit
      When the meta-learner is trained with the legacy call on the trend and indicator families
      And the meta-learner is trained with 8 combiner_weights of 1.0 on the trend and indicator families
      Then both trained meta-learners predict the same p_hat for the same held-out row
      And both trained meta-learners have identical combiner coefficients and intercept

    Scenario: Without combiner_weights the LogisticRegression fit receives no sample_weight at all
      Given LogisticRegression fits are observed
      When the meta-learner is trained with combiner_weights omitted on the trend and indicator families
      Then 1 LogisticRegression fit was observed
      And no observed LogisticRegression fit received a sample_weight

  Rule: Each fitting stage receives its own weights and nothing else (RWT-05, RWT-08)

    Scenario: Family weights reach only the LightGBM fits and combiner weights reach only the LogisticRegression fit
      Given LightGBM fits are observed
      And LogisticRegression fits are observed
      And family_weights are the 40 values 0.05, 0.10, 0.15, ... up to 2.00
      And combiner_weights are the 8 values 0.25, 0.50, 0.75, ... up to 2.00
      When the meta-learner is trained with those family_weights and combiner_weights on the trend and indicator families
      Then 2 LightGBM fits were observed
      And every observed fit received sample_weight equal to 0.05, 0.10, 0.15, ... up to 2.00 in that order
      And 1 LogisticRegression fit was observed
      And the observed LogisticRegression fit received sample_weight equal to 0.25, 0.50, 0.75, ... up to 2.00 in that order
      And the observed LogisticRegression fit received 8 input rows equal to the families' P(up) on split.validation in order

    Scenario: Combiner weights alone leave the family fits unweighted
      Given LightGBM fits are observed
      And LogisticRegression fits are observed
      And combiner_weights are the 8 values 0.25, 0.50, 0.75, ... up to 2.00
      When the meta-learner is trained with those combiner_weights on the trend and indicator families
      Then 2 LightGBM fits were observed
      And no observed fit received a sample_weight
      And 1 LogisticRegression fit was observed
      And the observed LogisticRegression fit received sample_weight equal to 0.25, 0.50, 0.75, ... up to 2.00 in that order

  Rule: Inverted or misaligned stage vectors are rejected before any fit (RWT-02)

    Scenario Outline: A stage vector sized for the other stage is rejected naming the vector and both counts (<case>)
      Given LightGBM fits are observed
      And LogisticRegression fits are observed
      And family_weights are <family_count> values of 1.0
      And combiner_weights are <combiner_count> values of 1.0
      When training the meta-learner with those family_weights and combiner_weights on the trend family fails
      Then the training failure names "<vector>"
      And the training failure names "<given>"
      And the training failure names "<expected>"
      And 0 LightGBM fits were observed
      And 0 LogisticRegression fits were observed

      Examples:
        | case                                            | family_count | combiner_count | vector           | given | expected |
        | combiner weights sized for the train span       | 40           | 40             | combiner_weights | 40    | 8        |
        | family weights sized for the validation span    | 8            | 8              | family_weights   | 8     | 40       |
        | combiner weights one short                      | 40           | 7              | combiner_weights | 7     | 8        |
        | combiner weights empty                          | 40           | 0              | combiner_weights | 0     | 8        |

    Scenario: Both stage vectors invalid at once fails naming family_weights, checked first (fail-fast ordering, RWT-02)
      Given family_weights are 39 values of 1.0
      And combiner_weights are 7 values of 1.0
      When training the meta-learner with those family_weights and combiner_weights on the trend family fails
      Then the training failure names "family_weights"

    Scenario Outline: A combiner weight that is negative or non-finite is rejected naming its position (<case>)
      Given LightGBM fits are observed
      And LogisticRegression fits are observed
      And combiner_weights are 8 values of 1.0 except position <position> which is <value>
      When training the meta-learner with those combiner_weights on the trend family fails
      Then the training failure names "combiner_weights"
      And the training failure names "<fragment>"
      And the training failure names "<position>"
      And 0 LightGBM fits were observed
      And 0 LogisticRegression fits were observed

      Examples:
        | case              | position | value | fragment |
        | negative          | 2        | -0.5  | negative |
        | NaN               | 0        | nan   | finite   |
        | positive infinity | 7        | inf   | finite   |

  Rule: A combiner that would see only one class is refused, weighted or not

    Scenario: A single-class validation span still fails fast when combiner weights are given
      Given LogisticRegression fits are observed
      And a walk-forward split whose validation labels are [1, 1, 1, 1]
      When training the meta-learner with 4 combiner_weights of 1.0 on the trend family fails
      Then the training failure names "only one label class"
      And 0 LogisticRegression fits were observed

    Scenario: Combiner weights that leave one class with zero total weight are a one-class fit and are refused
      Given LogisticRegression fits are observed
      And a walk-forward split whose validation labels are [1, 0, 1, 0]
      When training the meta-learner with the combiner_weights 1.0, 0.0, 1.0, 0.0 on the trend family fails
      Then the training failure names "combiner_weights"
      And the training failure names "one label class"
      And the training failure names "positive weight"
      And 0 LogisticRegression fits were observed

  Rule: The combiner fit depends only on out-of-sample validation predictions, never on split.test

    Scenario: Two splits that differ only in their test rows fit identical combiners
      When the meta-learner is trained with 8 combiner_weights of 0.5 on the trend and indicator families
      And the test rows are replaced by 4 different rows and the meta-learner is trained again with 8 combiner_weights of 0.5 on the trend and indicator families
      Then both trained meta-learners predict the same p_hat for the same held-out row
      And both trained meta-learners have identical combiner coefficients and intercept

    Scenario: The weighted combiner is still calibrated on validation, not on train (regression guard)
      Given a walk-forward split where trend_direction predicts UP in train but the true label is DOWN, and the reverse in validation
      When the meta-learner is trained on the trend family alone with uniform combiner_weights of 1.0
      Then a held-out UP-trend row's p_hat is below 0.5

  Rule: A weighted combiner fit really changes p_hat (not just the argument plumbing)

    Scenario Outline: On the balanced identical-feature validation fixture p_hat follows the combiner weights (<case>)
      Given a walk-forward split whose 40 validation rows share identical features, the first 20 labeled UP and the last 20 labeled DOWN
      When the meta-learner is trained on the trend family with <weighting>
      Then the meta-learner's p_hat for those features is <expectation>

      Examples:
        | case                              | weighting                                                          | expectation      |
        | unweighted: the classes tie       | combiner_weights omitted                                           | exactly 0.5      |
        | DOWN rows weighted to ~0          | the first 20 combiner weights 1.0 and the last 20 weights 0.000001 | above 0.99       |
        | UP rows weighted to ~0            | the first 20 combiner weights 0.000001 and the last 20 weights 1.0 | below 0.01       |
