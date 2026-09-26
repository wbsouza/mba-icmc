Feature: Strategy parameter validation
  validate_run_inputs gates a run before any container starts: the strategy must be known,
  the window ordered, and the strategy's own parameters present, well-typed and in range.
  Each registered strategy owns a closed parameter set. `baseline-ma`/`baseline-meanrev`
  are price-only baselines; `buyhold`/`random`/`perfect_foresight` (Spec 04h, docs/
  experiments.md #0) are the engine-sanity-check strategies — none here claims a news/
  sentiment signal.

  Rule: Each strategy accepts its own valid parameters

    Scenario: baseline-ma accepts fast below slow and a valid size
      Given strategy "baseline-ma" with params fast=3 slow=8 size=0.5
      When I validate the run inputs
      Then validation passes

    Scenario: baseline-meanrev accepts a window, a positive band and a valid size
      Given strategy "baseline-meanrev" with params window=20 band=0.001 size=0.5
      When I validate the run inputs
      Then validation passes

    Scenario: buyhold accepts a valid size
      Given strategy "buyhold" with params size=0.5
      When I validate the run inputs
      Then validation passes

    Scenario: random accepts a valid size and seed
      Given strategy "random" with params size=0.5 seed=42
      When I validate the run inputs
      Then validation passes

    Scenario: perfect_foresight accepts a valid size
      Given strategy "perfect_foresight" with params size=0.5
      When I validate the run inputs
      Then validation passes

  Rule: An unknown strategy or invalid parameters are rejected (fail fast)

    Scenario: an unknown strategy is rejected
      Given strategy "bogus" with params size=0.5
      When I validate the run inputs expecting failure
      Then validation fails naming the unknown strategy

    Scenario: params that are not the strategy's exact set are rejected
      Given strategy "baseline-meanrev" with params fast=3 slow=8 size=0.5
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set

    Scenario: buyhold rejects an out-of-range size
      Given strategy "buyhold" with params size=1.5
      When I validate the run inputs expecting failure
      Then validation fails naming "size"

    Scenario: random rejects a non-integer seed
      Given strategy "random" with params size=0.5 seed=notanumber
      When I validate the run inputs expecting failure
      Then validation fails naming "seed"

    Scenario: baseline-meanrev with a non-positive band is rejected
      Given strategy "baseline-meanrev" with params window=20 band=0 size=0.5
      When I validate the run inputs expecting failure
      Then validation fails saying the band must be positive

    Scenario: baseline-meanrev with a too-small window is rejected
      Given strategy "baseline-meanrev" with params window=1 band=0.001 size=0.5
      When I validate the run inputs expecting failure
      Then validation fails saying the window must be at least 2
