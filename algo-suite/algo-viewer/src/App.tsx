import { useCallback, useEffect, useMemo, useState } from "react";
import type { Database } from "sql.js";
import { fetchBundledDatabase, openDatabase, type LocateFile } from "./db/loader";
import { getRun, listRuns, tradeDetail } from "./db/queries";
import type { RunRow } from "./model/types";
import { parseRoute, routeHash, type Route } from "./router";
import { applyTheme, initialTheme, type Theme } from "./theme";
import { DbPicker } from "./views/DbPicker";
import { RunsTable } from "./views/RunsTable";
import { CompareView } from "./views/CompareView";
import { RunView } from "./views/RunView";
import { TradeDrawer } from "./views/TradeDrawer";

interface Props {
  locateFile?: LocateFile;
  /** Bytes to open immediately (tests); otherwise ./results.sqlite is tried, then the picker. */
  initialBytes?: Uint8Array;
  initialHash?: string;
}

export function App({ locateFile, initialBytes, initialHash }: Props) {
  const [db, setDb] = useState<Database | null>(null);
  const [dbName, setDbName] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const [route, setRoute] = useState<Route>(() => parseRoute(initialHash ?? window.location.hash));
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => applyTheme(theme), [theme]);
  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const open = useCallback(async (bytes: Uint8Array, name: string) => {
    setBusy(true);
    setError(null);
    try {
      const opened = await openDatabase(bytes, locateFile);
      setDb(opened);
      setDbName(name);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [locateFile]);

  useEffect(() => {
    if (initialBytes) {
      void open(initialBytes, "results.sqlite");
      return;
    }
    void (async () => {
      setBusy(true);
      const bytes = await fetchBundledDatabase();
      setBusy(false);
      if (bytes) await open(bytes, "results.sqlite");
    })();
  }, [initialBytes, open]);

  const navigate = useCallback((next: Route) => {
    window.location.hash = routeHash(next);
    setRoute(next);
  }, []);

  const runs = useMemo(() => (db ? listRuns(db) : []), [db]);
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
      </nav>
      <span className="spacer" />
      <span className="db-name">{dbName}</span>
      <button aria-label="Toggle dark mode" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "Light" : "Dark"}</button>
    </header>
  );

  if (db === null) {
    return (
      <>
        {nav}
        <main>
          <DbPicker busy={busy} error={error} onFile={(file) => { void file.arrayBuffer().then((buffer) => open(new Uint8Array(buffer), file.name)); }} />
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
    body = <CompareView db={db} runs={chosen} dark={theme === "dark"} onOpen={(runId) => navigate({ view: "run", runId, tradeId: null })} />;
  } else {
    const run = getRun(db, route.runId);
    if (run === null) {
      body = <p className="error">No run {route.runId} in this database.</p>;
    } else {
      const detail = route.tradeId === null ? null : tradeDetail(db, route.runId, route.tradeId);
      body = (
        <>
          <RunView db={db} run={run} dark={theme === "dark"} onSelectTrade={(tradeId) => navigate({ view: "run", runId: run.run_id, tradeId })} />
          {detail ? <TradeDrawer detail={detail} dark={theme === "dark"} onClose={() => navigate({ view: "run", runId: run.run_id, tradeId: null })} /> : null}
        </>
      );
    }
  }
  return (
    <>
      {nav}
      <main>{error ? <p className="error">{error}</p> : null}{body}</main>
    </>
  );
}
