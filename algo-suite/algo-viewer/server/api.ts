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
 *   GET /api/runs/:id/trades/:tradeId            TradeDetail
 *
 * Unknown runs and trades answer 404 with `{error}`; unknown routes 404; other methods 405.
 */

import type { Queryable } from "./db.js";
import { SCHEMA_VERSION } from "../src/model/types.js";
import {
  decisionSummary,
  equitySamples,
  getRun,
  listRuns,
  monthlyReturns,
  parameters,
  tradeDetail,
  trades,
} from "./queries.js";

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

function runResponse(db: Queryable, runId: string, rest: string[]): ApiResponse {
  const run = getRun(db, runId);
  if (run === null) return notFound(`run ${runId}`);
  const [resource, tradeId, ...extra] = rest;
  if (resource === undefined) return ok(run);
  if (resource === "trades" && tradeId !== undefined && extra.length === 0) {
    const detail = tradeDetail(db, runId, tradeId);
    return detail === null ? notFound(`trade ${tradeId} of run ${runId}`) : ok(detail);
  }
  const query = RUN_RESOURCES[resource];
  if (query === undefined || tradeId !== undefined) return notFound(`route /api/runs/${runId}/${rest.join("/")}`);
  return ok(query(db, runId));
}

/** Answer one API request; `path` is the URL path without query string. */
export function handleApi(db: Queryable, method: string, path: string): ApiResponse {
  if (method !== "GET") return { status: 405, body: { error: `${method} is not supported; the API is read-only` } };
  const parts = path.split("/").filter((p) => p !== "").map(decodeURIComponent);
  if (parts[0] !== "api") return notFound(`route ${path}`);
  if (parts[1] === "health" && parts.length === 2) {
    return ok({ schema_version: SCHEMA_VERSION, runs: listRuns(db).length });
  }
  if (parts[1] === "runs") {
    if (parts.length === 2) return ok(listRuns(db));
    const runId = parts[2];
    if (runId !== undefined) return runResponse(db, runId, parts.slice(3));
  }
  return notFound(`route ${path}`);
}
