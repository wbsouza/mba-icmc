import "../support/dom";
import { Given, Then, When } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { ApiClient } from "../../src/api/client";
import type { ParameterRow, TradeDetail } from "../../src/model/types";
import { openResultsDatabase } from "../../server/db";
import { parseArgs, type CliOptions } from "../../server/main";
import { apiClient, backendUrl } from "../support/server";

let status = 0;
let body: unknown = null;
let params: ParameterRow[] = [];
let detail: TradeDetail | null = null;
let clientFailure = "";
let openFailure = "";
let sqlitePath = "";
let parsed: CliOptions | Error | null = null;

Given("the backend serves the fixture database", function () {
  assert.ok(backendUrl().startsWith("http://"));
});

async function request(method: string, path: string): Promise<void> {
  const response = await fetch(`${backendUrl()}${path}`, { method });
  status = response.status;
  body = await response.json();
}

When("I GET {string}", async function (path: string) {
  await request("GET", path);
});

When("I POST {string}", async function (path: string) {
  await request("POST", path);
});

Then("the status is {int}", function (expected: number) {
  assert.equal(status, expected, JSON.stringify(body));
});

function obj(): Record<string, unknown> {
  assert.ok(typeof body === "object" && body !== null && !Array.isArray(body), `not an object: ${JSON.stringify(body)}`);
  return body as Record<string, unknown>;
}

Then("the JSON has schema_version {int} and runs {int}", function (version: number, runs: number) {
  assert.equal(obj()["schema_version"], version);
  assert.equal(obj()["runs"], runs);
});

Then("the JSON is a list of {int} item(s)", function (count: number) {
  assert.ok(Array.isArray(body), `not a list: ${JSON.stringify(body)}`);
  assert.equal(body.length, count);
});

Then("the JSON has strategy {string}, bar_minutes {int}, closed_trades {int} and win_rate {float}", function (strategy: string, bars: number, trades: number, winRate: number) {
  const run = obj();
  assert.equal(run["strategy"], strategy);
  assert.equal(run["bar_minutes"], bars);
  assert.equal(run["closed_trades"], trades);
  assert.equal(run["win_rate"], winRate);
});

Then("the JSON has {int} filters, {int} bars and {int} trail moves", function (filters: number, bars: number, moves: number) {
  const d = body as TradeDetail;
  assert.equal(d.filters.length, filters);
  assert.equal(d.bars.length, bars);
  assert.equal(d.trailMoves.length, moves);
});

Then("the error says {string}", function (text: string) {
  const error = String(obj()["error"]);
  assert.ok(error.includes(text), `${error} lacks ${text}`);
});

When("the client asks for the parameters of run {string}", async function (runId: string) {
  params = await apiClient().parameters(runId);
});

Then("the parameter {string} is {string} from {string}", function (key: string, value: string, source: string) {
  assert.deepEqual(params.find((p) => p.key === key), { key, value, source });
});

When("the client asks for trade {string} of run {string}", async function (tradeId: string, runId: string) {
  detail = await apiClient().tradeDetail(runId, tradeId);
});

Then("the trade's exit kind is {string} and its F3 pattern is {string}", function (kind: string, pattern: string) {
  assert.ok(detail);
  assert.equal(detail.trade.exit_kind, kind);
  assert.equal(detail.filters.find((f) => f.filter_name === "F3_pattern")?.pattern_name, pattern);
});

When("the client points at a closed port and asks for the runs", async function () {
  try {
    await new ApiClient("http://127.0.0.1:9").runs();
    clientFailure = "";
  } catch (e) {
    clientFailure = e instanceof Error ? e.message : String(e);
  }
});

Then("the client failure says {string}", function (text: string) {
  assert.ok(clientFailure.includes(text), `${clientFailure} lacks ${text}`);
});

Given("an SQLite file whose schema_version is {word}", function (version: string) {
  sqlitePath = join(mkdtempSync(join(tmpdir(), "viewer-")), "other.sqlite");
  const db = new DatabaseSync(sqlitePath);
  if (version === "none") {
    db.exec("CREATE TABLE something (x INTEGER)");
  } else {
    db.exec("CREATE TABLE schema_version (version INTEGER NOT NULL)");
    db.exec(`INSERT INTO schema_version VALUES (${Number(version)})`);
  }
  db.close();
});

When("the backend opens it expecting failure", function () {
  try {
    openResultsDatabase(sqlitePath).close();
    openFailure = "";
  } catch (e) {
    openFailure = e instanceof Error ? e.message : String(e);
  }
});

Then("the open failure says {string}", function (text: string) {
  assert.ok(openFailure.includes(text), `${openFailure} lacks ${text}`);
});

When("I parse the CLI arguments {string}", function (argv: string) {
  try {
    parsed = parseArgs(argv.split(/\s+/).filter((s) => s !== ""));
  } catch (e) {
    parsed = e instanceof Error ? e : new Error(String(e));
  }
});

Then("the parsed options are {}", function (outcome: string) {
  assert.ok(parsed);
  const error = /an error containing "(.+)"/.exec(outcome);
  if (error) {
    assert.ok(parsed instanceof Error, `expected an error, got ${JSON.stringify(parsed)}`);
    assert.ok(parsed.message.includes(error[1] ?? ""), parsed.message);
    return;
  }
  assert.ok(!(parsed instanceof Error), (parsed as Error).message);
  const m = /db (\S+), port (\d+), static (\S+)/.exec(outcome);
  assert.ok(m);
  assert.equal(parsed.db, m[1]);
  assert.equal(parsed.port, Number(m[2]));
  assert.equal(parsed.static ?? "none", m[3]);
});

Then("the JSON lists the example run {string} trade {string} {word} {int}", function (runId: string, tradeId: string, direction: string, profit: number) {
  assert.ok(Array.isArray(body));
  assert.equal(body.length, 1);
  const example = body[0] as Record<string, unknown>;
  assert.equal(example["run_id"], runId);
  assert.equal(example["trade_id"], tradeId);
  assert.equal(example["direction"], direction);
  assert.equal(example["profit"], profit);
  assert.equal(typeof example["entry_time"], "string");
});

Then("the JSON says {string}", function (text: string) {
  const error = String(obj()["error"]);
  assert.ok(error.includes(text), `${error} lacks ${text}`);
});
