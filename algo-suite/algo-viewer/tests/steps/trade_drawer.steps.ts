import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { render, screen, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { tradeDetail } from "../../src/db/queries";
import { explainFilter } from "../../src/model/explain";
import type { FilterRow } from "../../src/model/types";
import { TradeDrawer } from "../../src/views/TradeDrawer";
import { fixtureDatabase } from "../support/fixture";

let filterRow: FilterRow | null = null;

When("I open trade {string} of run {string}", async function (tradeId: string, runId: string) {
  const detail = tradeDetail(await fixtureDatabase(), runId, tradeId);
  assert.ok(detail, `no trade ${tradeId} in run ${runId}`);
  render(createElement(TradeDrawer, { detail, dark: false, onClose: () => undefined }));
});

function drawer(): HTMLElement {
  return screen.getByTestId("trade-drawer");
}

function step(title: string): HTMLElement {
  const items = within(drawer()).getByTestId("chain").querySelectorAll("li");
  for (const item of items) {
    if (item.querySelector(".title")?.textContent?.startsWith(title)) return item;
  }
  throw new Error(`no chain step titled ${title}`);
}

Then("the drawer lists the chain steps in order:", function (table: DataTable) {
  const items = [...within(drawer()).getByTestId("chain").querySelectorAll("li")];
  const actual = items.map((li) => ({
    step: li.querySelector(".title")?.firstChild?.textContent?.trim() ?? "",
    recommendation: li.querySelector(".title .badge")?.textContent ?? "",
  }));
  assert.deepEqual(actual, table.hashes());
});

Then("the drawer names the pattern {string}", function (label: string) {
  assert.equal(within(drawer()).getByTestId("pattern-name").textContent, label);
});

Then("the drawer describes the pattern with {string}", function (text: string) {
  const details = step("F3").querySelector(".details")?.textContent ?? "";
  assert.ok(details.includes(text), `${details} lacks ${text}`);
});

Then("the drawer step {string} reads {string}", function (title: string, summary: string) {
  assert.equal(step(title).querySelector(".summary")?.textContent, summary);
});

Then("the drawer shows the exit kind {string}", function (label: string) {
  assert.equal(within(drawer()).getByTestId("exit-kind").textContent, label);
});

Then("the drawer shows the plan stop {string}", function (text: string) {
  assert.ok(within(drawer()).getByText(text, { selector: "dd" }));
});

Then("the drawer shows the realized P\\/L {string}", function (text: string) {
  const cell = within(drawer()).getAllByText((content) => content.includes(text), { selector: "dd" });
  assert.ok(cell.length > 0);
});

Then("the drawer offers {int} entry bars", function (count: number) {
  const fallback = within(drawer()).getByTestId("chart-fallback").textContent ?? "";
  assert.ok(fallback.includes(`${count} bars`), fallback);
});

Then("the drawer lists the trail move {string}", function (text: string) {
  assert.ok(within(drawer()).getByText((content) => content.includes(text), { selector: "dd" }));
});

Given("a filter row {string} recommending {word} with veto {word} and reason {string}", function (name: string, recommendation: string, veto: string, reason: string) {
  const match = /detected candlestick pattern '([a-z_]+)'/.exec(reason);
  filterRow = { position: 0, filter_name: name, recommendation, veto: veto === "yes" ? 1 : 0, reason, pattern_name: match?.[1] ?? null };
});

Then("its explanation summary is {string}", function (summary: string) {
  assert.ok(filterRow);
  assert.equal(explainFilter(filterRow, [{ key: "volume_strength.min_relative_activity", value: "1.0", source: "x" }]).summary, summary);
});
