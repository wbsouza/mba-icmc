/** Row shapes of the results database (algo-analyze `results-db build`, schema version 1). */

export const SCHEMA_VERSION = 2;

export interface RunRow {
  run_id: string;
  job: string;
  run_dir: string;
  strategy: string;
  symbol: string;
  start: string;
  end: string;
  cash: number | null;
  bar_minutes: number;
  model_sha256: string | null;
  code_revision: string | null;
  success: number;
  closed_trades: number;
  total_return: number;
  sharpe: number | null;
  max_drawdown: number;
  hit_rate: number | null;
  statement_path: string | null;
  report_path: string | null;
  equity_png_path: string | null;
  /** Fraction of winning trades from the `trades` table, null when the run has none. */
  win_rate: number | null;
  /** Statement A/C summary: cash plus closed P/L (null when the statement has no summary). */
  balance: number | null;
  /** Statement A/C summary: floating P/L of the positions still open at the end. */
  floating_pl: number | null;
  /** Statement A/C summary: balance plus floating P/L. */
  equity_end: number | null;
}

/** A position the run left open, as its statement's "Open Trades" table reports it. */
export interface OpenPosition {
  ticket: number;
  open_time: string;
  direction: string;
  lots: number | null;
  open_price: number;
  stop_loss: number | null;
  take_profits: number[];
  mark_price: number | null;
  floating_pl: number;
}

export interface EquitySample {
  time: string;
  equity: number;
  drawdown_pct: number;
}

export interface MonthlyReturn {
  month: string;
  start_equity: number;
  end_equity: number;
  return_pct: number;
  trades: number;
}

export interface ParameterRow {
  key: string;
  value: string;
  source: string;
}

export type ExitKind = "stop" | "target" | "trail_stop" | "liquidation" | "reversal" | "unknown";

export interface TradeRow {
  run_id: string;
  trade_id: string;
  entry_order_id: number;
  direction: "buy" | "sell";
  lots: number | null;
  quantity: number;
  entry_time: string;
  entry_price: number;
  exit_time: string;
  exit_price: number;
  profit: number;
  fees: number;
  is_win: number;
  exit_kind: ExitKind;
  exit_order_id: number | null;
  exit_order_type: string | null;
  holding_minutes: number;
}

export interface PlanTarget {
  price: number;
  close_fraction: number;
  quantity?: number;
}

export interface TrailStep {
  at_pips?: number;
  to_pips?: number;
  at_price?: number;
  to_price?: number;
  at_level_ratio?: number;
  to_level_ratio?: number;
}

export interface TradePlan {
  stop_loss: number;
  stop_pips: number | null;
  targets: PlanTarget[];
  trail_steps: TrailStep[];
  spread_pips: number | null;
}

export interface DecisionRow {
  id: number;
  trade_id: string | null;
  timestamp: string;
  final_decision: string;
  vetoed_by: string | null;
  p_hat: number | null;
  is_entry: number;
}

export interface FilterRow {
  position: number;
  filter_name: string;
  recommendation: string;
  veto: number;
  reason: string;
  pattern_name: string | null;
}

export interface TrailMove {
  time: string;
  from_stop: number;
  to_stop: number;
}

export interface EntryBar {
  offset: number;
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface DecisionSummaryRow {
  final_decision: string;
  vetoed_by: string;
  count: number;
}

/** One chain evaluation with its filter rows (an entry, a repeat signal or a vetoed bar). */
export interface DecisionEvent {
  decision: DecisionRow;
  filters: FilterRow[];
}

/** Everything the trade drawer shows for one trade. */
export interface TradeDetail {
  run: RunRow;
  trade: TradeRow;
  plan: TradePlan | null;
  entryDecision: DecisionRow | null;
  filters: FilterRow[];
  /** Chain evaluations carrying this trade's id after the entry: repeat signals and vetoes while open. */
  events: DecisionEvent[];
  trailMoves: TrailMove[];
  bars: EntryBar[];
  parameters: ParameterRow[];
}

export type DecisionLogMode = "vetoes" | "entries" | "all";

/** Consecutive chain evaluations with the same outcome, vetoing filter and breached parameter, as one row. */
export interface DecisionLogGroup {
  /** The first decision of the group (its chain is what the row expands to). */
  first_id: number;
  first_time: string;
  last_time: string;
  /** How many bars the group spans. */
  bars: number;
  final_decision: string;
  vetoed_by: string | null;
  trade_id: string | null;
  /** The breached parameter (`null` when the veto names none or the row is not a veto). */
  parameter: string | null;
  /** `parameter: observed vs limit` of the first bar, `null` without a veto. */
  why: string | null;
}

export interface DecisionLogPage {
  mode: DecisionLogMode;
  page: number;
  size: number;
  /** Rows before grouping, in this mode. */
  total_rows: number;
  /** Groups in this mode (pages are cut over groups). */
  total_groups: number;
  groups: DecisionLogGroup[];
}

/** One chain evaluation for the decision panel: the row, its filters and the run's parameters. */
export interface DecisionDetail {
  decision: DecisionRow;
  filters: FilterRow[];
  parameters: ParameterRow[];
}
