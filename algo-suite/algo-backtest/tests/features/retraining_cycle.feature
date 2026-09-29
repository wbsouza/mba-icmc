Feature: The full adaptive-cycle coordinator (Story 19, T10)
  The coordinator runs the registered consume -> mature -> fit -> validate -> publish
  state machine exactly once per policy and boundary (RWT-25), checkpointing each
  completed stage so a retry resumes without refitting, recording every failed attempt
  with its failed stage (RWT-27), and never advancing the availability watermark or
  publishing anything a failed stage did not validate (RWT-23, RWT-26).

  A CycleRequest carries: policy, protocol_hash, cutoff (C), activation_boundary (D),
  source_watermark (the ledger watermark the requester built the request against;
  None for an empty ledger), prior_bundle_id (the previously active bundle, None for
  the first epoch), the source batches to consume, and the training settings. The
  cycle_id is the sha256 of the canonical JSON of (policy, protocol_hash, cutoff,
  activation_boundary, source_watermark, prior_bundle_id): content-addressed by the
  immutable inputs and the policy.

  On-disk records under the coordinator's directory:

      cycles/<cycle_id>/record.json     status, attempts (each with started/finished wall
                                        time, outcome, failed_stage, reason), completed
                                        stages, and the bundle_id once published
      cycles/<cycle_id>/checkpoints/    one file per completed stage (consume: the
                                        watermark reached; mature: mature/pending keys;
                                        fit: the staged model document + thresholds +
                                        provenance; validate: the validation report;
                                        publish: the bundle_id)

  Request handling order: (1) an existing successful record for this cycle_id returns
  its outcome without running any stage; (2) a successful record for the same policy
  and boundary under a different cycle_id is a conflict (the boundary already ran);
  (3) the ledger watermark must equal source_watermark, else the request is rejected
  at stage "consume" (watermark conflict); (4) stages run in order, each resumed from
  its checkpoint when one exists. The registered timeout is a wall-clock budget for one
  attempt measured on an injectable clock and checked at every stage boundary; an
  attempt over budget is recorded as failed with reason "timeout" at the stage that
  was running. A failed attempt raises to the caller after being recorded; replay must
  stop, it never falls back to another bundle. The activation boundary must be a UTC
  month start strictly after the cutoff; the published manifest's activation_boundary
  equals D (future-only), separately from the real publication wall time.

  The request/response exchange here is in-process (handle a request, get a response
  or a recorded failure); the native LEAN transport around it is T12's.

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
    And the trainer fixture batches "history-2015", "jan-2016", "feb-2016" and "mar-2016"
    And an empty coordinator directory with an empty registry and an empty ledger
    And a fake wall clock starting at 2026-09-28T10:00:00Z
    And a registered cycle timeout of 1800 seconds
    And the cycle request "first-U"
      | field               | value                              |
      | policy              | U                                  |
      | protocol_hash       | protocol-v1                        |
      | cutoff              | 2016-02-29T00:00:00Z               |
      | activation_boundary | 2016-03-01T00:00:00Z               |
      | source_watermark    | none                               |
      | prior_bundle_id     | none                               |
      | batches             | history-2015, jan-2016, feb-2016   |

  Rule: A complete cycle consumes, matures, fits, validates and publishes, then makes the bundle eligible (RWT-23, RWT-25, RWT-26)

    Scenario: The first cycle for policy U runs every stage once and publishes an eligible bundle
      Given LightGBM fits are observed
      When the cycle request "first-U" is handled
      Then the response status is "ok"
      And the response names a bundle_id
      And the response activation_boundary is 2016-03-01T00:00:00Z
      And the cycle record lists the completed stages "consume, mature, fit, validate, publish"
      And the cycle record has 1 attempt with outcome "ok"
      And the ledger watermark is 2016-02-25T00:00:00Z
      And the cycle's mature stage recorded 15 mature keys and 0 pending keys
      And 2 LightGBM fits were observed
      And the registry lists 1 published bundle
      And the eligible bundle for policy "U" at 2016-03-01T00:00:00Z is the response's bundle_id
      And the eligible bundle's manifest activation_boundary is 2016-03-01T00:00:00Z

    Scenario: The cycle's published manifest carries the simulated activation boundary separately from the real wall time
      When the cycle request "first-U" is handled
      Then the eligible bundle's manifest activation_boundary is 2016-03-01T00:00:00Z
      And the eligible bundle's manifest published_at is 2026-09-28T10:00:00Z by the fake clock
      And the eligible bundle's deployment span is [2016-03-01T00:00:00Z, 2016-04-01T00:00:00Z)
      And the cycle record's attempt started at 2026-09-28T10:00:00Z by the fake clock

    Scenario: A coordinator opened without an injected clock records the real wall-clock instant
      Given a coordinator with no injected clock
      When the cycle request "first-U" is handled
      Then the cycle record's attempt started within 5 minutes of the real wall-clock instant

  Rule: The cycle runs exactly once per policy and boundary (RWT-25)

    Scenario: Handling the identical request again is a no-op that returns the same artifact without refitting
      Given the cycle request "first-U" is handled
      And LightGBM fits are observed
      And the registry's file bytes are remembered
      When the cycle request "first-U" is handled again
      Then the response status is "ok"
      And both responses name the same bundle_id
      And 0 LightGBM fits were observed
      And the cycle record has 1 attempt with outcome "ok"
      And the registry lists 1 published bundle
      And the registry's file bytes are unchanged

    Scenario: A fresh coordinator on the same directories also treats the identical request as already done
      Given the cycle request "first-U" is handled
      And LightGBM fits are observed
      When a new coordinator is opened on the same directories and handles the cycle request "first-U"
      Then the response status is "ok"
      And both responses name the same bundle_id
      And 0 LightGBM fits were observed

    Scenario: A different request for a boundary that already ran for the policy is a conflict, not a second run
      Given the cycle request "first-U" is handled
      And the cycle request "first-U-v2" equals "first-U" except protocol_hash "protocol-v2"
      When handling the cycle request "first-U-v2" fails
      Then the cycle failure names "already"
      And the cycle failure names "2016-03-01T00:00:00Z"
      And the registry lists 1 published bundle
      And the cycle record of "first-U" still has 1 attempt with outcome "ok"

    Scenario: Different policies at the same boundary are independent cycles
      Given the cycle request "first-U" is handled
      And the cycle request "first-E" equals "first-U" except policy "E"
      When the cycle request "first-E" is handled
      Then the response status is "ok"
      And the registry lists 2 published bundles
      And the eligible bundle for policy "E" at 2016-03-01T00:00:00Z differs from the eligible bundle for policy "U"

  Rule: Pending labels stay out of the fit and are counted (RWT-24)

    Scenario: A row whose label matures after the cutoff is recorded as pending and fitted nowhere
      Given the batch "feb-2016" additionally carries the row "thr-pend" available 2016-02-28T20:00:00Z with label_time 2016-02-29T02:00:00Z and label 1
      When the cycle request "first-U" is handled
      Then the response status is "ok"
      And the cycle's mature stage recorded 15 mature keys and 1 pending keys
      And the cycle's pending keys are "thr-pend"
      And the fitted epoch's threshold row keys are "thr-1, thr-2, thr-3, thr-4, thr-5, thr-6"
      And the ledger watermark is 2016-02-28T20:00:00Z

  Rule: A request built against another data state is rejected before any stage (RWT-23)

    Scenario: A source watermark that disagrees with the ledger is a conflict recorded at the consume stage
      Given the cycle request "stale-U" equals "first-U" except source_watermark 2016-01-25T00:00:00Z
      When handling the cycle request "stale-U" fails
      Then the cycle failure names "watermark"
      And the cycle failure names "2016-01-25T00:00:00Z"
      And the cycle record of "stale-U" has 1 attempt with outcome "failed" at stage "consume"
      And the ledger watermark is none
      And the registry lists 0 published bundles

    Scenario: The watermark is checked only after the once-per-boundary lookup, so a completed cycle stays repeatable
      Given the cycle request "first-U" is handled
      Then the ledger watermark is 2016-02-25T00:00:00Z
      When the cycle request "first-U" is handled again
      Then the response status is "ok"
      And the cycle record has 1 attempt with outcome "ok"

  Rule: Failures are recorded with their stage, publish nothing and leave no eligible manifest (RWT-27)

    Scenario: A worker failure during the fit is recorded at stage fit and the boundary has no eligible bundle
      Given the LightGBM fit is made to raise "injected booster failure"
      When handling the cycle request "first-U" fails
      Then the cycle failure names "injected booster failure"
      And the cycle record has 1 attempt with outcome "failed" at stage "fit"
      And the cycle record's failed attempt reason names "injected booster failure"
      And the cycle record lists the completed stages "consume, mature"
      And the registry lists 0 published bundles
      And looking up the eligible bundle for policy "U" at 2016-03-01T00:00:00Z fails naming "failed"
      And looking up the eligible bundle for policy "U" at 2016-03-01T00:00:00Z fails naming "fit"

    Scenario: An attempt that exceeds the registered timeout is recorded as a failed attempt with reason timeout
      Given the fake wall clock advances 1801 seconds during the fit stage
      When handling the cycle request "first-U" fails
      Then the cycle failure names "timeout"
      And the cycle failure names "1800"
      And the cycle record has 1 attempt with outcome "failed" at stage "fit"
      And the cycle record's failed attempt reason names "timeout"
      And the registry lists 0 published bundles
      And looking up the eligible bundle for policy "U" at 2016-03-01T00:00:00Z fails naming "failed"

    Scenario: An attempt that lands exactly on the registered timeout budget is not over budget
      Given the fake wall clock advances 900 seconds during the fit stage
      When the cycle request "first-U" is handled
      Then the response status is "ok"
      And the cycle record has 1 attempt with outcome "ok"

    Scenario: A validation failure leaves no eligible manifest and no published bundle
      Given the staged model is corrupted before the validate stage
      When handling the cycle request "first-U" fails
      Then the cycle failure names "validat"
      And the cycle record has 1 attempt with outcome "failed" at stage "validate"
      And the cycle record lists the completed stages "consume, mature, fit"
      And the registry lists 0 published bundles
      And no manifest.json exists in the registry outside a staging directory
      And looking up the eligible bundle for policy "U" at 2016-03-01T00:00:00Z fails naming "validate"

    Scenario: Looking up the eligible bundle for a boundary that never had a cycle run fails naming that nothing is eligible
      Then looking up the eligible bundle for policy "Q" at 2016-03-01T00:00:00Z fails naming "no cycle recorded"
      And looking up the eligible bundle for policy "Q" at 2016-03-01T00:00:00Z fails naming "nothing is eligible"

  Rule: A retry resumes from the last checkpointed stage without refitting (RWT-27 recovery)

    Scenario: A publish-stage crash is retried from the fit checkpoint and completes without a second fit
      Given the atomic rename of the staged bundle is made to fail
      And LightGBM fits are observed
      When handling the cycle request "first-U" fails
      Then the cycle record has 1 attempt with outcome "failed" at stage "publish"
      And the cycle record lists the completed stages "consume, mature, fit, validate"
      And 2 LightGBM fits were observed
      And the registry lists 0 published bundles
      When the atomic rename works again and the cycle request "first-U" is handled
      Then the response status is "ok"
      And 2 LightGBM fits were observed
      And the cycle record has 2 attempts, the first "failed" at stage "publish" and the second "ok"
      And the cycle record lists the completed stages "consume, mature, fit, validate, publish"
      And the registry lists 1 published bundle
      And the eligible bundle for policy "U" at 2016-03-01T00:00:00Z is the response's bundle_id

    Scenario: A fit-stage failure is retried from the mature checkpoint: the batches are not consumed twice
      Given the LightGBM fit is made to raise "injected booster failure"
      And handling the cycle request "first-U" fails
      And the ledger's file bytes are remembered
      When the LightGBM fit works again and the cycle request "first-U" is handled
      Then the response status is "ok"
      And the ledger's file bytes are unchanged
      And the cycle record has 2 attempts, the first "failed" at stage "fit" and the second "ok"

    Scenario: A timeout right after the publish checkpoint is written is retried, resuming from the publish checkpoint itself
      Given the fake wall clock advances 1801 seconds when the bundle is renamed into the registry
      When handling the cycle request "first-U" fails
      Then the cycle failure names "timeout"
      And the cycle record has 1 attempt with outcome "failed" at stage "publish"
      And the cycle record lists the completed stages "consume, mature, fit, validate, publish"
      And the registry lists 1 published bundle
      When the cycle request "first-U" is handled
      Then the response status is "ok"
      And the cycle record has 2 attempts, the first "failed" at stage "publish" and the second "ok"
      And the cycle record lists the completed stages "consume, mature, fit, validate, publish"
      And the registry lists 1 published bundle
      And the eligible bundle for policy "U" at 2016-03-01T00:00:00Z is the response's bundle_id
      And the response's bundle_id is actually present in the registry

  Rule: Activation is future-only: the boundary is a month start strictly after the cutoff (RWT-26)

    Scenario Outline: An activation boundary that is not a month start after the cutoff is rejected before any stage (<case>)
      Given the cycle request "bad-D" equals "first-U" except activation_boundary <boundary>
      When handling the cycle request "bad-D" fails
      Then the cycle failure names "activation"
      And the cycle failure names "<fragment>"
      And the ledger watermark is none
      And the registry lists 0 published bundles

      Examples:
        | case                                | boundary             | fragment    |
        | boundary equal to the cutoff        | 2016-02-29T00:00:00Z | after       |
        | boundary before the cutoff          | 2016-02-01T00:00:00Z | after       |
        | boundary not a month start          | 2016-03-02T00:00:00Z | month start |
        | boundary outside the schedule       | 2017-03-01T00:00:00Z | registered  |

    Scenario: The second boundary's cycle names the prior bundle and activates only from its own boundary
      Given the cycle request "first-U" is handled
      And the cycle request "second-U"
        | field               | value                        |
        | policy              | U                            |
        | protocol_hash       | protocol-v1                  |
        | cutoff              | 2016-03-31T00:00:00Z         |
        | activation_boundary | 2016-04-01T00:00:00Z         |
        | source_watermark    | 2016-02-25T00:00:00Z         |
        | prior_bundle_id     | the bundle_id of "first-U"   |
        | batches             | mar-2016                     |
      When the cycle request "second-U" is handled
      Then the response status is "ok"
      And the response activation_boundary is 2016-04-01T00:00:00Z
      And the ledger watermark is 2016-03-26T00:00:00Z
      And the registry lists 2 published bundles
      And the eligible bundle for policy "U" at 2016-03-01T00:00:00Z is unchanged
      And the eligible bundle for policy "U" at 2016-04-01T00:00:00Z differs from the eligible bundle at 2016-03-01T00:00:00Z
      And the eligible bundle's manifest activation_boundary is 2016-04-01T00:00:00Z
