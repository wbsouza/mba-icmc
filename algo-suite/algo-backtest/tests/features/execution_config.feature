Feature: Execution parameters come from the strategy config.yaml execution section
  Story 12 (execution realism): the fill costs and the holding rule the executor applies
  are strategy parameters, not code constants — the optional top-level `execution:`
  section of `strategies/<name>/config.yaml` (specs.md §14.7, Strategy A05). It is not
  tied to any filter: the loader always resolves it, defaulting every key it omits, and
  writes the effective values back into the resolved config so the run's
  `strategy-config.{json,yaml}` records the cost assumptions the result was produced under.

  Rule: An absent section or key resolves to the documented default

    Scenario: an empty section resolves every default
      Given an empty execution section
      When the execution config is parsed for strategy "baseline"
      Then the parsed execution config is spread_pips 0.0, commission_per_lot 0.0, min_hold_bars 0, broker_stop_level_pips 0.0

    Scenario Outline: a partial section overrides only the key it names (<case>)
      Given an execution section with <key> set to <value>
      When the execution config is parsed for strategy "baseline"
      Then the execution mapping records <key> <value>
      And the execution mapping records <other> <other_default>

      Examples:
        | case                    | key                | value | other              | other_default |
        | one-pip spread (A05)    | spread_pips        | 1.0   | commission_per_lot | 0.0           |
        | ECN commission per lot  | commission_per_lot | 7.0   | spread_pips        | 0.0           |
        | hold at least three bars| min_hold_bars      | 3     | commission_per_lot | 0.0           |
        | integer spread          | spread_pips        | 2     | min_hold_bars      | 0             |
        | broker stop level       | broker_stop_level_pips | 2.5 | spread_pips      | 0.0           |

  Rule: An invalid or unknown value fails fast naming the strategy, section and key

    Scenario Outline: <case>
      Given an execution section with <key> set to <value>
      When parsing the execution config for strategy "baseline" fails
      Then the execution failure names "<failure>"
      And the execution failure names "strategy 'baseline'"

      Examples:
        | case                        | key                | value | failure                                                  |
        | negative spread             | spread_pips        | -0.5  | execution.spread_pips must be >= 0                       |
        | non-numeric spread          | spread_pips        | wide  | execution.spread_pips must be a number                   |
        | negative commission         | commission_per_lot | -7    | execution.commission_per_lot must be >= 0                |
        | boolean commission          | commission_per_lot | true  | execution.commission_per_lot must be a number            |
        | negative hold               | min_hold_bars      | -1    | execution.min_hold_bars must be an integer >= 0          |
        | fractional hold             | min_hold_bars      | 1.5   | execution.min_hold_bars must be an integer >= 0          |
        | boolean hold                | min_hold_bars      | true  | execution.min_hold_bars must be an integer >= 0          |
        | negative broker stop level  | broker_stop_level_pips | -1 | execution.broker_stop_level_pips must be >= 0          |
        | unknown key                 | slippage_pips      | 0.3   | execution has unknown keys ['slippage_pips']             |
