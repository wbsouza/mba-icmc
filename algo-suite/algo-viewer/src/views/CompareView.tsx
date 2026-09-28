import { useMemo } from "react";
import type { Database } from "sql.js";
import { equitySamples, monthlyReturns } from "../db/queries";
import type { RunRow } from "../model/types";
import { pivotMonthly, rebase, REBASE_TO } from "../model/rebase";
import { signedPct, barLabel } from "../model/format";
import { LineChart, type LineSeriesSpec } from "../charts/LineChart";
import { seriesColor } from "../charts/support";

interface Props {
  db: Database;
  runs: RunRow[];
  dark: boolean;
  onOpen: (runId: string) => void;
}

export function runLabel(run: RunRow): string {
  return `${run.strategy} · ${barLabel(run.bar_minutes)} · ${run.start}`;
}

/** Overlaid equity curves re-based to 10,000 plus the month-by-month table. */
export function CompareView({ db, runs, dark, onOpen }: Props) {
  const series: LineSeriesSpec[] = useMemo(
    () => runs.map((run, i) => ({
      id: run.run_id,
      label: runLabel(run),
      color: seriesColor(i),
      points: rebase(equitySamples(db, run.run_id)).map((p) => ({ time: p.time, value: p.equity })),
    })),
    [db, runs],
  );
  const pivot = useMemo(
    () => pivotMonthly(runs.map((run) => ({ runId: run.run_id, label: runLabel(run), months: monthlyReturns(db, run.run_id) }))),
    [db, runs],
  );
  if (runs.length === 0) {
    return <section className="panel"><p className="muted">Select runs in the Runs table to compare them.</p></section>;
  }
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
