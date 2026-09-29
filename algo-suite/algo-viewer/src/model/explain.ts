/**
 * "Why we entered": turn each filter's recorded reason into a short plain-English line.
 *
 * The reason strings are the chain's own audit text (chain/filters/*.py); the parsing here
 * only reads the `key=value` pairs those filters write and never invents a number. When a
 * filter is unknown or a field is absent, the recorded reason is shown verbatim.
 */

import type { FilterRow, ParameterRow } from "./types";
import { describePattern } from "./patterns";

export interface Explanation {
  /** Short filter title, e.g. "F1 · Trend". */
  title: string;
  /** One-sentence plain-English reading of the recorded reason. */
  summary: string;
  /** Extra lines (numbers, thresholds), shown smaller. */
  details: string[];
  /** The recorded reason, verbatim. */
  reason: string;
  recommendation: string;
  veto: boolean;
  /** Set for F3 when a pattern was detected. */
  pattern: ReturnType<typeof describePattern> | null;
}

/** `a=1.0, b=x; c=2` -> {a: "1.0", b: "x", c: "2"} (also reads `(key=value)` inside prose). */
export function parseFields(reason: string): Record<string, string> {
  const out: Record<string, string> = {};
  const re = /([A-Za-z_][A-Za-z0-9_]*)=([^,;()\s]+)/g;
  for (const match of reason.matchAll(re)) {
    const key = match[1];
    const value = match[2];
    if (key !== undefined && value !== undefined) out[key] = value;
  }
  return out;
}

