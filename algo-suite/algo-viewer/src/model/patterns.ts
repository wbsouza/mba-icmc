/**
 * The six candlestick patterns F3 recognises (perception/candlestick.py, TA-Lib CDL*):
 * one card each with the direction it argues for, a two-sentence plain-English
 * description (the shape, then the classical reading), a public reference page and the
 * TA-Lib function that detects it. Shown in the trade drawer and on the Patterns page.
 */

export type PatternDirection = "bullish" | "bearish";

export interface PatternInfo {
  name: string;
  title: string;
  direction: PatternDirection;
  /** Two sentences: the shape, then the classical reading. */
  description: string;
  reference_url: string;
  talib_function: string;
}

export const TALIB_FUNCTIONS_URL = "https://ta-lib.org/functions/";

/** In F3's vocabulary order (bullish names first, as chain/filters/f3_pattern.py lists them). */
export const PATTERNS: readonly PatternInfo[] = [
  {
    name: "bullish_engulfing",
    title: "Bullish engulfing",
    direction: "bullish",
    description:
      "A down candle is followed by a larger up candle whose body covers the previous body. " +
      "Buyers took over after a sell-off, so the classical reading is a possible turn upward.",
    reference_url: "https://www.investopedia.com/terms/b/bullishengulfingpattern.asp",
    talib_function: "CDLENGULFING",
  },
  {
    name: "hammer",
    title: "Hammer",
    direction: "bullish",
    description:
      "A small body sits at the top of the range above a long lower shadow, after a decline. " +
      "The bar sold off hard but closed near its high, a rejection of lower prices that argues for a bounce.",
    reference_url: "https://en.wikipedia.org/wiki/Hammer_(candlestick_pattern)",
    talib_function: "CDLHAMMER",
  },
  {
    name: "morning_star",
    title: "Morning star",
    direction: "bullish",
    description:
      "Three bars: a long down candle, a small-bodied pause that gaps lower, then a strong up candle closing well into the first body. " +
      "The decline stalled and buyers returned, the classical sign of a bottom.",
    reference_url: "https://en.wikipedia.org/wiki/Morning_star_(candlestick_pattern)",
    talib_function: "CDLMORNINGSTAR",
  },
  {
    name: "bearish_engulfing",
    title: "Bearish engulfing",
    direction: "bearish",
    description:
      "An up candle is followed by a larger down candle whose body covers the previous body. " +
      "Sellers took over after a rally, so the classical reading is a possible turn downward.",
    reference_url: "https://www.investopedia.com/terms/b/bearishengulfingp.asp",
    talib_function: "CDLENGULFING",
  },
  {
    name: "shooting_star",
    title: "Shooting star",
    direction: "bearish",
    description:
      "A small body sits at the bottom of the range below a long upper shadow, after an advance. " +
      "The bar rallied but closed near its low, a rejection of higher prices that argues for a drop.",
    reference_url: "https://en.wikipedia.org/wiki/Shooting_star_(candlestick_pattern)",
    talib_function: "CDLSHOOTINGSTAR",
  },
  {
    name: "evening_star",
    title: "Evening star",
    direction: "bearish",
    description:
      "Three bars: a long up candle, a small-bodied pause that gaps higher, then a strong down candle closing well into the first body. " +
      "The advance stalled and sellers returned, the classical sign of a top.",
    reference_url: "https://www.investopedia.com/terms/e/eveningstar.asp",
    talib_function: "CDLEVENINGSTAR",
  },
];

/** Look a pattern up by its snake_case name; unknown names get a neutral placeholder. */
export function describePattern(name: string): PatternInfo {
  const known = PATTERNS.find((p) => p.name === name);
  if (known) return known;
  return {
    name,
    title: name.replace(/_/g, " "),
    direction: "bullish",
    description: "A pattern this viewer has no card for. The detector named it as shown.",
    reference_url: TALIB_FUNCTIONS_URL,
    talib_function: "unknown",
  };
}
