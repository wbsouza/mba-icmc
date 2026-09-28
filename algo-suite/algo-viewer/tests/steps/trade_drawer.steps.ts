import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { explainFilter } from "../../src/model/explain";
import type { FilterRow } from "../../src/model/types";
import { TradeDrawer } from "../../src/views/TradeDrawer";
import { verticalGuides } from "../../src/charts/CandleChart";
import type { EntryBar } from "../../src/model/types";
import { apiClient } from "../support/server";

let filterRow: FilterRow | null = null;

When("I open trade {string} of run {string}", async function (tradeId: string, runId: string) {
  const detail = await apiClient().tradeDetail(runId, tradeId);
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
  const details = step("F3").querySelector(".pattern-card p")?.textContent ?? "";
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

let clipboard = "";

Then("the drawer shows a pattern card {string} \\({word}\\) linking to {string} and to TA-Lib {word}", function (title: string, direction: string, url: string, fn: string) {
  const card = within(drawer()).getByTestId("pattern-card");
  assert.equal(card.querySelector(".name")?.textContent, title);
  assert.equal(card.querySelector(".badge")?.textContent, direction);
  const links = within(card).getAllByRole("link");
  assert.ok(links.some((a) => a.getAttribute("href") === url), `no link to ${url}`);
  assert.ok(links.some((a) => a.textContent === `TA-Lib ${fn}`), `no TA-Lib ${fn} link`);
});

When("I press {string}", async function (label: string) {
  clipboard = "";
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: (text: string) => { clipboard = text; return Promise.resolve(); } },
  });
  fireEvent.click(within(drawer()).getByText(label));
  await waitFor(() => assert.notEqual(clipboard, ""));
});

Then("the copied link ends with {string}", function (suffix: string) {
  assert.ok(clipboard.endsWith(suffix), `${clipboard} does not end with ${suffix}`);
});

Then("the button reads {string}", async function (label: string) {
  await waitFor(() => assert.equal(within(drawer()).getByTestId("copy-link").textContent, label));
});

Then("the chart caption reads {string} and {string}", function (entry: string, exit: string) {
  const caption = within(drawer()).getByTestId("chart-caption");
  const entryText = caption.querySelector(".entry")?.textContent ?? "";
  const exitText = caption.querySelector(".exit")?.textContent ?? "";
  assert.equal(entryText.replace(/\s+/g, " ").trim(), entry);
  assert.equal(exitText.replace(/\s+/g, " ").trim(), exit);
});

Then("the entry-bars heading reads {string}", function (text: string) {
  assert.equal(within(drawer()).getByTestId("bars-heading").textContent, text);
});

Then("the chart caption says {string}", function (text: string) {
  const note = within(drawer()).getByTestId("chart-caption").querySelector(".beyond")?.textContent ?? "";
  assert.equal(note.replace(/\s+/g, " ").trim(), text);
});

Then("the chart caption does not say the exit is beyond the window", function () {
  assert.equal(within(drawer()).getByTestId("chart-caption").querySelector(".beyond"), null);
});

let guideBars: EntryBar[] = [];
let guideTrade = { exit_time: "" };

Given("entry bars every {int} minutes from {word} for {int} bars", function (minutes: number, first: string, count: number) {
  const start = new Date(first).getTime();
  guideBars = Array.from({ length: count }, (_, i) => ({
    offset: i - 2, time: new Date(start + i * minutes * 60_000).toISOString().replace(".000Z", "+00:00"),
    open: 1, high: 1, low: 1, close: 1,
  }));
});

Given("a trade entered at {word} and exited at {word}", function (_entry: string, exit: string) {
  guideTrade = { exit_time: exit };
});

Then("the vertical guides are {}", function (expected: string) {
  const actual = verticalGuides(guideBars, guideTrade).map((g) => `${g.kind}@${g.time}`);
  assert.deepEqual(actual, expected.split(",").map((s) => s.trim()));
});

Then("no step of the entry chain is vetoed", function () {
  const items = [...within(drawer()).getByTestId("chain").querySelectorAll("li")];
  assert.ok(items.length > 0);
  assert.ok(items.every((li) => li.getAttribute("data-vetoed") === "no" && !li.classList.contains("vetoed")));
});

function eventRows(): Element[] {
  return [...within(drawer()).getByTestId("trade-events").querySelectorAll("tbody tr[data-decision-id]")];
}

Then("the drawer lists the events while open:", function (expected: DataTable) {
  const rows = eventRows().map((tr) => {
    const [when, decision, vetoedBy, why] = [...tr.querySelectorAll("td")].map((td) => td.textContent?.replace(/\s+/g, " ").trim() ?? "");
    return { when: when ?? "", decision: decision ?? "", vetoed_by: vetoedBy ?? "", why: why ?? "", vetoed: tr.getAttribute("data-vetoed") ?? "" };
  });
  assert.deepEqual(rows, expected.hashes());
});

When("I click the event at {string}", function (when: string) {
  const row = eventRows().find((tr) => tr.querySelector("td")?.textContent?.trim() === when);
  assert.ok(row, `no event at ${when}`);
  fireEvent.click(row);
});

Then("the event chain step {string} is vetoed with why {string}", async function (filter: string, why: string) {
  const chain = await waitFor(() => within(drawer()).getByTestId("event-chain"));
  const step = chain.querySelector(`li[data-filter="${filter}"]`);
  assert.ok(step, `no step for ${filter}`);
  assert.equal(step.getAttribute("data-vetoed"), "yes");
  assert.equal(step.querySelector(".why")?.textContent, why);
});

Then("the drawer says {string}", function (text: string) {
  assert.ok(within(drawer()).getByText(text));
});
