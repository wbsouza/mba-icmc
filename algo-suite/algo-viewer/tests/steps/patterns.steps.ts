import "../support/dom";
import { Given, Then, When } from "@cucumber/cucumber";
import { render, screen, waitFor, within } from "@testing-library/react";
import assert from "node:assert/strict";
import { createElement } from "react";
import { describePattern, PATTERNS, TALIB_FUNCTIONS_URL, type PatternInfo } from "../../src/model/patterns";
import { PatternsPage } from "../../src/views/PatternsPage";
import { PatternCard } from "../../src/views/PatternCard";
import { apiClient } from "../support/server";

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

When("I render the pattern card for {string}", function (name: string) {
  card = describePattern(name);
  render(createElement(PatternCard, { pattern: card }));
});

Then("its schematic is an svg with {int} candle rects, {int} up and {int} down", function (rects: number, up: number, down: number) {
  const svg = screen.getByRole("img");
  assert.equal(svg.tagName.toLowerCase(), "svg");
  assert.equal(svg.querySelectorAll("rect").length, rects);
  assert.equal(svg.querySelectorAll("g.candle.up").length, up);
  assert.equal(svg.querySelectorAll("g.candle.down").length, down);
});

Then("its caption reads {string}", function (caption: string) {
  assert.equal(screen.getByText(caption).tagName.toLowerCase(), "figcaption");
});

function bodyRange(c: { open: number; close: number }): [number, number] {
  return [Math.min(c.open, c.close), Math.max(c.open, c.close)];
}

Then("its schematic satisfies {string}", function (rule: string) {
  assert.ok(card);
  const [a, b, c] = card.schematic;
  assert.ok(a);
  const [aLow, aHigh] = bodyRange(a);
  const aBody = aHigh - aLow;
  switch (rule) {
    case "the second body covers the first body": {
      assert.ok(b);
      const [bLow, bHigh] = bodyRange(b);
      assert.ok(bLow < aLow && bHigh > aHigh, `${bLow}..${bHigh} does not cover ${aLow}..${aHigh}`);
      break;
    }
    case "the lower shadow is at least twice the body":
      assert.ok(aLow - a.low >= 2 * aBody, `shadow ${aLow - a.low} vs body ${aBody}`);
      break;
    case "the upper shadow is at least twice the body":
      assert.ok(a.high - aHigh >= 2 * aBody, `shadow ${a.high - aHigh} vs body ${aBody}`);
      break;
    case "the middle body gaps below and the third closes above the first body's midpoint": {
      assert.ok(b && c);
      assert.ok(bodyRange(b)[1] < aLow, "middle body does not gap below");
      assert.ok(c.close > (aLow + aHigh) / 2 && c.close > c.open, "third candle does not close above the midpoint");
      break;
    }
    case "the middle body gaps above and the third closes below the first body's midpoint": {
      assert.ok(b && c);
      assert.ok(bodyRange(b)[0] > aHigh, "middle body does not gap above");
      assert.ok(c.close < (aLow + aHigh) / 2 && c.close < c.open, "third candle does not close below the midpoint");
      break;
    }
    default:
      throw new Error(`unknown rule ${rule}`);
  }
});

When("I open the Patterns page against the backend", async function () {
  render(createElement(PatternsPage, { api: apiClient() }));
  await waitFor(() => assert.equal(screen.getAllByTestId("pattern-examples").length, PATTERNS.length));
});

function cardByTitle(title: string): HTMLElement {
  const match = screen.getAllByTestId("pattern-card").find((c) => c.querySelector(".name")?.textContent === title);
  assert.ok(match, `no card ${title}`);
  return match;
}

Then("the card {string} offers {int} example link to {string}", function (title: string, count: number, href: string) {
  const links = within(within(cardByTitle(title)).getByTestId("pattern-examples")).getAllByRole("link");
  assert.equal(links.length, count);
  assert.equal(links[0]?.getAttribute("href"), href);
});

Then("the card {string} says {string}", function (title: string, text: string) {
  assert.ok(within(cardByTitle(title)).getByTestId("pattern-examples").textContent?.includes(text));
});