function num(fields: Record<string, string>, key: string): number | null {
  const raw = fields[key];
  if (raw === undefined) return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function fixed(value: number | null, digits: number): string {
  return value === null ? "n/a" : value.toFixed(digits);
}

function directionWord(value: number | null): string {
  if (value === null) return "unknown";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

function param(parameters: readonly ParameterRow[], key: string): string | null {
  const hit = parameters.find((p) => p.key === key);
  return hit ? hit.value : null;
}

function base(filter: FilterRow, title: string, summary: string, details: string[]): Explanation {
  return {
    title,
    summary,
    details,
    reason: filter.reason,
    recommendation: filter.recommendation,
    veto: filter.veto !== 0,
    pattern: null,
  };
}

function explainTrend(filter: FilterRow): Explanation {
  const f = parseFields(filter.reason);
  const primary = num(f, "trend_direction");
  const higher = num(f, "higher_tf_trend_direction");
  const strength = num(f, "trend_strength");
  if (filter.veto !== 0) {
    return base(filter, "F1 · Trend", `The primary trend (${directionWord(primary)}) disagrees with the higher timeframe (${directionWord(higher)}); the chain stood aside.`, []);
  }
  if (primary === null) return base(filter, "F1 · Trend", filter.reason, []);
  return base(
    filter,
    "F1 · Trend",
    `Primary trend ${directionWord(primary)}, higher-timeframe trend ${directionWord(higher)} → leaning ${filter.recommendation}.`,
    [`trend strength ${fixed(strength, 2)}`],
  );
}

function explainIndicator(filter: FilterRow): Explanation {
  const f = parseFields(filter.reason);
  const rsi = num(f, "rsi");
  const midline = num(f, "rsi_midline");
  const hist = num(f, "macd_hist");
  const threshold = num(f, "macd_hist_threshold");
  if (rsi === null) return base(filter, "F2 · RSI / MACD", filter.reason, []);
  const rsiSide = midline === null ? "" : rsi > midline ? `above its ${fixed(midline, 0)} midline` : `below its ${fixed(midline, 0)} midline`;
  const macdSide = hist === null ? "" : hist > (threshold ?? 0) ? "positive" : "negative";
  return base(
    filter,
    "F2 · RSI / MACD",
    `RSI ${fixed(rsi, 1)} ${rsiSide}, MACD histogram ${macdSide} → ${filter.recommendation}.`,
    [`macd_hist ${fixed(hist, 5)} vs threshold ${fixed(threshold, 5)}`],
  );
}

function explainPattern(filter: FilterRow): Explanation {
  if (filter.pattern_name === null) {
    return base(filter, "F3 · Candlestick pattern", "No candlestick pattern on the decision bar; F3 abstained.", []);
  }
  const info = describePattern(filter.pattern_name);
  const out = base(
    filter,
    "F3 · Candlestick pattern",
    `${info.title} (${info.direction}) → ${filter.recommendation}.`,
    [info.description],
  );
  out.pattern = info;
  return out;
}

function explainNews(filter: FilterRow): Explanation {
  const f = parseFields(filter.reason);
  const intensity = num(f, "event_intensity") ?? num(f, "news_event_intensity");
  const summary = filter.veto !== 0
    ? "A high-risk news window was active; the chain stood aside."
    : `News intensity ${fixed(intensity, 3)}: no active high-risk event, no sentiment signal.`;
  return base(filter, "F4 · News context", summary, []);
}

function explainActivity(filter: FilterRow, parameters: readonly ParameterRow[]): Explanation {
  const match = /relative tick activity ([0-9.]+)/.exec(filter.reason);
  const ratio = match?.[1] !== undefined ? Number(match[1]) : null;
  const threshold = param(parameters, "volume_strength.min_relative_activity");
  const verb = filter.veto !== 0 ? "below" : "at or above";
  const summary = ratio === null
    ? filter.reason
    : `Tick activity ${ratio.toFixed(2)}× its recent average, ${verb} the ${threshold ?? "configured"} minimum.`;
  return base(filter, "Activity ratio", summary, []);
}

function explainRisk(filter: FilterRow): Explanation {
  const summary = filter.veto !== 0 ? `A risk cap was breached: ${filter.reason}.` : "No risk-guard cap (daily/weekly drawdown, leverage, concurrent trades) was breached.";
  return base(filter, "F5 · Risk guard", summary, []);
}

function explainCapital(filter: FilterRow): Explanation {
  const lot = /lot size ([0-9.]+)/.exec(filter.reason)?.[1];
  const rr = /reward:risk long ([0-9.]+)/.exec(filter.reason)?.[1];
  const stop = /\(long ([0-9.]+),/.exec(filter.reason)?.[1];
  const summary = lot === undefined
    ? filter.reason
    : `Margin sufficient for ${Number(lot).toFixed(2)} lots; stop ${stop ?? "n/a"} pips, reward:risk ${rr ?? "n/a"}.`;
  return base(filter, "F6 · Capital management", summary, []);
}

function explainMeta(filter: FilterRow): Explanation {
  const f = parseFields(filter.reason);
  const p = num(f, "p_hat");
  const high = num(f, "theta_high");
  const low = num(f, "theta_low");
  const gate = f["regime_gate"];
  const regime = f["regime"];
  if (p === null) return base(filter, "F7 · Meta-learner", filter.reason, []);
  let verdict = "between the thresholds → HOLD";
  if (high !== null && p >= high) verdict = `at or above θ_high ${fixed(high, 2)} → BUY`;
  else if (low !== null && p <= low) verdict = `at or below θ_low ${fixed(low, 2)} → SELL`;
  const gateText = gate === "True" ? `regime gate on (regime ${regime ?? "n/a"})` : "regime gate off";
  return base(filter, "F7 · Meta-learner", `p̂ = ${fixed(p, 3)}, ${verdict}.`, [`θ_high ${fixed(high, 2)}, θ_low ${fixed(low, 2)}, ${gateText}`]);
}

/** Plain-English reading of one filter's row, by filter name (case-insensitive). */
export function explainFilter(filter: FilterRow, parameters: readonly ParameterRow[] = []): Explanation {
  const name = filter.filter_name.toLowerCase();
  if (name.startsWith("f1")) return explainTrend(filter);
  if (name.startsWith("f2")) return explainIndicator(filter);
  if (name.startsWith("f3")) return explainPattern(filter);
  if (name.startsWith("f4")) return explainNews(filter);
  if (name.startsWith("volume")) return explainActivity(filter, parameters);
  if (name.startsWith("f5")) return explainRisk(filter);
  if (name.startsWith("f6")) return explainCapital(filter);
  if (name.startsWith("f7")) return explainMeta(filter);
  return base(filter, filter.filter_name, filter.reason, []);
}
