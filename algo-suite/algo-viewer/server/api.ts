/**
 * The JSON API, as a pure dispatcher (method + path -> status + body) so the scenarios
 * can call it directly and `http.ts` only has to serialize.
 *
 *   GET /api/health                              {schema_version, runs}
 *   GET /api/runs                                RunRow[]
 *   GET /api/runs/:id                            RunRow
 *   GET /api/runs/:id/equity                     EquitySample[]
 *   GET /api/runs/:id/monthly                    MonthlyReturn[]
 *   GET /api/runs/:id/parameters                 ParameterRow[]
 *   GET /api/runs/:id/trades                     TradeRow[]
 *   GET /api/runs/:id/decision-summary           DecisionSummaryRow[]
 *   GET /api/runs/:id/trades/:tradeId            TradeDetail (with the events while the trade was open)
 *   GET /api/runs/:id/decisions?mode=vetoes&page=1&size=200   DecisionLogPage (mode vetoes|entries|all; size 1..1000)
 *   GET /api/runs/:id/decisions/:decisionId      DecisionDetail (one bar's chain with the run's parameters)
 *   GET /api/patterns/:name/examples?limit=3     PatternExample[] (most recent distinct entry times, limit 1..50)
 *
 * Unknown runs and trades answer 404 with `{error}`; unknown routes 404; other methods 405.
 */

import type { Queryable } from "./db.js";
import { SCHEMA_VERSION, type DecisionLogMode } from "../src/model/types.js";
import {
  decisionDetail,
  decisionLog,
  decisionSummary,
  equitySamples,
  getRun,
  listRuns,
  monthlyReturns,
  parameters,
  patternExamples,
  tradeDetail,
  trades,
} from "./queries.js";

const MAX_EXAMPLES = 50;
const MAX_LOG_PAGE = 1000;
const LOG_MODES: readonly DecisionLogMode[] = ["vetoes", "entries", "all"];

export interface ApiResponse {
  status: number;
  body: unknown;
}

type RunQuery = (db: Queryable, runId: string) => unknown;

const RUN_RESOURCES: Record<string, RunQuery> = {
  equity: equitySamples,
  monthly: monthlyReturns,
  parameters,
  trades,
  "decision-summary": decisionSummary,
};

function ok(body: unknown): ApiResponse {
  return { status: 200, body };
}

function notFound(what: string): ApiResponse {
  return { status: 404, body: { error: `${what} not found` } };
}

function runResponse(db: Queryable, runId: string, rest: string[], search: URLSearchParams): ApiResponse {
  const run = getRun(db, runId);
  if (run === null) return notFound(`run ${runId}`);
  const [resource, tradeId, ...extra] = rest;
  if (resource === undefined) return ok(run);
  if (resource === "trades" && tradeId !== undefined && extra.length === 0) {
    const detail = tradeDetail(db, runId, tradeId);
    return detail === null ? notFound(`trade ${tradeId} of run ${runId}`) : ok(detail);
  }
  if (resource === "decisions" && tradeId !== undefined && extra.length === 0) {
    const id = Number(tradeId);
    if (!Number.isInteger(id) || id < 1) return { status: 400, body: { error: `decision id must be a positive integer, got ${tradeId}` } };
    const detail = decisionDetail(db, runId, id);
    return detail === null ? notFound(`decision ${tradeId} of run ${runId}`) : ok(detail);
  }
  if (resource === "decisions" && tradeId === undefined) return decisionsResponse(db, runId, search);
  const query = RUN_RESOURCES[resource];
  if (query === undefined || tradeId !== undefined) return notFound(`route /api/runs/${runId}/${rest.join("/")}`);
  return ok(query(db, runId));
}

function positiveInt(search: URLSearchParams, name: string, fallback: number, max: number): number | ApiResponse {
  const raw = search.get(name);
  if (raw === null) return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > max) {
    return { status: 400, body: { error: `${name} must be an integer between 1 and ${max}, got ${raw}` } };
  }
  return value;
}

function decisionsResponse(db: Queryable, runId: string, search: URLSearchParams): ApiResponse {
  const mode = search.get("mode") ?? "vetoes";
  if (!LOG_MODES.includes(mode as DecisionLogMode)) {
    return { status: 400, body: { error: `mode must be one of ${LOG_MODES.join(", ")}, got ${mode}` } };
  }
  const page = positiveInt(search, "page", 1, Number.MAX_SAFE_INTEGER);
  if (typeof page !== "number") return page;
  const size = positiveInt(search, "size", 200, MAX_LOG_PAGE);
  if (typeof size !== "number") return size;
  return ok(decisionLog(db, runId, mode as DecisionLogMode, page, size));
}

function examplesResponse(db: Queryable, name: string, query: URLSearchParams): ApiResponse {
  const raw = query.get("limit") ?? "3";
  const limit = Number(raw);
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_EXAMPLES) {
    return { status: 400, body: { error: `limit must be an integer between 1 and ${MAX_EXAMPLES}, got ${raw}` } };
  }
  return ok(patternExamples(db, name, limit));
}

/** Answer one API request; `path` is the URL path, `query` its query string. */
export function handleApi(db: Queryable, method: string, path: string, query: URLSearchParams = new URLSearchParams()): ApiResponse {
  if (method !== "GET") return { status: 405, body: { error: `${method} is not supported; the API is read-only` } };
  const parts = path.split("/").filter((p) => p !== "").map(decodeURIComponent);
  if (parts[0] !== "api") return notFound(`route ${path}`);
  if (parts[1] === "health" && parts.length === 2) {
    return ok({ schema_version: SCHEMA_VERSION, runs: listRuns(db).length });
  }
  if (parts[1] === "runs") {
    if (parts.length === 2) return ok(listRuns(db));
    const runId = parts[2];
    if (runId !== undefined) return runResponse(db, runId, parts.slice(3), query);
  }
  if (parts[1] === "patterns" && parts[2] !== undefined && parts[3] === "examples" && parts.length === 4) {
    return examplesResponse(db, parts[2], query);
  }
  return notFound(`route ${path}`);
}
