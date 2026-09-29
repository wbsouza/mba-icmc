Feature: Candlestick pattern cards
  Every pattern F3 can name (perception/candlestick.py: bullish_engulfing, bearish_engulfing,
  hammer, shooting_star, morning_star, evening_star) has one card: its title, its
  direction, a two-sentence plain-English description (the shape, then the classical
  reading), a public reference page and the TA-Lib function that detects it. The cards
  are shown in the trade drawer when F3 detected the pattern and on the Patterns page.

  Scenario Outline: each vocabulary name has a card with a reference URL and a TA-Lib function
    Given the pattern card for "<name>"
    Then its title is "<title>" and its direction is <direction>
    And its description has 2 sentences
    And its reference URL is "<reference_url>"
    And its TA-Lib function is <talib> linked to "https://ta-lib.org/functions/"

    Examples:
      | name              | title             | direction | reference_url                                                  | talib           |
      | bullish_engulfing | Bullish engulfing | bullish   | https://www.investopedia.com/terms/b/bullishengulfingpattern.asp | CDLENGULFING    |
      | bearish_engulfing | Bearish engulfing | bearish   | https://www.investopedia.com/terms/b/bearishengulfingp.asp       | CDLENGULFING    |
      | hammer            | Hammer            | bullish   | https://en.wikipedia.org/wiki/Hammer_(candlestick_pattern)       | CDLHAMMER       |
      | shooting_star     | Shooting star     | bearish   | https://en.wikipedia.org/wiki/Shooting_star_(candlestick_pattern) | CDLSHOOTINGSTAR |
      | morning_star      | Morning star      | bullish   | https://en.wikipedia.org/wiki/Morning_star_(candlestick_pattern)  | CDLMORNINGSTAR  |
      | evening_star      | Evening star      | bearish   | https://www.investopedia.com/terms/e/eveningstar.asp             | CDLEVENINGSTAR  |

  Scenario Outline: each card draws its schematic with one rect per candle, in the right colours
    When I render the pattern card for "<name>"
    Then its schematic is an svg with <candles> candle rects, <up> up and <down> down
    And its caption reads "<caption>"

    Examples:
      | name              | candles | up | down | caption                                                                                  |
      | bullish_engulfing | 2       | 1  | 1    | A small down candle, then a larger up body that covers it.                                |
      | bearish_engulfing | 2       | 1  | 1    | A small up candle, then a larger down body that covers it.                                |
      | hammer            | 1       | 1  | 0    | Small body at the top; lower shadow at least twice the body.                             |
      | shooting_star     | 1       | 0  | 1    | Small body at the bottom; upper shadow at least twice the body.                          |
      | morning_star      | 3       | 1  | 2    | Long down candle, a small body gapped below it, a long up candle past the midpoint.      |
      | evening_star      | 3       | 2  | 1    | Long up candle, a small body gapped above it, a long down candle past the midpoint.      |

  Scenario Outline: the schematic geometry matches the pattern's definition
    Given the pattern card for "<name>"
    Then its schematic satisfies "<rule>"

    Examples:
      | name              | rule                                                  |
      | bullish_engulfing | the second body covers the first body                 |
      | bearish_engulfing | the second body covers the first body                 |
      | hammer            | the lower shadow is at least twice the body           |
      | shooting_star     | the upper shadow is at least twice the body           |
      | morning_star      | the middle body gaps below and the third closes above the first body's midpoint |
      | evening_star      | the middle body gaps above and the third closes below the first body's midpoint |

  Scenario: the Patterns page links real trades whose entry carried the pattern
    Given the backend serves the fixture database
    When I open the Patterns page against the backend
    Then the card "Hammer" offers 1 example link to "#/run/20260928T010000-fixture/trade/1"
    And the card "Evening star" says "no example in this database"

  Scenario: the vocabulary is exactly the six names F3 recognises
    Then the pattern vocabulary is bullish_engulfing, hammer, morning_star, bearish_engulfing, shooting_star, evening_star

  Scenario: the Patterns page lists every card with its links
    When I open the Patterns page
    Then it shows 6 pattern cards
    And the card "Hammer" links to "https://en.wikipedia.org/wiki/Hammer_(candlestick_pattern)"
    And the card "Hammer" links to "https://ta-lib.org/functions/"
