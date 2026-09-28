Feature: One epoch's weighted training (Story 19, T9)
  The trainer builds one policy epoch from the ingestion ledger and publishes it as an
  immutable bundle, using only what was knowable at the epoch's preparation cutoff
  C = D - 1 day (RWT-01, RWT-24):

      rows      = the ledger's rows visible and mature as of C (label_time <= C)
      family    = select_rows(rows, spans.family)     weights: E exponential, else uniform
      combiner  = select_rows(rows, spans.combiner)   weights: E exponential, else uniform
      threshold = select_rows(rows, spans.threshold)  unweighted q10 scores of the new model
      fit       = train_meta_learner(families, split(train=family, validation=combiner, test=()),
                                     family_weights, combiner_weights, random_state=seed)
      bundle    = publish(model, thresholds, provenance)

  E's raw weights are 2^(-age_days/60) with the age measured to the stage's own span
  end (family end, combiner end) and mean-one normalized per stage (RWT-04/05). Support
  is checked per stage against the settings' minima before any fit (RWT-06); the
  registered production minima are family 1000/50/200, combiner 100/20/50, threshold
  100, and the settings object lets a test lower them so the mechanics show on a
  handful of rows. Features are looked up by row key from a caller-given feature
  source; the trainer reads no trade outcome, veto or profit field (RWT-09), needs no
  row after the cutoff and never requires a test span to fit (RWT-30).

  Provenance recorded per epoch: the ordered row keys of every stage, each stage's
  raw and normalized weights and n_eff, the thresholds, the ledger watermark, the
  seed and the bundle's semantic model payload hash (`hashes.model_sha256`). Repeating
  a fit on identical pinned inputs gives the same bundle_id and payload hash; the wall
  time fields (`published_at`, `training_duration_seconds`) are recorded separately
  and are not required to be equal (RWT-30).

  The fixture dates are chosen so that E's family ages are exact multiples of the
  half-life (300, 240, 180, 120 and 60 days before 2015-12-31) and its combiner ages
  are 30, 20, 10 and 5 days before 2016-01-30.

  Background:
    Given the test training settings
      | setting                   | value           |
      | half_life_days            | 60              |
      | seed                      | 42              |
      | families                  | trend, indicator |
      | family_min_rows           | 3               |
      | family_min_per_class      | 1               |
      | family_min_effective_n    | 2               |
      | combiner_min_rows         | 4               |
      | combiner_min_per_class    | 1               |
      | combiner_min_effective_n  | 2               |
      | threshold_min_rows        | 4               |
    And the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
    And an empty bundle registry directory
    And an empty ledger directory
    And the source batch "history-2015" carries the rows
      | key   | available_at         | label_time           | label | trend_direction | trend_strength | higher_tf_trend_direction | rsi  | macd_hist |
      | fam-1 | 2015-03-06T00:00:00Z | 2015-03-06T01:00:00Z | 1     | 1.0             | 20.0           | 1.0                       | 55.0 | 0.0001    |
      | fam-2 | 2015-05-05T00:00:00Z | 2015-05-05T01:00:00Z | 0     | -1.0            | 30.0           | 0.0                       | 45.0 | -0.0001   |
      | fam-3 | 2015-07-04T00:00:00Z | 2015-07-04T01:00:00Z | 1     | 1.0             | 40.0           | 1.0                       | 60.0 | 0.0002    |
      | fam-4 | 2015-09-02T00:00:00Z | 2015-09-02T01:00:00Z | 0     | -1.0            | 50.0           | -1.0                      | 40.0 | -0.0002   |
      | fam-5 | 2015-11-01T00:00:00Z | 2015-11-01T01:00:00Z | 1     | 1.0             | 60.0           | 1.0                       | 65.0 | 0.0003    |
    And the source batch "jan-2016" carries the rows
      | key   | available_at         | label_time           | label | trend_direction | trend_strength | higher_tf_trend_direction | rsi  | macd_hist |
      | cmb-1 | 2015-12-31T00:00:00Z | 2015-12-31T01:00:00Z | 1     | 1.0             | 35.0           | 1.0                       | 58.0 | 0.0001    |
      | cmb-2 | 2016-01-10T00:00:00Z | 2016-01-10T01:00:00Z | 0     | -1.0            | 45.0           | -1.0                      | 42.0 | -0.0001   |
      | cmb-3 | 2016-01-20T00:00:00Z | 2016-01-20T01:00:00Z | 1     | 1.0             | 55.0           | 1.0                       | 62.0 | 0.0002    |
      | cmb-4 | 2016-01-25T00:00:00Z | 2016-01-25T01:00:00Z | 0     | -1.0            | 65.0           | 0.0                       | 38.0 | -0.0002   |
    And the source batch "feb-2016" carries the rows
      | key   | available_at         | label_time           | label | trend_direction | trend_strength | higher_tf_trend_direction | rsi  | macd_hist |
      | thr-1 | 2016-02-01T00:00:00Z | 2016-02-01T01:00:00Z | 1     | 1.0             | 25.0           | 1.0                       | 57.0 | 0.0001    |
      | thr-2 | 2016-02-05T00:00:00Z | 2016-02-05T01:00:00Z | 0     | -1.0            | 35.0           | -1.0                      | 43.0 | -0.0001   |
      | thr-3 | 2016-02-10T00:00:00Z | 2016-02-10T01:00:00Z | 1     | 1.0             | 45.0           | 0.0                       | 61.0 | 0.0002    |
      | thr-4 | 2016-02-15T00:00:00Z | 2016-02-15T01:00:00Z | 0     | -1.0            | 55.0           | -1.0                      | 39.0 | -0.0002   |
      | thr-5 | 2016-02-20T00:00:00Z | 2016-02-20T01:00:00Z | 1     | 1.0             | 65.0           | 1.0                       | 63.0 | 0.0003    |
      | thr-6 | 2016-02-25T00:00:00Z | 2016-02-25T01:00:00Z | 0     | -1.0            | 75.0           | 0.0                       | 37.0 | -0.0003   |
    And the source batch "mar-2016" carries the rows
      | key   | available_at         | label_time           | label | trend_direction | trend_strength | higher_tf_trend_direction | rsi  | macd_hist |
      | mar-1 | 2016-03-05T00:00:00Z | 2016-03-05T01:00:00Z | 1     | 1.0             | 30.0           | 1.0                       | 56.0 | 0.0001    |
      | mar-2 | 2016-03-12T00:00:00Z | 2016-03-12T01:00:00Z | 0     | -1.0            | 40.0           | -1.0                      | 44.0 | -0.0001   |
      | mar-3 | 2016-03-19T00:00:00Z | 2016-03-19T01:00:00Z | 1     | 1.0             | 50.0           | 1.0                       | 59.0 | 0.0002    |
      | mar-4 | 2016-03-26T00:00:00Z | 2016-03-26T01:00:00Z | 0     | -1.0            | 60.0           | -1.0                      | 41.0 | -0.0002   |
    And the batches "history-2015, jan-2016, feb-2016" are consumed into the ledger

  Rule: Every policy produces its epoch from watermark-visible mature rows with exact row and weight provenance (RWT-01, RWT-09, RWT-11)

    Scenario Outline: Policy <policy> prepares the first epoch (D = 2016-03-01, C = 2016-02-29)
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy <policy>
      Then a bundle is published for policy "<policy>"
      And the epoch's family row keys are "<family_keys>"
      And the epoch's combiner row keys are "cmb-1, cmb-2, cmb-3, cmb-4"
      And the epoch's threshold row keys are "thr-1, thr-2, thr-3, thr-4, thr-5, thr-6"
      And the epoch's family weights are <family_weights>
      And the epoch's combiner weights are <combiner_weights>
      And the epoch's family n_eff is <family_n_eff>
      And the epoch's combiner n_eff is <combiner_n_eff>
      And the epoch's family weighting is "<weighting>"
      And the epoch's thresholds are strictly inside (0, 1) with theta_low below theta_high
      And the epoch's thresholds equal the 0.10 and 0.90 linear quantiles of the published model's p_hat over the threshold rows
      And the epoch's ledger watermark is 2016-02-25T00:00:00Z
      And the epoch's seed is 42

      Examples:
        | policy | family_keys                       | family_weights                                                                                      | combiner_weights                                                                | family_n_eff       | combiner_n_eff     | weighting   |
        | F      | fam-1, fam-2, fam-3, fam-4, fam-5 | 1.0, 1.0, 1.0, 1.0, 1.0                                                                             | 1.0, 1.0, 1.0, 1.0                                                              | 5.0                | 4.0                | uniform     |
        | Q      | fam-1, fam-2, fam-3, fam-4, fam-5 | 1.0, 1.0, 1.0, 1.0, 1.0                                                                             | 1.0, 1.0, 1.0, 1.0                                                              | 5.0                | 4.0                | uniform     |
        | R      | fam-3, fam-4, fam-5               | 1.0, 1.0, 1.0                                                                                       | 1.0, 1.0, 1.0, 1.0                                                              | 3.0                | 4.0                | uniform     |
        | U      | fam-1, fam-2, fam-3, fam-4, fam-5 | 1.0, 1.0, 1.0, 1.0, 1.0                                                                             | 1.0, 1.0, 1.0, 1.0                                                              | 5.0                | 4.0                | uniform     |
        | E      | fam-1, fam-2, fam-3, fam-4, fam-5 | 0.16129032258064516, 0.3225806451612903, 0.6451612903225806, 1.2903225806451613, 2.5806451612903225 | 0.8479565287425547, 0.9517990221296736, 1.0683582799585316, 1.1318861691692401 | 2.8181818181818183 | 3.9530502473117797 | exponential |

    Scenario: Policy E records the raw exponential weights of both stages beside the normalized ones
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy E
      Then the epoch's raw family weights are 0.03125, 0.0625, 0.125, 0.25, 0.5
      And the epoch's raw combiner weights are 0.7071067811865476, 0.7937005259840998, 0.8908987181403393, 0.9438743126816935
      And the epoch's family half-life is 60 days
      And the epoch's combiner half-life is 60 days

    Scenario: F, Q and U share the first epoch's semantic payload; R and E do not
      When the epoch starting 2016-03-01T00:00:00Z is trained for each policy F, Q, R, U, E
      Then the policies F, Q and U have the same hashes.model_sha256
      And the policies F, Q and U have the same thresholds
      And the policy R's hashes.model_sha256 differs from U's
      And the policy E's hashes.model_sha256 differs from U's
      And the registry lists 5 published bundles

    Scenario: The epoch is trained with no row at or after the cutoff and no test span
      Then the ledger holds no row available at or after 2016-02-29T00:00:00Z
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy U
      Then a bundle is published for policy "U"
      And the epoch's deployment span is [2016-03-01T00:00:00Z, 2016-04-01T00:00:00Z)
      And the epoch's activation boundary is 2016-03-01T00:00:00Z

  Rule: Exponential weighting really changes the fitted model on identical row support

    Scenario: Recent DOWN labels outweigh older UP labels under E but not under U
      Given the batch "history-2015" is replaced by rows sharing identical features, labeled 1, 1, 1, 0, 0 from oldest to newest
      And the batches "history-2015, jan-2016, feb-2016" are consumed into a fresh ledger
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy U
      And the epoch starting 2016-03-01T00:00:00Z is trained for policy E
      Then U's published trend family P(up) for the shared features is above 0.55
      And E's published trend family P(up) for the shared features is below 0.35

  Rule: Later epochs shift or keep the stage spans per policy on the same ledger

    Scenario Outline: The second epoch (D = 2016-04-01, C = 2016-03-31) for policy <policy>
      Given the batch "mar-2016" is consumed into the ledger
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy F
      And the epoch starting 2016-04-01T00:00:00Z is trained for policy <policy>
      Then the epoch's family row keys are "<family_keys>"
      And the epoch's combiner row keys are "<combiner_keys>"
      And the epoch's threshold row keys are "mar-1, mar-2, mar-3, mar-4"
      And the epoch's hashes.model_sha256 <payload_relation> F's first-epoch payload hash
      And the epoch's thresholds <threshold_relation> F's first-epoch thresholds
      And the epoch's ledger watermark is 2016-03-26T00:00:00Z

      Examples:
        | policy | family_keys                                                            | combiner_keys                              | payload_relation | threshold_relation |
        | Q      | fam-1, fam-2, fam-3, fam-4, fam-5                                      | cmb-1, cmb-2, cmb-3, cmb-4                 | equals           | equals              |
        | U      | fam-1, fam-2, fam-3, fam-4, fam-5, cmb-1, cmb-2, cmb-3, cmb-4          | thr-1, thr-2, thr-3, thr-4, thr-5, thr-6   | differs from     | differs from        |

  Rule: Insufficient support or a failed fit publishes nothing (RWT-06, RWT-15)

    Scenario: The registered production minima reject the tiny fixture with measured and required counts, before any fit
      Given the training settings use the registered support minima
      And LightGBM fits are observed
      When training the epoch starting 2016-03-01T00:00:00Z for policy U fails
      Then the training failure names "family"
      And the training failure names "rows: measured 5, required 1000"
      And 0 LightGBM fits were observed
      And the registry lists 0 published bundles
      And no manifest.json exists in the registry outside a staging directory

    Scenario: A failing LightGBM fit propagates and publishes nothing
      Given the LightGBM fit is made to raise "injected booster failure"
      When training the epoch starting 2016-03-01T00:00:00Z for policy U fails
      Then the training failure names "injected booster failure"
      And the registry lists 0 published bundles
      And no manifest.json exists in the registry outside a staging directory

    Scenario: A one-class combiner span fails in the fit and publishes nothing
      Given the training settings set combiner_min_per_class to none
      And the batch "jan-2016" is replaced by the same rows all labeled 1
      And the batches "history-2015, jan-2016, feb-2016" are consumed into a fresh ledger
      When training the epoch starting 2016-03-01T00:00:00Z for policy U fails
      Then the training failure names "only one label class"
      And the registry lists 0 published bundles

  Rule: Pending labels are excluded and the future tail cannot influence the fit (RWT-24, RWT-30)

    Scenario: Rows whose label is pending at the cutoff or at their stage end are fitted nowhere
      Given the source batch "jan-2016-pending" carries the rows
        | key      | available_at         | label_time           | label | trend_direction | trend_strength | higher_tf_trend_direction | rsi  | macd_hist |
        | cmb-pend | 2016-01-29T23:00:00Z | 2016-01-30T01:00:00Z | 1     | 1.0             | 50.0           | 1.0                       | 50.0 | 0.0       |
      And the source batch "feb-2016-pending" carries the rows
        | key      | available_at         | label_time           | label | trend_direction | trend_strength | higher_tf_trend_direction | rsi  | macd_hist |
        | thr-pend | 2016-02-28T20:00:00Z | 2016-02-29T02:00:00Z | 1     | 1.0             | 50.0           | 1.0                       | 50.0 | 0.0       |
      And the batches "history-2015, jan-2016, jan-2016-pending, feb-2016, feb-2016-pending" are consumed into a fresh ledger
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy U
      Then the row "cmb-pend" is mature in the ledger
      And the row "thr-pend" is pending in the ledger
      And the epoch's ledger watermark is 2016-02-28T20:00:00Z
      And the epoch's family row keys are "fam-1, fam-2, fam-3, fam-4, fam-5"
      And the epoch's combiner row keys are "cmb-1, cmb-2, cmb-3, cmb-4"
      And the epoch's threshold row keys are "thr-1, thr-2, thr-3, thr-4, thr-5, thr-6"
      And the epoch's stage row counts are family 5, combiner 4, threshold 6

    Scenario: Consuming and mutating rows after the cutoff leaves the semantic payload hash and provenance unchanged
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy E
      And the epoch's bundle_id, hashes.model_sha256, thresholds and row keys are remembered
      And the batch "mar-2016" is consumed into the ledger with every feature value doubled and every label flipped
      And the epoch starting 2016-03-01T00:00:00Z is trained again for policy E into a fresh registry
      Then the epoch's bundle_id is unchanged
      And the epoch's hashes.model_sha256 is unchanged
      And the epoch's thresholds are unchanged
      And the epoch's row keys are unchanged

  Rule: Eligibility ignores trade execution, vetoes and realized profit (RWT-09)

    Scenario: Trade outcome fields attached to the rows do not change which rows are fitted or what is fitted
      Given the trade context attached to the rows
        | key   | vetoed | traded | trade_pnl |
        | fam-1 | yes    | no     | none      |
        | fam-2 | no     | yes    | -35.0     |
        | fam-3 | no     | yes    | 80.0      |
        | cmb-2 | yes    | no     | none      |
        | thr-4 | no     | yes    | -12.5     |
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy U
      And the epoch's bundle_id and row keys are remembered
      And every trade context field is flipped and the epoch starting 2016-03-01T00:00:00Z is trained again for policy U into a fresh registry
      Then the epoch's family row keys are "fam-1, fam-2, fam-3, fam-4, fam-5"
      And the epoch's bundle_id is unchanged
      And the epoch's row keys are unchanged

  Rule: Repeating a fit on identical pinned inputs reproduces the semantic payload; wall time is volatile (RWT-30)

    Scenario: Two fits into two registries agree on bundle_id and payload hash while recording their own wall time
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy E
      And the epoch starting 2016-03-01T00:00:00Z is trained again for policy E into a fresh registry
      Then both epochs have the same bundle_id
      And both epochs have the same hashes.model_sha256
      And both epochs have the same thresholds
      And both epochs record a published_at UTC instant and a non-negative training_duration_seconds
      And the volatile fields are outside the bundle_id

    Scenario: Training the same epoch twice into the same registry reuses the published artifact without rewriting it
      When the epoch starting 2016-03-01T00:00:00Z is trained for policy U
      And the published bundle's file bytes are remembered
      And the epoch starting 2016-03-01T00:00:00Z is trained again for policy U
      Then the second training reports the bundle as reused
      And the registry lists 1 published bundle
      And the published bundle's file bytes are unchanged
