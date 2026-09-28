import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { fireEvent, render, screen, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement, useState } from "react";
import { RunsTable } from "../../src/views/RunsTable";
import type { RunRow } from "../../src/model/types";

function runFromRow(cells: Record<string, string>): RunRow {
  return {
    run_id: cells["run_id"] ?? "", job: cells["job"] ?? "", run_dir: "/runs/" + (cells["run_id"] ?? ""),
    strategy: cells["strategy"] ?? "", symbol: "EURUSD", start: cells["start"] ?? "", end: cells["end"] ?? "",
    cash: 10000, bar_minutes: Number(cells["bar_minutes"]), model_sha256: null, code_revision: null, success: 1,
    closed_trades: Number(cells["closed_trades"]), total_return: Number(cells["total_return"]), sharpe: null,
    max_drawdown: Number(cells["max_drawdown"]), hit_rate: null, statement_path: null, report_path: null,
    equity_png_path: null, win_rate: Number(cells["win_rate"]),
  };
}

function Harness({ runs }: { runs: RunRow[] }) {
  // A tiny stateful wrapper so ticking a checkbox updates the selection like the App does.
  const [selected, setSelected] = useState<Set<string>>(new Set());
  return createElement(RunsTable, {
    runs, selected,
    onToggle: (id: string) => setSelected((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; }),
    onOpen: () => undefined, onCompare: () => undefined,
  });
}

Given("these runs:", function (table: DataTable) {
  const runs = table.hashes().map(runFromRow);
  render(createElement(Harness, { runs }));
});

function visibleIds(): string[] {
  const table = screen.getByTestId("runs-table");
  return within(table).getAllByRole("row").slice(1).map((row) => row.getAttribute("data-run-id") ?? "");
}

When("I filter the runs table by {string}", function (text: string) {
  fireEvent.change(screen.getByLabelText("Filter runs"), { target: { value: text } });
});

When("I choose the bar size {string}", function (label: string) {
  const select = screen.getByLabelText("Bar size");
  const option = within(select).getByText<HTMLOptionElement>(label);
  fireEvent.change(select, { target: { value: option.value } });
});

When("I sort the runs by {string} {word}", function (column: string, direction: string) {
  const header = screen.getByText((content) => content.startsWith(column), { selector: "th" });
  const arrow = direction === "descending" ? "▼" : "▲";
  const text = () => header.textContent ?? "";
  for (let i = 0; i < 3 && !text().includes(arrow); i += 1) fireEvent.click(header);
  assert.ok(text().includes(arrow), `header ${column} did not reach ${direction}`);
});

When("I tick runs {word} and {word}", function (a: string, b: string) {
  fireEvent.click(screen.getByLabelText(`select ${a}`));
  fireEvent.click(screen.getByLabelText(`select ${b}`));
});

Then("the visible run ids are {}", function (ids: string) {
  const expected = ids.trim() === "" ? [] : ids.split(",").map((s) => s.trim());
  assert.deepEqual(visibleIds(), expected);
});

Then("the visible run ids are", function () {
  assert.deepEqual(visibleIds(), []);
});

Then("the compare button is disabled", function () {
  assert.equal(screen.getByText<HTMLButtonElement>("Compare selected").disabled, true);
});

Then("the compare button is enabled", function () {
  assert.equal(screen.getByText<HTMLButtonElement>("Compare selected").disabled, false);
});

Then("the toolbar reads {string}", function (text: string) {
  assert.ok(screen.getByText((content) => content.includes(text)));
});
