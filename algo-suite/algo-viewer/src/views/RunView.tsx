import { useMemo } from "react";
import type { ApiClient } from "../api/client";
import { Pending, useAsync } from "../api/useAsync";
import type { DecisionSummaryRow, EquitySample, MonthlyReturn, ParameterRow, RunRow, TradeRow } from "../model/types";
import { barLabel, EXIT_KIND_LABELS, lots, minutes, money, pct, price, priceDecimals, signedPct, when } from "../model/format";
import { LineChart } from "../charts/LineChart";
import { MonthlyBarsChart } from "../charts/MonthlyBars";
import { ChainWorkflow } from "./ChainWorkflow";

interface Props {
  api: ApiClient;
  run: RunRow;
  dark: boolean;
  onSelectTrade: (tradeId: string) => void;
}

/** Pure: parameters grouped by their section (the key's first dotted segment). */
export function groupParameters(rows: readonly ParameterRow[]): Map<string, ParameterRow[]> {
  const groups = new Map<string, ParameterRow[]>();
  for (const row of rows) {
    const section = row.key.includes(".") ? row.key.split(".")[0] ?? row.key : "run";
    const list = groups.get(section) ?? [];
    list.push(row);
    groups.set(section, list);
  }
  return groups;
}

interface Loaded {
  samples: EquitySample[];
  months: MonthlyReturn[];
  params: ParameterRow[];
  trades: TradeRow[];
  funnel: DecisionSummaryRow[];
}

