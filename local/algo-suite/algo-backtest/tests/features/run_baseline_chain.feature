Feature: Run the F1-F7 baseline chain via the run CLI (wiring smoke test)
  `algo-backtest run --strategy baseline` wires the config.yaml-driven F1+F2+F3+F5+F6+F7
  chain (no F4/news) into a real LEAN algorithm for the first time (2026-09-26). This is
  a wiring smoke test, not a methodology result -- see technical-debt.md's TD-51 and
  docs/stories/done/2026-09-26-04h-algo-backtest-hybrid-integration/progress.md: F3's
  candlestick-pattern feature is never populated (no real detector), F5/F6's
  account-risk features use fixed placeholder economics (no real ATR/margin model), and
  F7's meta-learner is trained on a short window by
  scripts/train_baseline_meta_learner.py, not a statistically meaningful model.

  Rule: Inputs are validated before any container starts

    Scenario: a size param is rejected — F6's trade plan sizes the position (story 12)
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param size=0.5 --param cash=10000"
      Then the run command exits with code 2
      And the error says params must be exactly
      And the error names "size"

    Scenario: a non-positive starting cash is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param cash=0"
      Then the run command exits with code 2
      And the error says cash must be positive

    Scenario: a model trained for hybrid is rejected for baseline before any container starts
      When I run baseline with the bundled hybrid model as --model
      Then the run command exits with code 2
      And the error names the model's families and the strategy's declared families

    Scenario: an unknown param is rejected
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param cash=10000 --param bogus=1"
      Then the run command exits with code 2
      And the error says params must be exactly

  Rule: The execution bootstrap prints every strategy parameter and its source

    Scenario Outline: parameters are printed with their provenance before any data check (<key>)
      When I run "algo-backtest run --strategy baseline --symbol EURUSD --from 2014-05-07 --to 2014-05-08 --param cash=10000"
      Then the run command exits with code 2
      And the bootstrap output lists strategy parameter "<key>" = <value> from "<source>"

      Examples:
        | key                       | value | source               |
        | meta_learner.regime_gate  | false | baseline/config.yaml |
        | capital_mgmt.risk_per_trade | 0.03 | baseline/config.yaml |
        | price_features.ema_fast   | 3     | baseline/config.yaml |
        | execution.close_on_veto   | false | baseline/config.yaml |

  Rule: A validated run executes the full F1-F7 chain on the engine without crashing

    @integration
    Scenario: the baseline chain trades a sine cycle and every decision joins its LEAN trade
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      When I run baseline over the 2014-05-08 to 2014-05-09 test span with cash 10000 and that model
      Then the strategy run exits successfully
      And the container log shows the algorithm loaded the fixture model
      And a metrics summary is reported
      And the run artifacts are written under the data root
      And the container log shows the F1-F7 chain actually evaluated a decision
      And decisions.parquet is written under the run's results directory
      And every decisions.parquet row's trade_id names the LEAN trade open at that row's instant
      And at least one decisions.parquet row is joined to a trades.json trade
      And trade-plans.json is written under the run's results directory with at least 1 plan

  Rule: A YAML variant in --strategies-dir runs without a code change

    @integration
    Scenario: an external variant runs on the same engine and records its own parameters
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      And an external strategies directory with "probe-tight" extending baseline with theta_high 0.52 and theta_low 0.48
      When I run probe-tight from that directory over the 2014-05-08 to 2014-05-09 test span with cash 10000 and that model
      Then the strategy run exits successfully
      And the run's strategy-config.json under "probe-tight" records theta_high 0.52 and theta_low 0.48
      And the run's strategy-provenance.json under "probe-tight" attributes "meta_learner.theta_high" to "probe-tight/config.yaml" and "risk_guard.max_leverage" to "baseline/config.yaml"

  Rule: The executor places F6's trade plan and manages it (story 12, item D)
    Each BUY/SELL while flat becomes a market entry sized from the plan's lot size, a
    stop-market order at the stop distance and one take-profit limit per target; trailing
    steps move the stop; a fill that flattens the position cancels the rest (OCO); every
    entry is recorded in trade-plans.json. The variants below narrow baseline's reference plan so
    the sine fixture exercises each mechanism within the two-day test span; every tolerance
    is a table value, never a literal in a step.

    @integration
    Scenario: planned stop fills at the configured distance
      The fixture's ask peaks 1.5 pips above the short entry the model takes at the sine
      top (entry slips half the 1-pip spread), so the stop must sit inside that reach: a
      1-pip stop is touched at the next peak, four hours on; a 2-pip stop never would be.
      The exit slips the other half-spread, hence the 2-pip tolerance on the fill.
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      And an external strategies directory with "planned-stop" extending baseline with these capital_mgmt overrides:
        | key                  | value  |
        | stop_distance_source | fixed  |
        | stop_loss_pips       | 1      |
        | stop_loss_shrink     | 0.0    |
        | min_stop_pips        | 0.0    |
        | risk_per_trade       | 0.0015 |
        | targets              | []     |
        | trail_stops          | []     |
        | min_reward_risk      | null   |
      When I run planned-stop from that directory over the 2014-05-08 to 2014-05-09 test span with cash 10000 and that model
      Then the strategy run exits successfully
      And trade-plans.json is written under the run's results directory with at least 1 plan
      And every plan's stop_loss is 1 pips of 0.0001 from its entry_price within 1e-9
      And at least one closed trade exited within 2 pip of 0.0001 of its plan's stop_loss

    @integration
    Scenario: the intermediate target closes half the position
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      And an external strategies directory with "planned-targets" extending baseline with these capital_mgmt overrides:
        | key                  | value                                                                                 |
        | stop_distance_source | fixed                                                                                 |
        | stop_loss_pips       | 4                                                                                     |
        | stop_loss_shrink     | 0.0                                                                                   |
        | min_stop_pips        | 0.0                                                                                   |
        | risk_per_trade       | 0.006                                                                                 |
        | targets              | [{at_level_ratio: 0.5, close_fraction: 0.5}, {at_level_ratio: 1.0, close_fraction: 0.5}] |
        | trail_stops          | []                                                                                    |
        | min_reward_risk      | null                                                                                  |
      When I run planned-targets from that directory over the 2014-05-08 to 2014-05-09 test span with cash 10000 and that model
      Then the strategy run exits successfully
      And every plan has 2 take_profits whose quantities sum to its whole position within 1 unit
      And some closed trade has at least 3 order ids and its first exit closes 0.5 of its plan's quantity within 1 unit

    @integration
    Scenario: the trailing stop moves after the arm level
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      And an external strategies directory with "planned-trail" extending baseline with these capital_mgmt overrides:
        | key                  | value                                          |
        | stop_distance_source | fixed                                          |
        | stop_loss_pips       | 10                                             |
        | stop_loss_shrink     | 0.0                                            |
        | min_stop_pips        | 0.0                                            |
        | risk_per_trade       | 0.01                                           |
        | targets              | []                                             |
        | trail_stops          | [{at_level_ratio: 0.5, to_level_ratio: -0.5}] |
        | min_reward_risk      | null                                           |
      When I run planned-trail from that directory over the 2014-05-08 to 2014-05-09 test span with cash 10000 and that model
      Then the strategy run exits successfully
      And the container log has a "BASELINE_TRAIL|" line
      And every "BASELINE_TRAIL|" line moves the stop closer to its entry than the stop it replaced

    @integration
    Scenario: spread widens fills by half the configured spread
      Given materialized EUR/USD minute data with a four-hour sine cycle over 2014-05-05 to 2014-05-09
      And a baseline F7 model trained on it: train through 2014-05-06, validate on 2014-05-07, test 2014-05-08 to 2014-05-09
      And an external strategies directory with "wide-spread" extending baseline with these execution overrides:
        | key         | value |
        | spread_pips | 2.0   |
      When I run wide-spread from that directory over the 2014-05-08 to 2014-05-09 test span with cash 10000 and that model
      Then the strategy run exits successfully
      And the container log has a "BASELINE_FILL_COSTS|model=slippage" line
      And every buy market fill is 1 pip of 0.0001 above the fixture bar's ask within 1e-6
