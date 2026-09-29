import { useMemo, useState } from "react";
import type { RunRow } from "../model/types";
import { barLabel, pct, signedPct } from "../model/format";

export type SortKey = keyof Pick<
  RunRow,
  "job" | "strategy" | "bar_minutes" | "start" | "closed_trades" | "total_return" | "max_drawdown" | "win_rate"
>;

export interface RunsFilter {
  text: string;
  barMinutes: number | null;
}

/** Pure: the runs matching a text filter (job/strategy/symbol/run id) and a bar size. */
export function filterRuns(runs: readonly RunRow[], filter: RunsFilter): RunRow[] {
  const needle = filter.text.trim().toLowerCase();
  return runs.filter((run) => {
    if (filter.barMinutes !== null && run.bar_minutes !== filter.barMinutes) return false;
    if (needle === "") return true;
    return [run.job, run.strategy, run.symbol, run.run_id].some((v) => v.toLowerCase().includes(needle));
  });
}

/** Pure: runs sorted by one column, nulls last. */
export function sortRuns(runs: readonly RunRow[], key: SortKey, descending: boolean): RunRow[] {
  const sign = descending ? -1 : 1;
  return [...runs].sort((a, b) => {
    const x = a[key];
    const y = b[key];
    if (x === null && y === null) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    if (typeof x === "number" && typeof y === "number") return sign * (x - y);
    return sign * String(x).localeCompare(String(y));
  });
}

interface Props {
  runs: RunRow[];
  selected: ReadonlySet<string>;
  onToggle: (runId: string) => void;
  onOpen: (runId: string) => void;
  onCompare: () => void;
}

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "job", label: "Job", numeric: false },
  { key: "strategy", label: "Strategy", numeric: false },
  { key: "bar_minutes", label: "Bars", numeric: false },
  { key: "start", label: "Span", numeric: false },
  { key: "closed_trades", label: "Trades", numeric: true },
  { key: "total_return", label: "Return", numeric: true },
  { key: "max_drawdown", label: "Max DD", numeric: true },
  { key: "win_rate", label: "Win %", numeric: true },
];

export function RunsTable({ runs, selected, onToggle, onOpen, onCompare }: Props) {
  const [text, setText] = useState("");
  const [barMinutes, setBarMinutes] = useState<number | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("total_return");
  const [descending, setDescending] = useState(true);
  const barSizes = useMemo(() => [...new Set(runs.map((r) => r.bar_minutes))].sort((a, b) => a - b), [runs]);
  const visible = useMemo(
    () => sortRuns(filterRuns(runs, { text, barMinutes }), sortKey, descending),
    [runs, text, barMinutes, sortKey, descending],
  );
  const sortBy = (key: SortKey) => {
    if (key === sortKey) setDescending(!descending);
    else {
      setSortKey(key);
      setDescending(key === "total_return" || key === "closed_trades" || key === "win_rate");
    }
  };
  return (
    <section className="panel" aria-label="Runs">
      <div className="toolbar">
        <input aria-label="Filter runs" placeholder="Filter by job, strategy, symbol or run id" value={text} onChange={(e) => setText(e.target.value)} />
        <select aria-label="Bar size" value={barMinutes ?? ""} onChange={(e) => setBarMinutes(e.target.value === "" ? null : Number(e.target.value))}>
          <option value="">All bar sizes</option>
          {barSizes.map((m) => (
            <option key={m} value={m}>{barLabel(m)}</option>
          ))}
        </select>
        <span className="muted">{visible.length} of {runs.length} runs · {selected.size} selected</span>
        <button className="primary" disabled={selected.size < 1} onClick={onCompare}>Compare selected</button>
      </div>
      <table className="grid" data-testid="runs-table">
        <thead>
          <tr>
            <th aria-label="select" />
            {COLUMNS.map((c) => (
              <th key={c.key} className={`${c.numeric ? "num " : ""}${c.key === sortKey ? "sorted" : ""}`} onClick={() => sortBy(c.key)}>
                {c.label}{c.key === sortKey ? (descending ? " ▼" : " ▲") : ""}
              </th>
            ))}
            <th>Run id</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((run) => (
            <tr key={run.run_id} className="clickable" data-run-id={run.run_id} onClick={() => onOpen(run.run_id)}>
              <td onClick={(e) => e.stopPropagation()}>
                <input type="checkbox" aria-label={`select ${run.run_id}`} checked={selected.has(run.run_id)} onChange={() => onToggle(run.run_id)} />
              </td>
              <td>{run.job}</td>
              <td>{run.strategy}</td>
              <td>{barLabel(run.bar_minutes)}</td>
              <td>{run.start} → {run.end}</td>
              <td className="num">{run.closed_trades}</td>
              <td className={`num ${run.total_return >= 0 ? "up" : "down"}`}>{signedPct(run.total_return * 100)}</td>
              <td className="num">{pct(run.max_drawdown)}</td>
              <td className="num">{pct(run.win_rate, 0)}</td>
              <td className="mono">{run.run_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
