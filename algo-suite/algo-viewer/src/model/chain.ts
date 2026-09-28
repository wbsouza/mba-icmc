/**
 * The chain as the run page draws it: which filters exist, what each does, and which of
 * the run's parameters belong to it (by config section, with the few keys that cross
 * sections assigned explicitly). Mirrors algo-backtest/src/algo_backtest/chain/filters/.
 */

import type { ParameterRow } from "./types";

export interface FilterInfo {
  /** Lower-case name as the run's `filters` list and decisions record it. */
  name: string;
  /** Short label for the node. */
  label: string;
  /** Full title for the details panel. */
  title: string;
  /** What the filter does, in plain English. */
  description: string;
  reads: string;
  emits: string;
  /** Config sections whose keys belong to this filter. */
  sections: string[];
  /** Individual keys claimed from shared sections (checked before `sections`). */
  keys: string[];
}

export const FILTERS: readonly FilterInfo[] = [
  {
    name: "f1_trend", label: "F1 Trend", title: "F1 Trend",
    description: "Reads the fast/slow EMA slope and the higher-timeframe trend; votes BUY or SELL with the trend and vetoes the bar when the primary and higher-timeframe directions conflict.",
    reads: "closed bars (EMA fast/slow, higher-timeframe EMA, swing lookback)",
    emits: "trend_direction, trend_strength, higher_tf_trend_direction; enrichment trend_score",
    sections: ["perception_source"],
    keys: ["price_features.bar_minutes", "price_features.ema_fast", "price_features.ema_slow", "price_features.ema_higher_tf", "price_features.swing_lookback_bars"],
  },
  {
    name: "f2_indicator", label: "F2 RSI / MACD", title: "F2 RSI / MACD",
    description: "Momentum confirmation: RSI against its midline and the MACD histogram against its threshold; BUY when both point up, SELL when both point down, NEUTRAL otherwise. Never vetoes.",
    reads: "RSI and MACD of the closed bars",
    emits: "rsi, macd_hist and the thresholds it compared against",
    sections: ["indicator"],
    keys: ["price_features.rsi_period", "price_features.macd_fast", "price_features.macd_slow", "price_features.macd_signal"],
  },
  {
    name: "f3_pattern", label: "F3 Candlestick", title: "F3 Candlestick pattern",
    description: "Names the candlestick pattern the detector found on the closed bar (six-pattern TA-Lib vocabulary) and votes with its polarity; ABSTAINs when there is none. Never vetoes.",
    reads: "the detector's candlestick_pattern feature",
    emits: "the detected pattern name (see the Patterns page)",
    sections: ["pattern"],
    keys: [],
  },
  {
    name: "f4_news_context", label: "F4 News context", title: "F4 News context",
    description: "Vetoes the bar during a high-risk news window (GDELT event intensity below the threshold) and reads the net sentiment when a source is present; ABSTAINs otherwise.",
    reads: "news_event_intensity and, when present, news_sentiment_score",
    emits: "enrichment news_event_intensity",
    sections: ["news_context"],
    keys: [],
  },
  {
    name: "volume_strength", label: "Activity ratio", title: "Activity ratio (quote-tick volume strength)",
    description: "Compares the bar's quote-tick activity with its recent average and vetoes quiet bars below the minimum relative activity; ABSTAINs when active enough.",
    reads: "tick_count of the closed bars over the lookback",
    emits: "relative tick activity",
    sections: ["volume_strength"],
    keys: [],
  },
  {
    name: "f5_risk_guard", label: "F5 Risk guard", title: "F5 Risk guard",
    description: "Account-level caps: daily and weekly drawdown limits, maximum leverage, concurrent trades and portfolio at risk; vetoes when any cap is breached.",
    reads: "the account state the engine reports",
    emits: "which cap was breached, if any",
    sections: ["risk_guard"],
    keys: [],
  },
  {
    name: "f6_capital_mgmt", label: "F6 Capital mgmt", title: "F6 Capital management",
    description: "Builds the trade plan: stop distance (ATR or swing based, floored), lot size from the risk per trade, targets and trailing steps, reward:risk check; vetoes when margin is insufficient or reward:risk too low.",
    reads: "ATR/swing distances, equity, leverage",
    emits: "enrichment proposed_lot_size and trade_plan",
    sections: ["capital_mgmt", "execution"],
    keys: ["price_features.atr_period"],
  },
  {
    name: "f7_meta_learner", label: "F7 Meta-learner", title: "F7 Meta-learner",
    description: "The terminal rule: the trained model's probability of an up move against theta_high/theta_low decides BUY, SELL or HOLD; with the regime gate on, a trade must also agree with F1's regime.",
    reads: "the accumulated features of the chain",
    emits: "p_hat and the decision",
    sections: ["meta_learner"],
    keys: [],
  },
];

/** The filter description for a recorded name, matching case-insensitively by prefix (F1_trend = f1_trend). */
export function describeFilter(name: string): FilterInfo {
  const lower = name.toLowerCase();
  const numbered = /^f\d/.exec(lower)?.[0];
  const known = FILTERS.find((f) => f.name === lower || (numbered !== undefined && f.name.startsWith(numbered)));
  return known ?? {
    name: lower, label: name, title: name, description: "A filter this viewer has no description for.",
    reads: "", emits: "", sections: [lower], keys: [],
  };
}

/** The run's `filters` parameter as the chain order, or null when the run recorded none. */
export function chainOrder(parameters: readonly ParameterRow[]): string[] | null {
  const row = parameters.find((p) => p.key === "filters");
  if (row === undefined) return null;
  const parsed: unknown = JSON.parse(row.value);
  return Array.isArray(parsed) ? parsed.map(String) : null;
}

/** The run's parameters that belong to `filter`, by explicit key first, then by section. */
export function parametersFor(filter: FilterInfo, parameters: readonly ParameterRow[]): ParameterRow[] {
  const claimedElsewhere = new Set(FILTERS.filter((f) => f !== filter).flatMap((f) => f.keys));
  return parameters.filter((p) => {
    if (filter.keys.includes(p.key)) return true;
    if (claimedElsewhere.has(p.key)) return false;
    const section = p.key.split(".")[0] ?? p.key;
    return p.key.includes(".") && filter.sections.includes(section);
  });
}
