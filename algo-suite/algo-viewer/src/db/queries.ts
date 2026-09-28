/** Typed queries over the results database (one function per view need). */

import type { Database } from "sql.js";
import { rows } from "./loader";
import type {
  DecisionRow,
  DecisionSummaryRow,
  EntryBar,
  EquitySample,
  FilterRow,
  MonthlyReturn,
  ParameterRow,
  PlanTarget,
  RunRow,
  TradeDetail,
  TradePlan,
  TradeRow,
  TrailMove,
  TrailStep,
} from "../model/types";

const RUN_COLUMNS =
  "r.*, (SELECT AVG(is_win) FROM trades t WHERE t.run_id = r.run_id) AS win_rate";

export function listRuns(db: Database): RunRow[] {
  return rows<RunRow>(db, `SELECT ${RUN_COLUMNS} FROM runs r ORDER BY job, strategy, start, run_id`);
}

export function getRun(db: Database, runId: string): RunRow | null {
  return rows<RunRow>(db, `SELECT ${RUN_COLUMNS} FROM runs r WHERE run_id = ?`, [runId])[0] ?? null;
}

export function equitySamples(db: Database, runId: string): EquitySample[] {
  return rows<EquitySample>(
    db,
    "SELECT time, equity, drawdown_pct FROM equity_samples WHERE run_id = ? ORDER BY time",
    [runId],
  );
}

export function monthlyReturns(db: Database, runId: string): MonthlyReturn[] {
  return rows<MonthlyReturn>(
    db,
    "SELECT month, start_equity, end_equity, return_pct, trades FROM monthly_returns WHERE run_id = ? ORDER BY month",
    [runId],
  );
}

export function parameters(db: Database, runId: string): ParameterRow[] {
  return rows<ParameterRow>(
    db,
    "SELECT key, value, source FROM run_parameters WHERE run_id = ? ORDER BY key",
    [runId],
  );
}

export function trades(db: Database, runId: string): TradeRow[] {
  return rows<TradeRow>(db, "SELECT * FROM trades WHERE run_id = ? ORDER BY entry_time", [runId]);
}

export function decisionSummary(db: Database, runId: string): DecisionSummaryRow[] {
  return rows<DecisionSummaryRow>(
    db,
    "SELECT final_decision, vetoed_by, count FROM decision_summary WHERE run_id = ? ORDER BY count DESC",
    [runId],
  );
}

interface PlanRow {
  stop_loss: number;
  stop_pips: number | null;
  targets_json: string;
  trail_steps_json: string;
  spread_pips: number | null;
}

function plan(db: Database, runId: string, tradeId: string): TradePlan | null {
  const row = rows<PlanRow>(
    db,
    "SELECT stop_loss, stop_pips, targets_json, trail_steps_json, spread_pips FROM trade_plans WHERE run_id = ? AND trade_id = ?",
    [runId, tradeId],
  )[0];
  if (row === undefined) return null;
  return {
    stop_loss: row.stop_loss,
    stop_pips: row.stop_pips,
    targets: JSON.parse(row.targets_json) as PlanTarget[],
    trail_steps: JSON.parse(row.trail_steps_json) as TrailStep[],
    spread_pips: row.spread_pips,
  };
}

export function tradeDetail(db: Database, runId: string, tradeId: string): TradeDetail | null {
  const run = getRun(db, runId);
  const trade = rows<TradeRow>(db, "SELECT * FROM trades WHERE run_id = ? AND trade_id = ?", [runId, tradeId])[0];
  if (run === null || trade === undefined) return null;
  const entryDecision =
    rows<DecisionRow>(
      db,
      "SELECT * FROM decisions WHERE run_id = ? AND trade_id = ? AND is_entry = 1 ORDER BY timestamp LIMIT 1",
      [runId, tradeId],
    )[0] ?? null;
  const filters = entryDecision
    ? rows<FilterRow>(
        db,
        "SELECT position, filter_name, recommendation, veto, reason, pattern_name FROM decision_filters WHERE decision_id = ? ORDER BY position",
        [entryDecision.id],
      )
    : [];
  return {
    run,
    trade,
    plan: plan(db, runId, tradeId),
    entryDecision,
    filters,
    trailMoves: rows<TrailMove>(
      db,
      "SELECT time, from_stop, to_stop FROM trail_moves WHERE run_id = ? AND trade_id = ? ORDER BY time",
      [runId, tradeId],
    ),
    bars: rows<EntryBar>(
      db,
      "SELECT offset, time, open, high, low, close FROM entry_bars WHERE run_id = ? AND trade_id = ? ORDER BY offset",
      [runId, tradeId],
    ),
    parameters: parameters(db, runId),
  };
}
