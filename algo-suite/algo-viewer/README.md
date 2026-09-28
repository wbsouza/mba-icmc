# algo-viewer — browse backtest results in the browser

A small TypeScript backend plus a React 18 front end. The backend (`server/`, Node 22,
no framework) opens the SQLite file `algo-analyze results-db build` writes with Node's
built-in `node:sqlite` (read-only) and answers JSON on `/api/...`; the front end
(`src/`, Vite + React + TypeScript) only ever calls those endpoints and plots the answers.
A person can navigate runs, compare equity curves and click any trade to see **why the
chain entered it** — the filters at the entry bar in order (F1 trend, F2 RSI/MACD, F3
candlestick pattern with its reference card, F4 news, activity ratio, F5/F6, F7
probability against its thresholds), the ±N candlestick bars around the entry with the
entry, stop, targets, trail moves and exit marked, the plan, the exit and the P/L.

## Build, run, open

```sh
# 1. the database (from algo-suite/; --bars-root enables the candlestick window)
uv run algo-analyze results-db build \
  --runs-root data/training/2026-09-28-broad-window-h4/data/runs \
  --runs-root data/training/2026-09-28-one-year-protocol/data/runs \
  --bars-root data/training/2026-09-28-broad-window-h4/data \
  --out results.sqlite

# 2. the app (Node 22 / npm 10; nothing installed globally)
make viewer            # = cd algo-viewer && npm ci && npm run build
                       #   -> algo-viewer/dist/ (page) + algo-viewer/dist-server/ (backend)

# 3. serve page + API from one origin and open http://127.0.0.1:8787/
make viewer-serve DB=results.sqlite
# = node dist-server/server/main.js --db results.sqlite --static dist --port 8787
```

`dist/` and `dist-server/` are self-contained (the compiled backend has no runtime
dependencies beyond Node itself), so the two directories plus a `results.sqlite` can be
copied anywhere and started with the same `node` command. The backend refuses a file
that is not a results database or has another schema version, with the message that
says what to rebuild. Flags: `--db` (required), `--static DIR` (omit for the API only),
`--port` (default 8787), `--host` (default 127.0.0.1).

Development: `make viewer-serve DB=...` for the backend and `make viewer-dev` for Vite's
dev server, which proxies `/api` to `http://127.0.0.1:8787` (override with
`ALGO_VIEWER_API`). `npm run serve -- --db results.sqlite` runs the backend from the
TypeScript sources through tsx.

Light theme by default; the **Dark** button switches (remembered per browser).
Navigation is by URL hash (`#/runs`, `#/compare/<id,id>`, `#/run/<id>`,
`#/run/<id>/trade/<trade id>`, `#/patterns`), so a trade drawer can be bookmarked; the
drawer's **Copy link** puts that address on the clipboard.

## API

All endpoints are `GET` and answer JSON (`server/api.ts`); unknown runs/trades answer
404 `{error}`, other methods 405.

| path | answer |
|---|---|
| `/api/health` | `{schema_version, runs}` |
| `/api/runs` | every run with `win_rate` (fraction of winning trades) |
| `/api/runs/:id` | one run |
| `/api/runs/:id/equity` · `/monthly` · `/parameters` · `/trades` · `/decision-summary` · `/open-positions` | the run's rows of that table (`open-positions`: what the statement's "Open Trades" table lists as still open at the end of the run) |
| `/api/runs/:id/trades/:tradeId` | the trade drawer's detail: trade, plan, entry decision with its filter rows, the events while the trade was open (repeat signals and vetoes carrying its id), trail moves, entry bars, parameters |
| `/api/runs/:id/decisions?mode=vetoes&page=1&size=200` | the decision log: one row per bar in `mode` (`vetoes`, `entries`, `all`), consecutive bars with the same outcome, vetoing filter and breached parameter collapsed into one group; `why` reads `parameter: observed vs limit` (needs a database built with `--decisions full`) |
| `/api/runs/:id/decisions/:decisionId` | one bar's chain: the decision, its filter rows and the run's parameters |
| `/api/patterns/:name/examples?limit=3` | the most recent closed trades whose entry decision carried that candlestick pattern (`run_id, trade_id, entry_time, direction, profit`; limit 1..50) |

## Views

Two equities are shown and named: **Realized equity** (trades table column and KPI: cash plus the net P/L of the trades closed so far, from the statement's balance) and **Final equity** (KPI, equity curve, month table: mark-to-market, open positions included). Their difference is the **Floating P/L** KPI, and the "Open positions at the end of the run" section lists the positions behind it (ticket, side, lots, open price, stop, targets, mark price, floating P/L). The database is schema version 2 (`algo-analyze results-db build` reads these from `statement.md`).

Vetoes are salmon wherever a chain evaluation is shown: the decision log rows on the run page, the "Events while open" rows in the trade drawer, and the vetoing step inside an expanded chain, each with a why line such as `risk_guard.daily_drawdown_limit: -0.074 < -0.05` (`src/model/veto.ts` maps each filter's recorded reason to the parameter that set the limit; unrecognised reasons are shown verbatim).


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
  entry bar; a detected candlestick pattern gets its card with direction, description,
  reference page and TA-Lib function), the candlestick window, the plan (lots, stop and
  pips, targets, trail steps, spread), the exit (kind, time, price, trail moves) and the
  realized P/L, and **Copy link**.
- **Patterns** — the reference page listing the six patterns F3 recognises
  (`src/model/patterns.ts`: title, direction, description, reference URL, TA-Lib
  function, and the schematic the app draws as an inline SVG — one rect per candle with
  the geometry the name implies), each card linking up to three real trades of the
  database whose entry carried the pattern ("Example from our runs"); citable from the
  thesis. The same card appears in the trade drawer.

Exit kinds are classified by the ingester (see `../algo-analyze/SPEC.md` §6.2): stop,
target, trailing stop, reversal, liquidation, unknown.

## Development

```sh
cd algo-viewer
npm ci
npm run lint     # eslint (typescript-eslint strict, type-checked) over src/, server/ and tests/
npm test         # @cucumber/cucumber: tests/features/*.feature with TypeScript steps
npm run build    # tsc --noEmit, vite build -> dist/, tsc (NodeNext) -> dist-server/
```

Every test is a Gherkin scenario in `tests/features/` — the backend API (every
endpoint, refusals, the CLI flags), the runs table filtering and sorting, comparison
re-basing and the monthly pivot, the trade drawer content, the pattern cards — with step
definitions in `tests/steps/*.steps.ts`. The scenarios start the real backend on a free
port over `tests/fixtures/results.sqlite`, a database the Python ingester builds from the
synthetic run described in `tests/fixtures/fixture-run.json` (regenerate it with
`make viewer-fixture` from `algo-suite/` after a schema change), and render the React
views under jsdom against it. jsdom has no canvas, so the chart components render a text
fallback there; the scenarios assert content.

Layout: `server/` (db binding, queries, API dispatcher, HTTP server, CLI), `src/api/`
(fetch client, async hook), `src/model/` (row types, re-basing, pattern cards, the
reason-text explanations), `src/views/`, `src/charts/` (lightweight-charts wrappers),
`src/router.ts`.
