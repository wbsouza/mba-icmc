import { useMemo } from "react";
import type { ApiClient } from "../api/client";
import { Pending, useAsync } from "../api/useAsync";
import type { EquitySample, MonthlyReturn, RunRow } from "../model/types";
import { pivotMonthly, rebase, REBASE_TO } from "../model/rebase";
import { signedPct, barLabel } from "../model/format";
import { LineChart, type LineSeriesSpec } from "../charts/LineChart";
import { seriesColor } from "../charts/support";

interface Props {
  api: ApiClient;
  runs: RunRow[];
  dark: boolean;
  onOpen: (runId: string) => void;
}

export function runLabel(run: RunRow): string {
  return `${run.strategy} · ${barLabel(run.bar_minutes)} · ${run.start}`;
}

interface Loaded {
  equity: Record<string, EquitySample[]>;
  monthly: Record<string, MonthlyReturn[]>;
}

/** Overlaid equity curves re-based to 10,000 plus the month-by-month table. */
export function CompareView({ api, runs, dark, onOpen }: Props) {
  const ids = runs.map((r) => r.run_id).join(",");
  const state = useAsync<Loaded>(async () => {
    const equity: Record<string, EquitySample[]> = {};
    const monthly: Record<string, MonthlyReturn[]> = {};
    await Promise.all(runs.map(async (run) => {
      [equity[run.run_id], monthly[run.run_id]] = await Promise.all([api.equity(run.run_id), api.monthly(run.run_id)]);
    }));
    return { equity, monthly };
  }, [api, ids]);
  const series: LineSeriesSpec[] = useMemo(
    () => state.data === null ? [] : runs.map((run, i) => ({
      id: run.run_id,
      label: runLabel(run),
      color: seriesColor(i),
      points: rebase(state.data?.equity[run.run_id] ?? []).map((p) => ({ time: p.time, value: p.equity })),
    })),
    [state.data, runs],
  );
  const pivot = useMemo(
    () => state.data === null ? [] : pivotMonthly(runs.map((run) => ({ runId: run.run_id, label: runLabel(run), months: state.data?.monthly[run.run_id] ?? [] }))),
    [state.data, runs],
  );
  if (runs.length === 0) {
    return <section className="panel"><p className="muted">Select runs in the Runs table to compare them.</p></section>;
  }
  if (state.data === null) return <Pending state={state} label="equity curves" />;
  return (
    <>
      <section className="panel" aria-label="Equity comparison">
        <h2>Equity re-based to {REBASE_TO.toLocaleString("en-US")}</h2>
        <LineChart series={series} dark={dark} />
        <div className="legend">
          {series.map((s, i) => {
            const last = s.points[s.points.length - 1];
            return (
              <span key={s.id}>
                <span className="swatch" style={{ background: seriesColor(i) }} />
                <a href={`#/run/${s.id}`} onClick={(e) => { e.preventDefault(); onOpen(s.id); }}>{s.label}</a>
                {last ? <span className={last.value >= REBASE_TO ? " up" : " down"}> {signedPct((last.value / REBASE_TO - 1) * 100)}</span> : null}
              </span>
            );
          })}
        </div>
      </section>
      <section className="panel" aria-label="Monthly returns">
        <h2>Month by month</h2>
        <table className="grid" data-testid="monthly-table">
          <thead>
            <tr>
              <th>Month</th>
              {runs.map((run) => <th key={run.run_id} className="num">{runLabel(run)}</th>)}
            </tr>
          </thead>
          <tbody>
            {pivot.map((row) => (
              <tr key={row.month}>
                <td>{row.month}</td>
                {runs.map((run) => {
                  const v = row.cells[run.run_id] ?? null;
                  return <td key={run.run_id} className={`num ${v === null ? "muted" : v >= 0 ? "up" : "down"}`}>{v === null ? "—" : signedPct(v)}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
