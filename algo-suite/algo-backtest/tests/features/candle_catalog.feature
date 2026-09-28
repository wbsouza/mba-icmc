Feature: Expanded multilabel candlestick catalog
  Story 22, task T3 (CND-01, CND-02, CND-04, CND-05, CND-09). A pure recognizer over
  the T1-admitted rules that returns EVERY hit (bullish, bearish and neutral) on the
  final closed bar, in stable id order, with per-rule lookback and readiness. The six
  legacy rules are the existing TA-Lib recognizers exactly as
  `perception/candlestick.py` calls them (default candle settings, star penetration
  0.3); the thirteen new rules use the explicit formulas below. Synthetic fixtures
  prove mechanics only, never market performance.

  Per-bar quantities (all in price units):
    body  = |close - open|          range = high - low
    upper = high - max(open, close) lower = min(open, close) - low
    bullish: close > open; bearish: close < open; a bar with range == 0 (flat) matches
    no geometric rule. mid(prior) = (open[t-1] + close[t-1]) / 2 (prior BODY midpoint).
    net(k) = close[t-1] - close[t-1-k] (local trend proxy over k closed bars before t).
  Named parameters (catalog version "1"):
    doji_body_ratio = 0.10, doji_shadow_ratio = 0.10, long_leg_ratio = 0.30,
    spinning_top_body_ratio = 0.30, umbrella_shadow_multiple = 2,
    umbrella_opposite_ratio = 0.10, trend_lookback = 3.
  Formulas (sources: book = High Profit Candlestick Patterns, printed page / PDF page;
  webinar = transcript time; "conventional" = no source threshold, stated here so the
  T1 ledger can adopt or dispute it):
    doji             body <= 0.10 * range                      book 21/27 and 23/29 ("same or very near"), ratio conventional
    doji_long_legged doji and min(upper, lower) >= 0.30 * range  webinar 07:48; ratio conventional
    doji_dragonfly   doji and upper <= 0.10 * range              webinar 07:54 ("opens and closes at the top")
    doji_gravestone  doji and lower <= 0.10 * range              webinar 08:05
    spinning_top     0.10 * range < body <= 0.30 * range and upper >= body and lower >= body
                                                                 book 20/26 (small body relative to shadows), webinar 29:56; ratios conventional
    bullish_harami   prior bearish, current bullish, open > close[t-1] and close < open[t-1]
                                                                 book 75/81 criteria 3 (strict: an equal edge is not a harami)
    bearish_harami   prior bullish, current bearish, open < close[t-1] and close > open[t-1]
                                                                 book 81/86 criteria 3
    piercing_line    prior bearish, current bullish, open < close[t-1], close > mid(prior), close < open[t-1]
                                                                 book 65/71 criteria 3-4 and webinar 34:33; FX adaptation: the book's
                                                                 open below the prior LOW becomes open below the prior CLOSE (no
                                                                 intraday gaps in spot FX); a close reaching open[t-1] is engulfing
    dark_cloud_cover prior bullish, current bearish, open > close[t-1], close < mid(prior), close > open[t-1]
                                                                 book 70/76; same FX adaptation
    bullish_kicker   prior bearish, current bullish, open >= open[t-1]
                                                                 book 110/116 criteria 1 ("same open or gaps beyond"), webinar 53:08;
                                                                 bodies do not overlap, touching allowed; no marubozu requirement
    bearish_kicker   prior bullish, current bearish, open <= open[t-1]
    hanging_man      body > 0, lower >= 2 * body, upper <= 0.10 * range, net(3) > 0
                                                                 book 60/66 (tail two times the body, small upper shadow, top of trend),
                                                                 webinar 30:14 and 33:17; net(3) trend proxy conventional
    inverted_hammer  body > 0, upper >= 2 * body, lower <= 0.10 * range, net(3) < 0
                                                                 book 91/97 criteria 1-3, webinar 38:39
    legacy six       bullish_engulfing / bearish_engulfing = sign of CDLENGULFING; hammer = CDLHAMMER;
                     shooting_star = CDLSHOOTINGSTAR; morning_star / evening_star = CDLMORNINGSTAR /
                     CDLEVENINGSTAR with penetration 0.3 (book 37/43, 46/52, 53/59, 87/93, 97/103,
                     104/110 describe the same shapes; TA-Lib's averaged thresholds are kept
                     verbatim for byte-identical legacy behaviour).
  TA-Lib is NOT used for the new rules: CDLDOJI, CDLHARAMI, CDLPIERCING,
  CDLDARKCLOUDCOVER, CDLKICKING, CDLHANGINGMAN and CDLINVERTEDHAMMER use 10-bar
  averaged thresholds, marubozu or range-gap requirements that differ from the
  formulas above; the ledger records each difference.

  Story 23 (BEXT-01, BEXT-02, BEXT-03, BEXT-04, BEXT-05, BEXT-06) admits three further
  rules to the catalog. They are usable via enabled_rules but excluded from the default
  configuration, so every scenario above stays byte-identical
  (`docs/stories/in-progress/23-bigalow-extended-signals/rule-ledger-addendum.md` is the
  T1 ledger for these three):
    counterattack_tolerance = 0.10 (a separately named constant, same value as
    doji_body_ratio by convention, not the same constant, so the two rules can diverge
    independently later).
    bearish_counterattack_line  prior bullish, open > close[t-1], close > mid(prior),
                                 abs(close - close[t-1]) <= 0.10 * range
                                                                 book PDF p.318 lines 12008-12018,
                                                                 p.368-369 lines 14022-14028; close > mid(prior)
                                                                 is the mutual-exclusivity guard against
                                                                 dark_cloud_cover (BEXT-03)
    bullish_counterattack_line  prior bearish, open < close[t-1], close < mid(prior),
                                 abs(close - close[t-1]) <= 0.10 * range
                                                                 same source, mirrored; close < mid(prior)
                                                                 guards against piercing_line (BEXT-03)
    methods_rising  bullish signal bar B; for some n in {3,4,5,6}, the n bars right
                     before the final bar each close >= open(B); the final bar (the
                     last of those n) opens above the previous bar's close and closes
                     above close(B)                            book PDF p.260-261 lines 9679-9714;
                                                                 lookback 4 is the n=3 minimum, n up to 6
                                                                 is tried whenever enough history exists
                                                                 (BEXT-04); no bearish mirror is sourced

  Story 23 fixtures reuse the bullish/bearish prior convention above for the
  counterattack lines; Methods Rising fixtures are given as an explicit bar table.

  Readiness: a rule is WARMUP until its lookback (candle_contract.feature table) of
  closed bars exists; a WARMUP rule appears in the hits as a WARMUP entry with
  polarity 0; a READY rule that did not fire is omitted; the evidence status is WARMUP
  while any enabled rule is WARMUP, and READY hits are reported even then (CND-04).
  Hits are a tuple sorted by id whatever the enabled_rules order (CND-02).

  Fixtures: the "context candle" is (1000, 1060, 980, 1040) unless stated; the
  "bearish prior" is (1000, 1010, 890, 900) and the "bullish prior" is
  (900, 1010, 890, 1000), both with body 900..1000 and body midpoint 950. Integer
  prices keep every equality boundary exact. The "legacy recognition fixtures" are
  the OHLC lists of test_candlestick_detector.py, after 20 float context candles
  (10, 10.6, 9.8, 10.4).

  Rule: Single-bar neutral shapes follow the doji and spinning-top formulas exactly

    Scenario Outline: Doji family and spinning top geometry (<case>)
      Given the catalog restricted to "doji,doji_long_legged,doji_dragonfly,doji_gravestone,spinning_top"
      And the closed bars (<open>, <high>, <low>, <close>)
      When the catalog evaluates the final bar
      Then the READY hits are "<hits>" with polarity 0 each
      And the evidence status is "READY"

      Examples:
        | case                                   | open | high | low  | close | hits                          |
        | doji: body 2 of range 80               | 1000 | 1060 | 980  | 1002  | doji                          |
        | doji boundary: body 10 of range 100    | 1000 | 1075 | 975  | 1010  | doji                          |
        | not a doji: body 11 of range 100       | 1000 | 1075 | 975  | 1011  | spinning_top                  |
        | long-legged: zero body, shadows 50/50  | 1000 | 1050 | 950  | 1000  | doji,doji_long_legged         |
        | long-legged boundary: upper 30 of 100  | 1020 | 1050 | 950  | 1020  | doji,doji_long_legged         |
        | not long-legged: upper 29 of 100       | 1021 | 1050 | 950  | 1021  | doji                          |
        | dragonfly: no upper shadow             | 1050 | 1050 | 950  | 1050  | doji,doji_dragonfly           |
        | dragonfly boundary: upper 10 of 100    | 1040 | 1050 | 950  | 1040  | doji,doji_dragonfly           |
        | not dragonfly: upper 11 of 100         | 1039 | 1050 | 950  | 1039  | doji                          |
        | gravestone: no lower shadow            | 950  | 1050 | 950  | 950   | doji,doji_gravestone          |
        | gravestone boundary: lower 10 of 100   | 960  | 1050 | 950  | 960   | doji,doji_gravestone          |
        | not gravestone: lower 11 of 100        | 961  | 1050 | 950  | 961   | doji                          |
        | spinning top: body 20, shadows 40/40   | 1000 | 1060 | 960  | 1020  | spinning_top                  |
        | spinning top bearish body              | 1020 | 1060 | 960  | 1000  | spinning_top                  |
        | spinning top boundary: body 30 of 100  | 1000 | 1065 | 965  | 1030  | spinning_top                  |
        | not spinning: body 31 of 101           | 1000 | 1066 | 965  | 1031  |                               |
        | spinning boundary: upper == body       | 1000 | 1040 | 960  | 1020  | spinning_top                  |
        | not spinning: upper 5 < body 20        | 1000 | 1025 | 955  | 1020  |                               |
        | long body is no neutral shape          | 1000 | 1100 | 990  | 1090  |                               |
        | flat bar matches nothing               | 1000 | 1000 | 1000 | 1000  |                               |

  Rule: Two-bar reversal shapes compare bodies with strict or inclusive edges as stated

    Scenario Outline: Harami, piercing, dark cloud and kicker geometry (<case>)
      Given the catalog restricted to "bullish_harami,bearish_harami,piercing_line,dark_cloud_cover,bullish_kicker,bearish_kicker,doji,doji_long_legged"
      And the closed bars: the <prior> prior then (<open>, <high>, <low>, <close>)
      When the catalog evaluates the final bar
      Then the READY hits are "<hits>"
      And the evidence status is "READY"

      Examples:
        | case                                          | prior   | open | high | low  | close | hits                                  |
        | bullish harami inside 900..1000               | bearish | 920  | 990  | 910  | 980   | bullish_harami                        |
        | bullish harami: open equal to prior close     | bearish | 900  | 990  | 895  | 980   |                                       |
        | bullish harami: close equal to prior open     | bearish | 920  | 1005 | 910  | 1000  |                                       |
        | bullish harami needs a bullish body           | bearish | 980  | 990  | 910  | 920   |                                       |
        | harami cross: a doji inside the prior body    | bearish | 950  | 980  | 920  | 952   | bullish_harami,doji,doji_long_legged  |
        | bearish harami inside 900..1000               | bullish | 980  | 990  | 910  | 920   | bearish_harami                        |
        | bearish harami: open equal to prior close     | bullish | 1000 | 1005 | 910  | 920   |                                       |
        | bearish harami: close equal to prior open     | bullish | 980  | 990  | 895  | 900   |                                       |
        | bearish harami needs a bearish body           | bullish | 920  | 990  | 910  | 980   |                                       |
        | piercing: open 880 < 900, close 970 > 950     | bearish | 880  | 980  | 870  | 970   | piercing_line                         |
        | piercing just above the midpoint              | bearish | 880  | 960  | 870  | 951   | piercing_line                         |
        | piercing boundary: close equal to midpoint    | bearish | 880  | 960  | 870  | 950   |                                       |
        | piercing boundary: open equal to prior close  | bearish | 900  | 980  | 890  | 970   |                                       |
        | dark cloud: open 1020 > 1000, close 930 < 950 | bullish | 1020 | 1030 | 920  | 930   | dark_cloud_cover                      |
        | dark cloud just below the midpoint            | bullish | 1020 | 1030 | 940  | 949   | dark_cloud_cover                      |
        | dark cloud boundary: close equal to midpoint  | bullish | 1020 | 1030 | 940  | 950   |                                       |
        | dark cloud boundary: open equal to prior close| bullish | 1000 | 1030 | 920  | 930   |                                       |
        | bullish kicker: open 1030 above prior open    | bearish | 1030 | 1100 | 1030 | 1090  | bullish_kicker                        |
        | bullish kicker boundary: open equals 1000     | bearish | 1000 | 1100 | 1000 | 1090  | bullish_kicker                        |
        | not a kicker: bodies overlap by 1             | bearish | 999  | 1100 | 999  | 1090  |                                       |
        | bearish kicker: open 870 below prior open     | bullish | 870  | 870  | 800  | 810   | bearish_kicker                        |
        | bearish kicker boundary: open equals 900      | bullish | 900  | 900  | 800  | 810   | bearish_kicker                        |
        | not a bearish kicker: bodies overlap by 1     | bullish | 901  | 901  | 800  | 810   |                                       |

    Scenario: A close reaching the prior open is a legacy engulfing, not a piercing line
      Given the default catalog
      And the closed bars: 20 context candles, the bearish prior, then (880, 1020, 870, 1000)
      When the catalog evaluates the final bar
      Then the READY hits are "bullish_engulfing"
      And real TA-Lib gives the engulfing score 80 on those bars

  Rule: Umbrella shapes require the local trend precondition and the shadow ratios

    Scenario Outline: Hanging man and inverted hammer (<case>)
      Given the catalog restricted to "hanging_man,inverted_hammer"
      And four flat-bodied prior bars closing at <c1>, <c2>, <c3>, <c4>
      And a final closed bar (<open>, <high>, <low>, <close>)
      When the catalog evaluates the final bar
      Then the READY hits are "<hits>"
      And the evidence status is "READY"

      Examples:
        | case                                            | c1   | c2   | c3   | c4   | open | high | low  | close | hits            |
        | hanging man after net(3) = +140                 | 900  | 1040 | 1040 | 1040 | 955  | 962  | 850  | 960   | hanging_man     |
        | umbrella with net(3) = 0 is nothing             | 1040 | 1040 | 1040 | 1040 | 955  | 962  | 850  | 960   |                 |
        | umbrella with net(3) < 0 is nothing             | 1040 | 1040 | 1040 | 900  | 955  | 962  | 850  | 960   |                 |
        | hanging man boundary: lower == 2 * body         | 900  | 1040 | 1040 | 1040 | 940  | 951  | 920  | 950   | hanging_man     |
        | not hanging: lower 19 < 2 * body 10             | 900  | 1040 | 1040 | 1040 | 940  | 951  | 921  | 950   |                 |
        | hanging man boundary: upper == 0.10 * range     | 900  | 1040 | 1040 | 1040 | 940  | 960  | 860  | 950   | hanging_man     |
        | not hanging: upper 11 > 0.10 * 101              | 900  | 1040 | 1040 | 1040 | 940  | 961  | 860  | 950   |                 |
        | zero body is a doji matter, not a hanging man   | 900  | 1040 | 1040 | 1040 | 950  | 951  | 850  | 950   |                 |
        | inverted hammer after net(3) = -140             | 1040 | 900  | 900  | 900  | 960  | 1070 | 952  | 955   | inverted_hammer |
        | inverted shape with net(3) = 0 is nothing       | 900  | 900  | 900  | 900  | 960  | 1070 | 952  | 955   |                 |
        | inverted shape with net(3) > 0 is nothing       | 900  | 1040 | 1040 | 1040 | 960  | 1070 | 952  | 955   |                 |
        | inverted hammer boundary: upper == 2 * body     | 1040 | 900  | 900  | 900  | 950  | 980  | 949  | 960   | inverted_hammer |
        | not inverted: upper 19 < 2 * body 10            | 1040 | 900  | 900  | 900  | 950  | 979  | 949  | 960   |                 |
        | net(3) = 0 after a round trip is nothing        | 1040 | 900  | 900  | 1040 | 960  | 1070 | 952  | 955   |                 |

  Rule: The six legacy rules are the TA-Lib recognizers with their own lookbacks

    Scenario Outline: Each legacy fixture fires its TA-Lib rule with the registered polarity (<pattern>)
      Given the default catalog
      And the legacy recognition fixture for "<pattern>" with 20 context candles
      When the catalog evaluates the final bar
      Then the READY hits include "<pattern>" with polarity <polarity>
      And the real TA-Lib output confirms "<pattern>"
      And the evidence status is "READY"

      Examples:
        | pattern           | polarity |
        | bullish_engulfing | 1        |
        | bearish_engulfing | -1       |
        | hammer            | 1        |
        | shooting_star     | -1       |
        | morning_star      | 1        |
        | evening_star      | -1       |

    Scenario Outline: Each legacy rule is WARMUP one bar before its lookback and READY at it (<pattern>)
      Given the default catalog
      And the legacy recognition fixture for "<pattern>" with <context> context candles
      When the catalog evaluates the final bar
      Then the hit for "<pattern>" has status "<status>"

      Examples:
        | pattern           | context | status |
        | bullish_engulfing | 0       | WARMUP |
        | bullish_engulfing | 1       | READY  |
        | bearish_engulfing | 0       | WARMUP |
        | bearish_engulfing | 1       | READY  |
        | hammer            | 10      | WARMUP |
        | hammer            | 11      | READY  |
        | shooting_star     | 10      | WARMUP |
        | shooting_star     | 11      | READY  |
        | morning_star      | 9       | WARMUP |
        | morning_star      | 10      | READY  |
        | evening_star      | 9       | WARMUP |
        | evening_star      | 10      | READY  |

    Scenario Outline: Legacy equality boundaries stay TA-Lib's (<case>)
      Given the default catalog
      And the legacy boundary fixture "<case>"
      When the catalog evaluates the final bar
      Then the READY hits include "<pattern>"
      And real TA-Lib gives the score <score> for "<pattern>"

      Examples:
        | case                                       | pattern           | score |
        | bullish engulfing with one equal body edge | bullish_engulfing | 80    |
        | bearish engulfing with one equal body edge | bearish_engulfing | -80   |
        | morning star closing 40 percent into body  | morning_star      | 100   |
        | evening star closing 40 percent into body  | evening_star      | -100  |

  Rule: Shared multilabel mechanics

    Scenario: A single bar reports the ready short-lookback hits beside every warming rule
      Given the default catalog
      And the closed bars (1000, 1050, 950, 1000)
      When the catalog evaluates the final bar
      Then the evidence status is "WARMUP"
      And the hits are exactly, in order:
        | id                | polarity | status |
        | bearish_engulfing | 0        | WARMUP |
        | bearish_harami    | 0        | WARMUP |
        | bearish_kicker    | 0        | WARMUP |
        | bullish_engulfing | 0        | WARMUP |
        | bullish_harami    | 0        | WARMUP |
        | bullish_kicker    | 0        | WARMUP |
        | dark_cloud_cover  | 0        | WARMUP |
        | doji              | 0        | READY  |
        | doji_long_legged  | 0        | READY  |
        | evening_star      | 0        | WARMUP |
        | hammer            | 0        | WARMUP |
        | hanging_man       | 0        | WARMUP |
        | inverted_hammer   | 0        | WARMUP |
        | morning_star      | 0        | WARMUP |
        | piercing_line     | 0        | WARMUP |
        | shooting_star     | 0        | WARMUP |

    Scenario Outline: Rules leave WARMUP at their own lookback (<bars> bars)
      Given the default catalog
      And <bars> context candles
      When the catalog evaluates the final bar
      Then the WARMUP hit ids are exactly "<warming>"
      And the evidence status is "<status>"

      Examples:
        | bars | warming                                                                        | status |
        | 1    | bearish_engulfing,bearish_harami,bearish_kicker,bullish_engulfing,bullish_harami,bullish_kicker,dark_cloud_cover,evening_star,hammer,hanging_man,inverted_hammer,morning_star,piercing_line,shooting_star | WARMUP |
        | 2    | bearish_engulfing,bullish_engulfing,evening_star,hammer,hanging_man,inverted_hammer,morning_star,shooting_star | WARMUP |
        | 3    | evening_star,hammer,hanging_man,inverted_hammer,morning_star,shooting_star      | WARMUP |
        | 4    | evening_star,hammer,hanging_man,inverted_hammer,morning_star,shooting_star      | WARMUP |
        | 5    | evening_star,hammer,morning_star,shooting_star                                 | WARMUP |
        | 11   | evening_star,hammer,morning_star,shooting_star                                 | WARMUP |
        | 12   | evening_star,morning_star                                                      | WARMUP |
        | 13   |                                                                                | READY  |
        | 300  |                                                                                | READY  |

    Scenario: Simultaneous neutral and directional hits are all preserved in id order
      Given the default catalog
      And the closed bars: 20 context candles, the bearish prior, then (950, 980, 920, 952)
      When the catalog evaluates the final bar
      Then the hits are exactly, in order:
        | id               | polarity | status |
        | bullish_harami   | 1        | READY  |
        | doji             | 0        | READY  |
        | doji_long_legged | 0        | READY  |
      And the evidence status is "READY"

    Scenario: Opposing hits on one bar are both reported and neither is chosen
      Given the default catalog
      And the closed bars: 8 float context candles, (10, 10.6, 8.9, 9.0), 3 float context candles, then (9.55, 9.62, 8.5, 9.6)
      When the catalog evaluates the final bar
      Then the hits are exactly, in order:
        | id             | polarity | status |
        | doji           | 0        | READY  |
        | doji_dragonfly | 0        | READY  |
        | hammer         | 1        | READY  |
        | hanging_man    | -1       | READY  |
      And the evidence status is "READY"
      And real TA-Lib reports hammer 100 on those bars
      And the legacy label of those hits is "hammer"

    Scenario: Hit order is by id regardless of the enabled_rules order
      Given the catalog restricted to "doji_long_legged,doji,bullish_harami"
      And the closed bars: 20 context candles, the bearish prior, then (950, 980, 920, 952)
      When the catalog evaluates the final bar
      Then the READY hit ids are exactly "bullish_harami,doji,doji_long_legged"
      And the same bars through the catalog restricted to "bullish_harami,doji,doji_long_legged" give identical evidence

    Scenario: A disabled rule is never reported, not even as WARMUP
      Given the catalog restricted to "doji"
      And the closed bars: the bearish prior, then (950, 980, 920, 952)
      When the catalog evaluates the final bar
      Then the hits are exactly, in order:
        | id   | polarity | status |
        | doji | 0        | READY  |
      And the evidence status is "READY"

    Scenario: Future candles cannot change an already observed prefix
      Given the default catalog
      And the legacy recognition fixture for "bullish_engulfing" with 70 context candles
      When the same prefix is streamed before a morning-star suffix and before an evening-star suffix
      Then the per-bar evidence over the prefix is identical under both suffixes
      And the final prefix hits include "bullish_engulfing"

    Scenario: Flat history is READY with no hits and a None legacy label
      Given the default catalog
      And 20 flat closed bars (1000, 1000, 1000, 1000)
      When the catalog evaluates the final bar
      Then the READY hits are ""
      And the evidence status is "READY"
      And the legacy label of those hits is None

    Scenario Outline: The legacy label reproduces select_pattern over the six legacy ids only (<case>)
      Given READY hits "<hits>"
      When the legacy label is derived
      Then the legacy label is "<label>"

      Examples:
        | case                              | hits                                        | label             |
        | no hits                           |                                             | none              |
        | only new rules                    | bullish_harami,doji                         | none              |
        | one legacy bullish                | doji,hammer                                 | hammer            |
        | lexical first within a polarity   | bullish_engulfing,hammer,morning_star       | bullish_engulfing |
        | lexical first bearish             | evening_star,shooting_star                  | evening_star      |
        | opposing legacy hits abstain      | hammer,shooting_star                        | none              |
        | new bearish does not oppose       | hammer,hanging_man                          | hammer            |
        | new bullish does not oppose       | bullish_kicker,evening_star                 | evening_star      |
        | warmup entries are not hits       | hammer:WARMUP,shooting_star                 | shooting_star     |

    Scenario: Frozen legacy equality against the existing detector on every prefix
      Given the default catalog
      And the legacy corpora: every legacy recognition fixture with 20 context candles, the overlapping hammer and engulfing fixtures, and the varied 500-candle history of test_candlestick_detector.py
      When every prefix of every corpus is evaluated by the catalog and by perception.candlestick.detect_pattern
      Then the legacy label of the catalog hits equals detect_pattern on every prefix
      And the legacy labels over the 500-candle history emit all six legacy names
      And the catalog history never retains more than max_history bars

  Rule: Counterattack Line reverses a gap back to the prior close without crossing the piercing/dark-cloud midpoint

    Scenario Outline: Counterattack Line geometry (<case>)
      Given the catalog restricted to "bearish_counterattack_line,bullish_counterattack_line,piercing_line,dark_cloud_cover"
      And the closed bars: the <prior> prior, then (<open>, <high>, <low>, <close>)
      When the catalog evaluates the final bar
      Then the READY hits are "<hits>"
      And the evidence status is "READY"

      Examples:
        | case                                                | prior   | open | high | low | close | hits                        |
        | bearish counterattack: gaps to 1020, closes near 1000 | bullish | 1020 | 1025 | 995 | 1002  | bearish_counterattack_line  |
        | bearish counterattack: no gap past the prior close    | bullish | 995  | 1010 | 985 | 999   |                             |
        | bearish counterattack boundary: tolerance exactly 4/40| bullish | 1020 | 1020 | 980 | 1004  | bearish_counterattack_line  |
        | bearish counterattack: tolerance 5 of 40, just past   | bullish | 1020 | 1020 | 980 | 1005  |                             |
        | bullish counterattack: gaps to 880, closes near 900   | bearish | 880  | 905  | 875 | 902   | bullish_counterattack_line  |
        | bullish counterattack: no gap past the prior close    | bearish | 905  | 920  | 880 | 898   |                             |
        | bullish counterattack boundary: tolerance exactly 4/40| bearish | 880  | 900  | 860 | 896   | bullish_counterattack_line  |
        | bullish counterattack: tolerance 5 of 40, just past   | bearish | 880  | 900  | 860 | 895   |                             |

    Scenario: A close reaching the dark-cloud zone does not also count as a bearish counterattack
      Given the catalog restricted to "dark_cloud_cover,bearish_counterattack_line"
      And the closed bars: the bullish prior, then (1020, 1030, 920, 930)
      When the catalog evaluates the final bar
      Then the READY hits are "dark_cloud_cover"

    Scenario: A close reaching the piercing zone does not also count as a bullish counterattack
      Given the catalog restricted to "piercing_line,bullish_counterattack_line"
      And the closed bars: the bearish prior, then (880, 980, 870, 970)
      When the catalog evaluates the final bar
      Then the READY hits are "piercing_line"

    Scenario: A close within counterattack tolerance but past the dark-cloud midpoint stays dark cloud only
      Given the catalog restricted to "dark_cloud_cover,bearish_counterattack_line"
      And the closed bars: the bullish prior, then (1020, 1600, 900, 949)
      When the catalog evaluates the final bar
      Then the READY hits are "dark_cloud_cover"

    Scenario: A close within counterattack tolerance but past the piercing midpoint stays piercing only
      Given the catalog restricted to "piercing_line,bullish_counterattack_line"
      And the closed bars: the bearish prior, then (880, 1000, 300, 951)
      When the catalog evaluates the final bar
      Then the READY hits are "piercing_line"

    Scenario Outline: Counterattack lines are WARMUP before two bars and READY at two (<bars> bars)
      Given the catalog restricted to "bearish_counterattack_line,bullish_counterattack_line"
      And <bars> context candles
      When the catalog evaluates the final bar
      Then the WARMUP hit ids are exactly "<warming>"

      Examples:
        | bars | warming                                                   |
        | 1    | bearish_counterattack_line,bullish_counterattack_line     |
        | 2    |                                                            |

  Rule: Methods Rising is a variable-length bullish continuation with an inclusive pullback floor

    Scenario: Methods Rising fires with the minimum three pullback bars
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1008 | 1010 | 1000 | 1003  |
        | 1010 | 1030 | 1005 | 1025  |
      When the catalog evaluates the final bar
      Then the READY hits are "methods_rising"

    Scenario: Methods Rising does not fire when the final close stays below the signal's close
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1008 | 1010 | 1000 | 1003  |
        | 1010 | 1022 | 1005 | 1018  |
      When the catalog evaluates the final bar
      Then the READY hits are ""

    Scenario: Methods Rising accepts a pullback closing exactly at the signal's open
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1005 | 1008 | 998  | 1000  |
        | 1010 | 1030 | 1005 | 1025  |
      When the catalog evaluates the final bar
      Then the READY hits are "methods_rising"

    Scenario: Methods Rising is rejected with only two pullback bars (still WARMUP)
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1010 | 1030 | 1005 | 1025  |
      When the catalog evaluates the final bar
      Then the hit for "methods_rising" has status "WARMUP"

    Scenario: Methods Rising fires with the maximum six pullback bars
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1008 | 1010 | 1000 | 1003  |
        | 1006 | 1009 | 1001 | 1004  |
        | 1007 | 1011 | 1002 | 1006  |
        | 1009 | 1012 | 1003 | 1007  |
        | 1010 | 1030 | 1005 | 1025  |
      When the catalog evaluates the final bar
      Then the READY hits are "methods_rising"

    Scenario: Methods Rising does not fire over seven pullback bars
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1008 | 1010 | 1000 | 1003  |
        | 1006 | 1009 | 1001 | 1004  |
        | 1007 | 1011 | 1002 | 1006  |
        | 1009 | 1012 | 1003 | 1007  |
        | 1011 | 1013 | 1004 | 1008  |
        | 1010 | 1030 | 1005 | 1025  |
      When the catalog evaluates the final bar
      Then the READY hits are ""

    Scenario: Methods Rising evidence over a prefix is unaffected by what comes after
      Given the catalog restricted to "methods_rising"
      And the closed bars:
        | open | high | low  | close |
        | 1000 | 1025 | 995  | 1020  |
        | 1015 | 1018 | 1002 | 1005  |
        | 1008 | 1010 | 1000 | 1003  |
        | 1010 | 1030 | 1005 | 1025  |
      When the same prefix is streamed before a morning-star suffix and before an evening-star suffix
      Then the per-bar evidence over the prefix is identical under both suffixes
      And the final prefix hits include "methods_rising"

  Rule: The Story 23 extended-signal rules never appear in the default catalog

    Scenario: The default catalog omits the extended-signal ids even with ample history
      Given the default catalog
      And 300 context candles
      When the catalog evaluates the final bar
      Then the hits never include the extended rule ids
