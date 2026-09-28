import { useState } from "react";
import type { ApiClient } from "../api/client";
import { Pending, useAsync } from "../api/useAsync";
import type { DecisionDetail, DecisionLogGroup, DecisionLogMode, DecisionLogPage, ParameterRow } from "../model/types";
import { when } from "../model/format";
import { ChainSteps } from "./ChainSteps";

interface Props {
  api: ApiClient;
  runId: string;
  parameters: readonly ParameterRow[];
  pageSize?: number;
}

const MODES: ReadonlyArray<[DecisionLogMode, string]> = [["vetoes", "Vetoes"], ["entries", "Entries"], ["all", "Every bar"]];

/** Pure: how a group reads in the log ("×14 bars, 2016-06-24 08:00 → 2016-06-26 20:00"). */
export function spanLabel(group: DecisionLogGroup): string {
  return group.bars === 1 ? when(group.first_time) : `×${group.bars} bars, ${when(group.first_time)} → ${when(group.last_time)}`;
}

/**
 * The run's chain evaluations, one row per bar, consecutive identical vetoes collapsed.
 * Vetoed rows are salmon and say why; a click expands the bar's full chain.
 */
export function DecisionLog({ api, runId, parameters, pageSize = 200 }: Props) {
  const [mode, setMode] = useState<DecisionLogMode>("vetoes");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<number | null>(null);
  const state = useAsync<DecisionLogPage>(() => api.decisionLog(runId, mode, page, pageSize), [api, runId, mode, page, pageSize]);
  const data = state.data;
  const pages = data === null ? 1 : Math.max(1, Math.ceil(data.total_groups / data.size));
  return (
    <div data-testid="decision-log">
      <div className="log-controls">
        {MODES.map(([value, label]) => (
          <button key={value} className={mode === value ? "active" : ""} data-mode={value} onClick={() => { setMode(value); setPage(1); setOpen(null); }}>{label}</button>
        ))}
        {data === null ? null : (
          <span className="muted" data-testid="log-summary">
            {data.total_rows} bar(s) in {data.total_groups} row(s) · page {data.page} of {pages}
          </span>
        )}
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
      {data === null ? <Pending state={state} label="decision log" /> : (
        <table className="grid" data-testid="decision-table">
          <thead><tr><th>When</th><th>Decision</th><th>Vetoed by</th><th>Why</th><th>Trade</th></tr></thead>
          <tbody>
            {data.groups.map((g) => (
              <LogRow key={g.first_id} group={g} open={open === g.first_id} onToggle={() => setOpen(open === g.first_id ? null : g.first_id)} api={api} runId={runId} parameters={parameters} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

interface RowProps {
  group: DecisionLogGroup;
  open: boolean;
  onToggle: () => void;
  api: ApiClient;
  runId: string;
  parameters: readonly ParameterRow[];
}

function LogRow({ group, open, onToggle, api, runId, parameters }: RowProps) {
  const vetoed = group.vetoed_by !== null;
  return (
    <>
      <tr className={`clickable ${vetoed ? "vetoed" : ""}`} data-decision-id={group.first_id} data-vetoed={vetoed ? "yes" : "no"} onClick={onToggle}>
        <td>{spanLabel(group)}</td>
        <td><span className={`badge ${group.final_decision === "BUY" ? "buy" : group.final_decision === "SELL" ? "sell" : ""}`}>{group.final_decision}</span></td>
        <td className="mono">{group.vetoed_by ?? ""}</td>
        <td className="mono why">{group.why ?? ""}</td>
        <td className="mono">{group.trade_id ?? ""}</td>
      </tr>
      {open ? (
        <tr className="expanded"><td colSpan={5}><DecisionChain api={api} runId={runId} decisionId={group.first_id} parameters={parameters} /></td></tr>
      ) : null}
    </>
  );
}

function DecisionChain({ api, runId, decisionId, parameters }: { api: ApiClient; runId: string; decisionId: number; parameters: readonly ParameterRow[] }) {
  const state = useAsync<DecisionDetail>(() => api.decisionDetail(runId, decisionId), [api, runId, decisionId]);
  if (state.data === null) return <Pending state={state} label={`decision ${decisionId}`} />;
  return <ChainSteps filters={state.data.filters} parameters={parameters.length > 0 ? parameters : state.data.parameters} api={api} testId="decision-chain" />;
}
