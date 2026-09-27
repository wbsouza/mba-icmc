Feature: Price-feature parameters come from the strategy config.yaml price_features section
  The EMA/RSI/MACD periods behind F1, F2 and the F7 feature families are strategy
  parameters (2026-09-27 amendment, story 09): declared under `price_features:`, with
  defaults for the values that almost never change, shared by training and serving so
  the two cannot drift, and recorded in the model's provenance.

  Rule: An absent section or key resolves to the documented default

    Scenario: an empty section resolves every default
      Given an empty price_features section
      When the price-feature config is parsed for strategy "baseline"
      Then the parsed price features are ema_fast 3, ema_slow 8, ema_higher_tf 60, rsi_period 14, macd_fast 12, macd_slow 26, macd_signal 9

    Scenario Outline: a partial section overrides only the keys it names (<case>)
      Given a price_features section with <key> set to <value>
      When the price-feature config is parsed for strategy "baseline"
      Then the parsed price feature <key> is <value>
      And the parsed price feature <other> is <other_default>

      Examples:
        | case                    | key           | value | other       | other_default |
        | slower fast EMA         | ema_fast      | 5     | ema_slow    | 8             |
        | four-hour higher TF     | ema_higher_tf | 240   | ema_fast    | 3             |
        | longer RSI              | rsi_period    | 21    | macd_signal | 9             |
        | wider MACD              | macd_slow     | 35    | macd_fast   | 12            |

  Rule: Invalid periods fail fast naming the key and the strategy

    Scenario Outline: <case>
      Given a price_features section with <key> set to <value>
      When parsing the price-feature config for strategy "baseline" fails
      Then the price-feature failure names "<names>"
      And the price-feature failure names "baseline"

      Examples:
        | case                              | key           | value | names         |
        | zero period                       | rsi_period    | 0     | rsi_period    |
        | fractional period                 | ema_fast      | 2.5   | ema_fast      |
        | string period                     | macd_slow     | slow  | macd_slow     |
        | fast EMA not below slow EMA       | ema_fast      | 8     | ema_fast      |
        | slow EMA not below higher-TF EMA  | ema_slow      | 60    | ema_slow      |
        | MACD fast not below MACD slow     | macd_fast     | 26    | macd_fast     |

    Scenario: an unknown key fails fast rather than being ignored
      Given a price_features section with unknown key "ema_medium"
      When parsing the price-feature config for strategy "baseline" fails
      Then the price-feature failure names "ema_medium"

  Rule: Warm-up is derived from the periods, matching LEAN indicator readiness

    Scenario Outline: warm-up bars for <case>
      Given a price_features section with ema_higher_tf <htf>, rsi_period <rsi>, macd_slow <slow>, macd_signal <signal>
      When the price-feature config is parsed for strategy "baseline"
      Then the warm-up is <warmup> bars

      Examples:
        | case                     | htf | rsi | slow | signal | warmup |
        | defaults (EMA 60 rules)  | 60  | 14  | 26   | 9      | 59     |
        | MACD dominates           | 20  | 14  | 26   | 9      | 33     |
        | RSI dominates            | 10  | 40  | 13   | 9      | 40     |
