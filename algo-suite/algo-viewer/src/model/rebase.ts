/** Comparison maths: re-basing equity curves and pivoting monthly returns. */

import type { EquitySample, MonthlyReturn } from "./types";

export const REBASE_TO = 10000;

export interface RebasedPoint {
  time: string;
  equity: number;
}

/** Scale a run's curve so its first sample equals `base` (10,000 by default). */
export function rebase(samples: readonly EquitySample[], base = REBASE_TO): RebasedPoint[] {
  const first = samples[0];
  if (first === undefined) return [];
  if (first.equity <= 0) {
    throw new Error(`cannot re-base a curve that starts at equity ${first.equity}`);
  }
  const factor = base / first.equity;
  return samples.map((s) => ({ time: s.time, equity: s.equity * factor }));
}

export interface MonthlyColumn {
  runId: string;
  label: string;
  months: readonly MonthlyReturn[];
}

export interface MonthlyPivotRow {
  month: string;
  /** Return % per run id, null where the run has no sample in that month. */
  cells: Record<string, number | null>;
}

/** One row per month covered by any run, the runs' returns side by side. */
export function pivotMonthly(columns: readonly MonthlyColumn[]): MonthlyPivotRow[] {
  const months = new Set<string>();
  for (const column of columns) for (const m of column.months) months.add(m.month);
  return [...months].sort().map((month) => {
    const cells: Record<string, number | null> = {};
    for (const column of columns) {
      const hit = column.months.find((m) => m.month === month);
      cells[column.runId] = hit ? hit.return_pct : null;
    }
    return { month, cells };
  });
}
