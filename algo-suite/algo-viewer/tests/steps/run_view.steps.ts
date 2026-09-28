import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { render, screen, waitFor, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { monthlyBars } from "../../src/charts/MonthlyBars";
import type { MonthlyReturn, TradeRow } from "../../src/model/types";
import { balancesAfter } from "../../src/model/balance";
import { RunView } from "../../src/views/RunView";
import { apiClient } from "../support/server";

let months: MonthlyReturn[] = [];

let noOpenPositions = false;

Given("the fixture run had no open positions", function () {
  noOpenPositions = true;
});

When("I open the run page of {string}", async function (runId: string) {
  const client = apiClient();
  const api = noOpenPositions
    ? Object.create(client, { openPositions: { value: () => Promise.resolve([]) } }) as typeof client
    : client;
  noOpenPositions = false;
  const run = await api.run(runId);
  render(createElement(RunView, { api, run, dark: false, onSelectTrade: () => undefined }));
  await waitFor(() => screen.getByTestId("trades-table"));
});

Then("the last two sections of the page are {string} and {string}", function (before: string, last: string) {
  const labels = [...document.querySelectorAll("section.panel")].map((el) => el.getAttribute("aria-label"));
  assert.deepEqual(labels.slice(-2), [before, last], labels.join(" > "));
});

Then("the open trades section is titled {string}", function (title: string) {
  const heading = document.querySelector('section[aria-label="Open trades"] h2');
  assert.ok(heading);
  assert.ok(heading.textContent?.startsWith(title), heading.textContent ?? "");
});

Then("the open trades section lists:", async function (expected: DataTable) {
  const table = await waitFor(() => screen.getByTestId("open-positions"));
  const rows = [...table.querySelectorAll("tbody tr")].map((tr) => {
    const cells = [...tr.querySelectorAll("td")].map((td) => td.textContent?.replace(/\s+/g, " ").trim() ?? "");
    const [ticket, side, lots, opened, open_price, stop, targets, mark, floating_pl] = cells;
    return { ticket: ticket ?? "", side: side ?? "", lots: lots ?? "", opened: opened ?? "", open_price: open_price ?? "", stop: stop ?? "", targets: targets ?? "", mark: mark ?? "", floating_pl: floating_pl ?? "" };
  });
  assert.deepEqual(rows, expected.hashes());
});

Then("the page says {string}", async function (text: string) {
  await waitFor(() => screen.getByText(text));
});

Then("the KPI {string} reads {string}", function (label: string, value: string) {
  const kpi = within(screen.getByTestId("kpis")).getByText(label).parentElement;
  assert.ok(kpi);
  assert.equal(kpi.querySelector(".value")?.textContent, value);
});

Then("the charts on the page are {string} and {string}", function (first: string, second: string) {
  const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
  assert.ok(headings.includes(first), `${headings.join(" | ")} lacks ${first}`);
  assert.ok(headings.includes(second), `${headings.join(" | ")} lacks ${second}`);
});

Then("the monthly bars are {}", function (spec: string) {
  const items = [...screen.getByTestId("monthly-bars").querySelectorAll("li")];
  const actual = items.map((li) => `${li.textContent ?? ""} ${li.getAttribute("data-tone") ?? ""}`);
  assert.deepEqual(actual, spec.split(",").map((s) => s.trim()));
});

Then("there is no {string} heading", function (text: string) {
  assert.equal(screen.queryByRole("heading", { name: text }), null);
});

Given("monthly returns of {}", function (values: string) {
  months = values.split(",").map((v, i) => ({ month: `2016-0${i + 1}`, start_equity: 0, end_equity: 0, return_pct: Number(v.trim()), trades: 0 }));
});

Then("their bar colours are {}", function (colours: string) {
  assert.deepEqual(monthlyBars(months).map((b) => b.tone), colours.split(",").map((s) => s.trim()));
});

let ledger: TradeRow[] = [];
let cash = 0;

Then("the trades table has an {string} column explained as {string}", function (label: string, tooltip: string) {
  const header = within(screen.getByTestId("trades-table")).getByText(label, { selector: "th" });
  assert.ok((header.getAttribute("title") ?? "").includes(tooltip));
});

Then("the trades table shows the equity after each trade:", function (table: DataTable) {
  const rows = [...screen.getByTestId("trades-table").querySelectorAll("tbody tr")].map((tr) => {
    const cells = [...tr.querySelectorAll("td")];
    return { trade_id: tr.getAttribute("data-trade-id") ?? "", profit: cells[9]?.textContent ?? "", equity: cells[10]?.textContent ?? "" };
  });
  assert.deepEqual(rows, table.hashes());
});

Given("trades closed as {} starting from cash {int}", function (closes: string, starting: number) {
  cash = starting;
  ledger = closes.split(",").map((part, i) => {
    const m = /(\w+) exit (\S+) ([+-]?\d+) fee (\d+)/.exec(part.trim());
    assert.ok(m, part);
    return {
      run_id: "r", trade_id: m[1] ?? "", entry_order_id: i, direction: "buy", lots: null, quantity: 1, entry_time: "2016-01-01T00:00:00+00:00",
      entry_price: 1, exit_time: `${m[2] ?? ""}T00:00:00+00:00`, exit_price: 1, profit: Number(m[3]), fees: Number(m[4]), is_win: 1,
      exit_kind: "stop", exit_order_id: null, exit_order_type: null, holding_minutes: 1,
    };
  });
});

Then("the equity after each trade, in row order, is {}", function (expected: string) {
  const balances = balancesAfter(ledger, cash);
  assert.deepEqual(ledger.map((t) => balances.get(t.trade_id)), expected.split(",").map((s) => Number(s.trim())));
});
