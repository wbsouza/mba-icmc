import "../support/dom";
import { Given, Then, When } from "@cucumber/cucumber";
import { render, screen, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { describePattern, PATTERNS, TALIB_FUNCTIONS_URL, type PatternInfo } from "../../src/model/patterns";
import { PatternsPage } from "../../src/views/PatternsPage";

let card: PatternInfo | null = null;

Given("the pattern card for {string}", function (name: string) {
  card = describePattern(name);
  assert.ok(PATTERNS.some((p) => p.name === name), `${name} is not in the vocabulary`);
});

Then("its title is {string} and its direction is {word}", function (title: string, direction: string) {
  assert.ok(card);
  assert.equal(card.title, title);
  assert.equal(card.direction, direction);
});

Then("its description has {int} sentences", function (count: number) {
  assert.ok(card);
  const sentences = card.description.split(/(?<=\.)\s+/).filter((s) => s.trim() !== "");
  assert.equal(sentences.length, count, card.description);
});

Then("its reference URL is {string}", function (url: string) {
  assert.ok(card);
  assert.equal(card.reference_url, url);
  assert.ok(url.startsWith("https://"));
});

Then("its TA-Lib function is {word} linked to {string}", function (fn: string, url: string) {
  assert.ok(card);
  assert.equal(card.talib_function, fn);
  assert.equal(TALIB_FUNCTIONS_URL, url);
});

Then("the pattern vocabulary is {}", function (names: string) {
  assert.deepEqual(PATTERNS.map((p) => p.name), names.split(",").map((s) => s.trim()));
});

When("I open the Patterns page", function () {
  render(createElement(PatternsPage));
});

Then("it shows {int} pattern cards", function (count: number) {
  assert.equal(screen.getAllByTestId("pattern-card").length, count);
});

Then("the card {string} links to {string}", function (title: string, url: string) {
  const match = screen.getAllByTestId("pattern-card").find((c) => c.querySelector(".name")?.textContent === title);
  assert.ok(match, `no card ${title}`);
  const hrefs = within(match).getAllByRole("link").map((a) => a.getAttribute("href"));
  assert.ok(hrefs.includes(url), `${hrefs.join(", ")} lacks ${url}`);
});
