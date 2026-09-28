import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { render, screen, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { pivotMonthly, rebase, type MonthlyColumn, type MonthlyPivotRow, type RebasedPoint } from "../../src/model/rebase";
import type { EquitySample } from "../../src/model/types";
import { CompareView } from "../../src/views/CompareView";
import { listRuns } from "../../src/db/queries";
import { fixtureDatabase } from "../support/fixture";

interface World {
  series?: EquitySample[];
  rebased?: RebasedPoint[];
  failure?: string;
  columns: MonthlyColumn[];
  pivot?: MonthlyPivotRow[];
}

const state: World = { columns: [] };

Given("an equity series of {}", function (values: string) {
  state.series = values.split(",").map((v, i) => ({ time: `2016-03-0${i + 1}T00:00:00+00:00`, equity: Number(v.trim()), drawdown_pct: 0 }));
  state.columns = [];
});

When("I re-base it", function () {
  state.rebased = rebase(state.series ?? []);
});

When("I re-base it expecting failure", function () {
  try {
    rebase(state.series ?? []);
    state.failure = "";
  } catch (e) {
    state.failure = e instanceof Error ? e.message : String(e);
  }
});

Then("the re-based series is {}", function (values: string) {
  const expected = values.split(",").map((v) => Number(v.trim()));
  const actual = (state.rebased ?? []).map((p) => Number(p.equity.toFixed(6)));
  assert.deepEqual(actual, expected);
});

Then("the re-basing fails with {string}", function (text: string) {
  assert.ok((state.failure ?? "").includes(text), `failure ${JSON.stringify(state.failure)} lacks ${text}`);
});

Given("run {string} with monthly returns:", function (runId: string, table: DataTable) {
  state.columns.push({
    runId, label: runId,
    months: table.hashes().map((r) => ({ month: r["month"] ?? "", start_equity: 0, end_equity: 0, return_pct: Number(r["return_pct"]), trades: 0 })),
  });
});

When("I pivot the monthly returns", function () {
  state.pivot = pivotMonthly(state.columns);
});

Then("the pivot rows are:", function (table: DataTable) {
  const [header, ...rows] = table.raw();
  const runIds = (header ?? []).slice(1);
  const expected = rows.map((r) => ({ month: r[0], cells: Object.fromEntries(runIds.map((id, i) => [id, r[i + 1] === "" ? null : Number(r[i + 1])])) }));
  assert.deepEqual(state.pivot, expected);
});

Given("the fixture results database is open", async function () {
  await fixtureDatabase();
});

When("I compare the runs {}", async function (ids: string) {
  const db = await fixtureDatabase();
  const runs = listRuns(db).filter((r) => ids.split(",").map((s) => s.trim()).includes(r.run_id));
  render(createElement(CompareView, { db, runs, dark: false, onOpen: () => undefined }));
});

Then("the monthly table lists the months {}", function (months: string) {
  const table = screen.getByTestId("monthly-table");
  const shown = within(table).getAllByRole("row").slice(1).map((row) => row.querySelector("td")?.textContent ?? "");
  assert.deepEqual(shown, months.split(",").map((s) => s.trim()));
});

Then("the legend names {string}", function (label: string) {
  assert.ok(screen.getAllByText(label).length >= 1);
});
