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

  Scenario: the vocabulary is exactly the six names F3 recognises
    Then the pattern vocabulary is bullish_engulfing, hammer, morning_star, bearish_engulfing, shooting_star, evening_star

  Scenario: the Patterns page lists every card with its links
    When I open the Patterns page
    Then it shows 6 pattern cards
    And the card "Hammer" links to "https://en.wikipedia.org/wiki/Hammer_(candlestick_pattern)"
    And the card "Hammer" links to "https://ta-lib.org/functions/"
