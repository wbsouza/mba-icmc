/** Typed queries over the results database (one function per endpoint). */

import type { Queryable } from "./db.js";
import { vetoLine, vetoParameter } from "../src/model/veto.js";
import type {
  DecisionDetail,
  DecisionEvent,
  DecisionLogGroup,
  DecisionLogMode,
  DecisionLogPage,
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
} from "../src/model/types.js";

const RUN_COLUMNS =
  "r.*, (SELECT AVG(is_win) FROM trades t WHERE t.run_id = r.run_id) AS win_rate";

export function listRuns(db: Queryable): RunRow[] {
  return db.rows<RunRow>(`SELECT ${RUN_COLUMNS} FROM runs r ORDER BY job, strategy, start, run_id`);
}

export function getRun(db: Queryable, runId: string): RunRow | null {
  return db.rows<RunRow>(`SELECT ${RUN_COLUMNS} FROM runs r WHERE run_id = ?`, [runId])[0] ?? null;
}

export function equitySamples(db: Queryable, runId: string): EquitySample[] {
  return db.rows<EquitySample>(
    "SELECT time, equity, drawdown_pct FROM equity_samples WHERE run_id = ? ORDER BY seq",
    [runId],
  );
}

export function monthlyReturns(db: Queryable, runId: string): MonthlyReturn[] {
  return db.rows<MonthlyReturn>(
    "SELECT month, start_equity, end_equity, return_pct, trades FROM monthly_returns WHERE run_id = ? ORDER BY month",
    [runId],
  );
}

export function parameters(db: Queryable, runId: string): ParameterRow[] {
  return db.rows<ParameterRow>(
    "SELECT key, value, source FROM run_parameters WHERE run_id = ? ORDER BY key",
    [runId],
  );
}

export function trades(db: Queryable, runId: string): TradeRow[] {
  return db.rows<TradeRow>("SELECT * FROM trades WHERE run_id = ? ORDER BY entry_time", [runId]);
}

