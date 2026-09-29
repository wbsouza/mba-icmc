import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { fireEvent, screen, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { describeFilter, parametersFor } from "../../src/model/chain";
import type { ParameterRow } from "../../src/model/types";

let parameters: ParameterRow[] = [];

Then("the chain workflow nodes are, in order:", function (table: DataTable) {
  const nodes = [...screen.getByTestId("chain-workflow").querySelectorAll("li[data-node]")];
  const actual = nodes.map((li) => ({
    node: li.getAttribute("data-node") ?? "",
    label: li.querySelector(".label")?.textContent ?? "",
    vetoes: li.getAttribute("data-vetoes") ?? "",
  }));
  assert.deepEqual(actual, table.hashes());
});

Then("no filter details are shown", function () {
  assert.equal(screen.queryByTestId("filter-details"), null);
});

When("I click the chain node {string}", function (name: string) {
  const node = screen.getByTestId("chain-workflow").querySelector(`li[data-node="${name}"] button`);
  assert.ok(node, `no node ${name}`);
  fireEvent.click(node);
});

Then("the filter details are titled {string}", function (title: string) {
  assert.equal(within(screen.getByTestId("filter-details")).getByRole("heading", { level: 3 }).textContent, title);
});

Then("the filter details list the parameters:", function (table: DataTable) {
  const rows = [...screen.getByTestId("filter-parameters").querySelectorAll("tbody tr")].map((tr) => {
    const cells = [...tr.querySelectorAll("td")].map((td) => td.textContent ?? "");
    return { key: cells[0] ?? "", value: cells[1] ?? "", source: cells[2] ?? "" };
  });
  assert.deepEqual(rows, table.hashes());
});

Given("the run parameters:", function (table: DataTable) {
  parameters = table.hashes().map((r) => ({ key: r["key"] ?? "", value: r["value"] ?? "", source: "x" }));
});

Then("the parameters of filter {string} are {}", function (name: string, keys: string) {
  const actual = parametersFor(describeFilter(name), parameters).map((p) => p.key).sort();
  assert.deepEqual(actual, keys.split(",").map((s) => s.trim()).sort());
});
