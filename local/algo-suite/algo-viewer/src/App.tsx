import { useCallback, useEffect, useState } from "react";
import { ApiClient } from "./api/client";
import { Pending, useAsync } from "./api/useAsync";
import type { RunRow, TradeDetail } from "./model/types";
import { parseRoute, routeHash, type Route } from "./router";
import { applyTheme, initialTheme, type Theme } from "./theme";
import { RunsTable } from "./views/RunsTable";
import { CompareView } from "./views/CompareView";
import { RunView } from "./views/RunView";
import { TradeDrawer } from "./views/TradeDrawer";
import { PatternsPage } from "./views/PatternsPage";

interface Props {
  /** The backend; defaults to the page's own origin. */
  api?: ApiClient;
  initialHash?: string;
}

const START_HINT = "start the backend: node dist-server/server/main.js --db results.sqlite --static dist";

export function App({ api: given, initialHash }: Props) {
  const [api] = useState(() => given ?? new ApiClient());
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const [route, setRoute] = useState<Route>(() => parseRoute(initialHash ?? window.location.hash));
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const health = useAsync(() => api.health(), [api]);
  const runsState = useAsync(() => api.runs(), [api, health.data]);
  const runs = runsState.data ?? [];

  useEffect(() => applyTheme(theme), [theme]);
  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((next: Route) => {
    window.location.hash = routeHash(next);
    setRoute(next);
  }, []);

  const toggle = (runId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  const nav = (
    <header className="topbar">
      <h1>algo-viewer</h1>
      <nav>
        <a href="#/runs" className={route.view === "runs" ? "active" : ""} onClick={(e) => { e.preventDefault(); navigate({ view: "runs" }); }}>Runs</a>
        <a href="#/compare" className={route.view === "compare" ? "active" : ""} onClick={(e) => { e.preventDefault(); navigate({ view: "compare", runIds: [...selected] }); }}>Compare ({selected.size})</a>
        {route.view === "run" ? <a href={routeHash(route)} className="active">Run</a> : null}
        <a href="#/patterns" className={route.view === "patterns" ? "active" : ""} onClick={(e) => { e.preventDefault(); navigate({ view: "patterns" }); }}>Patterns</a>
      </nav>
      <span className="spacer" />
      <span className="db-name">{health.data ? `${health.data.runs} runs · schema v${health.data.schema_version}` : ""}</span>
      <button aria-label="Toggle dark mode" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "Light" : "Dark"}</button>
    </header>
  );

  if (route.view === "patterns") {
    return (
      <>
        {nav}
        <main><PatternsPage api={api} /></main>
      </>
    );
  }

  if (health.data === null) {
    return (
      <>
        {nav}
        <main>
          {health.loading ? <Pending state={health} label="backend" /> : (
            <p className="error">Backend not reachable: {health.error}. {START_HINT}</p>
          )}
        </main>
      </>
    );
  }

  let body;
  if (route.view === "runs") {
    body = (
      <RunsTable runs={runs} selected={selected} onToggle={toggle}
        onOpen={(runId) => navigate({ view: "run", runId, tradeId: null })}
        onCompare={() => navigate({ view: "compare", runIds: [...selected] })} />
    );
  } else if (route.view === "compare") {
    const ids = route.runIds.length > 0 ? route.runIds : [...selected];
    const chosen = ids.map((id) => runs.find((r) => r.run_id === id)).filter((r): r is RunRow => r !== undefined);
    body = <CompareView api={api} runs={chosen} dark={theme === "dark"} onOpen={(runId) => navigate({ view: "run", runId, tradeId: null })} />;
  } else {
    const run = runs.find((r) => r.run_id === route.runId);
    if (run === undefined) {
      body = runsState.loading ? <Pending state={runsState} label="runs" /> : <p className="error">No run {route.runId} in this database.</p>;
    } else {
      body = (
        <>
          <RunView api={api} run={run} dark={theme === "dark"} onSelectTrade={(tradeId) => navigate({ view: "run", runId: run.run_id, tradeId })} />
          {route.tradeId === null ? null : (
            <TradeDrawerLoader api={api} runId={run.run_id} tradeId={route.tradeId} dark={theme === "dark"}
              onClose={() => navigate({ view: "run", runId: run.run_id, tradeId: null })} />
          )}
        </>
      );
    }
  }
  return (
    <>
      {nav}
      <main>{runsState.error === null ? null : <p className="error">{runsState.error}</p>}{body}</main>
    </>
  );
}

function TradeDrawerLoader({ api, runId, tradeId, dark, onClose }: { api: ApiClient; runId: string; tradeId: string; dark: boolean; onClose: () => void }) {
  const state = useAsync<TradeDetail>(() => api.tradeDetail(runId, tradeId), [api, runId, tradeId]);
  if (state.data === null) {
    return (
      <>
        <div className="drawer-backdrop" onClick={onClose} />
        <aside className="drawer" role="dialog" aria-label={`Trade ${tradeId}`}><Pending state={state} label={`trade ${tradeId}`} /></aside>
      </>
    );
  }
  return <TradeDrawer detail={state.data} dark={dark} onClose={onClose} api={api} />;
}
