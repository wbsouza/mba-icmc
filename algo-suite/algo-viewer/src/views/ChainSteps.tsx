import type { FilterRow, ParameterRow } from "../model/types";
import { explainFilter } from "../model/explain";
import { vetoWhy } from "../model/veto";
import { PatternCard } from "./PatternCard";
import type { ApiClient } from "../api/client";

interface Props {
  filters: FilterRow[];
  parameters: readonly ParameterRow[];
  /** With a client the pattern card links other trades that carried the same pattern. */
  api?: ApiClient | undefined;
  testId?: string;
}

/**
 * One chain evaluation as numbered steps. A step that vetoed is tinted salmon and carries
 * a "why" line per breached cap: `risk_guard.daily_drawdown_limit: -0.074 < -0.05`.
 */
export function ChainSteps({ filters, parameters, api, testId = "chain" }: Props) {
  return (
    <ol className="chain" data-testid={testId}>
      {filters.map((filter, i) => {
        const x = explainFilter(filter, parameters);
        const why = vetoWhy(filter, parameters);
        return (
          <li key={i} data-filter={filter.filter_name} className={x.veto ? "vetoed" : ""} data-vetoed={x.veto ? "yes" : "no"}>
            <span className="step">{i + 1}</span>
            <div>
              <div className="title">
                {x.title} <span className={`badge ${x.recommendation === "BUY" ? "buy" : x.recommendation === "SELL" ? "sell" : ""}`}>{x.recommendation}</span>
                {x.veto ? <span className="badge veto">veto</span> : null}
                {x.pattern ? <span className="badge" data-testid="pattern-name">{x.pattern.title}</span> : null}
              </div>
              <div className="summary">{x.summary}</div>
              {why.map((w, j) => <div key={j} className="why" data-parameter={w.parameter ?? ""}>{w.text}</div>)}
              {x.pattern ? <PatternCard pattern={x.pattern} api={api} /> : x.details.map((d, j) => <div key={j} className="details">{d}</div>)}
              <div className="reason">{x.reason}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
