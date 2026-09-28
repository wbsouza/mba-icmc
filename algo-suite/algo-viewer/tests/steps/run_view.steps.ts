import "../support/dom";
import { Given, Then, When } from "@cucumber/cucumber";
import { render, screen, waitFor, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { monthlyBars } from "../../src/charts/MonthlyBars";
import type { MonthlyReturn } from "../../src/model/types";
import { RunView } from "../../src/views/RunView";
import { apiClient } from "../support/server";

let months: MonthlyReturn[] = [];

When("I open the run page of {string}", async function (runId: string) {
  const api = apiClient();
  const run = await api.run(runId);
  render(createElement(RunView, { api, run, dark: false, onSelectTrade: () => undefined }));
  await waitFor(() => screen.getByTestId("trades-table"));
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
