/** Presentation helpers: numbers, prices and times as the tables show them. */

export function pct(fraction: number | null, digits = 2): string {
  if (fraction === null || Number.isNaN(fraction)) return "n/a";
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function signedPct(value: number | null, digits = 2): string {
  if (value === null || Number.isNaN(value)) return "n/a";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function money(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "n/a";
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Quote precision: JPY-style prices (> 20) carry 3 decimals, everything else 5. */
export function priceDecimals(sample: number): number {
  return Math.abs(sample) > 20 ? 3 : 5;
}

export function price(value: number | null, decimals: number): string {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toFixed(decimals);
}

export function lots(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

/** `2016-03-22T14:00:00+00:00` -> `2016-03-22 14:00` (UTC, as recorded). */
export function when(iso: string): string {
  return iso.replace("T", " ").replace(/:\d\d(\.\d+)?(\+00:00|Z)$/, "");
}

export function minutes(total: number): string {
  if (total < 60) return `${Math.round(total)} min`;
  if (total < 1440) return `${(total / 60).toFixed(1)} h`;
  return `${(total / 1440).toFixed(1)} d`;
}

export function barLabel(barMinutes: number): string {
  if (barMinutes % 1440 === 0) return `D${barMinutes / 1440}`;
  if (barMinutes % 60 === 0) return `H${barMinutes / 60}`;
  return `M${barMinutes}`;
}

export const EXIT_KIND_LABELS: Record<string, string> = {
  stop: "Stop loss",
  target: "Take profit",
  trail_stop: "Trailing stop",
  liquidation: "Liquidation",
  reversal: "Reversal",
  unknown: "Unknown",
};
