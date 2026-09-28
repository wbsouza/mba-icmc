/**
 * The six candlestick patterns F3 recognises (perception/candlestick.py, TA-Lib CDL*),
 * with a plain-English description and the direction each one argues for.
 */

export type PatternDirection = "bullish" | "bearish";

export interface PatternInfo {
  name: string;
  label: string;
  direction: PatternDirection;
  description: string;
}

export const PATTERNS: Record<string, PatternInfo> = {
  bullish_engulfing: {
    name: "bullish_engulfing",
    label: "Bullish engulfing",
    direction: "bullish",
    description:
      "A down candle followed by a larger up candle whose body covers the previous body: " +
      "buyers took over after a sell-off, so the reading is a possible turn upward.",
  },
  hammer: {
    name: "hammer",
    label: "Hammer",
    direction: "bullish",
    description:
      "A small body at the top of the range with a long lower shadow: the bar sold off " +
      "hard but closed near its high, a rejection of lower prices that argues for a bounce.",
  },
  morning_star: {
    name: "morning_star",
    label: "Morning star",
    direction: "bullish",
    description:
      "Three bars: a long down candle, a small-bodied pause, then a strong up candle " +
      "closing well into the first body. The decline stalled and buyers returned.",
  },
  bearish_engulfing: {
    name: "bearish_engulfing",
    label: "Bearish engulfing",
    direction: "bearish",
    description:
      "An up candle followed by a larger down candle whose body covers the previous body: " +
      "sellers took over after a rally, so the reading is a possible turn downward.",
  },
  shooting_star: {
    name: "shooting_star",
    label: "Shooting star",
    direction: "bearish",
    description:
      "A small body at the bottom of the range with a long upper shadow: the bar rallied " +
      "but closed near its low, a rejection of higher prices that argues for a drop.",
  },
  evening_star: {
    name: "evening_star",
    label: "Evening star",
    direction: "bearish",
    description:
      "Three bars: a long up candle, a small-bodied pause, then a strong down candle " +
      "closing well into the first body. The advance stalled and sellers returned.",
  },
};

/** Look a pattern up by its snake_case name; unknown names get a neutral placeholder. */
export function describePattern(name: string): PatternInfo {
  const known = PATTERNS[name];
  if (known) return known;
  return {
    name,
    label: name.replace(/_/g, " "),
    direction: "bullish",
    description: "A pattern this viewer has no description for; the detector named it as shown.",
  };
}
