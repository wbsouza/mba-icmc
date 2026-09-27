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

    Scenario Outline: the chain strategies accept a valid size and a positive starting cash (<strategy>)
      Given strategy "<strategy>" with params size=0.5 cash=<cash>
      When I validate the run inputs
      Then validation passes

      Examples:
        | strategy      | cash   |
        | baseline      | 10000  |
        | baseline-dsha | 10000  |
        | hybrid        | 10000  |
        | baseline      | 250.5  |
        | baseline      | 0.5    |

  Rule: An unknown strategy or invalid parameters are rejected (fail fast)

    Scenario: an unknown strategy is rejected
      Given strategy "bogus" with params size=0.5
      When I validate the run inputs expecting failure
      Then validation fails naming the unknown strategy

    Scenario: params that are not the strategy's exact set are rejected
      Given strategy "baseline-meanrev" with params fast=3 slow=8 size=0.5
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set

    Scenario Outline: the chain strategies reject a non-positive or non-numeric starting cash (<strategy>, cash=<cash>)
      Given strategy "<strategy>" with params size=0.5 cash=<cash>
      When I validate the run inputs expecting failure
      Then validation fails naming "cash"
      And validation fails naming "<strategy>"

      Examples:
        | strategy      | cash  |
        | baseline      | 0     |
        | baseline      | -100  |
        | hybrid        | lots  |
        | baseline-dsha | 0     |

    Scenario Outline: the chain strategies reject an out-of-range size naming the strategy (<strategy>)
      Given strategy "<strategy>" with params size=<size> cash=10000
      When I validate the run inputs expecting failure
      Then validation fails naming "size"
      And validation fails naming "<strategy>"

      Examples:
        | strategy      | size |
        | baseline      | 1.5  |
        | hybrid        | 0    |
        | baseline-dsha | -0.1 |

    Scenario: a chain strategy without a starting cash is rejected as an incomplete param set
      Given strategy "baseline" with params size=0.5
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

  Rule: The run window is inclusive on both ends

    Scenario: a single-day window (from equals to) is accepted
      Given strategy "buyhold" with params size=0.5
      When I validate the run inputs for the window 2014-05-07 to 2014-05-07
      Then validation passes

    Scenario: a from-date after the to-date is rejected
      Given strategy "buyhold" with params size=0.5
      When I validate the run inputs for the window 2014-05-08 to 2014-05-07 expecting failure
      Then validation fails naming "must not be after"

    Scenario Outline: lean-data coverage counts a day-zip on the window's <edge> day
      Given materialized lean-data day-zips for EURUSD on <days>
      Then lean-data covers 2014-05-07 to 2014-05-09 is <covered>

      Examples:
        | edge            | days                   | covered |
        | last            | 20140509               | true    |
        | first           | 20140507               | true    |
        | day after last  | 20140510               | false   |
        | day before first| 20140506               | false   |

  Scenario Outline: DSHA validation failures identify the requested strategy
    Given strategy "baseline-dsha" with params <params>
    When I validate the run inputs expecting failure
    Then validation fails naming "baseline-dsha"

    Examples:
      | params       |
      | wrong=0.5    |
      | size=wrong   |
      | size=1.5     |

  Rule: A model must have been trained on the strategy's price-feature parameters

    Scenario Outline: model provenance vs strategy price_features (<case>)
      Given a baseline-family model file whose provenance price_features is <provenance>
      When I validate the run inputs for strategy "baseline" with that model <outcome>
      Then <assertion>

      Examples:
        | case                                   | provenance             | outcome           | assertion                                 |
        | identical periods                      | {ema_fast: 3}          | passes            | validation passes                         |
        | pre-amendment model without the key    | absent                 | passes            | validation passes                         |
        | different fast EMA                     | {ema_fast: 5}          | expecting failure | validation fails naming "price_features"  |
        | different RSI period                   | {rsi_period: 21}       | expecting failure | validation fails naming "rsi_period"      |

  Rule: Chain strategies are resolved from their YAML, not from a code registry (2026-09-27)
    A new `strategies/<name>/config.yaml` — bundled or in an external `--strategies-dir` —
    runs without a code change. The YAML decides which LEAN algorithm hosts it (F4 listed →
    the news-aware one, with the news Parquet mounted) and always takes size + cash.

    Scenario Outline: a YAML variant in an external directory resolves from its filters (<name>)
      Given an external strategies directory holding "<name>" extending "<base>" with extra "<extra_yaml>"
      When strategy "<name>" is resolved from that directory
      Then the resolved strategy runs on algorithm "<algo_dir>" with news data <news>
      And validating strategy "<name>" with params size=0.5 cash=10000 from that directory passes

      Examples:
        | name    | base     | extra_yaml                                      | algo_dir | news  |
        | tight   | baseline | {meta_learner: {theta_high: 0.6, theta_low: 0.4}} | baseline | false |
        | newsy   | hybrid   | {news_context: {event_intensity_veto_threshold: -2.0}} | hybrid | true |

    Scenario: the bundled strategies still resolve without any directory
      When strategy "hybrid" is resolved from the bundled directory
      Then the resolved strategy runs on algorithm "hybrid" with news data true

    Scenario: an unknown name names the registry, the bundled directory and the external one
      Given an external strategies directory holding "tight" extending "baseline" with extra "{}"
      When resolving strategy "nope" from that directory fails
      Then the resolution failure names "nope"
      And the resolution failure names "buyhold"
      And the resolution failure names "tight"
