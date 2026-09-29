import "../support/dom";
import { DataTable, Given, Then, When } from "@cucumber/cucumber";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { groupDecisions } from "../../server/queries";
import type { FilterRow, ParameterRow } from "../../src/model/types";
import { vetoWhy } from "../../src/model/veto";

let runParameters: ParameterRow[] = [];
let vetoed: FilterRow | null = null;
let grouped = "";

function log(): HTMLElement {
  return screen.getByTestId("decision-log");
}

async function table(): Promise<HTMLElement> {
  return waitFor(() => within(log()).getByTestId("decision-table"));
}

function cells(row: Element): string[] {
  return [...row.querySelectorAll("td")].map((td) => td.textContent?.replace(/\s+/g, " ").trim() ?? "");
}

Then("the decision log summary reads {string}", async function (text: string) {
  await waitFor(() => assert.equal(within(log()).getByTestId("log-summary").textContent?.replace(/\s+/g, " ").trim(), text));
});

Then("the decision log rows are:", async function (expected: DataTable) {
  const body = await table();
  const rows = [...body.querySelectorAll("tbody tr[data-decision-id]")].map((tr) => {
    const [when, decision, vetoedBy, why] = cells(tr);
    return { when: when ?? "", decision: decision ?? "", vetoed_by: vetoedBy ?? "", why: why ?? "", vetoed: tr.getAttribute("data-vetoed") ?? "" };
  });
  assert.deepEqual(rows, expected.hashes());
});

When("I switch the decision log to {string}", function (label: string) {
  fireEvent.click(within(log()).getByText(label, { selector: "button" }));
});

When("I click the decision log row at {string}", async function (when: string) {
  const body = await table();
  const row = [...body.querySelectorAll("tbody tr[data-decision-id]")].find((tr) => cells(tr)[0] === when);
  assert.ok(row, `no decision log row at ${when}`);
  fireEvent.click(row);
});

async function expandedChain(): Promise<HTMLElement> {
  return waitFor(() => within(log()).getByTestId("decision-chain"));
}

Then("the expanded chain has {int} steps", async function (count: number) {
  assert.equal((await expandedChain()).querySelectorAll("li").length, count);
});

Then("the expanded chain step {string} is vetoed with why {string}", async function (filter: string, why: string) {
  const step = (await expandedChain()).querySelector(`li[data-filter="${filter}"]`);
  assert.ok(step, `no step for ${filter}`);
  assert.equal(step.getAttribute("data-vetoed"), "yes");
  assert.ok(step.classList.contains("vetoed"));
  assert.equal(step.querySelector(".why")?.textContent, why);
});

Then("the expanded chain step {string} is not vetoed", async function (filter: string) {
  const step = (await expandedChain()).querySelector(`li[data-filter="${filter}"]`);
  assert.ok(step, `no step for ${filter}`);
  assert.equal(step.getAttribute("data-vetoed"), "no");
  assert.equal(step.querySelector(".why"), null);
});

Given("the run parameter {string} is {string}", function (key: string, value: string) {
  runParameters = [{ key, value, source: "fixture/config.yaml" }];
});

When("the filter {string} vetoed with reason {string}", function (name: string, reason: string) {
  vetoed = { position: 0, filter_name: name, recommendation: "ABSTAIN", veto: 1, reason, pattern_name: null };
});

Then("the why line is {string} naming the parameter {string}", function (why: string, parameter: string) {
  assert.ok(vetoed);
  const lines = vetoWhy(vetoed, runParameters);
  assert.equal(lines.map((w) => w.text).join("; "), why);
  assert.equal(lines[0]?.parameter ?? "", parameter);
});

Given("the log rows:", function (rows: DataTable) {
  const parsed = rows.hashes().map((r, i) => ({
    id: i + 1, trade_id: r["trade"] === "" ? null : (r["trade"] ?? null), timestamp: `${r["time"]}:00+00:00`.replace(" ", "T"),
    final_decision: r["decision"] ?? "", vetoed_by: r["vetoed_by"] === "" ? null : (r["vetoed_by"] ?? null), p_hat: null,
    is_entry: 0, veto_filter: r["vetoed_by"] === "" ? null : (r["vetoed_by"] ?? null), veto_reason: r["reason"] === "" ? null : (r["reason"] ?? null),
  }));
  grouped = groupDecisions(parsed, [])
    .map((g) => `×${g.bars} ${g.parameter?.split(".")[1] ?? g.final_decision} @${g.first_time.slice(0, 16).replace("T", " ")}→${g.last_time.slice(11, 16)}`)
    .join("; ");
});

Then("the grouped log is {}", function (expected: string) {
  assert.equal(grouped, expected);
});
