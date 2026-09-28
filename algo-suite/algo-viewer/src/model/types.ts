/** Row shapes of the results database (algo-analyze `results-db build`, schema version 1). */

export const SCHEMA_VERSION = 1;

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

/** Everything the trade drawer shows for one trade. */
export interface TradeDetail {
  run: RunRow;
  trade: TradeRow;
  plan: TradePlan | null;
  entryDecision: DecisionRow | null;
  filters: FilterRow[];
  trailMoves: TrailMove[];
  bars: EntryBar[];
  parameters: ParameterRow[];
}
