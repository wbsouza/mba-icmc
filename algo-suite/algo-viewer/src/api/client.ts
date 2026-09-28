/** The frontend's only data source: the backend's JSON endpoints (server/api.ts). */

import type {
  DecisionDetail,
  DecisionLogMode,
  DecisionLogPage,
  DecisionSummaryRow,
  EquitySample,
  MonthlyReturn,
  ParameterRow,
  RunRow,
  TradeDetail,
  TradeRow,
} from "../model/types";

export interface PatternExample {
  run_id: string;
  trade_id: string;
  entry_time: string;
  direction: "buy" | "sell";
  profit: number;
}

export interface Health {
  schema_version: number;
  runs: number;
}

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

export class ApiClient {
  /** `base` is the backend origin; empty = same origin as the page. */
  constructor(private readonly base = "") {}

  private async get<T>(path: string): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${this.base}${path}`, { headers: { accept: "application/json" } });
    } catch (error) {
      throw new ApiError(0, `backend unreachable at ${this.base || "this origin"}${path}: ${String(error)}`);
    }
    const text = await response.text();
    let body: unknown = null;
    try {
      body = text === "" ? null : JSON.parse(text);
    } catch {
      throw new ApiError(response.status, `backend answered ${response.status} with non-JSON content at ${path}`);
    }
    if (!response.ok) {
      const error = typeof body === "object" && body !== null && "error" in body ? String(body.error) : response.statusText;
      throw new ApiError(response.status, error);
    }
    return body as T;
  }

  health(): Promise<Health> { return this.get("/api/health"); }
  runs(): Promise<RunRow[]> { return this.get("/api/runs"); }
  run(runId: string): Promise<RunRow> { return this.get(`/api/runs/${encodeURIComponent(runId)}`); }
  equity(runId: string): Promise<EquitySample[]> { return this.get(`/api/runs/${encodeURIComponent(runId)}/equity`); }
  monthly(runId: string): Promise<MonthlyReturn[]> { return this.get(`/api/runs/${encodeURIComponent(runId)}/monthly`); }
  parameters(runId: string): Promise<ParameterRow[]> { return this.get(`/api/runs/${encodeURIComponent(runId)}/parameters`); }
  trades(runId: string): Promise<TradeRow[]> { return this.get(`/api/runs/${encodeURIComponent(runId)}/trades`); }
  decisionSummary(runId: string): Promise<DecisionSummaryRow[]> { return this.get(`/api/runs/${encodeURIComponent(runId)}/decision-summary`); }
  decisionLog(runId: string, mode: DecisionLogMode, page = 1, size = 200): Promise<DecisionLogPage> {
    return this.get(`/api/runs/${encodeURIComponent(runId)}/decisions?mode=${mode}&page=${page}&size=${size}`);
  }
  decisionDetail(runId: string, decisionId: number): Promise<DecisionDetail> {
    return this.get(`/api/runs/${encodeURIComponent(runId)}/decisions/${decisionId}`);
  }
  patternExamples(name: string, limit = 3): Promise<PatternExample[]> {
    return this.get(`/api/patterns/${encodeURIComponent(name)}/examples?limit=${limit}`);
  }
  tradeDetail(runId: string, tradeId: string): Promise<TradeDetail> {
    return this.get(`/api/runs/${encodeURIComponent(runId)}/trades/${encodeURIComponent(tradeId)}`);
  }
}
