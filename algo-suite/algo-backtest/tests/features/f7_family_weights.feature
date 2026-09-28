Feature: F7 family-model fitting accepts optional row-aligned sample weights (Story 19, T5)
  `train_meta_learner` gains one optional keyword, `family_weights`, a sequence of one
  finite non-negative float per `split.train` row, in `split.train` order. When given,
  every family's LightGBM fit receives it as `sample_weight` (RWT-07); the weights are
  produced and mean-one normalized by the retraining weights module (RWT-05), F7 only
  validates and forwards them. When omitted, training is bit-identical to today's fit
  (RWT-17): the public signature `train_meta_learner(families, split, *, random_state)`
  keeps working unchanged. The logistic combiner is untouched by this task (T6 adds
  its own, independently normalized stage weights).

  The "real effect" fixture has forty train rows with identical trend features, half
  labeled UP and half labeled DOWN: an unweighted fit cannot prefer either class, so
  the trend family's P(up) is exactly 0.5; weighting one half to ~0 must move it.

  Background:
    Given a synthetic walk-forward training split with 40 labeled rows

  Rule: Omitted weights reproduce today's fit exactly (RWT-17, backward-compatible API)

    Scenario: Training without family_weights and training with the legacy call predict identically
      When the meta-learner is trained with the legacy call on the trend and indicator families
      And the meta-learner is trained with family_weights omitted on the trend and indicator families
      Then both trained meta-learners predict the same p_hat for the same held-out row
      And both trained meta-learners' trend family P(up) is identical on every train row

    Scenario: Uniform weights of 1.0 reproduce the unweighted fit bit for bit
      When the meta-learner is trained with the legacy call on the trend and indicator families
      And the meta-learner is trained with 40 family_weights of 1.0 on the trend and indicator families
      Then both trained meta-learners predict the same p_hat for the same held-out row
      And both trained meta-learners' trend family P(up) is identical on every train row

  Rule: Each family's LightGBM fit receives the row-aligned family-stage weights (RWT-07)

    Scenario: The fit of every family receives sample_weight equal to family_weights, in split.train order
      Given LightGBM fits are observed
      And family_weights are the 40 values 0.05, 0.10, 0.15, ... up to 2.00
      When the meta-learner is trained with those family_weights on the trend and indicator families
      Then 2 LightGBM fits were observed
      And every observed fit received sample_weight equal to 0.05, 0.10, 0.15, ... up to 2.00 in that order
      And every observed fit received 40 input rows in split.train order

    Scenario: Without family_weights the LightGBM fit receives no sample_weight at all
      Given LightGBM fits are observed
      When the meta-learner is trained with family_weights omitted on the trend and indicator families
      Then 2 LightGBM fits were observed
      And no observed fit received a sample_weight

  Rule: Invalid weights are rejected before any family is fitted (RWT-02)

    Scenario Outline: A weight vector of the wrong length is rejected naming both counts (<case>)
      Given LightGBM fits are observed
      And family_weights are <count> values of 1.0
      When training the meta-learner with those family_weights on the trend family fails
      Then the training failure names "family_weights"
      And the training failure names "<count>"
      And the training failure names "40"
      And 0 LightGBM fits were observed

      Examples:
        | case                 | count |
        | one short            | 39    |
        | one long             | 41    |
        | empty                | 0     |

    Scenario Outline: A weight that is negative or non-finite is rejected naming its position (<case>)
      Given LightGBM fits are observed
      And family_weights are 40 values of 1.0 except position <position> which is <value>
      When training the meta-learner with those family_weights on the trend family fails
      Then the training failure names "family_weights"
      And the training failure names "<fragment>"
      And the training failure names "<position>"
      And 0 LightGBM fits were observed

      Examples:
        | case             | position | value | fragment |
        | negative         | 3        | -0.5  | negative |
        | NaN              | 0        | nan   | finite   |
        | positive infinity| 39       | inf   | finite   |

  Rule: A weighted fit really changes the family model (not just the argument plumbing)

    Scenario Outline: On the balanced identical-feature fixture the trend family's P(up) follows the weights (<case>)
      Given a walk-forward split whose 40 train rows share identical trend features, the first 20 labeled UP and the last 20 labeled DOWN
      When the meta-learner is trained on the trend family with <weighting>
      Then the trend family's P(up) for those features is <expectation>

      Examples:
        | case                              | weighting                                                | expectation      |
        | unweighted: the classes tie       | family_weights omitted                                   | exactly 0.5      |
        | DOWN rows weighted to ~0          | the first 20 weights 1.0 and the last 20 weights 0.000001 | above 0.99       |
        | UP rows weighted to ~0            | the first 20 weights 0.000001 and the last 20 weights 1.0 | below 0.01       |
