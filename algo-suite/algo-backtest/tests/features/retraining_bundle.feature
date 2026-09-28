Feature: Immutable epoch bundles (Story 19, T7)
  An epoch bundle wraps one portable F7 model document (f7_model_io, pickle-free) in a
  validated, content-addressed, immutable artifact with its complete provenance
  (RWT-11) and refuses anything missing, corrupt, conflicting or incompatible
  (RWT-15). One registry directory holds many bundles:

      <registry>/<bundle_id>/manifest.json     the manifest (provenance + identity)
      <registry>/<bundle_id>/model.json        the f7_model_io document

  Identity. `model_sha256` is the sha256 of `model.json`'s bytes: the SEMANTIC MODEL
  PAYLOAD HASH (RWT-30). `bundle_id` is the sha256 of the canonical JSON (sorted keys,
  no whitespace) of every manifest field except the volatile ones. The volatile fields
  are `published_at` (real wall-clock UTC instant), `training_duration_seconds` and
  `host`; they are recorded but sit outside the identity, so two publications of the
  same content at different wall times have the same `bundle_id`. Simulated instants
  (`activation_boundary`, every span bound, `ledger_watermark`) are identity fields.

  Manifest fields (design.md "EpochBundle"; every one is required, none may be null):

      | field                      | identity | meaning                                              |
      | schema_version             | yes      | 1                                                    |
      | policy                     | yes      | F, Q, R, U or E                                      |
      | seed                       | yes      | 42                                                   |
      | families                   | yes      | ordered feature-family names, as the model was fitted |
      | spans.family               | yes      | start/end, half-open UTC                             |
      | spans.combiner             | yes      | start/end                                            |
      | spans.threshold            | yes      | start/end                                            |
      | spans.deployment           | yes      | start/end                                            |
      | activation_boundary        | yes      | the simulated instant from which the bundle may act  |
      | ledger_watermark           | yes      | the ingestion watermark the fit was prepared against |
      | stages.family              | yes      | weighting, half_life_days, rows, per_class, n_eff, raw_weight_min, raw_weight_max |
      | stages.combiner            | yes      | same keys as stages.family                           |
      | stages.threshold           | yes      | rows                                                 |
      | thresholds                 | yes      | theta_low, theta_high                                |
      | hashes.model_sha256        | yes      | sha256 of model.json bytes (semantic payload)        |
      | hashes.rows_sha256         | yes      | sha256 of the ordered stage row keys                 |
      | hashes.data_sha256         | yes      | sha256 over the consumed partitions' identities      |
      | hashes.config_sha256       | yes      | sha256 of the resolved strategy configuration        |
      | hashes.protocol_sha256     | yes      | sha256 of the frozen protocol document               |
      | runtime                    | yes      | python, lightgbm, scikit-learn, numpy versions       |
      | published_at               | no       | real UTC wall-clock instant of publication           |
      | training_duration_seconds  | no       | real elapsed fitting time                            |
      | host                       | no       | machine identifier                                   |

  Publication is atomic: the bundle is written into a staging directory named
  `.staging-<bundle_id>-<nonce>` inside the registry, validated there (the model is
  reloaded from the staged bytes and must reproduce the in-memory model's p_hat on the
  bundle's probe rows; the checksums are recomputed), then renamed to `<bundle_id>` in
  one rename. Anything that fails before the rename leaves no published bundle; a
  staging directory may remain and is never listed as a bundle. Publishing content that
  is already published returns the existing artifact untouched (identical reuse);
  content whose identity exists on disk with different bytes is a conflict and is
  never repaired or overwritten.

  Background:
    Given a meta-learner trained on seeded synthetic rows with the trend and indicator families
    And an empty bundle registry directory
    And a bundle description for policy "U" with thresholds theta_low 0.45 and theta_high 0.55 and activation boundary 2016-03-01T00:00:00Z

  Rule: A published bundle reloads into a model that predicts exactly what was published (RWT-11)

    Scenario: Round-tripping a bundle preserves every prediction, the thresholds and the family order
      When the bundle is published
      And the bundle is loaded from the registry by its id
      Then the loaded model's p_hat matches the published model's on every probe row
      And the loaded thresholds are theta_low 0.45 and theta_high 0.55
      And the loaded families are "trend, indicator" in that order
      And the loaded model carries no scikit-learn or pickled object

    Scenario: The manifest is complete: every required field is present and non-null
      When the bundle is published
      Then the registry lists 1 published bundle
      And the published manifest contains every required field
        | field                      |
        | schema_version             |
        | bundle_id                  |
        | policy                     |
        | seed                       |
        | families                   |
        | spans.family               |
        | spans.combiner             |
        | spans.threshold            |
        | spans.deployment           |
        | activation_boundary        |
        | ledger_watermark           |
        | stages.family              |
        | stages.combiner            |
        | stages.threshold           |
        | thresholds                 |
        | hashes.model_sha256        |
        | hashes.rows_sha256         |
        | hashes.data_sha256         |
        | hashes.config_sha256       |
        | hashes.protocol_sha256     |
        | runtime                    |
        | published_at               |
        | training_duration_seconds  |
        | host                       |
      And the manifest's schema_version is 1
      And the manifest's policy is "U"
      And the manifest's seed is 42
      And the manifest's activation_boundary is 2016-03-01T00:00:00Z
      And the manifest's published_at is a UTC instant with a Z suffix
      And the manifest's runtime names the installed lightgbm, scikit-learn and numpy versions

    Scenario: The bundle id and the semantic payload hash are content-addressed
      When the bundle is published
      Then the manifest's hashes.model_sha256 equals the sha256 of the published model.json bytes
      And the manifest's bundle_id equals the sha256 of the canonical manifest without its volatile fields
      And the published bundle directory is named after the bundle_id

  Rule: Identical content is reused; a colliding identity with different bytes is a conflict

    Scenario: Publishing identical content a second time, at a later wall time, returns the same artifact untouched
      Given the bundle is published
      And the published bundle's file bytes are remembered
      When the same bundle description is published again 1 hour of wall time later
      Then the second publication reports the bundle as reused
      And both publications have the same bundle_id
      And the registry lists 1 published bundle
      And the published bundle's file bytes are unchanged

    Scenario: A bundle id already on disk with different model bytes is a conflict and is left as found
      Given the bundle is published
      And the published model.json is overwritten on disk with different bytes
      And the published bundle's file bytes are remembered
      When publishing the same bundle description fails
      Then the bundle failure names "conflict"
      And the bundle failure names the bundle_id
      And the published bundle's file bytes are unchanged
      And the registry lists 1 published bundle

    Scenario: Two descriptions that differ only in the policy label are two bundles with one semantic payload
      Given the bundle is published
      When the same bundle description is published again for policy "F"
      Then the registry lists 2 published bundles
      And the two bundles have different bundle_ids
      And the two bundles have the same hashes.model_sha256

  Rule: Missing, corrupt, unknown or incompatible bundles are refused explicitly (RWT-15)

    Scenario: Loading an id that is not in the registry fails naming the id and the registry
      When loading the bundle "0000000000000000000000000000000000000000000000000000000000000000" from the registry fails
      Then the bundle failure names "missing"
      And the bundle failure names "0000000000000000000000000000000000000000000000000000000000000000"

    Scenario: A corrupt model file is rejected by its checksum, not silently loaded
      Given the bundle is published
      And one byte of the published model.json is flipped on disk
      When loading the published bundle fails
      Then the bundle failure names "sha256"
      And the bundle failure names the bundle_id

    Scenario: A manifest whose bundle_id does not match its content is rejected
      Given the bundle is published
      And the published manifest's policy field is edited on disk to "E"
      When loading the published bundle fails
      Then the bundle failure names "bundle_id"

    Scenario: An unknown manifest schema version is rejected naming the version
      Given the bundle is published
      And the published manifest's schema_version is edited on disk to 99
      When loading the published bundle fails
      Then the bundle failure names "schema_version"
      And the bundle failure names "99"

    Scenario Outline: A manifest missing a required field is rejected naming the field (<field>)
      Given the bundle is published
      And the published manifest's field "<field>" is removed on disk
      When loading the published bundle fails
      Then the bundle failure names "<field>"

      Examples:
        | field                 |
        | thresholds            |
        | hashes.model_sha256   |
        | spans.deployment      |
        | activation_boundary   |
        | stages.family         |

    Scenario: Manifest families that disagree with the model document's families are incompatible
      Given the bundle is published
      And the published manifest's families are edited on disk to "trend, indicator, pattern" with the bundle_id recomputed
      When loading the published bundle fails
      Then the bundle failure names "families"

    Scenario: A bundle is refused for a strategy that declares other families
      Given the bundle is published
      When loading the published bundle for the strategy families "trend, indicator, pattern" fails
      Then the bundle failure names "meta_learner.families"
      And the bundle failure names "trend"

    Scenario: Non-increasing thresholds are refused at publication
      Given a bundle description for policy "U" with thresholds theta_low 0.55 and theta_high 0.55 and activation boundary 2016-03-01T00:00:00Z
      When publishing the bundle fails
      Then the bundle failure names "theta_low"
      And the registry lists 0 published bundles

  Rule: An interrupted publication leaves no published bundle (temp file + atomic rename)

    Scenario: A failure between writing the staged files and the atomic rename publishes nothing and is recoverable
      Given the atomic rename of the staged bundle is made to fail
      When publishing the bundle fails
      Then the bundle failure names "rename"
      And the registry lists 0 published bundles
      And no manifest.json exists in the registry outside a staging directory
      And loading the bundle by its would-be id fails naming "missing"
      When the atomic rename works again and the bundle is published
      Then the registry lists 1 published bundle
      And the bundle is loaded from the registry by its id

    Scenario: A staged bundle that fails validation is never renamed into the registry
      Given the staged model.json is corrupted before validation
      When publishing the bundle fails
      Then the bundle failure names "validat"
      And the registry lists 0 published bundles
      And no manifest.json exists in the registry outside a staging directory

    Scenario: Staging directories are never listed as bundles
      Given a leftover staging directory in the registry
      When the bundle is published
      Then the registry lists 1 published bundle
      And the leftover staging directory is not the listed bundle
