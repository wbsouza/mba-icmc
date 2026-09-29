/**
 * Why a filter vetoed: the recorded reason turned into "parameter: observed vs limit".
 *
 * The chain writes its veto reasons as prose with the numbers inline
 * (chain/filters/*.py, rules/risk_guard.py); this module only reads those numbers back
 * and names the strategy parameter that set the limit, e.g.
 * `risk_guard.daily_drawdown_limit: -0.074 < -0.05`. A reason this module does not
 * recognise is shown verbatim with no parameter, never guessed.
 */

import type { FilterRow, ParameterRow } from "./types.js";

export interface VetoWhy {
  /** The strategy parameter whose limit was breached, `null` when the veto has none. */
  parameter: string | null;
  /** `parameter: observed <cmp> limit`, or the reason itself when unparsed. */
  text: string;
}

/** A number as the chain printed it, shortened to what a reader needs (−0.0744 → −0.074). */
export function short(raw: string): string {
  const value = Number(raw);
  if (!Number.isFinite(value)) return raw;
  if (Number.isInteger(value)) return String(value);
  const rounded = Number(value.toPrecision(3));
  return String(rounded);
}

function line(parameter: string | null, observed: string, cmp: string, limit: string): VetoWhy {
  const head = parameter === null ? "" : `${parameter}: `;
  return { parameter, text: `${head}${short(observed)} ${cmp} ${short(limit)}` };
}

function paramValue(parameters: readonly ParameterRow[], key: string): string | null {
  return parameters.find((p) => p.key === key)?.value ?? null;
}

const RISK_CAPS: ReadonlyArray<[RegExp, string, string]> = [
  [/^portfolio_at_risk (\S+) exceeds cap (\S+)$/, "risk_guard.portfolio_at_risk_cap", ">"],
  [/^daily_pnl_fraction (\S+) is below limit (\S+)$/, "risk_guard.daily_drawdown_limit", "<"],
  [/^weekly_pnl_fraction (\S+) is below limit (\S+)$/, "risk_guard.weekly_drawdown_limit", "<"],
  [/^open_trade_count (\S+) has reached the cap (\S+)$/, "risk_guard.max_concurrent_trades_per_account", "≥"],
  [/^leverage (\S+) exceeds cap (\S+)$/, "risk_guard.max_leverage", ">"],
];

function riskWhy(reason: string): VetoWhy[] {
  const out: VetoWhy[] = [];
  for (const part of reason.split("; ")) {
    const hit = RISK_CAPS.map(([re, key, cmp]) => ({ m: re.exec(part.trim()), key, cmp })).find((x) => x.m !== null);
    if (hit?.m?.[1] !== undefined && hit.m[2] !== undefined) out.push(line(hit.key, hit.m[1], hit.cmp, hit.m[2]));
    else out.push({ parameter: null, text: part.trim() });
  }
  return out;
}

function newsWhy(reason: string): VetoWhy[] {
  const m = /event_intensity=(\S+) <= veto threshold (\S+)/.exec(reason);
  return m?.[1] !== undefined && m[2] !== undefined
    ? [line("news_context.event_intensity_veto_threshold", m[1], "≤", m[2])]
    : [{ parameter: null, text: reason }];
}

function activityWhy(reason: string, parameters: readonly ParameterRow[]): VetoWhy[] {
  const m = /relative tick activity (\S+)/.exec(reason);
  const limit = paramValue(parameters, "volume_strength.min_relative_activity");
  if (m?.[1] !== undefined && limit !== null) return [line("volume_strength.min_relative_activity", m[1], "<", limit)];
  return [{ parameter: m ? "volume_strength.min_relative_activity" : null, text: reason }];
}

function capitalWhy(reason: string): VetoWhy[] {
  const rr = /reward:risk below capital_mgmt\.min_reward_risk (\S+): (.+?)(?:;|$)/.exec(reason);
  if (rr?.[1] !== undefined && rr[2] !== undefined) {
    const sides = rr[2].split(", ").map((s) => s.split(" ")).filter((s) => s[1] !== undefined).map((s) => `${s[0]} ${short(s[1] ?? "")}`);
    return [{ parameter: "capital_mgmt.min_reward_risk", text: `capital_mgmt.min_reward_risk: ${sides.join(", ")} < ${short(rr[1])}` }];
  }
  const margin = /insufficient margin: proposed lot (\S+) needs (\S+) but only (\S+) is available/.exec(reason);
  if (margin?.[1] !== undefined && margin[2] !== undefined && margin[3] !== undefined) {
    return [{ parameter: "capital_mgmt.assumed_leverage", text: `capital_mgmt.assumed_leverage: lot ${short(margin[1])} needs margin ${short(margin[2])} > available ${short(margin[3])}` }];
  }
  return [{ parameter: null, text: reason }];
}

function trendWhy(reason: string): VetoWhy[] {
  const m = /trend_direction=(\S+) vs\. higher_tf_trend_direction=(\S+)/.exec(reason);
  return m?.[1] !== undefined && m[2] !== undefined
    ? [{ parameter: "price_features.ema_higher_tf", text: `price_features.ema_higher_tf: primary trend ${short(m[1])} vs higher timeframe ${short(m[2])}` }]
    : [{ parameter: null, text: reason }];
}

/** Every breach behind one vetoing filter row; empty when the row did not veto. */
export function vetoWhy(filter: FilterRow, parameters: readonly ParameterRow[] = []): VetoWhy[] {
  if (filter.veto === 0) return [];
  const name = filter.filter_name.toLowerCase();
  if (name.startsWith("f5")) return riskWhy(filter.reason);
  if (name.startsWith("f4")) return newsWhy(filter.reason);
  if (name.startsWith("volume")) return activityWhy(filter.reason, parameters);
  if (name.startsWith("f6")) return capitalWhy(filter.reason);
  if (name.startsWith("f1")) return trendWhy(filter.reason);
  return [{ parameter: null, text: filter.reason }];
}

/** The one line the log shows for a vetoed bar: the breaches joined, or `null` without a veto. */
export function vetoLine(filter: FilterRow | null | undefined, parameters: readonly ParameterRow[] = []): string | null {
  if (!filter || filter.veto === 0) return null;
  return vetoWhy(filter, parameters).map((w) => w.text).join("; ");
}

/** The parameter key the log groups consecutive vetoes by (`null` for unparsed vetoes). */
export function vetoParameter(filter: FilterRow | null | undefined, parameters: readonly ParameterRow[] = []): string | null {
  if (!filter || filter.veto === 0) return null;
  return vetoWhy(filter, parameters)[0]?.parameter ?? null;
}
