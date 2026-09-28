import { useEffect, useState } from "react";
import type { TradeDetail, TrailStep } from "../model/types";
import { EXIT_KIND_LABELS, lots, minutes, money, price, priceDecimals, when } from "../model/format";
import { CandleChart, windowSummary } from "../charts/CandleChart";
import { ChainSteps } from "./ChainSteps";
import { routeHash } from "../router";
import type { ApiClient } from "../api/client";

interface Props {
  detail: TradeDetail;
  dark: boolean;
  onClose: () => void;
  /** With a client the pattern card links other trades that carried the same pattern. */
  api?: ApiClient | undefined;
}

/** The shareable address of a trade: the page plus its `#/run/<id>/trade/<id>` hash. */
export function tradeLink(runId: string, tradeId: string): string {
  const { origin, pathname } = window.location;
  return `${origin}${pathname}${routeHash({ view: "run", runId, tradeId })}`;
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/** Why the chain entered, the plan, the exit and the realized P/L of one trade. */
export function TradeDrawer({ detail, dark, onClose, api }: Props) {
  const { trade, plan, filters, trailMoves, bars, parameters, run } = detail;
  const decimals = priceDecimals(trade.entry_price);
  const [copied, setCopied] = useState<"idle" | "copied" | "failed">("idle");
  const link = tradeLink(run.run_id, trade.trade_id);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`Trade ${trade.trade_id}`} data-testid="trade-drawer">
        <header>
          <h2>
            Trade {trade.trade_id} · <span className={`badge ${trade.direction}`}>{trade.direction}</span> {run.symbol} · {lots(trade.lots)} lots ·{" "}
            <span className={trade.profit >= 0 ? "up" : "down"}>{money(trade.profit)}</span>
          </h2>
          <button
            data-testid="copy-link"
            data-link={link}
            title={link}
            onClick={() => { void copyText(link).then((ok) => setCopied(ok ? "copied" : "failed")); }}
          >
            {copied === "copied" ? "Copied" : copied === "failed" ? "Copy failed — use the address bar" : "Copy link"}
          </button>
          <button onClick={onClose} aria-label="Close">Close</button>
        </header>
        <section className="panel" aria-label="Why we entered">
          <h2>Why we entered <span className="muted">— the chain at {detail.entryDecision ? when(detail.entryDecision.timestamp) : when(trade.entry_time)}</span></h2>
          {filters.length === 0 ? (
            <p className="muted">No entry decision is stored for this trade (the database was built without the chain's audit rows).</p>
          ) : (
            <ChainSteps filters={filters} parameters={parameters} api={api} />
          )}
        </section>
        <section className="panel" aria-label="Entry bars">
          <h2 data-testid="bars-heading">{barsHeading(windowSummary(bars, trade))}</h2>
          <CandleChart bars={bars} trade={trade} plan={plan} trailMoves={trailMoves} dark={dark} />
        </section>
        <div className="two-col">
          <section className="panel" aria-label="Plan">
            <h2>Plan</h2>
            {plan ? (
              <dl className="facts">
                <dt>Lots</dt><dd>{lots(trade.lots)} ({trade.quantity.toLocaleString("en-US")} units)</dd>
                <dt>Stop</dt><dd>{price(plan.stop_loss, decimals)}{plan.stop_pips === null ? "" : ` (${plan.stop_pips.toFixed(1)} pips)`}</dd>
                <dt>Targets</dt>
                <dd>{plan.targets.map((t, i) => `T${i + 1} ${price(t.price, decimals)} (${Math.round(t.close_fraction * 100)}%)`).join(" · ")}</dd>
                <dt>Trail</dt>
                <dd>{plan.trail_steps.length === 0 ? "none" : plan.trail_steps.map((s) => trailStepLabel(s, decimals)).join(" · ")}</dd>
                <dt>Spread</dt><dd>{plan.spread_pips === null ? "n/a" : `${plan.spread_pips.toFixed(1)} pips`}</dd>
              </dl>
            ) : <p className="muted">No trade plan recorded for this run.</p>}
          </section>
          <section className="panel" aria-label="Exit">
            <h2>Exit</h2>
            <dl className="facts">
              <dt>Kind</dt><dd><span className="badge kind" data-testid="exit-kind">{EXIT_KIND_LABELS[trade.exit_kind] ?? trade.exit_kind}</span></dd>
              <dt>Entered</dt><dd>{when(trade.entry_time)} @ {price(trade.entry_price, decimals)}</dd>
              <dt>Exited</dt><dd>{when(trade.exit_time)} @ {price(trade.exit_price, decimals)}</dd>
              <dt>Held</dt><dd>{minutes(trade.holding_minutes)}</dd>
              <dt>Trail moves</dt>
              <dd>{trailMoves.length === 0 ? "none" : trailMoves.map((m) => `${when(m.time)}: ${price(m.from_stop, decimals)} → ${price(m.to_stop, decimals)}`).join(" · ")}</dd>
              <dt>Realized P/L</dt><dd className={trade.profit >= 0 ? "up" : "down"}>{money(trade.profit)}{trade.fees !== 0 ? ` (fees ${money(trade.fees)})` : ""}</dd>
            </dl>
          </section>
        </div>
      </aside>
    </>
  );
}

/** "2 bars before the entry, 8 after": the stored window's actual reach on each side. */
export function barsHeading({ before, after }: { before: number; after: number }): string {
  return `${before} bar${before === 1 ? "" : "s"} before the entry, ${after} after`;
}

function trailStepLabel(step: TrailStep, decimals: number): string {
  if (step.at_price !== undefined && step.to_price !== undefined) {
    return `at ${price(step.at_price, decimals)} → stop ${price(step.to_price, decimals)}`;
  }
  if (step.at_pips !== undefined && step.to_pips !== undefined) {
    return `at +${step.at_pips.toFixed(1)} pips → stop +${step.to_pips.toFixed(1)} pips`;
  }
  return `at ${String(step.at_level_ratio)}R → ${String(step.to_level_ratio)}R`;
}
