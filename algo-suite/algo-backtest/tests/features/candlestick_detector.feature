Feature: Strict causal TA-Lib candlestick detection
  Closed OHLC candles produce only the six pattern names understood by F3 and F7.
  Fixtures are synthetic recognition examples, not evidence of trading performance.
  Recognition uses TA-Lib default candle settings and star penetration 0.3.

  Scenario Outline: Each supported pattern is recognized by real TA-Lib
    Given a recognition fixture for "<pattern>" with 20 context candles
    When the recognition candles are processed by batch and streaming detectors
    Then both detectors report "<pattern>"
    And the real TA-Lib output confirms "<pattern>"

    Examples:
      | pattern           |
      | bullish_engulfing |
      | bearish_engulfing |
      | hammer           |
      | shooting_star    |
      | morning_star     |
      | evening_star     |

  Scenario Outline: Each recognizer respects its own warmup
    Given a recognition fixture for "<pattern>" with <context> context candles
    When the recognition candles are processed by batch and streaming detectors
    Then both detectors report "<expected>"

    Examples:
      | pattern           | context | expected          |
      | bullish_engulfing | 0       | none              |
      | bullish_engulfing | 1       | bullish_engulfing  |
      | bearish_engulfing | 0       | none              |
      | bearish_engulfing | 1       | bearish_engulfing  |
      | hammer           | 10      | none              |
      | hammer           | 11      | hammer            |
      | shooting_star    | 10      | none              |
      | shooting_star    | 11      | shooting_star     |
      | morning_star     | 9       | none              |
      | morning_star     | 10      | morning_star      |
      | evening_star     | 9       | none              |
      | evening_star     | 10      | evening_star      |

  Scenario Outline: Empty and flat input abstain
    Given <count> flat recognition candles
    When the recognition candles are processed by batch and streaming detectors
    Then both detectors report "none"

    Examples:
      | count |
      | 0     |
      | 1     |
      | 2     |
      | 80    |

  Scenario Outline: Engulfing includes TA-Lib edge-touch scores
    Given an engulfing fixture with direction "<direction>" and one equal body edge
    When the recognition candles are processed by batch and streaming detectors
    Then both detectors report "<pattern>"
    And real TA-Lib gives the engulfing score <score>

    Examples:
      | direction | pattern           | score |
      | bullish   | bullish_engulfing | 80    |
      | bearish   | bearish_engulfing | -80   |

  Scenario Outline: Star penetration remains 0.3
    Given a "<pattern>" fixture closing 40 percent into the first body
    When the recognition candles are processed by batch and streaming detectors
    Then both detectors report "<pattern>"
    And real TA-Lib recognizes that star at penetration 0.3 but not 0.5

    Examples:
      | pattern      |
      | morning_star |
      | evening_star |

  Scenario: Streamed history matches an independent full-prefix oracle after repeated rollovers
    Given a varied recognition history spanning at least 500 candles and all six patterns
    When every recognition prefix is evaluated independently with real TA-Lib
    Then streaming and batch signals match the independent oracle at every prefix
    And the history actually emits all six supported names
    And the streaming detector retains at most 64 candles

  Scenario: Future candles cannot change an already observed prefix
    Given a recognition fixture for "bullish_engulfing" with 70 context candles
    When the same prefix is streamed before two different future suffixes
    Then the observed prefix signals are identical and end in "bullish_engulfing"

  Scenario: A previous detection is not carried forward
    Given a recognition fixture for "bearish_engulfing" with 20 context candles
    When a flat candle follows the recognized pattern
    Then both detectors report "none"

  Scenario Outline: Simultaneous real recognizers obey the selection policy
    Given real overlapping hammer and "<direction>" engulfing candles
    When the recognition candles are processed by batch and streaming detectors
    Then real TA-Lib reports both hammer and "<direction>" engulfing
    And both detectors report "<expected>"

    Examples:
      | direction | expected          |
      | bearish   | none              |
      | bullish   | bullish_engulfing |

  Scenario Outline: Selection is independent of mapping insertion order and score magnitude
    Given raw pattern detections <detections>
    When pattern selection runs in every insertion order
    Then every selection reports "<expected>"

    Examples:
      | detections                                                    | expected          |
      | {}                                                            | none              |
      | {"hammer": 0, "evening_star": 0}                              | none              |
      | {"hammer": 100, "morning_star": 100, "bullish_engulfing": 80} | bullish_engulfing  |
      | {"hammer": 100, "morning_star": 100}                          | hammer            |
      | {"shooting_star": -100, "evening_star": -100, "bearish_engulfing": -80} | bearish_engulfing |
      | {"shooting_star": -100, "evening_star": -100}                  | evening_star      |
      | {"hammer": 100, "bearish_engulfing": -80}                     | none              |
      | {"morning_star": 100, "shooting_star": -100}                  | none              |
      | {"bullish_engulfing": 80, "evening_star": -100}               | none              |
      | {"hammer": 100, "shooting_star": 0}                           | hammer            |
      | {"hammer": 0, "shooting_star": -100}                          | shooting_star     |

  Scenario Outline: Invalid detection mappings fail explicitly
    Given raw pattern detections <detections>
    When pattern selection rejects the invalid mapping
    Then the detector error identifies "<field>" and a remedy

    Examples:
      | detections                            | field          |
      | {"doji": 100}                         | doji           |
      | {"doji": 0}                           | doji           |
      | {"hammer": -100}                      | hammer         |
      | {"shooting_star": 100}                 | shooting_star  |
      | {"bullish_engulfing": true}            | bullish_engulfing |
      | {"hammer": "100"}                    | hammer         |
      | {"hammer": null}                      | hammer         |
      | {"hammer": 100.5}                     | hammer         |
      | {"hammer": NaN}                       | hammer         |

  Scenario Outline: Every OHLC field must be a finite positive real number
    Given a candle whose "<field>" price is <value>
    When batch and streaming detection reject that candle
    Then both errors identify "<field>" and a remedy
    And rejected input does not consume or evict streaming history

    Examples:
      | field | value         |
      | open  | "10"          |
      | high  | "10.2"        |
      | low   | "9.8"         |
      | close | "10"          |
      | open  | true          |
      | high  | true          |
      | low   | true          |
      | close | true          |
      | open  | null          |
      | high  | []            |
      | low   | {}            |
      | close | complex       |
      | open  | NaN           |
      | high  | NaN           |
      | low   | NaN           |
      | close | NaN           |
      | open  | Infinity      |
      | high  | Infinity      |
      | low   | -Infinity     |
      | close | Infinity      |
      | open  | 0             |
      | high  | 0             |
      | low   | 0             |
      | close | 0             |
      | open  | -1            |
      | high  | -1            |
      | low   | -1            |
      | close | -1            |
      | open  | huge_integer  |
      | low   | numpy_bool    |

  Scenario Outline: Invalid OHLC ordering is rejected by both entry points
    Given a candle with OHLC <prices>
    When batch and streaming detection reject that candle
    Then both errors identify "ordering" and a remedy
    And rejected input does not consume or evict streaming history

    Examples:
      | prices          |
      | [11, 10, 8, 9]  |
      | [9, 10, 8, 11]  |
      | [7, 10, 8, 9]   |
      | [9, 10, 8, 7]   |
      | [9, 8, 10, 9]   |

  Scenario: Batch validation includes invalid historical candles
    Given a candle whose "low" price is NaN
    When batch detection receives it before 80 valid candles
    Then the detector error identifies "low" and a remedy

  Scenario Outline: Real integer and NumPy prices are supported
    Given valid recognition candles with "<kind>" prices
    When the recognition candles are processed by batch and streaming detectors
    Then both detectors report "bullish_engulfing"

    Examples:
      | kind          |
      | integer       |
      | numpy_integer |
      | numpy_float   |
