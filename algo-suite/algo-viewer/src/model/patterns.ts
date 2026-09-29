/**
 * The six candlestick patterns F3 recognises (perception/candlestick.py, TA-Lib CDL*):
 * one card each with the direction it argues for, a two-sentence plain-English
 * description (the shape, then the classical reading), a public reference page and the
 * TA-Lib function that detects it. Shown in the trade drawer and on the Patterns page.
 */

export type PatternDirection = "bullish" | "bearish";

/** One candle of a schematic, on a 0..100 price scale (open/close = body, high/low = wicks). */
export interface SchematicCandle {
  open: number;
  close: number;
  high: number;
  low: number;
}

export interface PatternInfo {
  name: string;
  title: string;
  direction: PatternDirection;
  /** Two sentences: the shape, then the classical reading. */
  description: string;
  reference_url: string;
  talib_function: string;
  /** The candles the schematic draws, left to right, with the geometry the name implies. */
  schematic: SchematicCandle[];
  /** One line under the drawing. */
  caption: string;
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
    schematic: [{ open: 60, close: 50, high: 64, low: 46 }, { open: 45, close: 72, high: 76, low: 42 }],
    caption: "A small down candle, then a larger up body that covers it.",
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
    schematic: [{ open: 70, close: 76, high: 78, low: 40 }],
    caption: "Small body at the top; lower shadow at least twice the body.",
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
    schematic: [{ open: 80, close: 40, high: 84, low: 36 }, { open: 34, close: 31, high: 37, low: 27 }, { open: 38, close: 70, high: 74, low: 35 }],
    caption: "Long down candle, a small body gapped below it, a long up candle past the midpoint.",
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
    schematic: [{ open: 50, close: 60, high: 64, low: 46 }, { open: 65, close: 38, high: 68, low: 34 }],
    caption: "A small up candle, then a larger down body that covers it.",
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
    schematic: [{ open: 30, close: 24, high: 60, low: 22 }],
    caption: "Small body at the bottom; upper shadow at least twice the body.",
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
    schematic: [{ open: 20, close: 60, high: 64, low: 16 }, { open: 66, close: 69, high: 73, low: 63 }, { open: 62, close: 30, high: 65, low: 26 }],
    caption: "Long up candle, a small body gapped above it, a long down candle past the midpoint.",
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
    schematic: [],
    caption: "",
  };
}

export const SCHEMATIC_WIDTH = 120;
export const SCHEMATIC_HEIGHT = 80;

export interface SchematicShape {
  /** The body as a rect (x, y, width, height in SVG units), never thinner than 1 unit. */
  body: { x: number; y: number; width: number; height: number };
  /** The wick as a vertical line through the body's centre. */
  wick: { x: number; y1: number; y2: number };
  up: boolean;
}

/** Project a pattern's candles onto the 120×80 drawing (price 0..100 -> y 76..4, top down). */
export function schematicShapes(candles: readonly SchematicCandle[]): SchematicShape[] {
  const y = (price: number) => 4 + (100 - price) * 0.72;
  const slot = SCHEMATIC_WIDTH / Math.max(candles.length, 1);
  const width = Math.min(24, slot * 0.5);
  return candles.map((c, i) => {
    const x = slot * i + slot / 2;
    const top = Math.min(y(c.open), y(c.close));
    const height = Math.max(1, Math.abs(y(c.open) - y(c.close)));
    return {
      body: { x: x - width / 2, y: top, width, height },
      wick: { x, y1: y(c.high), y2: y(c.low) },
      up: c.close >= c.open,
    };
  });
}