export function RunView({ api, run, dark, onSelectTrade }: Props) {
  const state = useAsync<Loaded>(async () => {
    const [samples, months, params, tradeRows, funnel] = await Promise.all([
      api.equity(run.run_id), api.monthly(run.run_id), api.parameters(run.run_id), api.trades(run.run_id), api.decisionSummary(run.run_id),
    ]);
    return { samples, months, params, trades: tradeRows, funnel };
  }, [api, run.run_id]);
  const samples = useMemo(() => state.data?.samples ?? [], [state.data]);
  const months = state.data?.months ?? [];
  const params = useMemo(() => groupParameters(state.data?.params ?? []), [state.data]);
  const tradeRows = state.data?.trades ?? [];
  const funnel = state.data?.funnel ?? [];
  const decimals = priceDecimals(tradeRows[0]?.entry_price ?? 1);
  const equitySeries = useMemo(
    () => [{ id: "equity", label: "Equity", color: "#1f6feb", points: samples.map((s) => ({ time: s.time, value: s.equity })) }],
    [samples],
  );
  const last = samples[samples.length - 1];
  if (state.data === null) return <Pending state={state} label={`run ${run.run_id}`} />;
  return (
    <>
      <div className="kpis" data-testid="kpis">
        <Kpi label="Strategy" value={run.strategy} />
        <Kpi label="Window" value={`${run.start} → ${run.end}`} />
        <Kpi label="Bars" value={barLabel(run.bar_minutes)} />
        <Kpi label="Return" value={signedPct(run.total_return * 100)} tone={run.total_return >= 0 ? "up" : "down"} />
        <Kpi label="Max drawdown" value={pct(run.max_drawdown)} tone="down" />
        <Kpi label="Sharpe" value={run.sharpe === null ? "n/a" : run.sharpe.toFixed(2)} />
        <Kpi label="Trades" value={String(run.closed_trades)} />
        <Kpi label="Win rate" value={pct(run.win_rate, 0)} />
        <Kpi label="Final equity" value={money(last?.equity ?? null)} />
      </div>
      <section className="panel" aria-label="Equity">
        <h2>Equity</h2>
        <LineChart series={equitySeries} dark={dark} />
      </section>
      <section className="panel" aria-label="Monthly returns chart">
        <h2>Monthly returns</h2>
        <MonthlyBarsChart months={months} dark={dark} />
      </section>
      <div className="two-col">
        <section className="panel" aria-label="Monthly returns table">
          <h2>Month by month</h2>
          <table className="grid">
            <thead><tr><th>Month</th><th className="num">Start</th><th className="num">End</th><th className="num">Return</th><th className="num">Trades</th></tr></thead>
            <tbody>
              {months.map((m) => (
                <tr key={m.month}>
                  <td>{m.month}</td><td className="num">{money(m.start_equity)}</td><td className="num">{money(m.end_equity)}</td>
                  <td className={`num ${m.return_pct >= 0 ? "up" : "down"}`}>{signedPct(m.return_pct)}</td><td className="num">{m.trades}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel" aria-label="Decision funnel">
          <h2>Decision funnel</h2>
          <p className="muted">Every chain invocation of the run by outcome (and the filter that vetoed it).</p>
          <div className="funnel">
            {funnel.map((f) => (
              <span key={`${f.final_decision}/${f.vetoed_by}`} className={`badge ${f.vetoed_by ? "veto" : ""}`}>
                {f.final_decision}{f.vetoed_by ? ` · ${f.vetoed_by}` : ""}: {f.count}
              </span>
            ))}
          </div>
          <h3>Run facts</h3>
          <dl className="facts">
            <dt>Job</dt><dd>{run.job}</dd>
            <dt>Symbol</dt><dd>{run.symbol}</dd>
            <dt>Cash</dt><dd>{money(run.cash)}</dd>
            <dt>Model</dt><dd className="mono">{run.model_sha256 ?? "not recorded"}</dd>
            <dt>Code revision</dt><dd className="mono">{run.code_revision ?? "not recorded"}</dd>
            <dt>Run directory</dt><dd className="mono">{run.run_dir}</dd>
          </dl>
        </section>
      </div>
      <section className="panel" aria-label="Strategy chain">
        <h2>Strategy chain <span className="muted">(click a filter for what it does and its parameters)</span></h2>
        <ChainWorkflow parameters={state.data.params} funnel={funnel} />
      </section>
      <section className="panel" aria-label="Parameters">
        <h2>All parameters with provenance</h2>
        {[...params.entries()].map(([section, rows]) => (
          <details key={section} className="params" open={section === "meta_learner"}>
            <summary>{section} <span className="muted">({rows.length})</span></summary>
            <table className="grid">
              <tbody>
                {rows.map((p) => (
                  <tr key={p.key}><td className="mono">{p.key}</td><td className="mono">{p.value}</td><td className="muted">{p.source}</td></tr>
                ))}
              </tbody>
            </table>
          </details>
        ))}
      </section>
      <section className="panel" aria-label="Trades">
        <h2>Trades <span className="muted">(click one to see why the chain entered it)</span></h2>
        <table className="grid" data-testid="trades-table">
          <thead>
            <tr><th>#</th><th>Side</th><th className="num">Lots</th><th>Entry</th><th className="num">Price</th><th>Exit</th><th className="num">Price</th><th>Exit kind</th><th className="num">Held</th><th className="num">P/L</th></tr>
          </thead>
          <tbody>
            {tradeRows.map((t: TradeRow) => (
              <tr key={t.trade_id} className="clickable" data-trade-id={t.trade_id} onClick={() => onSelectTrade(t.trade_id)}>
                <td className="mono">{t.trade_id}</td>
                <td><span className={`badge ${t.direction}`}>{t.direction}</span></td>
                <td className="num">{lots(t.lots)}</td>
                <td>{when(t.entry_time)}</td><td className="num">{price(t.entry_price, decimals)}</td>
                <td>{when(t.exit_time)}</td><td className="num">{price(t.exit_price, decimals)}</td>
                <td><span className="badge kind">{EXIT_KIND_LABELS[t.exit_kind] ?? t.exit_kind}</span></td>
                <td className="num">{minutes(t.holding_minutes)}</td>
                <td className={`num ${t.profit >= 0 ? "up" : "down"}`}>{money(t.profit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className={`value ${tone ?? ""}`}>{value}</div>
    </div>
  );
}
