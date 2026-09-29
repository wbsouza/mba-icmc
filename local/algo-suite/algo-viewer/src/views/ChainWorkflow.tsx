import { useState } from "react";
import type { DecisionSummaryRow, ParameterRow } from "../model/types";
import { chainOrder, describeFilter, parametersFor } from "../model/chain";

interface Props {
  parameters: ParameterRow[];
  funnel: DecisionSummaryRow[];
}

/** The chain as nodes in order; click one to see what it does and its parameters. */
export function ChainWorkflow({ parameters, funnel }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const order = chainOrder(parameters);
  if (order === null) {
    return <p className="muted">This run recorded no `filters` list (a code-registered strategy); the chain cannot be drawn.</p>;
  }
  const vetoes = (name: string) => funnel.filter((f) => f.vetoed_by.toLowerCase() === name.toLowerCase()).reduce((n, f) => n + f.count, 0);
  const info = selected === null ? null : describeFilter(selected);
  return (
    <>
      <ol className="workflow" data-testid="chain-workflow">
        {order.map((name, i) => {
          const f = describeFilter(name);
          const count = vetoes(name);
          return (
            <li key={name} className={selected === name ? "node selected" : "node"} data-node={name} data-vetoes={count}>
              <button type="button" onClick={() => setSelected(selected === name ? null : name)} aria-pressed={selected === name}>
                <span className="step">{i + 1}</span>
                <span className="label">{f.label}</span>
                <span className={count > 0 ? "vetoes down" : "vetoes muted"}>{count > 0 ? `vetoed ${count}` : "no vetoes"}</span>
              </button>
              {i < order.length - 1 ? <span className="arrow" aria-hidden="true">→</span> : null}
            </li>
          );
        })}
        <li className="node terminal"><span className="label">Order executor</span></li>
      </ol>
      {info === null ? null : (
        <div className="filter-details" data-testid="filter-details">
          <h3>{info.title}</h3>
          <p>{info.description}</p>
          <dl className="facts">
            <dt>Reads</dt><dd>{info.reads || "—"}</dd>
            <dt>Emits</dt><dd>{info.emits || "—"}</dd>
            <dt>Vetoed</dt><dd>{vetoes(info.name)} bar(s) in this run</dd>
          </dl>
          <table className="grid" data-testid="filter-parameters">
            <thead><tr><th>Parameter</th><th>Value</th><th>Set by</th></tr></thead>
            <tbody>
              {parametersFor(info, parameters).map((p) => (
                <tr key={p.key}><td className="mono">{p.key}</td><td className="mono">{p.value}</td><td className="muted">{p.source}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
