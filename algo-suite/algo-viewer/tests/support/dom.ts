/**
 * jsdom as the DOM for every scenario. This module is imported first (cucumber.js
 * `import` order and each step file's first import) so react-dom sees a window when it
 * is evaluated. Canvas is not implemented by jsdom, so the chart components render their
 * text fallback — the scenarios assert content, not pixels.
 */

import { JSDOM, VirtualConsole } from "jsdom";

const virtualConsole = new VirtualConsole();
virtualConsole.on("error", () => undefined); // silence jsdom's "not implemented" notes
const dom = new JSDOM("<!doctype html><html><body><div id=\"root\"></div></body></html>", {
  url: "http://localhost/",
  pretendToBeVisual: true,
  virtualConsole,
});

const globals: Record<string, unknown> = {
  window: dom.window,
  document: dom.window.document,
  navigator: dom.window.navigator,
  HTMLElement: dom.window.HTMLElement,
  HTMLInputElement: dom.window.HTMLInputElement,
  Element: dom.window.Element,
  Node: dom.window.Node,
  Event: dom.window.Event,
  KeyboardEvent: dom.window.KeyboardEvent,
  MouseEvent: dom.window.MouseEvent,
  MutationObserver: dom.window.MutationObserver,
  getComputedStyle: dom.window.getComputedStyle.bind(dom.window),
  requestAnimationFrame: (cb: FrameRequestCallback) => setTimeout(() => cb(Date.now()), 0),
  cancelAnimationFrame: (id: number) => clearTimeout(id),
  IS_REACT_ACT_ENVIRONMENT: true,
  ResizeObserver: class {
    observe() { /* jsdom has no layout */ }
    unobserve() { /* jsdom has no layout */ }
    disconnect() { /* jsdom has no layout */ }
  },
};
// Node 22 defines some of these (navigator) as getters on globalThis: redefine, don't assign.
for (const [name, value] of Object.entries(globals)) {
  Object.defineProperty(globalThis, name, { value, configurable: true, writable: true });
}
