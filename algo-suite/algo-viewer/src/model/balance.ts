/** The account balance after each closed trade: starting cash plus the net P/L so far, in closing order. */

import type { TradeRow } from "./types";

/** Map trade id -> balance after that trade closed (profit minus fees accumulated by exit time, then trade id). */
export function balancesAfter(trades: readonly TradeRow[], startingCash: number): Map<string, number> {
  const order = [...trades].sort((a, b) => a.exit_time.localeCompare(b.exit_time) || a.entry_order_id - b.entry_order_id);
  const out = new Map<string, number>();
  let balance = startingCash;
  for (const t of order) {
    balance += t.profit - t.fees;
    out.set(t.trade_id, balance);
  }
  return out;
}
