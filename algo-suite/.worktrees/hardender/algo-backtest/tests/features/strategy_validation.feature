Feature: Strategy parameter validation
  validate_run_inputs gates a run before any container starts: the strategy must be known,
  the window ordered, and the strategy's own parameters present, well-typed and in range.
  Each registered strategy owns a closed parameter set. These are all price-only baselines —
  no strategy here claims a news/sentiment signal.

  Rule: Each strategy accepts its own valid parameters

    Scenario: baseline-ma accepts fast below slow and a valid size
      Given strategy "baseline-ma" with params fast=3 slow=8 size=0.5
      When I validate the run inputs
      Then validation passes

    Scenario: baseline-meanrev accepts a window, a positive band and a valid size
      Given strategy "baseline-meanrev" with params window=20 band=0.001 size=0.5
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

    Scenario: baseline-meanrev with a non-positive band is rejected
      Given strategy "baseline-meanrev" with params window=20 band=0 size=0.5
      When I validate the run inputs expecting failure
      Then validation fails saying the band must be positive

    Scenario: baseline-meanrev with a too-small window is rejected
      Given strategy "baseline-meanrev" with params window=1 band=0.001 size=0.5
      When I validate the run inputs expecting failure
      Then validation fails saying the window must be at least 2
