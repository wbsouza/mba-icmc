Feature: Strategy parameter validation
  validate_run_inputs gates a run before any container starts: the strategy must be known,
  the window ordered, and the strategy's own parameters present, well-typed and in range.
  Each registered strategy owns a closed parameter set. `baseline-ma`/`baseline-meanrev`
  are price-only baselines; `buyhold`/`random`/`perfect_foresight` (Spec 04h, docs/
  experiments.md #0) are the engine-sanity-check strategies — none here claims a news/
  sentiment signal. Every strategy, code-registered or YAML-resolved, takes `cash` — the
  account's starting deposit (story 12, TD-65) — so a control and a chain strategy can be
  compared from the same deposit. Every behaviour parameter is external: `random`'s
  per-bar entry/exit probabilities and its long/short split are run parameters too, never
  literals in the algorithm. The chain strategies take nothing but `cash`: F6's trade plan
  sizes every order (story 12, item D), so `size` is a control-only parameter.

  Rule: Each strategy accepts its own closed parameter set, cash included

    Scenario Outline: <strategy> accepts <params>
      Given strategy "<strategy>" with params <params>
      When I validate the run inputs
      Then validation passes

      Examples: the code-registered baselines and engine controls
        | strategy          | params                                 |
        | baseline-ma       | fast=3 slow=8 size=0.5 cash=10000      |
        | baseline-meanrev  | window=20 band=0.001 size=0.5 cash=10000 |
        | buyhold           | size=0.5 cash=10000                    |
        | random            | size=0.5 seed=42 cash=10000 entry_probability=0.02 exit_probability=0.05 long_probability=0.5 |
        | perfect_foresight | size=0.5 cash=10000                    |
        | buyhold           | size=1 cash=250.5                      |
        | random            | size=0.5 seed=-7 cash=0.5 entry_probability=1 exit_probability=1 long_probability=0 |
        | random            | size=0.5 seed=7 cash=10000 entry_probability=0.5 exit_probability=0.5 long_probability=1 |

      Examples: the config.yaml chain strategies take cash alone
        | strategy      | params     |
        | baseline      | cash=10000 |
        | baseline-dsha | cash=10000 |
        | hybrid        | cash=10000 |
        | baseline      | cash=250.5 |
        | baseline      | cash=0.5   |

  Rule: An unknown strategy or invalid parameters are rejected (fail fast)

    Scenario: an unknown strategy is rejected
      Given strategy "bogus" with params size=0.5 cash=10000
      When I validate the run inputs expecting failure
      Then validation fails naming the unknown strategy

    Scenario: params that are not the strategy's exact set are rejected
      Given strategy "baseline-meanrev" with params fast=3 slow=8 size=0.5 cash=10000
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set

    Scenario Outline: <strategy> rejects a non-positive or non-numeric starting cash (<params>)
      Given strategy "<strategy>" with params <params>
      When I validate the run inputs expecting failure
      Then validation fails naming "cash"
      And validation fails naming "<strategy>"

      Examples: the code-registered baselines and engine controls
        | strategy          | params                                |
        | baseline-ma       | fast=3 slow=8 size=0.5 cash=0         |
        | baseline-meanrev  | window=20 band=0.001 size=0.5 cash=-1 |
        | buyhold           | size=0.5 cash=0                       |
        | random            | size=0.5 seed=42 cash=lots entry_probability=0.02 exit_probability=0.05 long_probability=0.5 |
        | perfect_foresight | size=0.5 cash=-100                    |

      Examples: the config.yaml chain strategies
        | strategy      | params    |
        | baseline      | cash=0    |
        | baseline      | cash=-100 |
        | hybrid        | cash=lots |
        | baseline-dsha | cash=0    |

    Scenario Outline: <strategy> without a starting cash is rejected as an incomplete param set
      Given strategy "<strategy>" with params <params>
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set
      And validation fails naming "cash"

      Examples:
        | strategy          | params                        |
        | baseline-ma       | fast=3 slow=8 size=0.5        |
        | baseline-meanrev  | window=20 band=0.001 size=0.5 |
        | buyhold           | size=0.5                      |
        | random            | size=0.5 seed=42 entry_probability=0.02 exit_probability=0.05 long_probability=0.5 |
        | perfect_foresight | size=0.5                      |

    Scenario: a chain strategy with no params at all is rejected naming the missing cash
      Given strategy "baseline" with no params
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set
      And validation fails naming "cash"

    Scenario Outline: the chain strategies reject a size param — F6's trade plan sizes the trade (<strategy>)
      Given strategy "<strategy>" with params size=<size> cash=10000
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set
      And validation fails naming "size"
      And validation fails naming "<strategy>"

      Examples:
        | strategy      | size |
        | baseline      | 0.5  |
        | hybrid        | 1    |
        | baseline-dsha | 0.25 |

    Scenario: buyhold rejects an out-of-range size
      Given strategy "buyhold" with params size=1.5 cash=10000
      When I validate the run inputs expecting failure
      Then validation fails naming "size"

    Scenario: random rejects a non-integer seed
      Given strategy "random" with params size=0.5 seed=notanumber cash=10000 entry_probability=0.02 exit_probability=0.05 long_probability=0.5
      When I validate the run inputs expecting failure
      Then validation fails naming "seed"

    Scenario Outline: random rejects an out-of-range or non-numeric <param> (<value>)
      Given strategy "random" with params size=0.5 seed=42 cash=10000 <params>
      When I validate the run inputs expecting failure
      Then validation fails naming "<param>"
      And validation fails naming "random"

      Examples: entry/exit probabilities must be in (0, 1]
        | param             | value  | params                                                              |
        | entry_probability | 0      | entry_probability=0 exit_probability=0.05 long_probability=0.5      |
        | entry_probability | 1.5    | entry_probability=1.5 exit_probability=0.05 long_probability=0.5    |
        | exit_probability  | 0      | entry_probability=0.02 exit_probability=0 long_probability=0.5      |
        | exit_probability  | often  | entry_probability=0.02 exit_probability=often long_probability=0.5  |

      Examples: the long/short split must be in [0, 1]
        | param            | value | params                                                            |
        | long_probability | -0.1  | entry_probability=0.02 exit_probability=0.05 long_probability=-0.1 |
        | long_probability | 1.1   | entry_probability=0.02 exit_probability=0.05 long_probability=1.1  |

    Scenario Outline: random without <param> is rejected as an incomplete param set
      Given strategy "random" with params size=0.5 seed=42 cash=10000 <params>
      When I validate the run inputs expecting failure
      Then validation fails saying the params must be exactly the strategy's set
      And validation fails naming "<param>"

      Examples:
        | param             | params                                        |
        | entry_probability | exit_probability=0.05 long_probability=0.5    |
        | exit_probability  | entry_probability=0.02 long_probability=0.5   |
        | long_probability  | entry_probability=0.02 exit_probability=0.05  |

    Scenario: baseline-meanrev with a non-positive band is rejected
      Given strategy "baseline-meanrev" with params window=20 band=0 size=0.5 cash=10000
      When I validate the run inputs expecting failure
      Then validation fails saying the band must be positive

    Scenario: baseline-meanrev with a too-small window is rejected
      Given strategy "baseline-meanrev" with params window=1 band=0.001 size=0.5 cash=10000
      When I validate the run inputs expecting failure
      Then validation fails saying the window must be at least 2

  Rule: The run window is inclusive on both ends

    Scenario: a single-day window (from equals to) is accepted
      Given strategy "buyhold" with params size=0.5 cash=10000
      When I validate the run inputs for the window 2014-05-07 to 2014-05-07
      Then validation passes

    Scenario: a from-date after the to-date is rejected
      Given strategy "buyhold" with params size=0.5 cash=10000
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
      | params               |
      | wrong=0.5 cash=10000 |
      | cash=wrong           |
      | size=0.5 cash=10000  |

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
        | the mismatch names the strategy        | {ema_fast: 5}          | expecting failure | validation fails naming "but strategy 'baseline' declares" |
        | invalid provenance names the model     | {ema_fast: 0}          | expecting failure | validation fails naming "strategy 'model model.json': price_features.ema_fast must be a positive integer" |
        | non-mapping provenance counts as defaults | scalar              | passes            | validation passes                         |

    Scenario Outline: the model's label horizon must match the strategy's (<case>)
      Given a baseline-family model file trained with a <horizon>-minute label horizon
      When I validate the run inputs for strategy "baseline" with that model <outcome>
      Then <assertion>

      Examples:
        | case             | horizon | outcome           | assertion |
        | matching horizon | 15      | passes            | validation passes |
        | longer horizon   | 30      | expecting failure | validation fails naming "trained with a 30-minute label horizon but strategy 'baseline' declares meta_learner.label_horizon_minutes=15" |

    Scenario Outline: a model whose families differ from the strategy's fails naming the model file (<case>)
      Given a baseline-family model file whose families are "<families>"
      When I validate the run inputs for strategy "baseline" with that model expecting failure
      Then validation fails naming "model.json"

      Examples:
        | case            | families                        |
        | one family only | trend                           |
        | extra family    | trend, indicator, pattern, news |

    Scenario: a model path that is not a file fails fast before any container starts
      Given a baseline-family model path that does not exist
      When I validate the run inputs for strategy "baseline" with that model expecting failure
      Then validation fails naming "is not a file"

    Scenario: --model is rejected for a strategy without an F7 model
      Given a baseline-family model file whose provenance price_features is {ema_fast: 3}
      And strategy "buyhold" with params size=0.5 cash=10000
      When I validate the run inputs for strategy "buyhold" with that model expecting failure
      Then validation fails naming "--model only applies to the config.yaml chain strategies, not 'buyhold'"

    Scenario Outline: model provenance vs strategy label horizon and provenance shape (<case>)
      Given a baseline-family model file whose provenance strategy_config is <strategy_config> and horizon_minutes is <horizon>
      When I validate the run inputs for strategy "baseline" with that model <outcome>
      Then <assertion>

      Examples:
        | case                                            | strategy_config | horizon | outcome           | assertion                               |
        | identical label horizon                         | {}              | 15      | passes            | validation passes                       |
        | different label horizon                         | {}              | 30      | expecting failure | validation fails naming "label horizon" |
        | legacy provenance without a strategy_config     | null            | 15      | passes            | validation passes                       |
        | legacy provenance with a scalar strategy_config | pre-story-09    | 15      | passes            | validation passes                       |

  Rule: Chain strategies are resolved from their YAML, not from a code registry (2026-09-27)
    A new `strategies/<name>/config.yaml` — bundled or in an external `--strategies-dir` —
    runs without a code change. The YAML decides which LEAN algorithm hosts it (F4 listed →
    the news-aware one, with the news Parquet mounted) and always takes cash alone.

    Scenario Outline: a YAML variant in an external directory resolves from its filters (<name>)
      Given an external strategies directory holding "<name>" extending "<base>" with extra "<extra_yaml>"
      When strategy "<name>" is resolved from that directory
      Then the resolved strategy runs on algorithm "<algo_dir>" with news data <news>
      And validating strategy "<name>" with params cash=10000 from that directory passes

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
      And the resolution failure names the external strategies directory
