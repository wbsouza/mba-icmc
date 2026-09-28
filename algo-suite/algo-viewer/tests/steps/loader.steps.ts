import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import initSqlJs from "sql.js";
import type { Database } from "sql.js";
import { openDatabase, rows } from "../../src/db/loader";
import { decisionSummary, getRun, listRuns, parameters, tradeDetail } from "../../src/db/queries";
import { fixtureBytes } from "../support/fixture";

let bytes: Uint8Array = new Uint8Array();
let opened: Database | null = null;
let failure = "";

async function emptyDatabase(statements: string[]): Promise<Uint8Array> {
  const SQL = await initSqlJs();
  const db = new SQL.Database();
  for (const sql of statements) db.run(sql);
  const out = db.export();
  db.close();
  return out;
}

Given("the fixture results database bytes", function () {
  bytes = fixtureBytes();
});

Given("the bytes of an empty SQLite database", async function () {
  bytes = await emptyDatabase([]);
});

Given("the bytes of an SQLite database whose schema_version is {int}", async function (version: number) {
  bytes = await emptyDatabase(["CREATE TABLE schema_version (version INTEGER NOT NULL)", `INSERT INTO schema_version VALUES (${version})`]);
});

When("I open the database", async function () {
  opened = await openDatabase(bytes);
});

When("I open the database expecting failure", async function () {
  try {
    await openDatabase(bytes);
    failure = "";
  } catch (e) {
    failure = e instanceof Error ? e.message : String(e);
  }
});

Then("it holds {int} run, {int} trades and {int} entry decisions", function (runs: number, trades: number, entries: number) {
  assert.ok(opened);
  assert.equal(listRuns(opened).length, runs);
  assert.equal(rows<{ n: number }>(opened, "SELECT COUNT(*) AS n FROM trades")[0]?.n, trades);
  assert.equal(rows<{ n: number }>(opened, "SELECT COUNT(*) AS n FROM decisions WHERE is_entry = 1")[0]?.n, entries);
});

Then("the run {string} is strategy {string} on {word} with {int} trades and win rate {float}", function (runId: string, strategy: string, bars: string, trades: number, winRate: number) {
  assert.ok(opened);
  const run = getRun(opened, runId);
  assert.ok(run);
  assert.equal(run.strategy, strategy);
  assert.equal(bars, run.bar_minutes === 60 ? "H1" : String(run.bar_minutes));
  assert.equal(run.closed_trades, trades);
  assert.equal(run.win_rate, winRate);
});

Then("the run's parameter {string} is {string} from {string}", function (key: string, value: string, source: string) {
  assert.ok(opened);
  const run = listRuns(opened)[0];
  assert.ok(run);
  const hit = parameters(opened, run.run_id).find((p) => p.key === key);
  assert.deepEqual(hit, { key, value, source });
});

Then("the run's decision funnel is:", function (table: DataTable) {
  assert.ok(opened);
  const run = listRuns(opened)[0];
  assert.ok(run);
  const key = (r: Record<string, string>) => `${r["final_decision"] ?? ""}/${r["vetoed_by"] ?? ""}`;
  const actual = decisionSummary(opened, run.run_id)
    .map((r) => ({ final_decision: r.final_decision, vetoed_by: r.vetoed_by, count: String(r.count) }))
    .sort((a, b) => key(a).localeCompare(key(b)));
  const expected = [...table.hashes()].sort((a, b) => key(a).localeCompare(key(b)));
  assert.deepEqual(actual, expected);
});

Then("trade {string} has {int} entry bars from offset {int} to {int}", function (tradeId: string, count: number, first: number, last: number) {
  assert.ok(opened);
  const run = listRuns(opened)[0];
  assert.ok(run);
  const detail = tradeDetail(opened, run.run_id, tradeId);
  assert.ok(detail);
  assert.equal(detail.bars.length, count);
  assert.equal(detail.bars[0]?.offset, first);
  assert.equal(detail.bars[detail.bars.length - 1]?.offset, last);
});

Then("the failure says {string}", function (text: string) {
  assert.ok(failure.includes(text), `${failure} lacks ${text}`);
});