export function decisionSummary(db: Queryable, runId: string): DecisionSummaryRow[] {
  return db.rows<DecisionSummaryRow>(
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

function plan(db: Queryable, runId: string, tradeId: string): TradePlan | null {
  const row = db.rows<PlanRow>(
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

export function tradeDetail(db: Queryable, runId: string, tradeId: string): TradeDetail | null {
  const run = getRun(db, runId);
  const trade = db.rows<TradeRow>("SELECT * FROM trades WHERE run_id = ? AND trade_id = ?", [runId, tradeId])[0];
  if (run === null || trade === undefined) return null;
  const entryDecision =
    db.rows<DecisionRow>(
      "SELECT * FROM decisions WHERE run_id = ? AND trade_id = ? AND is_entry = 1 ORDER BY timestamp LIMIT 1",
      [runId, tradeId],
    )[0] ?? null;
  const filters = entryDecision
    ? db.rows<FilterRow>(
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
    events: tradeEvents(db, runId, tradeId),
    trailMoves: db.rows<TrailMove>(
      "SELECT time, from_stop, to_stop FROM trail_moves WHERE run_id = ? AND trade_id = ? ORDER BY time",
      [runId, tradeId],
    ),
    bars: db.rows<EntryBar>(
      "SELECT offset, time, open, high, low, close FROM entry_bars WHERE run_id = ? AND trade_id = ? ORDER BY offset",
      [runId, tradeId],
    ),
    parameters: parameters(db, runId),
  };
}

export interface PatternExample {
  run_id: string;
  trade_id: string;
  entry_time: string;
  direction: "buy" | "sell";
  profit: number;
}

/** Candidates fetched per requested example: enough to find distinct entry times and runs. */
const CANDIDATES_PER_EXAMPLE = 25;

/**
 * Pick `limit` examples from candidates sorted most recent first: one per entry time
 * (sibling runs over the same window fire on the same bar, which would show triplicates),
 * preferring a run not chosen yet when several candidates share an entry time.
 */
export function selectExamples(candidates: readonly PatternExample[], limit: number): PatternExample[] {
  const chosen: PatternExample[] = [];
  const usedRuns = new Set<string>();
  const byTime = new Map<string, PatternExample[]>();
  for (const c of candidates) {
    const group = byTime.get(c.entry_time) ?? [];
    group.push(c);
    byTime.set(c.entry_time, group);
  }
  for (const group of byTime.values()) {
    if (chosen.length >= limit) break;
    const pick = group.find((c) => !usedRuns.has(c.run_id)) ?? group[0];
    if (pick === undefined) continue;
    chosen.push(pick);
    usedRuns.add(pick.run_id);
  }
  return chosen;
}

/** Up to `limit` closed trades whose entry decision carried `pattern`, most recent distinct entry times first. */
export function patternExamples(db: Queryable, pattern: string, limit: number): PatternExample[] {
  const candidates = db.rows<PatternExample>(
    "SELECT d.run_id, d.trade_id, t.entry_time, t.direction, t.profit FROM decision_filters f " +
      "JOIN decisions d ON d.id = f.decision_id JOIN trades t ON t.run_id = d.run_id AND t.trade_id = d.trade_id " +
      "WHERE d.is_entry = 1 AND f.pattern_name = ? ORDER BY t.entry_time DESC, d.run_id, d.trade_id LIMIT ?",
    [pattern, limit * CANDIDATES_PER_EXAMPLE],
  );
  return selectExamples(candidates, limit);
}

// ---- chain evaluations: events while a trade was open, the run's decision log, one bar's chain

function filtersOf(db: Queryable, decisionId: number): FilterRow[] {
  return db.rows<FilterRow>(
    "SELECT position, filter_name, recommendation, veto, reason, pattern_name FROM decision_filters WHERE decision_id = ? ORDER BY position",
    [decisionId],
  );
}

/** Chain evaluations carrying the trade's id after its entry, oldest first, each with its filters. */
export function tradeEvents(db: Queryable, runId: string, tradeId: string): DecisionEvent[] {
  const rows = db.rows<DecisionRow>(
    "SELECT * FROM decisions WHERE run_id = ? AND trade_id = ? AND is_entry = 0 ORDER BY timestamp, id",
    [runId, tradeId],
  );
  return rows.map((decision) => ({ decision, filters: filtersOf(db, decision.id) }));
}

/** One chain evaluation by id, with the run's parameters (for the limits the vetoes name). */
export function decisionDetail(db: Queryable, runId: string, decisionId: number): DecisionDetail | null {
  const decision = db.rows<DecisionRow>("SELECT * FROM decisions WHERE run_id = ? AND id = ?", [runId, decisionId])[0];
  if (decision === undefined) return null;
  return { decision, filters: filtersOf(db, decision.id), parameters: parameters(db, runId) };
}

interface LogRow extends DecisionRow {
  veto_filter: string | null;
  veto_reason: string | null;
}

const MODE_WHERE: Record<DecisionLogMode, string> = {
  vetoes: "AND d.vetoed_by IS NOT NULL",
  entries: "AND d.is_entry = 1",
  all: "",
};

/** Pure: consecutive rows with the same outcome, vetoing filter and breached parameter become one group. */
export function groupDecisions(rows: readonly LogRow[], runParameters: readonly ParameterRow[]): DecisionLogGroup[] {
  const groups: DecisionLogGroup[] = [];
  for (const row of rows) {
    const filter: FilterRow | null = row.veto_filter === null || row.veto_reason === null
      ? null
      : { position: 0, filter_name: row.veto_filter, recommendation: "", veto: 1, reason: row.veto_reason, pattern_name: null };
    const parameter = vetoParameter(filter, runParameters);
    const last = groups[groups.length - 1];
    if (last !== undefined && last.final_decision === row.final_decision && last.vetoed_by === row.vetoed_by && last.parameter === parameter && last.trade_id === row.trade_id) {
      last.last_time = row.timestamp;
      last.bars += 1;
      continue;
    }
    groups.push({
      first_id: row.id, first_time: row.timestamp, last_time: row.timestamp, bars: 1,
      final_decision: row.final_decision, vetoed_by: row.vetoed_by, trade_id: row.trade_id,
      parameter, why: vetoLine(filter, runParameters),
    });
  }
  return groups;
}

/** The run's chain evaluations in `mode`, grouped, one page of groups. */
export function decisionLog(db: Queryable, runId: string, mode: DecisionLogMode, page: number, size: number): DecisionLogPage {
  const rows = db.rows<LogRow>(
    `SELECT d.*, f.filter_name AS veto_filter, f.reason AS veto_reason
     FROM decisions d
     LEFT JOIN decision_filters f ON f.decision_id = d.id AND f.veto = 1
       AND f.position = (SELECT MIN(position) FROM decision_filters g WHERE g.decision_id = d.id AND g.veto = 1)
     WHERE d.run_id = ? ${MODE_WHERE[mode]}
     ORDER BY d.timestamp, d.id`,
    [runId],
  );
  const groups = groupDecisions(rows, parameters(db, runId));
  const start = (page - 1) * size;
  return { mode, page, size, total_rows: rows.length, total_groups: groups.length, groups: groups.slice(start, start + size) };
}
