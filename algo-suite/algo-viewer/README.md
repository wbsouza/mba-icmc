# algo-viewer — browse backtest results in the browser

A static web app (Vite + React 18 + TypeScript, no backend) that opens the SQLite file
`algo-analyze results-db build` writes and lets a person navigate runs, compare equity
curves and click any trade to see **why the chain entered it** — the filters at the entry
bar in order (F1 trend, F2 RSI/MACD, F3 candlestick pattern with a plain-English
description, F4 news, activity ratio, F5/F6, F7 probability against its thresholds), the
±N candlestick bars around the entry with the entry, stop, targets, trail moves and exit
marked, the plan, the exit and the realized P/L. The database is read with
[sql.js](https://sql.js.org) (SQLite compiled to WASM, bundled into `dist/`; nothing is
fetched from a CDN at runtime).

## Build, open, load a database

```sh
# 1. the database (from algo-suite/; --bars-root enables the candlestick window)
uv run algo-analyze results-db build \
  --runs-root data/training/2026-09-28-broad-window-h4/data/runs \
  --runs-root data/training/2026-09-28-one-year-protocol/data/runs \
  --bars-root data/training/2026-09-28-broad-window-h4/data \
  --decisions entries --out results.sqlite

# 2. the app (needs Node 22 / npm 10; nothing installed globally)
make viewer            # = cd algo-viewer && npm ci && npm run build  -> algo-viewer/dist/
cp results.sqlite algo-viewer/dist/results.sqlite

# 3. open it: any static file server over dist/, e.g.
cd algo-viewer && npx vite preview   # then http://localhost:4173/
```

On load the page tries `./results.sqlite` next to `index.html`; when it is absent (or
the page is opened from `file://`, where browsers refuse `fetch`), a file picker asks
for a `.sqlite` built by `algo-analyze`. A file of another schema version is refused
with the message that says what to rebuild. `make viewer-dev` starts Vite's dev server
(put a database at `algo-viewer/public/results.sqlite` to have it load automatically).

Light theme by default; the **Dark** button in the top bar switches (remembered per
browser). Navigation is by URL hash (`#/runs`, `#/compare/<id,id>`, `#/run/<id>`,
`#/run/<id>/trade/<trade id>`), so a trade drawer can be bookmarked.

## Views

- **Runs** — every run with job, strategy, bar size, span, trades, return, max drawdown
  and win %; free-text filter (job/strategy/symbol/run id), bar-size filter, click any
  column header to sort; tick runs to compare, click a row to open it.
- **Compare** — the ticked runs' equity curves overlaid, each re-based so its first
  sample equals 10,000 (raw equity × 10,000 / first sample), plus a month-by-month table
  of returns side by side.
- **Run** — KPI cards, equity and drawdown charts, monthly returns, the decision funnel
  (every chain invocation by outcome and vetoing filter), run facts (model hash, run
  directory), parameters grouped by filter section with the config file that set each
  one, and the trades table.
- **Trade drawer** — opened from the trades table: "Why we entered" (the chain at the
  entry bar), the candlestick window, the plan (lots, stop and pips, targets, trail
  steps, spread), the exit (kind, time, price, trail moves) and the realized P/L.

Exit kinds are classified by the ingester (see `../algo-analyze/SPEC.md` §6.2): stop,
target, trailing stop, reversal, liquidation, unknown.

## Development

```sh
cd algo-viewer
npm ci
npm run lint     # eslint (typescript-eslint strict, type-checked) over src/ and tests/
npm test         # @cucumber/cucumber: tests/features/*.feature with TypeScript steps (jsdom)
npm run build    # tsc --noEmit, then vite build -> dist/
```

Every test is a Gherkin scenario in `tests/features/` (runs table filtering and sorting,
comparison re-basing and the monthly pivot, the trade drawer content, the SQLite loader)
with step definitions in `tests/steps/*.steps.ts`. The loader and drawer scenarios run
against `tests/fixtures/results.sqlite`, a database the Python ingester builds from the
synthetic run described in `tests/fixtures/fixture-run.json` — regenerate it with
`make viewer-fixture` (from `algo-suite/`) after a schema change. jsdom has no canvas,
so the chart components render a text fallback there; the scenarios assert content.

Layout: `src/db/` (sql.js loader, typed queries), `src/model/` (row types, re-basing,
pattern descriptions, the reason-text explanations), `src/views/` (Runs, Compare, Run,
TradeDrawer, DbPicker), `src/charts/` (lightweight-charts wrappers), `src/router.ts`.
